"""Fit post-2015 OOI Center uplift to PyLith rheologies and screen failure."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import date, timedelta
from pathlib import Path

import h5py
import numpy as np
import source_value_bpr_failure as bpr
import source_value_maxwell_cases as maxwell

from axialstress.deployment_pressure import DepthObservation, fit_deployment_relative_pressure
from axialstress.maxwell_pressure_inversion import ramp_response_operator
from axialstress.paper_bpr import file_sha256
from axialstress.surface_interpolation import interpolate_triangular_surface

ROOT = Path(__file__).resolve().parents[1]
OBS = ROOT / "data" / "processed" / "ooi_center_daily"
SOURCE = ROOT / "data" / "processed" / "source_value_bpr_failure_2011_2015"
OUTPUT = ROOT / "data" / "processed" / "source_value_ooi_failure_2015_present"
BASIS = ROOT / "data" / "processed" / "refined_elastic_basis_400m"
SITE = (0.0, 0.0)  # OOI MJ03F position is the documented model origin.


def _surface_uplift(path: Path, expected_times_s: np.ndarray) -> np.ndarray:
    """Read the actual PyLith displacement at OOI MJ03F (m)."""
    with h5py.File(path, "r") as surface:
        times_s = np.asarray(surface["time"], dtype=float).reshape(-1)
        vertices = np.asarray(surface["geometry/vertices"], dtype=float)
        triangles = np.asarray(surface["viz/topology/cells"], dtype=np.int64)
        displacement = np.asarray(surface["vertex_fields/displacement"], dtype=float)
    if times_s.shape != expected_times_s.shape or not np.allclose(
        times_s, expected_times_s, rtol=0.0, atol=0.01
    ):
        raise ValueError("PyLith surface output times differ from OOI fit grid")
    return np.asarray(
        [
            interpolate_triangular_surface(vertices, triangles, field, SITE)[2]
            for field in displacement
        ]
    )


def _observations(
    obs_dir: Path, step_days: int = 7,
) -> tuple[list[date], list[DepthObservation], dict]:
    """Select observed daily depths at regular knots after the baseline."""
    summary_path = obs_dir / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    series_path = obs_dir / "center_relative_uplift.csv"
    if summary.get("paper_model_output_used") is not False or (
        file_sha256(series_path) != summary["series_sha256"]
    ):
        raise ValueError("OOI observational provenance is incomplete")
    start = date.fromisoformat(summary["baseline_date_utc"])
    end = date.fromisoformat(summary["last_observed_date_utc"])
    grid = [
        start + timedelta(days=step_days * i)
        for i in range((end - start).days // step_days + 1)
    ]
    index = {day: i for i, day in enumerate(grid)}
    records = []
    with series_path.open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            day = date.fromisoformat(row["time_utc"])
            if day in index:
                records.append(
                    DepthObservation("ooi_mj03f", index[day], -float(row["daily_depth_m"]))
                )
    if len(records) < 50 or records[0].time_index != 0:
        raise ValueError("OOI observation coverage does not support the selected grid")
    return grid, records, summary


def main() -> None:
    """Run bounded source-value Maxwell histories driven by OOI daily depth."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observation-dir", type=Path, default=OBS)
    parser.add_argument("--source-dir", type=Path, default=SOURCE)
    parser.add_argument("--basis-dir", type=Path, default=BASIS)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    parser.add_argument(
        "--case", choices=("constant_maxwell", "thermal_maxwell", "hydrothermal_maxwell")
    )
    parser.add_argument("--step-days", type=int, choices=(7, 28), default=7)
    args = parser.parse_args()
    obs_dir = args.observation_dir.resolve()
    source_dir = args.source_dir.resolve()
    basis_dir = args.basis_dir.resolve()
    out_dir = args.output_dir.resolve()
    source_path = source_dir / "summary.json"
    source = json.loads(source_path.read_text(encoding="utf-8"))
    if source.get("paper_output_data_used") is not False:
        raise ValueError("source-value model provenance is incomplete")
    grid, observations, obs_summary = _observations(obs_dir, args.step_days)
    elapsed_s = np.arange(len(grid), dtype=float) * args.step_days * maxwell.SECONDS_PER_DAY
    equilibrium = basis_dir / "fixed-base-equilibrium-material.h5"
    if file_sha256(equilibrium) != source["equilibrium_sha256"]:
        raise ValueError("gravity reference changed")
    mesh = basis_dir / "axial_ellipsoid.msh"
    if file_sha256(mesh) != source["mesh_sha256"]:
        raise ValueError("source-value mesh changed")
    selected_cases = (args.case,) if args.case else tuple(source["cases"])
    out_dir.mkdir(parents=True, exist_ok=True)
    for case in selected_cases:
        material = source_dir / "materials" / f"{case}.spatialdb"
        if file_sha256(material) != source["cases"][case]["material_sha256"]:
            raise ValueError(f"source-value material changed for {case}")
        case_dir = out_dir / case
        case_dir.mkdir(exist_ok=True)
        unit_dir = case_dir / "unit_ramp"
        maxwell._write_run(
            unit_dir,
            mesh,
            material,
            elapsed_seconds=elapsed_s,
            pressure_mpa=np.concatenate(([0.0], np.ones(len(grid) - 1))),
            time_step_s=args.step_days * maxwell.SECONDS_PER_DAY,
        )
        maxwell._run_pylith(unit_dir)
        response = _surface_uplift(unit_dir / "output/maxwell-surface.h5", elapsed_s[1:])
        operator = np.zeros((len(grid), len(grid)))
        operator[1:, 1:] = ramp_response_operator(response)
        fit = fit_deployment_relative_pressure(operator, observations, curvature_weight=1.0)
        forward_dir = case_dir / "bpr_pressure"
        maxwell._write_run(
            forward_dir,
            mesh,
            material,
            elapsed_seconds=elapsed_s,
            pressure_mpa=fit.pressure_mpa,
            time_step_s=args.step_days * maxwell.SECONDS_PER_DAY,
        )
        maxwell._run_pylith(forward_dir)
        actual = np.concatenate(
            ([0.0], _surface_uplift(forward_dir / "output/maxwell-surface.h5", elapsed_s[1:]))
        )
        predicted = operator @ fit.pressure_mpa
        relative_error = float(
            np.linalg.norm(actual - predicted) / max(np.linalg.norm(actual), np.finfo(float).eps)
        )
        if relative_error > 0.02:
            raise ValueError("PyLith forward response differs from linear inversion")
        times_s, failure = bpr._failure_summary(
            forward_dir / "output/maxwell-material.h5", equilibrium
        )
        if not np.allclose(times_s, elapsed_s[1:], rtol=0.0, atol=0.01):
            raise ValueError("PyLith stress times differ from OOI grid")
        series = case_dir / "pressure_failure.csv"
        with series.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(
                (
                    "time_utc",
                    "pressure_change_mpa",
                    "modeled_uplift_m",
                    "maximum_cavity_principal_stress_pa",
                    "connected_shear_path",
                    "joint_failure_zero_tensile_strength",
                )
            )
            for i, record in enumerate(failure, 1):
                tension = float(record["maximum_cavity_principal_stress_pa"])
                path = bool(record["cavity_to_surface_shear_path_found"])
                writer.writerow(
                    (
                        grid[i].isoformat(),
                        fit.pressure_mpa[i],
                        actual[i],
                        tension,
                        path,
                        tension > 0.0 and path,
                    )
                )
        first = next(
            (
                i
                for i, record in enumerate(failure, 1)
                if record["maximum_cavity_principal_stress_pa"] > 0.0
                and record["cavity_to_surface_shear_path_found"]
            ),
            None,
        )
        result = {
            "method": "OOI deployment-relative pressure fit and forward PyLith failure screen",
            "status": "conditional_bpr_failure_reconstruction_temporally_unresolved",
            "paper_output_data_used": False,
            "source_model_summary_sha256": file_sha256(source_path),
            "mesh_sha256": file_sha256(mesh),
            "observation_summary_sha256": file_sha256(obs_dir / "summary.json"),
            "observation_baseline_utc": obs_summary["baseline_date_utc"],
            "last_observed_utc": obs_summary["last_observed_date_utc"],
            "last_grid_utc": grid[-1].isoformat(),
            "selected_grid_observations": len(observations),
            "fit_rmse_m": fit.rmse_m,
            "fit_design_rank": fit.design_rank,
            "time_step_s": args.step_days * maxwell.SECONDS_PER_DAY,
            "time_step_to_shortest_maxwell_time_ratio": source["cases"][case][
                "time_step_to_shortest_maxwell_time_ratio"
            ],
            "forward_superposition_relative_l2_error": relative_error,
            "first_sampled_joint_failure_utc": grid[first].isoformat() if first else None,
            "first_sampled_joint_failure_pressure_mpa": float(fit.pressure_mpa[first])
            if first
            else None,
            "last_pressure_mpa": float(fit.pressure_mpa[-1]),
            "last_cavity_principal_stress_pa": float(
                failure[-1]["maximum_cavity_principal_stress_pa"]
            ),
            "series_sha256": file_sha256(series),
            "forward_material_sha256": file_sha256(forward_dir / "output/maxwell-material.h5"),
            "limitations": (
                "A BPR-constrained retrospective threshold crossing is not a prospective "
                "eruption forecast. One Maxwell branch and unresolved shortest relaxation "
                "time limit the timing."
            ),
        }
        (case_dir / "summary.json").write_text(
            json.dumps(result, indent=2) + "\n", encoding="utf-8"
        )
        print(case, result["first_sampled_joint_failure_utc"], result["last_pressure_mpa"])


if __name__ == "__main__":
    main()
