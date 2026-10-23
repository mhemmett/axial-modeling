"""Fit the 1998–2011 Center BPR cycle to source-value PyLith rheologies."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import h5py
import numpy as np
import source_value_bpr_failure as bpr
import source_value_maxwell_cases as maxwell

from axialstress.coordinates import CENTRAL_CALDERA_LAT_LON_DEG, local_east_north_offset_m
from axialstress.deployment_pressure import DepthObservation, fit_deployment_relative_pressure
from axialstress.maxwell_pressure_inversion import ramp_response_operator
from axialstress.paper_bpr import CANDIDATE_PROCESSED_CENTER_SOURCES, file_sha256
from axialstress.surface_interpolation import interpolate_triangular_surface

ROOT = Path(__file__).resolve().parents[1]
OBS = ROOT / "data/processed/paper_center_bpr"
SOURCE = ROOT / "data/processed/source_value_bpr_failure_2011_2015"
OUTPUT = ROOT / "data/processed/source_value_bpr_failure_1998_2011"
BASIS = ROOT / "data/processed/refined_elastic_basis_400m"
SLUGS = (
    "fox_wc81_1997_center",
    "nemo_2000_2002_center_processed",
    "nemo_2002_2004_center",
    "nemo_2003_2005_center",
    "nemo_2004_2007_center",
    "nemo_2007_2010_center",
    "nemo_2010_2011_center",
)
LAST_UTC = datetime(2011, 4, 6, 12, tzinfo=UTC)


def _observations(obs_dir: Path) -> tuple[list[datetime], list[DepthObservation], dict]:
    """Select archived positive-down Center depths at weekly UTC noons."""
    summary_path = obs_dir / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if summary.get("model_outputs_used") is not False:
        raise ValueError("historical BPR export has incomplete provenance")
    entries = {item["deployment"]: item for item in summary["deployments"]}
    registry = {item.deployment.slug: item for item in CANDIDATE_PROCESSED_CENTER_SOURCES}
    fox_path = obs_dir / f"{SLUGS[0]}.hourly.csv"
    with fox_path.open(encoding="utf-8", newline="") as stream:
        fox_rows = list(csv.DictReader(stream))
    peak_window = [
        (datetime.fromisoformat(row["time_utc"]), float(row["observed_depth_m"]))
        for row in fox_rows
        if "1998-01-24" <= row["time_utc"][:10] <= "1998-02-10" and row["time_utc"][11:13] == "12"
    ]
    if len(peak_window) < 10:
        raise ValueError("Fox 1998 deflation peak is not observable")
    peak = max(peak_window, key=lambda item: item[1])
    start = peak[0]
    dates = [start + timedelta(days=7 * i) for i in range((LAST_UTC - start).days // 7 + 1)]
    dates = [when for when in dates if when < LAST_UTC]
    grid_index = {when: i for i, when in enumerate(dates)}
    records = []
    selected_sources = []
    for slug in SLUGS:
        entry, source = entries[slug], registry[slug]
        path = obs_dir / f"{slug}.hourly.csv"
        if (
            entry["source_sha256"] != file_sha256(source.deployment.path)
            or entry["output_sha256"] != file_sha256(path)
            or entry["source_channel"] != source.channel
        ):
            raise ValueError(f"historical BPR source changed: {slug}")
        count = 0
        with path.open(encoding="utf-8", newline="") as stream:
            for row in csv.DictReader(stream):
                when = datetime.fromisoformat(row["time_utc"])
                if when in grid_index:
                    records.append(
                        DepthObservation(slug, grid_index[when], float(row["observed_depth_m"]))
                    )
                    count += 1
        if count < 2:
            raise ValueError(f"too few observed weekly values for {slug}")
        selected_sources.append(
            {
                "slug": slug,
                "source_doi": entry["source_doi"],
                "source_channel": source.channel,
                "source_sha256": entry["source_sha256"],
                "processed_sha256": entry["output_sha256"],
                "selected_weekly_observations": count,
            }
        )
    return (
        dates,
        records,
        {
            "source_summary_sha256": file_sha256(summary_path),
            "observed_post_1998_peak_utc": peak[0].isoformat(),
            "observed_post_1998_peak_depth_m": peak[1],
            "sources": selected_sources,
        },
    )


def _surface_responses(path: Path, expected_times_s: np.ndarray) -> dict[str, np.ndarray]:
    """Sample saved PyLith uplift at each archived BPR coordinate (m)."""
    with h5py.File(path, "r") as surface:
        times_s = np.asarray(surface["time"], dtype=float).reshape(-1)
        vertices = np.asarray(surface["geometry/vertices"], dtype=float)
        triangles = np.asarray(surface["viz/topology/cells"], dtype=np.int64)
        displacements = np.asarray(surface["vertex_fields/displacement"], dtype=float)
    if times_s.shape != expected_times_s.shape or not np.allclose(
        times_s, expected_times_s, rtol=0.0, atol=0.01
    ):
        raise ValueError("PyLith times differ from the historical BPR grid")
    registry = {item.deployment.slug: item for item in CANDIDATE_PROCESSED_CENTER_SOURCES}
    result = {}
    for slug in SLUGS:
        site = registry[slug].deployment
        xy = local_east_north_offset_m(
            site.latitude,
            site.longitude,
            origin_latitude_deg=CENTRAL_CALDERA_LAT_LON_DEG[0],
            origin_longitude_deg=CENTRAL_CALDERA_LAT_LON_DEG[1],
        )
        result[slug] = np.asarray(
            [
                interpolate_triangular_surface(vertices, triangles, field, xy)[2]
                for field in displacements
            ]
        )
    return result


def main() -> None:
    """Run bounded source-value Maxwell fits for the observed 1998–2011 cycle."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observation-dir", type=Path, default=OBS)
    parser.add_argument("--source-dir", type=Path, default=SOURCE)
    parser.add_argument("--basis-dir", type=Path, default=BASIS)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    parser.add_argument(
        "--case", choices=("constant_maxwell", "thermal_maxwell", "hydrothermal_maxwell")
    )
    args = parser.parse_args()
    obs_dir = args.observation_dir.resolve()
    source_dir = args.source_dir.resolve()
    basis_dir = args.basis_dir.resolve()
    out_dir = args.output_dir.resolve()
    source_path = source_dir / "summary.json"
    source = json.loads(source_path.read_text(encoding="utf-8"))
    if source.get("paper_output_data_used") is not False:
        raise ValueError("source-value model provenance is incomplete")
    dates, observations, obs_record = _observations(obs_dir)
    elapsed_s = np.arange(len(dates), dtype=float) * 7.0 * maxwell.SECONDS_PER_DAY
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
            pressure_mpa=np.concatenate(([0.0], np.ones(len(dates) - 1))),
            time_step_s=7.0 * maxwell.SECONDS_PER_DAY,
        )
        maxwell._run_pylith(unit_dir)
        responses = _surface_responses(unit_dir / "output/maxwell-surface.h5", elapsed_s[1:])
        operators = {}
        for slug, response in responses.items():
            operator = np.zeros((len(dates), len(dates)))
            operator[1:, 1:] = ramp_response_operator(response)
            operators[slug] = operator
        fit = fit_deployment_relative_pressure(
            operators[SLUGS[0]],
            observations,
            curvature_weight=1.0,
            deployment_response=operators,
        )
        forward_dir = case_dir / "bpr_pressure"
        maxwell._write_run(
            forward_dir,
            mesh,
            material,
            elapsed_seconds=elapsed_s,
            pressure_mpa=fit.pressure_mpa,
            time_step_s=7.0 * maxwell.SECONDS_PER_DAY,
        )
        maxwell._run_pylith(forward_dir)
        modeled = _surface_responses(forward_dir / "output/maxwell-surface.h5", elapsed_s[1:])
        actual = np.concatenate(([0.0], modeled[SLUGS[0]]))
        predicted = operators[SLUGS[0]] @ fit.pressure_mpa
        relative_error = float(
            np.linalg.norm(actual - predicted) / max(np.linalg.norm(actual), np.finfo(float).eps)
        )
        if relative_error > 0.02:
            raise ValueError("PyLith forward response differs from linear inversion")
        times_s, failure = bpr._failure_summary(
            forward_dir / "output/maxwell-material.h5", equilibrium
        )
        if not np.allclose(times_s, elapsed_s[1:], rtol=0.0, atol=0.01):
            raise ValueError("PyLith stress times differ from historical grid")
        series = case_dir / "pressure_failure.csv"
        with series.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(
                (
                    "time_utc",
                    "pressure_change_mpa",
                    "modeled_fox_site_uplift_m",
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
                        dates[i].isoformat(),
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
        first_positive = next(
            (
                i
                for i, record in enumerate(failure, 1)
                if fit.pressure_mpa[i] > 0.0
                and record["maximum_cavity_principal_stress_pa"] > 0.0
                and record["cavity_to_surface_shear_path_found"]
            ),
            None,
        )
        result = {
            "method": "archived Center deployment-relative pressure fit and PyLith failure screen",
            "status": "conditional_bpr_failure_reconstruction_temporally_unresolved",
            "paper_output_data_used": False,
            "source_model_summary_sha256": file_sha256(source_path),
            "mesh_sha256": file_sha256(mesh),
            "observation_provenance": obs_record,
            "cycle_start_utc": dates[0].isoformat(),
            "last_grid_utc": dates[-1].isoformat(),
            "observed_eruption_utc": LAST_UTC.isoformat(),
            "selected_weekly_observations": len(observations),
            "fit_rmse_m": fit.rmse_m,
            "fit_design_rank": fit.design_rank,
            "time_step_s": 7.0 * maxwell.SECONDS_PER_DAY,
            "time_step_to_shortest_maxwell_time_ratio": source["cases"][case][
                "time_step_to_shortest_maxwell_time_ratio"
            ],
            "forward_superposition_relative_l2_error": relative_error,
            "first_sampled_joint_failure_utc": dates[first].isoformat() if first else None,
            "first_positive_pressure_joint_utc": (
                dates[first_positive].isoformat() if first_positive else None
            ),
            "first_sampled_joint_failure_pressure_mpa": float(fit.pressure_mpa[first])
            if first
            else None,
            "first_joint_path_cell_indices": (
                list(map(int, failure[first - 1]["cavity_to_surface_path_cell_indices"]))
                if first
                else []
            ),
            "last_pressure_mpa": float(fit.pressure_mpa[-1]),
            "minimum_fitted_pressure_mpa": float(fit.pressure_mpa.min()),
            "maximum_fitted_pressure_mpa": float(fit.pressure_mpa.max()),
            "last_cavity_principal_stress_pa": float(
                failure[-1]["maximum_cavity_principal_stress_pa"]
            ),
            "series_sha256": file_sha256(series),
            "forward_material_sha256": file_sha256(forward_dir / "output/maxwell-material.h5"),
            "limitations": (
                "The 1998–2000 BPR gap and separate deployment datums leave gap pressure "
                "dependent on smoothing. One Maxwell branch, zero initial memory, and the "
                "unresolved shortest relaxation time prevent a prospective forecast claim."
            ),
        }
        (case_dir / "summary.json").write_text(
            json.dumps(result, indent=2) + "\n", encoding="utf-8"
        )
        print(case, result["first_sampled_joint_failure_utc"], result["last_pressure_mpa"])


if __name__ == "__main__":
    main()
