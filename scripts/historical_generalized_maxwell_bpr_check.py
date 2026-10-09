"""Drive a synthetic three-branch Maxwell model with raw historical BPR checks."""

from __future__ import annotations

import argparse
import csv
import json
import re
import shlex
import shutil
import subprocess
from datetime import date, timedelta
from pathlib import Path

import h5py
import matplotlib
import numpy as np

matplotlib.use("Agg")

import matplotlib.dates as mdates
import matplotlib.pyplot as plt

from axialstress.bpr_mogi_calibration import local_east_north_offset_m
from axialstress.ellipsoid_bpr_calibration import read_ellipsoid_unit_response
from axialstress.failure_analysis import analyze_pylith_material_history
from axialstress.generalized_maxwell import generalized_maxwell_relaxation_times_s
from axialstress.historical_bpr import DEPLOYMENTS, PROCESSED_DIR
from axialstress.historical_generalized_maxwell import (
    SECONDS_PER_YEAR,
    HistoricalPressureHistory,
    compare_model_history,
    prepare_center_fit_pressure_history,
    prepare_contiguous_center_pressure_forcing,
    stitch_overlapping_station_uplift,
)
from axialstress.surface_interpolation import interpolate_triangular_surface

ROOT = Path(__file__).resolve().parents[1]
STEP_DIR = ROOT / "pylith" / "step13_historical_generalized_maxwell_bpr"
MATERIAL_STEP_DIR = ROOT / "pylith" / "step12_generalized_maxwell_ellipsoid"
ELASTIC_SURFACE = (
    ROOT
    / "pylith"
    / "step05_ellipsoid_elastic"
    / "output"
    / "ellipsoid-surface.h5"
)
PYLITH_ROOT = ROOT / "pylith" / "pylith-5.0.2-linux-x86_64"
EVENT_PAIRS = {
    "1998": ("wc81_1997", "wc82a_1997"),
    "2011": ("nemo_2010_2011_center", "nemo_2009_2011_south"),
}
DEPLOYMENT_PAIRS = {
    "1995_1996": ("wc68_1995", "wc69_1995"),
    "2003_2005": ("nemo_2003_2005_center", "nemo_2003_2005_south"),
    "2005_2007": ("nemo_2004_2007_center", "nemo_2005_2007_south1"),
    "2007_2009": ("nemo_2007_2010_center", "nemo_2005_2009_south2"),
    "2011_2013": ("nemo_2011_2013_center", "nemo_2011_2013_south"),
    "2013_2015": ("nemo_2013_2015_center", "nemo_2013_2015_south2"),
    "2015_2017": ("nemo_2015_2017_center", "nemo_2015_2017_south2"),
}
POST_2011_DEPLOYMENT_PAIRS = {
    name: pair for name, pair in DEPLOYMENT_PAIRS.items() if name in {"2013_2015", "2015_2017"}
}
CORE_DEPLOYMENT_PAIRS = {
    name: pair for name, pair in DEPLOYMENT_PAIRS.items() if name not in POST_2011_DEPLOYMENT_PAIRS
}
ADDITIONAL_HELDOUTS = {
    "1995_1996": ("wc67_1995",),
    "2007_2009": ("nemo_2007_2009_south1",),
    "2013_2015": ("nemo_2013_2015_south1",),
}
ERUPTION_DATES = {"1998": date(1998, 1, 25), "2011": date(2011, 4, 6)}
YOUNGS_MODULUS_PA = 50.0e9
POISSON_RATIO = 0.25
DENSITY_KG_M3 = 2800.0
REFERENCE_VISCOSITY_PA_S_BY_BRANCH = np.asarray([1.0e18, 5.0e17, 2.0e18])
SHEAR_RATIO_BY_BRANCH = np.asarray([0.25, 0.25, 0.25])
INITIAL_DT_S = 7.0 * 86_400.0
FAILURE_COHESION_PA = 1.0e6
FAILURE_FRICTION_ANGLE_DEG = 25.0
FAILURE_PORE_PRESSURE_PA = 0.0


def _read_daily_depths(path: Path) -> dict[date, float]:
    """Read daily equivalent depths produced from original raw BPR channels."""
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        required = {"time_utc", "equivalent_depth_m", "relative_uplift_m"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError(f"unexpected daily BPR columns in {path}")
        depths: dict[date, float] = {}
        for row_number, row in enumerate(reader, start=2):
            if not row["relative_uplift_m"]:
                continue
            try:
                day = date.fromisoformat(row["time_utc"][:10])
                depth_m = float(row["equivalent_depth_m"])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"invalid daily BPR row {row_number} in {path}") from exc
            if not np.isfinite(depth_m) or day in depths:
                raise ValueError(
                    f"invalid or duplicate daily BPR date at row {row_number} in {path}"
                )
            depths[day] = depth_m
    if not depths:
        raise ValueError(f"no valid daily BPR depths in {path}")
    return depths


def _write_pressure_history(
    path: Path, elapsed_seconds: np.ndarray, pressure_mpa: np.ndarray
) -> None:
    """Write a daily pressure series with a constant terminal support interval."""
    if (
        elapsed_seconds.ndim != 1
        or elapsed_seconds.shape != pressure_mpa.shape
        or len(elapsed_seconds) < 2
        or not np.all(np.isfinite(elapsed_seconds))
        or not np.all(np.isfinite(pressure_mpa))
        or np.any(np.diff(elapsed_seconds) <= 0.0)
    ):
        raise ValueError("time history requires matched finite increasing arrays")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as stream:
        stream.write("#TIME HISTORY ascii\n")
        stream.write("TimeHistory {\n")
        stream.write(f"  num-points = {len(elapsed_seconds) + 1}\n")
        stream.write("  time-units = year\n")
        stream.write("}\n")
        for elapsed_s, pressure_value_mpa in zip(
            elapsed_seconds, pressure_mpa, strict=True
        ):
            stream.write(
                f"{elapsed_s / SECONDS_PER_YEAR:.12g} "
                f"{pressure_value_mpa:.12g}\n"
            )
        terminal_support_s = elapsed_seconds[-1] + INITIAL_DT_S
        stream.write(
            f"{terminal_support_s / SECONDS_PER_YEAR:.12g} "
            f"{pressure_mpa[-1]:.12g}\n"
        )


