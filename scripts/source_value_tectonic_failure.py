"""Screen the hydrothermal PyLith case with a stated spreading azimuth."""

from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

import h5py
import numpy as np
import reconstruct_center_pressure as center
import source_value_bpr_failure as bpr
import source_value_historical_cycle_failure as historical
import source_value_maxwell_cases as maxwell
import source_value_ooi_failure as ooi

from axialstress.deployment_pressure import DepthObservation, fit_deployment_relative_pressure
from axialstress.maxwell_pressure_inversion import ramp_response_operator
from axialstress.paper_bpr import file_sha256

ROOT = Path(__file__).resolve().parents[1]
CASE = "hydrothermal_maxwell"
RATE_M_PER_YEAR = 0.06
MODEL_WIDTH_M = 50_000.0
YEAR_S = 365.25 * 86_400.0
PROJECT_SPREADING_DIRECTION = np.asarray((np.sqrt(3.0) / 2.0, 0.5))
PROJECTED_SPREADING_WIDTH_M = MODEL_WIDTH_M * np.abs(PROJECT_SPREADING_DIRECTION).sum()


def _boundary_database(path: Path, corners_m: np.ndarray) -> None:
    """Write affine N60E displacement rate on one outer face."""
    if corners_m.shape != (4, 3):
        raise ValueError("one rectangular face requires four corners")
    rate_m_per_s = (
        RATE_M_PER_YEAR / (YEAR_S * PROJECTED_SPREADING_WIDTH_M)
        * (corners_m[:, :2] @ PROJECT_SPREADING_DIRECTION)[:, None]
        * PROJECT_SPREADING_DIRECTION[None, :]
    )
    lines = [
        "#SPATIAL.ascii 1",
        "SimpleDB {",
        "  num-values = 7",
        "  value-names = initial_amplitude_x initial_amplitude_y initial_amplitude_z "
        "rate_start_time rate_amplitude_x rate_amplitude_y rate_amplitude_z",
        "  value-units = m m m s m/s m/s m/s",
        "  num-locs = 4",
        "  data-dim = 2",
        "  space-dim = 3",
        "  cs-data = cartesian {",
        "    to-meters = 1.0",
        "    space-dim = 3",
        "  }",
        "}",
    ]
    for xyz_m, rate_xy in zip(corners_m, rate_m_per_s, strict=True):
        lines.append(
            " ".join(
                f"{value:.12g}"
                for value in (*xyz_m, 0.0, 0.0, 0.0, 0.0, *rate_xy, 0.0)
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _apply_extension(run_dir: Path, reference_path: Path) -> None:
    """Prescribe 60 mm/year full N60E strain on four side faces."""
    with h5py.File(reference_path, "r") as material:
        xyz = np.asarray(material["geometry/vertices"], dtype=float)
    low, high = xyz.min(axis=0), xyz.max(axis=0)
    if not np.allclose(high[:2] - low[:2], MODEL_WIDTH_M, atol=1.0):
        raise ValueError("tectonic rate needs the documented 50 km horizontal box")
    config_path = run_dir / "step06.cfg"
    config = config_path.read_text(encoding="utf-8")
    for axis, axis_name in enumerate(("x", "y")):
        other = 1 - axis
        for side, value in (("neg", low[axis]), ("pos", high[axis])):
            corners = []
            for other_value in (low[other], high[other]):
                for z_m in (low[2], high[2]):
                    point = np.zeros(3)
                    point[axis], point[other], point[2] = value, other_value, z_m
                    corners.append(point)
            db_name = f"tectonic-{axis_name}-{side}.spatialdb"
            _boundary_database(run_dir / db_name, np.asarray(corners))
            header = f"[pylithapp.problem.bc.bc_{axis_name}_{side}]"
            start = config.index(header)
            end = config.find("\n[", start + 1)
            if end < 0:
                end = len(config)
            section = config[start:end]
            section, dof_count = re.subn(
                r"(?m)^constrained_dof = \[[^\]]+\]$",
                "constrained_dof = [0, 1]",
                section,
            )
            section, file_count = re.subn(
                r"(?m)^db_auxiliary_field.iohandler.filename = bc_zero.spatialdb$",
                f"db_auxiliary_field.iohandler.filename = {db_name}",
                section,
            )
            if dof_count != 1 or file_count != 1:
                raise ValueError(f"unexpected PyLith side condition: {header}")
            section += "\nuse_rate = True\ndb_auxiliary_field.query_type = linear\n"
            config = config[:start] + section + config[end:]
    config_path.write_text(config, encoding="utf-8")


def _inputs(cycle: str, fit_dir: Path) -> tuple[datetime, datetime | None, Path, Path]:
    """Return cycle start, observed event, summary, and pressure series."""
    if cycle == "1998-2011":
        summary_path = fit_dir / CASE / "summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        start = datetime.fromisoformat(summary["cycle_start_utc"])
        event = datetime.fromisoformat(summary["observed_eruption_utc"])
        series_path = fit_dir / CASE / "pressure_failure.csv"
    elif cycle == "2011-2015":
        summary_path = fit_dir / "summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        start = datetime.fromisoformat(summary["cycle_start_utc"])
        event = datetime.fromisoformat(summary["eruption_utc"])
        series_path = fit_dir / summary["cases"][CASE]["pressure_failure_csv"]
    else:
        summary_path = fit_dir / CASE / "summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        start = datetime.fromisoformat(summary["observation_baseline_utc"] + "T00:00:00+00:00")
        event = None
        series_path = fit_dir / CASE / "pressure_failure.csv"
    if summary.get("paper_output_data_used") is not False:
        raise ValueError("pressure fit provenance is incomplete")
    if cycle != "2011-2015" and file_sha256(series_path) != summary["series_sha256"]:
        raise ValueError("pressure series changed")
    return start, event, summary_path, series_path


def _refit_pressure(
    cycle: str,
    fit_dir: Path,
    source_dir: Path,
    tectonic_surface_path: Path,
    zero_surface_path: Path,
    elapsed_s: np.ndarray,
) -> tuple[np.ndarray, float, dict]:
    """Remove tectonic uplift from BPR depths before fitting cavity pressure."""
    if cycle == "1998-2011":
        unit_path = fit_dir / CASE / "unit_ramp/output/maxwell-surface.h5"
        dates, observations, _ = historical._observations(historical.OBS)
        tectonic_uplift = historical._surface_responses(
            tectonic_surface_path, elapsed_s[1:]
        )
        unit_uplift = historical._surface_responses(unit_path, elapsed_s[1:])
        zero_uplift = historical._surface_responses(zero_surface_path, elapsed_s[1:])
        baseline_slug = historical.SLUGS[0]
        depth_sign = 1.0
    elif cycle == "2011-2015":
        unit_path = source_dir / "runs" / CASE / "unit_ramp/output/maxwell-surface.h5"
        dates = center._grid(7)
        observations, _, _ = center._load_observations(
            ROOT / "data/processed/paper_center_bpr", dates
        )
        tectonic_uplift = bpr._surface_responses(tectonic_surface_path, elapsed_s[1:])
        unit_uplift = bpr._surface_responses(unit_path, elapsed_s[1:])
        zero_uplift = bpr._surface_responses(zero_surface_path, elapsed_s[1:])
        baseline_slug = center.SOURCE_SLUGS[0]
        depth_sign = 1.0
    else:
        unit_path = fit_dir / CASE / "unit_ramp/output/maxwell-surface.h5"
        dates, observations, _ = ooi._observations(ooi.OBS)
        tectonic_uplift = {
            "ooi_mj03f": ooi._surface_uplift(tectonic_surface_path, elapsed_s[1:])
        }
        unit_uplift = {"ooi_mj03f": ooi._surface_uplift(unit_path, elapsed_s[1:])}
        zero_uplift = {"ooi_mj03f": ooi._surface_uplift(zero_surface_path, elapsed_s[1:])}
        baseline_slug = "ooi_mj03f"
        depth_sign = -1.0
    if len(dates) != len(elapsed_s):
        raise ValueError("tectonic response and BPR grid lengths differ")
    operators = {}
    for slug, response in unit_uplift.items():
        operator = np.zeros((len(dates), len(dates)))
        operator[1:, 1:] = ramp_response_operator(response - zero_uplift[slug])
        operators[slug] = operator
    adjusted = []
    for record in observations:
        index = record.time_index
        tectonic_value = 0.0 if index == 0 else float(tectonic_uplift[record.deployment][index - 1])
        adjusted.append(
            DepthObservation(
                record.deployment,
                index,
                record.depth_m + depth_sign * tectonic_value,
            )
        )
    fit = fit_deployment_relative_pressure(
        operators[baseline_slug],
        adjusted,
        curvature_weight=1.0,
        deployment_response=operators,
    )
    return fit.pressure_mpa, fit.rmse_m, {
        "selected_observations": len(observations),
        "unit_surface_sha256": file_sha256(unit_path),
        "tectonic_only_surface_sha256": file_sha256(tectonic_surface_path),
        "zero_pressure_surface_sha256": file_sha256(zero_surface_path),
        "fit_design_rank": fit.design_rank,
    }


def main() -> None:
    """Run one bounded tectonic plus hydrothermal PyLith stress history."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cycle", choices=("1998-2011", "2011-2015", "post-2015"), required=True)
    parser.add_argument("--fit-dir", type=Path)
    parser.add_argument("--source-dir", type=Path)
    parser.add_argument("--basis-dir", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    suffix = args.cycle.replace("-", "_")
    source_dir = (
        args.source_dir or ROOT / "data/processed/source_value_bpr_failure_2011_2015"
    ).resolve()
    if args.cycle == "post-2015":
        default_fit = ROOT / "data/processed/source_value_ooi_failure_2015_present"
    else:
        default_fit = ROOT / f"data/processed/source_value_bpr_failure_{suffix}"
    fit_dir = (args.fit_dir or default_fit).resolve()
    basis_dir = (args.basis_dir or ROOT / "data/processed/refined_elastic_basis_400m").resolve()
    output_dir = (
        args.output_dir or ROOT / f"data/processed/source_value_tectonic_{suffix}"
    ).resolve()
    source_path = source_dir / "summary.json"
    source = json.loads(source_path.read_text(encoding="utf-8"))
    mesh_path = basis_dir / "axial_ellipsoid.msh"
    reference_path = basis_dir / "fixed-base-equilibrium-material.h5"
    material_path = source_dir / "materials" / f"{CASE}.spatialdb"
    if (
        source.get("paper_output_data_used") is not False
        or file_sha256(mesh_path) != source["mesh_sha256"]
        or file_sha256(reference_path) != source["equilibrium_sha256"]
        or file_sha256(material_path) != source["cases"][CASE]["material_sha256"]
    ):
        raise ValueError("source-value model changed")
    start, event, fit_path, series_path = _inputs(args.cycle, fit_dir)
    fit_summary = json.loads(fit_path.read_text(encoding="utf-8"))
    if (
        "source_model_summary_sha256" in fit_summary
        and fit_summary["source_model_summary_sha256"] != file_sha256(source_path)
    ):
        raise ValueError("hydrothermal pressure fit uses a different source model")
    with series_path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    dates = []
    for row in rows:
        stamp = datetime.fromisoformat(row["time_utc"])
        dates.append(stamp if stamp.tzinfo is not None else stamp.replace(tzinfo=UTC))
    if not rows or (dates[0] - start).total_seconds() != 7.0 * 86_400.0:
        raise ValueError("pressure series does not begin at the first weekly state")
    pressure = [0.0, *(float(row["pressure_change_mpa"]) for row in rows)]
    weekly_elapsed_s = np.asarray(
        [(day - start).total_seconds() for day in (start, *dates)]
    )
    zero_dir = output_dir / "zero_pressure"
    maxwell._write_run(
        zero_dir,
        mesh_path,
        material_path,
        elapsed_seconds=weekly_elapsed_s,
        pressure_mpa=np.zeros(len(weekly_elapsed_s)),
        time_step_s=7.0 * 86_400.0,
    )
    maxwell._run_pylith(zero_dir)
    unit_dir = output_dir / "tectonic_only"
    maxwell._write_run(
        unit_dir,
        mesh_path,
        material_path,
        elapsed_seconds=weekly_elapsed_s,
        pressure_mpa=np.zeros(len(weekly_elapsed_s)),
        time_step_s=7.0 * 86_400.0,
    )
    _apply_extension(unit_dir, reference_path)
    maxwell._run_pylith(unit_dir)
    pressure_fit, fit_rmse_m, fit_provenance = _refit_pressure(
        args.cycle,
        fit_dir,
        source_dir,
        unit_dir / "output/maxwell-surface.h5",
        zero_dir / "output/maxwell-surface.h5",
        weekly_elapsed_s,
    )
    pressure = list(map(float, pressure_fit))
    if event is not None:
        if event <= dates[-1]:
            raise ValueError("eruption date must follow fitted grid")
        dates.append(event)
        pressure.append(pressure[-1])
    elapsed_s = np.asarray([(day - start).total_seconds() for day in (start, *dates)])
    run_dir = output_dir / "tectonic_hydrothermal"
    maxwell._write_run(
        run_dir,
        mesh_path,
        material_path,
        elapsed_seconds=elapsed_s,
        pressure_mpa=np.asarray(pressure),
        time_step_s=7.0 * 86_400.0,
    )
    _apply_extension(run_dir, reference_path)
    maxwell._run_pylith(run_dir)
    stress_path = run_dir / "output/maxwell-material.h5"
    times_s, failure = bpr._failure_summary(stress_path, reference_path)
    if (
        times_s.shape != elapsed_s[1:].shape
        or not np.isclose(times_s[0], elapsed_s[1], atol=0.01)
        or not np.isclose(times_s[-1], elapsed_s[-1], atol=0.01)
        or np.any(np.diff(times_s) <= 0.0)
    ):
        raise ValueError("tectonic PyLith stress does not span the fitted cycle")
    saved_dates = [start + timedelta(seconds=round(float(value))) for value in times_s]
    saved_pressures = np.interp(times_s, elapsed_s, pressure)
    off_grid = int(np.count_nonzero(np.abs(times_s - elapsed_s[1:]) > 0.01))
    output_dir.mkdir(parents=True, exist_ok=True)
    series_output = output_dir / "pressure_failure.csv"
    with series_output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(
            ("time_utc", "pressure_change_mpa", "maximum_cavity_principal_stress_pa",
             "connected_shear_path", "joint_failure_zero_tensile_strength")
        )
        for day, pressure_mpa, record in zip(saved_dates, saved_pressures, failure, strict=True):
            principal = float(record["maximum_cavity_principal_stress_pa"])
            path = bool(record["cavity_to_surface_shear_path_found"])
            writer.writerow(
                (day.isoformat(), pressure_mpa, principal, path, principal > 0 and path)
            )
    first = next(
        (i for i, record in enumerate(failure)
         if record["maximum_cavity_principal_stress_pa"] > 0
         and record["cavity_to_surface_shear_path_found"]),
        None,
    )
    result = {
        "method": "hydrothermal pressure-fit sensitivity with affine N60E extension",
        "paper_output_data_used": False,
        "cycle": args.cycle,
        "first_sampled_joint_failure_utc": (
            saved_dates[first].isoformat() if first is not None else None
        ),
        "first_sampled_joint_failure_pressure_mpa": (
            float(saved_pressures[first]) if first is not None else None
        ),
        "first_joint_path_cell_indices": (
            list(map(int, failure[first]["cavity_to_surface_path_cell_indices"]))
            if first is not None else []
        ),
        "last_utc": saved_dates[-1].isoformat(),
        "last_pressure_mpa": pressure[-1],
        "last_cavity_principal_stress_pa": failure[-1]["maximum_cavity_principal_stress_pa"],
        "full_spreading_rate_mm_per_year": 60.0,
        "project_spreading_azimuth_deg_clockwise_from_north": 60.0,
        "horizontal_model_width_m": MODEL_WIDTH_M,
        "projected_spreading_width_m": PROJECTED_SPREADING_WIDTH_M,
        "off_weekly_grid_output_states": off_grid,
        "pressure_fit_refitted_for_tectonic_uplift": True,
        "fit_rmse_m": fit_rmse_m,
        "fit_provenance": fit_provenance,
        "held_pressure_to_event_days": (
            (event - dates[-2]).total_seconds() / 86_400.0 if event else None
        ),
        "source_summary_sha256": file_sha256(source_path),
        "fit_summary_sha256": file_sha256(fit_path),
        "fit_series_sha256": file_sha256(series_path),
        "mesh_sha256": file_sha256(mesh_path),
        "material_sha256": file_sha256(material_path),
        "gravity_reference_sha256": file_sha256(reference_path),
        "stress_sha256": file_sha256(stress_path),
        "series_sha256": file_sha256(series_output),
        "limitations": (
            "The 60 mm/year full rate follows the paper main text. Supplement Table S1 "
            "instead lists -20 to +20 mm/year. A linear boundary strain represents "
            "extension along N60E in this PyLith box. N60E is perpendicular to "
            "the model reservoir axis; the paper does not tabulate a local "
            "ridge-normal azimuth. The BPR pressure history is refitted "
            "after subtracting modeled tectonic uplift."
        ),
    }
    (output_dir / "summary.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(args.cycle, result["first_sampled_joint_failure_utc"], result["last_utc"])


if __name__ == "__main__":
    main()
