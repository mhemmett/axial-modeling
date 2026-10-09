"""Refine historical Maxwell failure-path timing for two raw BPR windows."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import h5py
import historical_generalized_maxwell_bpr_check as historical
import numpy as np

from axialstress.ellipsoid_bpr_calibration import read_ellipsoid_unit_response
from axialstress.generalized_maxwell import generalized_maxwell_relaxation_times_s
from axialstress.historical_bpr import PROCESSED_DIR
from axialstress.historical_generalized_maxwell import (
    HistoricalPressureHistory,
    prepare_center_fit_pressure_history,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = (
    ROOT / "data" / "processed" / "historical_failure_time_refinement"
)
DEFAULT_STEPS_DAYS = (7.0, 3.5, 1.0)
DEFAULT_EVENTS = ("2011", "2002_2004")
SECONDS_PER_DAY = 86_400.0


def _event_pairs() -> dict[str, tuple[str, str]]:
    """Return eruption and deployment comparisons available in the driver."""
    return {**historical.EVENT_PAIRS, **historical.DEPLOYMENT_PAIRS}


def _truncate_history(
    history: HistoricalPressureHistory, duration_days: float
) -> HistoricalPressureHistory:
    """Keep the first bounded portion of a Center-fit daily BPR history."""
    end_time_s = duration_days * SECONDS_PER_DAY
    selected = history.elapsed_seconds <= end_time_s
    indices = np.flatnonzero(selected)
    if len(indices) < 2:
        raise ValueError("refinement duration must retain at least two BPR records")
    if not np.isclose(history.elapsed_seconds[indices[-1]], end_time_s):
        raise ValueError("refinement duration must end on an available daily BPR record")
    last = int(indices[-1]) + 1
    return HistoricalPressureHistory(
        dates_utc=history.dates_utc[:last],
        elapsed_seconds=history.elapsed_seconds[:last],
        center_uplift_m=history.center_uplift_m[:last],
        south_uplift_m=history.south_uplift_m[:last],
        pressure_change_mpa=history.pressure_change_mpa[:last],
    )


def _read_saved_times(material_path: Path) -> np.ndarray:
    """Read PyLith material times from a completed bounded run."""
    with h5py.File(material_path, "r") as material:
        times_s = np.asarray(material["time"], dtype=float).reshape(-1)
    if len(times_s) < 2 or not np.all(np.isfinite(times_s)):
        raise ValueError(f"invalid PyLith material time history in {material_path}")
    if np.any(np.diff(times_s) <= 0.0):
        raise ValueError(f"PyLith output times are not increasing in {material_path}")
    return times_s


def _run_refinement(
    event: str,
    pair: tuple[str, str],
    *,
    mesh_path: Path,
    material_database: Path,
    compliance_m_per_mpa: float,
    output_dir: Path,
    duration_days: float,
    step_days: float,
) -> dict[str, object]:
    """Run one bounded PyLith history and report its saved path transition."""
    center_slug, south_slug = pair
    history = prepare_center_fit_pressure_history(
        historical._read_daily_depths(PROCESSED_DIR / f"{center_slug}.daily.csv"),
        historical._read_daily_depths(PROCESSED_DIR / f"{south_slug}.daily.csv"),
        center_compliance_m_per_mpa=compliance_m_per_mpa,
    )
    history = _truncate_history(history, duration_days)
    step_s = step_days * SECONDS_PER_DAY
    step_tag = f"{step_days:g}d".replace(".", "p")
    run_dir = output_dir / "runs" / event / step_tag
    if run_dir.exists():
        raise FileExistsError(
            f"refinement output already exists; choose a new --output-dir: {run_dir}"
        )

    historical._configure_run(
        run_dir,
        mesh_path,
        material_database,
        history.elapsed_seconds,
        history.pressure_change_mpa,
        initial_dt_s=step_s,
    )
    historical._run_pylith(run_dir)
    material_path = run_dir / "output" / "genmaxwell-material.h5"
    times_s = _read_saved_times(material_path)

    material = np.atleast_2d(np.loadtxt(material_database, comments="#", skiprows=13))
    relaxation_times_s = generalized_maxwell_relaxation_times_s(
        historical.YOUNGS_MODULUS_PA,
        historical.POISSON_RATIO,
        material[:, 6:9].T,
        material[:, 9:12].T,
    )
    maximum_output_step_s = float(np.max(np.diff(times_s)))
    minimum_relaxation_time_s = float(np.min(relaxation_times_s))
    if maximum_output_step_s > minimum_relaxation_time_s / 5.0:
        raise ValueError("refined PyLith step exceeds one-fifth of the minimum relaxation time")

    result_dir = output_dir / "analysis" / event / step_tag
    result_dir.mkdir(parents=True, exist_ok=True)
    failure = historical._analyze_failure_history(
        material_path, f"{event}_{step_tag}", result_dir
    )
    result = {
        "event": event,
        "center_station_slug": center_slug,
        "south_station_slug": south_slug,
        "observation_provenance": "original raw NCEI/MGDS BPR channels",
        "paper_publication_data_used": False,
        "forcing_method": "raw Center daily uplift divided by static elastic compliance",
        "forcing_start_utc": history.dates_utc[0].isoformat(),
        "forcing_end_utc": history.dates_utc[-1].isoformat(),
        "forcing_duration_days": duration_days,
        "initial_timestep_days": step_days,
        "saved_record_count": len(times_s),
        "maximum_saved_interval_days": maximum_output_step_s / SECONDS_PER_DAY,
        "minimum_branch_relaxation_time_days": (
            minimum_relaxation_time_s / SECONDS_PER_DAY
        ),
        "one_fifth_relaxation_time_limit_passed": True,
        "failure_analysis": failure,
        "run_directory": str(run_dir.relative_to(ROOT)),
        "failure_csv": str(
            (result_dir / str(failure["history_csv"])).relative_to(ROOT)
        ),
    }
    return result


def main() -> None:
    """Run three temporal resolutions for one eruption and one quiet interval."""
    pairs = _event_pairs()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mesh", type=Path, required=True)
    parser.add_argument("--material-database", type=Path, required=True)
    parser.add_argument("--elastic-surface", type=Path, default=historical.ELASTIC_SURFACE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--events", nargs="+", choices=sorted(pairs), default=DEFAULT_EVENTS)
    parser.add_argument("--step-days", nargs="+", type=float, default=DEFAULT_STEPS_DAYS)
    parser.add_argument("--duration-days", type=float, default=80.0)
    args = parser.parse_args()
    args.mesh = args.mesh.resolve()
    args.material_database = args.material_database.resolve()
    args.elastic_surface = args.elastic_surface.resolve()
    args.output_dir = args.output_dir.resolve()

    for path in (args.mesh, args.material_database, args.elastic_surface):
        if not path.is_file():
            raise FileNotFoundError(path)
    if args.duration_days <= 0.0 or not np.isfinite(args.duration_days):
        raise ValueError("duration must be finite and positive")
    if not args.step_days or any(
        not np.isfinite(step) or step <= 0.0 for step in args.step_days
    ):
        raise ValueError("time steps must be finite and positive")
    if len(set(args.step_days)) != len(args.step_days):
        raise ValueError("time-step values must be unique")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise FileExistsError(
            f"refinement output is not empty; choose a new --output-dir: {args.output_dir}"
        )
    args.output_dir.mkdir(parents=True, exist_ok=True)

    center_response, _ = read_ellipsoid_unit_response(args.elastic_surface)
    compliance_m_per_mpa = float(center_response[2])
    results = []
    for event in args.events:
        for step_days in args.step_days:
            result = _run_refinement(
                event,
                pairs[event],
                mesh_path=args.mesh,
                material_database=args.material_database,
                compliance_m_per_mpa=compliance_m_per_mpa,
                output_dir=args.output_dir,
                duration_days=args.duration_days,
                step_days=step_days,
            )
            results.append(result)
            print(json.dumps(result, indent=2))

    summary = {
        "method": "bounded historical Maxwell output and time-step refinement",
        "mesh_tetrahedra": len(np.atleast_2d(np.loadtxt(
            args.material_database, comments="#", skiprows=13
        ))),
        "static_ellipsoid_mesh_converged": False,
        "branch_parameters_are_synthetic": True,
        "failure_parameters": {
            "cohesion_pa": historical.FAILURE_COHESION_PA,
            "friction_angle_deg": historical.FAILURE_FRICTION_ANGLE_DEG,
            "pore_pressure_pa": historical.FAILURE_PORE_PRESSURE_PA,
            "tensile_strength_assigned": False,
        },
        "limitations": [
            "the Center pressure history uses static compliance, not viscoelastic inversion",
            "the three Maxwell branch values remain synthetic",
            "failure paths are postprocessed from saved PyLith stress records",
            "raw daily BPR means retain ocean variability and instrument drift",
        ],
        "runs": results,
    }
    summary_path = args.output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {summary_path}")


if __name__ == "__main__":
    main()