def _write_cavity_database(path: Path) -> None:
    """Write a one-megapascal normalized cavity traction amplitude."""
    names = (
        "initial_amplitude_normal",
        "initial_amplitude_tangential_1",
        "initial_amplitude_tangential_2",
        "time_history_amplitude_normal",
        "time_history_amplitude_tangential_1",
        "time_history_amplitude_tangential_2",
        "time_history_start_time",
    )
    lines = [
        "#SPATIAL.ascii 1",
        "SimpleDB {",
        "  num-values = 7",
        f"  value-names = {' '.join(names)}",
        "  value-units = Pa Pa Pa Pa Pa Pa s",
        "  num-locs = 1",
        "  data-dim = 0",
        "  space-dim = 3",
        "  cs-data = cartesian {",
        "    to-meters = 1.0",
        "    space-dim = 3",
        "  }",
        "}",
        "0.0 0.0 0.0 0.0 0.0 0.0 -1.0e6 0.0 0.0 0.0",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _configure_run(
    run_dir: Path,
    mesh_path: Path,
    material_database: Path,
    elapsed_seconds: np.ndarray,
    pressure_mpa: np.ndarray,
) -> None:
    """Create a local generalized Maxwell case with raw BPR pressure forcing."""
    (run_dir / "mesh").mkdir(parents=True, exist_ok=True)
    (run_dir / "output").mkdir(parents=True, exist_ok=True)
    shutil.copy2(mesh_path, run_dir / "mesh" / "axial_ellipsoid.msh")
    shutil.copy2(material_database, run_dir / "output" / "genmaxwell-material.spatialdb")
    shutil.copy2(
        ROOT / "pylith" / "step06_maxwell_ellipsoid" / "bc_zero.spatialdb",
        run_dir / "output" / "bc_zero.spatialdb",
    )
    _write_cavity_database(run_dir / "output" / "bc_cavity.spatialdb")
    _write_pressure_history(
        run_dir / "output" / "pressure.timedb", elapsed_seconds, pressure_mpa
    )

    step_config = (MATERIAL_STEP_DIR / "generalized_maxwell.cfg").read_text(
        encoding="utf-8"
    )
    duration_s = float(elapsed_seconds[-1])
    step_config, end_count = re.subn(
        r"(?m)^end_time\s*=.*$", f"end_time = {duration_s:.12g}*s", step_config
    )
    step_config, dt_count = re.subn(
        r"(?m)^initial_dt\s*=.*$",
        f"initial_dt = {min(INITIAL_DT_S, duration_s):.12g}*s",
        step_config,
    )
    cavity_path = (
        "db_auxiliary_field.iohandler.filename = "
        "../step06_maxwell_ellipsoid/bc_cavity.spatialdb"
    )
    if step_config.count(cavity_path) != 1 or end_count != 1 or dt_count != 1:
        raise ValueError("could not configure generalized Maxwell time-history input")
    step_config = step_config.replace(
        cavity_path,
        "use_time_history = True\n"
        f"{cavity_path.split(' = ')[0]} = output/bc_cavity.spatialdb\n"
        "time_history = spatialdata.spatialdb.TimeHistory\n"
        "time_history.description = Raw Center BPR pressure inferred with "
        "static elastic compliance\n"
        "time_history.filename = output/pressure.timedb",
    )
    zero_path = (
        "db_auxiliary_field.iohandler.filename = "
        "../step06_maxwell_ellipsoid/bc_zero.spatialdb"
    )
    if step_config.count(zero_path) != 5:
        raise ValueError("could not configure generalized Maxwell boundary databases")
    step_config = step_config.replace(
        zero_path, "db_auxiliary_field.iohandler.filename = output/bc_zero.spatialdb"
    )
    (run_dir / "generalized_maxwell.cfg").write_text(step_config, encoding="utf-8")
    pylith_config = (MATERIAL_STEP_DIR / "pylithapp.cfg").read_text(encoding="utf-8")
    (run_dir / "pylithapp.cfg").write_text(pylith_config, encoding="utf-8")


def _run_pylith(run_dir: Path) -> None:
    """Run one event window with a five-minute wall-clock limit."""
    log_path = run_dir / "output" / "pylith.log"
    command = (
        f"cd {shlex.quote(str(PYLITH_ROOT))} && source setup.sh && "
        f"cd {shlex.quote(str(run_dir))} && "
        "timeout 300 pylith generalized_maxwell.cfg"
    )
    with log_path.open("w", encoding="utf-8") as log:
        completed = subprocess.run(
            ["bash", "-lc", command],
            cwd=ROOT,
            stdout=log,
            stderr=subprocess.STDOUT,
            check=False,
        )
    if completed.returncode:
        tail = "\n".join(log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-50:])
        raise RuntimeError(f"historical generalized Maxwell PyLith run failed:\n{tail}")


def _read_surface_history(
    path: Path,
    reference_station: object,
    stations: dict[str, object],
) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """Sample saved surface displacement at each BPR station location."""
    with h5py.File(path, "r") as surface:
        times_s = np.asarray(surface["time"], dtype=float).reshape(-1)
        vertices = np.asarray(surface["geometry/vertices"], dtype=float)
        triangles = np.asarray(surface["viz/topology/cells"], dtype=np.int64)
        displacement = np.asarray(surface["vertex_fields/displacement"], dtype=float)
    if displacement.shape != (len(times_s), *vertices.shape):
        raise ValueError("PyLith surface displacement has an unexpected shape")
    if len(times_s) < 2 or np.any(np.diff(times_s) <= 0.0):
        raise ValueError("PyLith surface output times must be increasing")
    station_uplift_m = {}
    for slug, station in stations.items():
        east_m, north_m = local_east_north_offset_m(
            station.latitude,
            station.longitude,
            origin_latitude_deg=reference_station.latitude,
            origin_longitude_deg=reference_station.longitude,
        )
        station_uplift_m[slug] = np.asarray(
            [
                interpolate_triangular_surface(
                    vertices, triangles, field, (east_m, north_m)
                )[2]
                for field in displacement
            ],
            dtype=float,
        )
    return times_s, station_uplift_m


def _analyze_failure_history(
    material_path: Path,
    event: str,
    output_dir: Path,
) -> dict[str, object]:
    """Summarize provisional Mohr–Coulomb paths through a BPR stress history."""
    analysis = analyze_pylith_material_history(
        material_path,
        cohesion_pa=FAILURE_COHESION_PA,
        friction_angle_deg=FAILURE_FRICTION_ANGLE_DEG,
        pore_pressure_pa=FAILURE_PORE_PRESSURE_PA,
    )
    records = analysis.pop("records")
    path = output_dir / f"historical_generalized_maxwell_{event}_failure.csv"
    rows = [
        {
            "time_s": record["time_s"],
            "elapsed_days": record["time_s"] / 86_400.0,
            "mohr_coulomb_shear_yield_cell_count": record[
                "mohr_coulomb_shear_yield_cell_count"
            ],
            "cavity_to_surface_shear_path_found": record[
                "cavity_to_surface_shear_path_found"
            ],
            "maximum_cavity_tensile_stress_pa": record[
                "maximum_cavity_tensile_stress_pa"
            ],
            "reservoir_tensile_failure": record["reservoir_tensile_failure"],
            "joint_eruption_criterion_met": record[
                "joint_eruption_criterion_met"
            ],
        }
        for record in records
    ]
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    bracket = analysis["interpolated_path_bracket"]
    onset_s = (
        analysis["first_cavity_to_surface_shear_path_interpolated_time_s"]
        if bracket is not None and bracket["upper_record_index"] != 0
        else None
    )
    first_record_path = bool(records[0]["cavity_to_surface_shear_path_found"])
    if first_record_path:
        interpretation = (
            "a connected path is present at the first saved record, so onset is "
            "bounded at or before that output time"
        )
    elif onset_s is not None:
        interpretation = (
            "linear stress interpolation estimates onset between saved records; "
            "no PyLith integration is performed within that interval"
        )
    else:
        interpretation = "no cavity-to-surface shear path occurs in the saved history"
    summary: dict[str, object] = {
        "method": "per-record Mohr-Coulomb threshold and cavity-to-top cell connectivity",
        "cohesion_pa": FAILURE_COHESION_PA,
        "friction_angle_deg": FAILURE_FRICTION_ANGLE_DEG,
        "friction_interpretation": "friction_angle_deg is used directly as phi",
        "pore_pressure_pa": FAILURE_PORE_PRESSURE_PA,
        "tensile_cutoff_applied_to_shear_path": False,
        "assumed_tensile_strength_pa": analysis["assumed_tensile_strength_pa"],
        "first_joint_eruption_criterion_record_time_s": analysis[
            "first_joint_eruption_criterion_record_time_s"
        ],
        "maximum_tensile_strength_with_a_saved_connected_path_pa": analysis[
            "maximum_tensile_strength_with_a_saved_connected_path_pa"
        ],
        "time_of_maximum_tensile_strength_with_a_saved_connected_path_s": analysis[
            "time_of_maximum_tensile_strength_with_a_saved_connected_path_s"
        ],
        "joint_criterion_interpolation": analysis["joint_criterion_interpolation"],
        "record_count": analysis["record_count"],
        "first_saved_record_time_s": records[0]["time_s"],
        "first_saved_record_has_cavity_to_surface_path": first_record_path,
        "first_path_record_time_s": analysis[
            "first_cavity_to_surface_shear_path_time_s"
        ],
        "interpolated_path_onset_time_s": onset_s,
        "path_found_record_count": int(
            sum(row["cavity_to_surface_shear_path_found"] for row in rows)
        ),
        "maximum_shear_yield_cell_count": max(
            row["mohr_coulomb_shear_yield_cell_count"] for row in rows
        ),
        "history_csv": path.name,
        "onset_interpolation_limitation": analysis["interpolation_limitation"],
        "interpretation": interpretation,
    }
    return summary


def _run_event(
    event: str,
    center_slug: str,
    south_slug: str,
    deployments: dict[str, object],
    *,
    mesh_path: Path,
    material_database: Path,
    center_compliance_m_per_mpa: float,
    output_dir: Path,
) -> dict[str, object]:
    """Run and summarize one raw Center/South deployment overlap."""
    center = deployments[center_slug]
    south = deployments[south_slug]
    center_depths = _read_daily_depths(PROCESSED_DIR / f"{center_slug}.daily.csv")
    south_depths = _read_daily_depths(PROCESSED_DIR / f"{south_slug}.daily.csv")
    history = prepare_center_fit_pressure_history(
        center_depths,
        south_depths,
        center_compliance_m_per_mpa=center_compliance_m_per_mpa,
    )
    additional_stations = {
        slug: deployments[slug] for slug in ADDITIONAL_HELDOUTS.get(event, ())
    }
    stations_to_sample = {center_slug: center, south_slug: south}
    stations_to_sample.update(additional_stations)
    run_dir = STEP_DIR / "output" / event
    if run_dir.exists():
        shutil.rmtree(run_dir)
    _configure_run(
        run_dir,
        mesh_path,
        material_database,
        history.elapsed_seconds,
        history.pressure_change_mpa,
    )
    _run_pylith(run_dir)
    times_s, model_uplift_by_station_m = _read_surface_history(
        run_dir / "output" / "genmaxwell-surface.h5", center, stations_to_sample
    )
    if times_s[0] > history.elapsed_seconds[0]:
        if history.elapsed_seconds[0] != 0.0 or not np.isclose(
            history.pressure_change_mpa[0], 0.0, rtol=0.0, atol=1.0e-12
        ):
            raise ValueError("PyLith output omits a nonzero initial pressure state")
        times_s = np.insert(times_s, 0, 0.0)
        model_uplift_by_station_m = {
            slug: np.insert(uplift, 0, 0.0)
            for slug, uplift in model_uplift_by_station_m.items()
        }
    center_model_m = model_uplift_by_station_m[center_slug]
    south_model_m = model_uplift_by_station_m[south_slug]
    rows, metrics = compare_model_history(
        history,
        times_s,
        center_model_m,
        south_model_m,
    )

    material = np.atleast_2d(np.loadtxt(material_database, comments="#", skiprows=13))
    relaxation_times_s = generalized_maxwell_relaxation_times_s(
        YOUNGS_MODULUS_PA,
        POISSON_RATIO,
        material[:, 6:9].T,
        material[:, 9:12].T,
    )
    maximum_step_s = float(np.max(np.diff(times_s)))
    minimum_relaxation_time_s = float(np.min(relaxation_times_s))
    if maximum_step_s > minimum_relaxation_time_s / 5.0:
        raise ValueError("historical PyLith step exceeds one-fifth of the minimum relaxation time")

    output_dir.mkdir(parents=True, exist_ok=True)
    failure_summary = _analyze_failure_history(
        run_dir / "output" / "genmaxwell-material.h5", event, output_dir
    )
    series_path = output_dir / f"historical_generalized_maxwell_{event}.csv"
    with series_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    additional_holdout_summaries = []
    for slug, station in additional_stations.items():
        station_depths = _read_daily_depths(PROCESSED_DIR / f"{slug}.daily.csv")
        station_depths = {
            day: depth
            for day, depth in station_depths.items()
            if day <= history.dates_utc[-1]
        }
        station_history = prepare_center_fit_pressure_history(
            center_depths,
            station_depths,
            center_compliance_m_per_mpa=center_compliance_m_per_mpa,
        )
        if station_history.dates_utc[0] != history.dates_utc[0]:
            raise ValueError(
                f"additional BPR overlap for {slug} starts at a different baseline"
            )
        station_rows, station_metrics = compare_model_history(
            station_history,
            times_s,
            center_model_m,
            model_uplift_by_station_m[slug],
        )
        station_rows = [
            {
                "time_utc": row["time_utc"],
                "pressure_change_mpa": row["pressure_change_mpa"],
                "center_observed_uplift_m": row["center_observed_uplift_m"],
                "center_model_uplift_m": row["center_model_uplift_m"],
                "center_residual_m": row["center_residual_m"],
                f"{slug}_observed_uplift_m": row["south_observed_uplift_m"],
                f"{slug}_model_uplift_m": row["south_model_uplift_m"],
                f"{slug}_residual_m": row["south_residual_m"],
            }
            for row in station_rows
        ]
        station_csv = output_dir / (
            f"historical_generalized_maxwell_{event}_{slug}.csv"
        )
        with station_csv.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(station_rows[0]))
            writer.writeheader()
            writer.writerows(station_rows)
        additional_holdout_summaries.append(
            {
                "station_slug": slug,
                "station": station.station,
                "raw_channel": station.raw_channel,
                "paired_daily_sample_count": station_metrics[
                    "paired_daily_sample_count"
                ],
                "overlap_start_utc": station_metrics["overlap_start_utc"],
                "overlap_end_utc": station_metrics["overlap_end_utc"],
                "metrics": station_metrics["south"],
                "series_csv": station_csv.name,
            }
        )

    comparison_type = "eruption-window" if event in EVENT_PAIRS else "deployment-overlap"
    summary: dict[str, object] = {
        "method": (
            "three-branch Maxwell forward run driven by Center pressure inferred "
            "from static elastic compliance"
        ),
        "comparison": event,
        "comparison_type": comparison_type,
        "center_station": center.station,
        "south_station": south.station,
        "center_raw_channel": center.raw_channel,
        "south_raw_channel": south.raw_channel,
        "observation_provenance": "original raw NCEI/MGDS BPR channels",
        "paper_publication_data_used": False,
        "pressure_history_calibration": (
            "daily Center uplift divided by the 1 MPa static PyLith elastic "
            "compliance; first shared daily sample sets zero"
        ),
        "pressure_history_is_viscoelastic_calibration": False,
        "static_center_compliance_m_per_mpa": center_compliance_m_per_mpa,
        "pressure_change_range_mpa": metrics["pressure_change_range_mpa"],
        "overlap_start_utc": metrics["overlap_start_utc"],
        "overlap_end_utc": metrics["overlap_end_utc"],
        "paired_daily_sample_count": metrics["paired_daily_sample_count"],
        "youngs_modulus_pa": YOUNGS_MODULUS_PA,
        "poisson_ratio": POISSON_RATIO,
        "density_kg_m3": DENSITY_KG_M3,
        "branch_reference_viscosity_pa_s": REFERENCE_VISCOSITY_PA_S_BY_BRANCH.tolist(),
        "branch_shear_modulus_fraction": SHEAR_RATIO_BY_BRANCH.tolist(),
        "branch_parameters_are_synthetic": True,
        "branch_temperature_law": "Eq. 15 Arrhenius viscosity on the steady Eq. 14/Eq. 22 field",
        "temperature_feedback": False,
        "initial_timestep_s": min(INITIAL_DT_S, float(history.elapsed_seconds[-1])),
        "maximum_output_step_s": maximum_step_s,
        "minimum_branch_relaxation_time_s": minimum_relaxation_time_s,
        "one_fifth_relaxation_time_limit_passed": True,
        "center": metrics["center"],
        "south": metrics["south"],
        "additional_held_out_stations": additional_holdout_summaries,
        "provisional_failure_threshold_analysis": failure_summary,
        "mesh_tetrahedra": len(material),
        "static_ellipsoid_mesh_converged": False,
        "tide_or_drift_correction_applied": False,
        "limitations": [
            "pressure history uses static elastic compliance, not a viscoelastic inversion",
            "branch viscosities and fractions are synthetic because the written source "
            "does not specify them",
            "the 7-day PyLith step smooths daily pressure changes between output times",
            "raw daily means retain ocean variability and instrument drift",
            "the ellipsoid compliance mesh is not converged",
        ],
    }
    summary_path = output_dir / f"historical_generalized_maxwell_{event}.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"wrote {series_path} and {summary_path}")
    return summary


def _run_2011_continuous_followup(
    deployments: dict[str, object],
    *,
    mesh_path: Path,
    material_database: Path,
    center_compliance_m_per_mpa: float,
    output_dir: Path,
) -> dict[str, object]:
    """Carry the 2011 event stress state into the later raw BPR deployment."""
    center_2010_slug = "nemo_2010_2011_center"
    south_2010_slug = "nemo_2009_2011_south"
    center_2011_slug = "nemo_2011_2013_center"
    south_2011_slug = "nemo_2011_2013_south"
    center_2010 = deployments[center_2010_slug]
    south_2010 = deployments[south_2010_slug]
    center_2011 = deployments[center_2011_slug]
    south_2011 = deployments[south_2011_slug]
    center_2010_depth = _read_daily_depths(
        PROCESSED_DIR / f"{center_2010_slug}.daily.csv"
    )
    center_2011_depth = _read_daily_depths(
        PROCESSED_DIR / f"{center_2011_slug}.daily.csv"
    )
    forcing = prepare_contiguous_center_pressure_forcing(
        center_2010_depth,
        center_2011_depth,
        center_compliance_m_per_mpa=center_compliance_m_per_mpa,
    )
    pressure_by_date = dict(zip(forcing.dates_utc, forcing.pressure_change_mpa, strict=True))

    event = "2011_continuous_followup"
    run_dir = STEP_DIR / "output" / event
    if run_dir.exists():
        shutil.rmtree(run_dir)
    _configure_run(
        run_dir,
        mesh_path,
        material_database,
        forcing.elapsed_seconds,
        forcing.pressure_change_mpa,
    )
    _run_pylith(run_dir)
    station_map = {
        center_2010_slug: center_2010,
        south_2010_slug: south_2010,
        center_2011_slug: center_2011,
        south_2011_slug: south_2011,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    times_s, model_by_station_m = _read_surface_history(
        run_dir / "output" / "genmaxwell-surface.h5",
        center_2010,
        station_map,
    )
    if times_s[0] > 0.0:
        times_s = np.insert(times_s, 0, 0.0)
        model_by_station_m = {
            slug: np.insert(uplift, 0, 0.0)
            for slug, uplift in model_by_station_m.items()
        }
    if times_s[-1] < forcing.elapsed_seconds[-1]:
        raise ValueError("continuous PyLith output ends before the final BPR record")

    south_segments = []
    for segment, center_slug, south_slug in (
        ("eruption", center_2010_slug, south_2010_slug),
        ("followup", center_2011_slug, south_2011_slug),
    ):
        center_depth = (
            center_2010_depth if center_slug == center_2010_slug else center_2011_depth
        )
        south_depth = _read_daily_depths(PROCESSED_DIR / f"{south_slug}.daily.csv")
        dates = tuple(sorted(center_depth.keys() & south_depth.keys()))
        if len(dates) < 5:
            raise ValueError(f"2011 {segment} has fewer than five paired daily records")
        first_date = dates[0]
        center_uplift = np.asarray(
            [center_depth[first_date] - center_depth[day] for day in dates], dtype=float
        )
        south_uplift = np.asarray(
            [south_depth[first_date] - south_depth[day] for day in dates], dtype=float
        )
        elapsed_seconds = np.asarray(
            [(day - forcing.dates_utc[0]).days * 86_400.0 for day in dates],
            dtype=float,
        )
        pressure = np.asarray([pressure_by_date[day] for day in dates], dtype=float)
        segment_history = HistoricalPressureHistory(
            dates_utc=dates,
            elapsed_seconds=elapsed_seconds,
            center_uplift_m=center_uplift,
            south_uplift_m=south_uplift,
            pressure_change_mpa=pressure,
        )
        model_origin_s = float(elapsed_seconds[0])
        segment_center_model = model_by_station_m[center_slug] - np.interp(
            model_origin_s, times_s, model_by_station_m[center_slug]
        )
        segment_south_model = model_by_station_m[south_slug] - np.interp(
            model_origin_s, times_s, model_by_station_m[south_slug]
        )
        rows, metrics = compare_model_history(
            segment_history,
            times_s,
            segment_center_model,
            segment_south_model,
        )
        series_path = output_dir / (
            f"historical_generalized_maxwell_2011_{segment}_continuous.csv"
        )
        with series_path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        south_segments.append(
            {
                "segment": segment,
                "center_station": deployments[center_slug].station,
                "center_raw_channel": deployments[center_slug].raw_channel,
                "south_station": deployments[south_slug].station,
                "south_raw_channel": deployments[south_slug].raw_channel,
                "record_count": len(rows),
                "start_utc": dates[0].isoformat(),
                "end_utc": dates[-1].isoformat(),
                "center_fit": metrics["center"],
                "south_holdout": metrics["south"],
                "series_csv": series_path.name,
            }
        )

    material = np.atleast_2d(np.loadtxt(material_database, comments="#", skiprows=13))
    relaxation_times_s = generalized_maxwell_relaxation_times_s(
        YOUNGS_MODULUS_PA,
        POISSON_RATIO,
        material[:, 6:9].T,
        material[:, 9:12].T,
    )
    maximum_step_s = float(np.max(np.diff(times_s)))
    minimum_relaxation_time_s = float(np.min(relaxation_times_s))
    if maximum_step_s > minimum_relaxation_time_s / 5.0:
        raise ValueError(
            "continuous PyLith step exceeds one-fifth of the minimum relaxation time"
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    failure_summary = _analyze_failure_history(
        run_dir / "output" / "genmaxwell-material.h5", event, output_dir
    )
    summary: dict[str, object] = {
        "method": (
            "continuous three-branch Maxwell forward run driven by two same-site "
            "raw Center BPR deployments"
        ),
        "comparison": event,
        "comparison_type": "2011 eruption plus post-eruption followup",
        "observation_provenance": "original raw MGDS Depth/RawDep BPR channels",
        "paper_publication_data_used": False,
        "pressure_history_calibration": (
            "each raw Center deployment is differenced from its first valid day; "
            "the second segment is offset to the terminal pressure of the first"
        ),
        "static_center_compliance_m_per_mpa": center_compliance_m_per_mpa,
        "pressure_change_range_mpa": [
            float(np.min(forcing.pressure_change_mpa)),
            float(np.max(forcing.pressure_change_mpa)),
        ],
        "center_deployment_transition_gap_days": forcing.transition_gap_days,
        "transition_gap_pressure_assumption": (
            "pressure is held at its final pre-gap value; the two Center records "
            "do not overlap"
        ),
        "continuous_history_start_utc": forcing.dates_utc[0].isoformat(),
        "continuous_history_end_utc": forcing.dates_utc[-1].isoformat(),
        "continuous_history_record_count": len(forcing.dates_utc),
        "segments": south_segments,
        "branch_reference_viscosity_pa_s": REFERENCE_VISCOSITY_PA_S_BY_BRANCH.tolist(),
        "branch_shear_modulus_fraction": SHEAR_RATIO_BY_BRANCH.tolist(),
        "branch_parameters_are_synthetic": True,
        "maximum_output_step_s": maximum_step_s,
        "minimum_branch_relaxation_time_s": minimum_relaxation_time_s,
        "one_fifth_relaxation_time_limit_passed": True,
        "provisional_failure_threshold_analysis": failure_summary,
        "mesh_tetrahedra": len(material),
        "static_ellipsoid_mesh_converged": False,
        "tide_or_drift_correction_applied": False,
        "limitations": [
            "center pressure is inferred from static, nonconverged compliance",
            "instrument changes are baselined independently and do not overlap",
            "pressure is held constant through the five-day deployment gap",
            "branch viscosities and fractions are synthetic",
            "South residuals retain raw ocean variability and instrument drift",
        ],
    }
    summary_path = output_dir / f"historical_generalized_maxwell_{event}.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"wrote {summary_path}")
    return summary


def _run_1998_continuous_followup(
    deployments: dict[str, object],
    *,
    mesh_path: Path,
    material_database: Path,
    center_compliance_m_per_mpa: float,
    output_dir: Path,
) -> dict[str, object]:
    """Carry the 1998 event stress state through the raw South BPR follow-up."""
    center_slug = "wc81_1997"
    south_event_slug = "wc82a_1997"
    south_followup_slug = "wc82b_1998"
    center = deployments[center_slug]
    south_event = deployments[south_event_slug]
    south_followup = deployments[south_followup_slug]
    if not np.allclose(
        (south_event.latitude, south_event.longitude),
        (south_followup.latitude, south_followup.longitude),
        rtol=0.0,
        atol=1.0e-6,
    ):
        raise ValueError("WC82 South records do not identify the same deployment site")
    center_depth = _read_daily_depths(
        PROCESSED_DIR / f"{center_slug}.daily.csv"
    )
    south_event_depth = _read_daily_depths(
        PROCESSED_DIR / f"{south_event_slug}.daily.csv"
    )
    south_followup_depth = _read_daily_depths(
        PROCESSED_DIR / f"{south_followup_slug}.daily.csv"
    )
    event_history = prepare_center_fit_pressure_history(
        center_depth,
        south_event_depth,
        center_compliance_m_per_mpa=center_compliance_m_per_mpa,
    )
    south_station_history = stitch_overlapping_station_uplift(
        south_event_depth, south_followup_depth
    )
    if south_station_history.dates_utc[0] != event_history.dates_utc[0]:
        raise ValueError("1998 Center and South BPR baselines must share a start date")
    if south_station_history.dates_utc[-1] <= event_history.dates_utc[-1]:
        raise ValueError("1998 South follow-up must extend beyond the Center record")

    full_elapsed_s = np.append(
        event_history.elapsed_seconds,
        (south_station_history.dates_utc[-1] - event_history.dates_utc[0]).days
        * 86_400.0,
    )
    full_pressure_mpa = np.append(
        event_history.pressure_change_mpa,
        event_history.pressure_change_mpa[-1],
    )
    event = "1998_continuous_followup"
    run_dir = STEP_DIR / "output" / event
    if run_dir.exists():
        shutil.rmtree(run_dir)
    _configure_run(
        run_dir,
        mesh_path,
        material_database,
        full_elapsed_s,
        full_pressure_mpa,
    )
    _run_pylith(run_dir)
    stations = {
        center_slug: center,
        south_event_slug: south_event,
        south_followup_slug: south_followup,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    times_s, model_by_station_m = _read_surface_history(
        run_dir / "output" / "genmaxwell-surface.h5", center, stations
    )
    if times_s[0] > 0.0:
        times_s = np.insert(times_s, 0, 0.0)
        model_by_station_m = {
            slug: np.insert(uplift, 0, 0.0)
            for slug, uplift in model_by_station_m.items()
        }
    if times_s[-1] < full_elapsed_s[-1]:
        raise ValueError("continuous 1998 PyLith output ends before the South record")

    event_rows, event_metrics = compare_model_history(
        event_history,
        times_s,
        model_by_station_m[center_slug],
        model_by_station_m[south_event_slug],
    )
    event_csv = output_dir / "historical_generalized_maxwell_1998_event_continuous.csv"
    with event_csv.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(event_rows[0]))
        writer.writeheader()
        writer.writerows(event_rows)

    followup_start = event_history.dates_utc[-1] + timedelta(days=1)
    uplift_by_date = dict(
        zip(
            south_station_history.dates_utc,
            south_station_history.relative_uplift_m,
            strict=True,
        )
    )
    followup_dates = tuple(
        day for day in south_station_history.dates_utc if day >= followup_start
    )
    if len(followup_dates) < 5:
        raise ValueError("1998 post-Center South follow-up has too few daily records")
    followup_observed = np.asarray(
        [uplift_by_date[day] - uplift_by_date[followup_dates[0]] for day in followup_dates],
        dtype=float,
    )
    followup_elapsed_s = np.asarray(
        [(day - event_history.dates_utc[0]).days * 86_400.0 for day in followup_dates],
        dtype=float,
    )
    followup_origin_s = float(followup_elapsed_s[0])
    followup_model = np.interp(
        followup_elapsed_s,
        times_s,
        model_by_station_m[south_followup_slug],
    )
    followup_model -= float(
        np.interp(followup_origin_s, times_s, model_by_station_m[south_followup_slug])
    )
    followup_residual = followup_model - followup_observed
    followup_correlation = (
        float(np.corrcoef(followup_observed, followup_model)[0, 1])
        if np.std(followup_observed) > 0.0 and np.std(followup_model) > 0.0
        else None
    )
    followup_metrics: dict[str, float | None] = {
        "rmse_m": float(np.sqrt(np.mean(followup_residual**2))),
        "bias_m": float(np.mean(followup_residual)),
        "correlation": followup_correlation,
    }
    followup_rows = [
        {
            "time_utc": f"{day.isoformat()}T00:00:00Z",
            "pressure_change_mpa": float(event_history.pressure_change_mpa[-1]),
            "south_observed_uplift_m": float(observed),
            "south_model_uplift_m": float(predicted),
            "south_residual_m": float(residual),
        }
        for day, observed, predicted, residual in zip(
            followup_dates,
            followup_observed,
            followup_model,
            followup_residual,
            strict=True,
        )
    ]
    followup_csv = output_dir / "historical_generalized_maxwell_1998_followup_continuous.csv"
    with followup_csv.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(followup_rows[0]))
        writer.writeheader()
        writer.writerows(followup_rows)

    material = np.atleast_2d(np.loadtxt(material_database, comments="#", skiprows=13))
    relaxation_times_s = generalized_maxwell_relaxation_times_s(
        YOUNGS_MODULUS_PA,
        POISSON_RATIO,
        material[:, 6:9].T,
        material[:, 9:12].T,
    )
    maximum_step_s = float(np.max(np.diff(times_s)))
    minimum_relaxation_time_s = float(np.min(relaxation_times_s))
    if maximum_step_s > minimum_relaxation_time_s / 5.0:
        raise ValueError("continuous 1998 PyLith step exceeds the relaxation-time limit")
    failure_summary = _analyze_failure_history(
        run_dir / "output" / "genmaxwell-material.h5", event, output_dir
    )
    forcing_hold_days = (
        south_station_history.dates_utc[-1] - event_history.dates_utc[-1]
    ).days
    summary: dict[str, object] = {
        "method": (
            "continuous three-branch Maxwell forward run driven by the original "
            "raw WC81 Center BPR, then held at terminal inferred pressure"
        ),
        "comparison": event,
        "comparison_type": "1998 eruption plus post-eruption followup",
        "observation_provenance": "original raw NCEI absolute-pressure BPR channels",
        "raw_channel_center": center.raw_channel,
        "raw_channels_south": [south_event.raw_channel, south_followup.raw_channel],
        "paper_publication_data_used": False,
        "pressure_history_calibration": (
            "daily WC81 uplift divided by the 1 MPa static PyLith elastic "
            "compliance through the final Center record"
        ),
        "static_center_compliance_m_per_mpa": center_compliance_m_per_mpa,
        "pressure_change_range_mpa": [
            float(np.min(full_pressure_mpa)),
            float(np.max(full_pressure_mpa)),
        ],
        "continuous_history_start_utc": event_history.dates_utc[0].isoformat(),
        "center_pressure_record_end_utc": event_history.dates_utc[-1].isoformat(),
        "continuous_history_end_utc": south_station_history.dates_utc[-1].isoformat(),
        "center_pressure_record_count": len(event_history.dates_utc),
        "south_stitched_record_count": len(south_station_history.dates_utc),
        "south_source_overlap_days": south_station_history.overlap_day_count,
        "south_second_segment_offset_m": south_station_history.second_segment_offset_m,
        "south_overlap_alignment_rmse_m": south_station_history.overlap_rmse_m,
        "constant_terminal_pressure_hold_days": forcing_hold_days,
        "event_window": {
            "record_count": event_metrics["paired_daily_sample_count"],
            "start_utc": event_metrics["overlap_start_utc"],
            "end_utc": event_metrics["overlap_end_utc"],
            "center_fit": event_metrics["center"],
            "south_holdout": event_metrics["south"],
        },
        "post_center_south_followup": {
            "record_count": len(followup_rows),
            "start_utc": followup_dates[0].isoformat(),
            "end_utc": followup_dates[-1].isoformat(),
            "south_holdout": followup_metrics,
        },
        "branch_reference_viscosity_pa_s": REFERENCE_VISCOSITY_PA_S_BY_BRANCH.tolist(),
        "branch_shear_modulus_fraction": SHEAR_RATIO_BY_BRANCH.tolist(),
        "branch_parameters_are_synthetic": True,
        "maximum_output_step_s": maximum_step_s,
        "minimum_branch_relaxation_time_s": minimum_relaxation_time_s,
        "one_fifth_relaxation_time_limit_passed": True,
        "provisional_failure_threshold_analysis": failure_summary,
        "mesh_tetrahedra": len(material),
        "static_ellipsoid_mesh_converged": False,
        "tide_or_drift_correction_applied": False,
        "limitations": [
            "Center pressure is inferred from static, nonconverged compliance",
            "terminal inferred pressure is held constant after the Center record ends",
            "the South archive segments are aligned using their eight-day raw overlap",
            "branch viscosities and fractions are synthetic",
            "South residuals retain raw ocean variability and instrument drift",
        ],
    }
    summary_path = output_dir / f"historical_generalized_maxwell_{event}.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"wrote {event_csv}, {followup_csv}, and {summary_path}")
    return summary


def _plot_comparisons(output_dir: Path, figure_stem: Path) -> tuple[Path, Path]:
    """Plot observed and modeled Center/South histories for both events."""
    figure, axes = plt.subplots(2, 1, figsize=(11.5, 8.2), sharex=False)
    styles = {
        "center_observed_uplift_m": ("#0072B2", "Center observed", "-"),
        "center_model_uplift_m": ("#0072B2", "Center Maxwell", "--"),
        "south_observed_uplift_m": ("#D55E00", "South observed", "-"),
        "south_model_uplift_m": ("#D55E00", "South Maxwell", "--"),
    }
    deployments = {deployment.slug: deployment for deployment in DEPLOYMENTS}
    for axis, event in zip(axes, EVENT_PAIRS, strict=True):
        series_path = output_dir / f"historical_generalized_maxwell_{event}.csv"
        with series_path.open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        times = [date.fromisoformat(row["time_utc"][:10]) for row in rows]
        center_station = deployments[EVENT_PAIRS[event][0]].station
        south_station = deployments[EVENT_PAIRS[event][1]].station
        for field, (color, label, linestyle) in styles.items():
            axis.plot(
                times,
                [float(row[field]) for row in rows],
                color=color,
                label=label,
                linestyle=linestyle,
                linewidth=1.0 if linestyle == "-" else 1.2,
            )
        axis.axvline(ERUPTION_DATES[event], color="#555555", linewidth=0.9, linestyle=":")
        axis.axhline(0.0, color="#555555", linewidth=0.6)
        axis.set_title(f"{event}: {center_station} forcing; {south_station} held out")
        axis.set_ylabel("Relative elevation (m; up positive)")
        axis.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        axis.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        axis.grid(True, color="#D9D9D9", linewidth=0.55)
        axis.legend(frameon=False, ncol=2, loc="best")
    axes[-1].set_xlabel("Date (UTC)")
    figure.suptitle(
        "Historical three-branch Maxwell forward checks from original raw BPR channels\n"
        "Synthetic branch parameters; center pressure inferred with static compliance"
    )
    figure.autofmt_xdate()
    figure.tight_layout()
    figure_stem.parent.mkdir(parents=True, exist_ok=True)
    png_path = figure_stem.with_suffix(".png")
    pdf_path = figure_stem.with_suffix(".pdf")
    figure.savefig(png_path, dpi=220)
    figure.savefig(pdf_path)
    plt.close(figure)
    return png_path, pdf_path


def _plot_2011_continuous_followup(
    output_dir: Path, figure_stem: Path
) -> tuple[Path, Path]:
    """Plot event and follow-up deployment segments against one model history."""
    figure, axes = plt.subplots(2, 1, figsize=(11.5, 8.2), sharex=False)
    series = (
        ("eruption", "2010–11 BPR pair; includes April 2011 eruption"),
        ("followup", "2011–13 replacement BPR pair"),
    )
    styles = {
        "center_observed_uplift_m": ("#0072B2", "Center observed", "-"),
        "center_model_uplift_m": ("#0072B2", "Center Maxwell", "--"),
        "south_observed_uplift_m": ("#D55E00", "South observed", "-"),
        "south_model_uplift_m": ("#D55E00", "South Maxwell", "--"),
    }
    for axis, (segment, title) in zip(axes, series, strict=True):
        series_path = output_dir / (
            f"historical_generalized_maxwell_2011_{segment}_continuous.csv"
        )
        with series_path.open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        times = [date.fromisoformat(row["time_utc"][:10]) for row in rows]
        for field, (color, label, linestyle) in styles.items():
            axis.plot(
                times,
                [float(row[field]) for row in rows],
                color=color,
                label=label,
                linestyle=linestyle,
                linewidth=1.0 if linestyle == "-" else 1.2,
            )
        if segment == "eruption":
            axis.axvline(
                ERUPTION_DATES["2011"],
                color="#555555",
                linewidth=0.9,
                linestyle=":",
            )
        axis.axhline(0.0, color="#555555", linewidth=0.6)
        axis.set_title(title)
        axis.set_ylabel("Relative elevation (m; up positive)")
        axis.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        axis.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        axis.grid(True, color="#D9D9D9", linewidth=0.55)
        axis.legend(frameon=False, ncol=2, loc="best")
    axes[-1].set_xlabel("Date (UTC)")
    figure.suptitle(
        "Continuous 2011 three-branch Maxwell check from original raw BPR channels\n"
        "Pressure carried across the nonoverlapping five-day Center deployment gap"
    )
    figure.autofmt_xdate()
    figure.tight_layout()
    figure_stem.parent.mkdir(parents=True, exist_ok=True)
    png_path = figure_stem.with_suffix(".png")
    pdf_path = figure_stem.with_suffix(".pdf")
    figure.savefig(png_path, dpi=220)
    figure.savefig(pdf_path)
    plt.close(figure)
    return png_path, pdf_path


def _plot_1998_continuous_followup(
    output_dir: Path, figure_stem: Path
) -> tuple[Path, Path]:
    """Plot the 1998 event and constant-load South follow-up windows."""
    figure, axes = plt.subplots(2, 1, figsize=(11.5, 8.2), sharex=False)
    event_path = output_dir / "historical_generalized_maxwell_1998_event_continuous.csv"
    with event_path.open(encoding="utf-8", newline="") as stream:
        event_rows = list(csv.DictReader(stream))
    event_dates = [date.fromisoformat(row["time_utc"][:10]) for row in event_rows]
    for field, color, label, linestyle in (
        ("center_observed_uplift_m", "#0072B2", "Center observed", "-"),
        ("center_model_uplift_m", "#0072B2", "Center Maxwell", "--"),
        ("south_observed_uplift_m", "#D55E00", "South observed", "-"),
        ("south_model_uplift_m", "#D55E00", "South Maxwell", "--"),
    ):
        axes[0].plot(
            event_dates,
            [float(row[field]) for row in event_rows],
            color=color,
            label=label,
            linestyle=linestyle,
            linewidth=1.0 if linestyle == "-" else 1.2,
        )
    axes[0].axvline(
        ERUPTION_DATES["1998"], color="#555555", linewidth=0.9, linestyle=":"
    )
    axes[0].axhline(0.0, color="#555555", linewidth=0.6)
    axes[0].set_title("WC81 Center forcing and WC82 South holdout through 1998-08-07")
    axes[0].set_ylabel("Relative elevation (m; up positive)")
    axes[0].legend(frameon=False, ncol=2, loc="best")

    followup_path = (
        output_dir / "historical_generalized_maxwell_1998_followup_continuous.csv"
    )
    with followup_path.open(encoding="utf-8", newline="") as stream:
        followup_rows = list(csv.DictReader(stream))
    followup_dates = [date.fromisoformat(row["time_utc"][:10]) for row in followup_rows]
    axes[1].plot(
        followup_dates,
        [float(row["south_observed_uplift_m"]) for row in followup_rows],
        color="#D55E00",
        label="South observed",
        linewidth=1.0,
    )
    axes[1].plot(
        followup_dates,
        [float(row["south_model_uplift_m"]) for row in followup_rows],
        color="#D55E00",
        label="South Maxwell",
        linestyle="--",
        linewidth=1.2,
    )
    axes[1].axhline(0.0, color="#555555", linewidth=0.6)
    axes[1].set_title("South holdout after Center pressure observations end")
    axes[1].set_ylabel("Relative elevation (m; up positive)")
    axes[1].set_xlabel("Date (UTC)")
    axes[1].legend(frameon=False, loc="best")

    for axis in axes:
        axis.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        axis.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        axis.grid(True, color="#D9D9D9", linewidth=0.55)
    figure.suptitle(
        "Continuous 1998 three-branch Maxwell check from raw NCEI BPR channels\n"
        "Terminal inferred Center pressure held constant through May 1999"
    )
    figure.autofmt_xdate()
    figure.tight_layout()
    figure_stem.parent.mkdir(parents=True, exist_ok=True)
    png_path = figure_stem.with_suffix(".png")
    pdf_path = figure_stem.with_suffix(".pdf")
    figure.savefig(png_path, dpi=220)
    figure.savefig(pdf_path)
    plt.close(figure)
    return png_path, pdf_path


def _plot_deployment_comparisons(
    output_dir: Path, figure_stem: Path
) -> tuple[Path, Path]:
    """Plot raw and modeled histories for inter-eruption station overlaps."""
    available_pairs = {
        name: pair
        for name, pair in DEPLOYMENT_PAIRS.items()
        if (output_dir / f"historical_generalized_maxwell_{name}.csv").is_file()
    }
    if not available_pairs:
        raise FileNotFoundError("no historical deployment-overlap results to plot")
    figure, axes = plt.subplots(
        len(available_pairs),
        1,
        figsize=(11.5, 3.2 * len(available_pairs)),
        sharex=False,
        constrained_layout=True,
    )
    styles = {
        "center_observed_uplift_m": ("#0072B2", "Center observed", "-"),
        "center_model_uplift_m": ("#0072B2", "Center Maxwell", "--"),
        "south_observed_uplift_m": ("#D55E00", "South observed", "-"),
        "south_model_uplift_m": ("#D55E00", "South Maxwell", "--"),
    }
    deployments = {deployment.slug: deployment for deployment in DEPLOYMENTS}
    for axis, (name, (center_slug, south_slug)) in zip(
        axes, available_pairs.items(), strict=True
    ):
        series_path = output_dir / f"historical_generalized_maxwell_{name}.csv"
        with series_path.open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        times = [date.fromisoformat(row["time_utc"][:10]) for row in rows]
        for field, (color, label, linestyle) in styles.items():
            axis.plot(
                times,
                [float(row[field]) for row in rows],
                color=color,
                label=label,
                linestyle=linestyle,
                linewidth=1.0 if linestyle == "-" else 1.2,
            )
        for extra_slug in ADDITIONAL_HELDOUTS.get(name, ()):
            extra_path = output_dir / (
                f"historical_generalized_maxwell_{name}_{extra_slug}.csv"
            )
            with extra_path.open(encoding="utf-8", newline="") as stream:
                extra_rows = list(csv.DictReader(stream))
            extra_times = [
                date.fromisoformat(row["time_utc"][:10]) for row in extra_rows
            ]
            extra_color = "#009E73" if extra_slug == "wc67_1995" else "#CC79A7"
            extra_label = deployments[extra_slug].station
            axis.plot(
                extra_times,
                [float(row[f"{extra_slug}_observed_uplift_m"]) for row in extra_rows],
                color=extra_color,
                label=f"{extra_label} observed",
                linewidth=1.0,
            )
            axis.plot(
                extra_times,
                [float(row[f"{extra_slug}_model_uplift_m"]) for row in extra_rows],
                color=extra_color,
                label=f"{extra_label} Maxwell",
                linestyle="--",
                linewidth=1.2,
            )
        center_station = deployments[center_slug].station
        south_station = deployments[south_slug].station
        axis.axhline(0.0, color="#555555", linewidth=0.6)
        axis.set_title(f"{name.replace('_', '–')}: {center_station}; {south_station}")
        axis.set_ylabel("Relative elevation (m; up positive)")
        axis.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
        axis.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        axis.grid(True, color="#D9D9D9", linewidth=0.55)
        axis.legend(frameon=False, ncol=3, loc="best")
    figure.suptitle(
        "Three-branch Maxwell checks across raw inter-eruption BPR deployments\n"
        "Separate deployment windows; no interpolation across data gaps"
    )
    figure_stem.parent.mkdir(parents=True, exist_ok=True)
    png_path = figure_stem.with_suffix(".png")
    pdf_path = figure_stem.with_suffix(".pdf")
    figure.savefig(png_path, dpi=220)
    figure.savefig(pdf_path)
    plt.close(figure)
    return png_path, pdf_path


def main() -> None:
    """Run historical three-branch checks for eruptions and deployment overlaps."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mesh", type=Path, required=True)
    parser.add_argument("--material-database", type=Path, required=True)
    parser.add_argument(
        "--elastic-surface",
        type=Path,
        default=ELASTIC_SURFACE,
        help="static 1 MPa PyLith surface output used for provisional pressure inference",
    )
    parser.add_argument("--output-dir", type=Path, default=PROCESSED_DIR)
    parser.add_argument(
        "--figure-stem",
        type=Path,
        default=ROOT / "figures" / "historical_generalized_maxwell_bpr_check",
    )
    followup_group = parser.add_mutually_exclusive_group()
    followup_group.add_argument(
        "--only-1998-continuous-followup",
        action="store_true",
        help="run the continuous 1997–1999 BPR event and follow-up check only",
    )
    followup_group.add_argument(
        "--only-2011-continuous-followup",
        action="store_true",
        help="run the continuous 2010–2013 BPR event and follow-up check only",
    )
    followup_group.add_argument(
        "--only-post-2011-deployment-checks",
        action="store_true",
        help="run the 2013–2017 raw BPR deployment overlaps only",
    )
    args = parser.parse_args()
    for required in (args.mesh, args.material_database, args.elastic_surface):
        if not required.is_file():
            raise FileNotFoundError(required)

    deployments = {deployment.slug: deployment for deployment in DEPLOYMENTS}
    center_response, _ = read_ellipsoid_unit_response(args.elastic_surface)
    center_compliance = float(center_response[2])
    if args.only_1998_continuous_followup:
        _run_1998_continuous_followup(
            deployments,
            mesh_path=args.mesh,
            material_database=args.material_database,
            center_compliance_m_per_mpa=center_compliance,
            output_dir=args.output_dir,
        )
        figure_stem = args.figure_stem.with_name(
            "historical_generalized_maxwell_1998_continuous_bpr_check"
        )
        png_path, pdf_path = _plot_1998_continuous_followup(
            args.output_dir, figure_stem
        )
        print(f"wrote {png_path} and {pdf_path}")
        return
    if args.only_2011_continuous_followup:
        _run_2011_continuous_followup(
            deployments,
            mesh_path=args.mesh,
            material_database=args.material_database,
            center_compliance_m_per_mpa=center_compliance,
            output_dir=args.output_dir,
        )
        figure_stem = args.figure_stem.with_name(
            "historical_generalized_maxwell_2011_continuous_bpr_check"
        )
        png_path, pdf_path = _plot_2011_continuous_followup(
            args.output_dir, figure_stem
        )
        print(f"wrote {png_path} and {pdf_path}")
        return
    if args.only_post_2011_deployment_checks:
        for interval, pair in POST_2011_DEPLOYMENT_PAIRS.items():
            _run_event(
                interval,
                *pair,
                deployments,
                mesh_path=args.mesh,
                material_database=args.material_database,
                center_compliance_m_per_mpa=center_compliance,
                output_dir=args.output_dir,
            )
        interval_png, interval_pdf = _plot_deployment_comparisons(
            args.output_dir,
            args.figure_stem.with_name(
                "historical_generalized_maxwell_deployment_bpr_check"
            ),
        )
        print(f"wrote {interval_png} and {interval_pdf}")
        return
    for event, pair in EVENT_PAIRS.items():
        _run_event(
            event,
            *pair,
            deployments,
            mesh_path=args.mesh,
            material_database=args.material_database,
            center_compliance_m_per_mpa=center_compliance,
            output_dir=args.output_dir,
        )
    for interval, pair in CORE_DEPLOYMENT_PAIRS.items():
        _run_event(
            interval,
            *pair,
            deployments,
            mesh_path=args.mesh,
            material_database=args.material_database,
            center_compliance_m_per_mpa=center_compliance,
            output_dir=args.output_dir,
        )
    png_path, pdf_path = _plot_comparisons(args.output_dir, args.figure_stem)
    print(f"wrote {png_path} and {pdf_path}")
    interval_png, interval_pdf = _plot_deployment_comparisons(
        args.output_dir,
        args.figure_stem.with_name(
            "historical_generalized_maxwell_deployment_bpr_check"
        ),
    )
    print(f"wrote {interval_png} and {interval_pdf}")


if __name__ == "__main__":
    main()
