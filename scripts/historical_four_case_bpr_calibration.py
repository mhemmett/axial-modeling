"""Calibrate four written rheology cases to an independent BPR event pair."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import time
from datetime import UTC, datetime
from pathlib import Path

import h5py
import matplotlib
import numpy as np

matplotlib.use("Agg")

import historical_generalized_maxwell_bpr_check as historical
import matplotlib.dates as mdates
import matplotlib.pyplot as plt

from axialstress.bpr_mogi_calibration import local_east_north_offset_m
from axialstress.failure_analysis import analyze_stress_history
from axialstress.generalized_maxwell import generalized_maxwell_relaxation_times_s
from axialstress.historical_bpr import DEPLOYMENTS, PROCESSED_DIR
from axialstress.historical_bpr_corrections import PROCESSED_CORRECTED_DIR
from axialstress.historical_generalized_maxwell import SECONDS_PER_YEAR
from axialstress.historical_maxwell_pressure import (
    prepare_historical_maxwell_history,
    read_raw_daily_depths,
)
from axialstress.material_database import (
    write_generalized_maxwell_database,
    write_temperature_dependent_generalized_maxwell_database,
)
from axialstress.maxwell_pressure_inversion import (
    invert_pressure_history,
    ramp_response_operator,
)
from axialstress.surface_interpolation import interpolate_triangular_surface
from axialstress.thermal import temperature_range_youngs_modulus_pa
from axialstress.thermal_model import (
    _read_gmsh_tetrahedral_mesh,
    solve_written_thermal_model,
)

ROOT = Path(__file__).resolve().parents[1]
ELASTIC_STEP_DIR = ROOT / "pylith" / "step05_ellipsoid_elastic"
MAXWELL_STEP_DIR = ROOT / "pylith" / "step12_generalized_maxwell_ellipsoid"
DEFAULT_MESH = ELASTIC_STEP_DIR / "mesh" / "axial_ellipsoid.msh"
EVENTS: dict[str, dict[str, object]] = {
    "1998": {
        "eruption_date_utc": datetime(1998, 1, 25, tzinfo=UTC),
        "eruption_label": "25 Jan 1998 eruption",
        "center_slug": "wc81_1997",
        "south_slug": "wc82a_1997",
        "output_dir": ROOT / "data" / "processed" / "historical_four_case_bpr_calibration_1998",
        "figure_stem": ROOT / "figures" / "historical_four_case_bpr_calibration_1998",
    },
    "2011": {
        "eruption_date_utc": datetime(2011, 4, 6, tzinfo=UTC),
        "eruption_label": "6 Apr 2011 eruption",
        "center_slug": "nemo_2010_2011_center",
        "south_slug": "nemo_2009_2011_south",
        "output_dir": ROOT / "data" / "processed" / "historical_four_case_bpr_calibration",
        "figure_stem": ROOT / "figures" / "historical_four_case_bpr_calibration",
    },
}
CASE_LABELS = {
    "elastic": "Elastic",
    "non_td_maxwell": "Constant-property Maxwell",
    "td_maxwell": "Thermal Maxwell",
    "td_hydrothermal_maxwell": "Hydrothermal Maxwell",
}
TIME_STEP_DAYS = 7.0
YOUNGS_MODULUS_PA = 50.0e9
DENSITY_KG_M3 = 2700.0
POISSON_RATIO = 0.25
REFERENCE_VISCOSITY_PA_S_BY_BRANCH = np.asarray([1.0e18, 5.0e17, 2.0e18])
SHEAR_RATIO_BY_BRANCH = np.asarray([0.25, 0.25, 0.25])
REFERENCE_TEMPERATURE_C = 1200.0
COHESION_PA = 1.0e6
FRICTION_ANGLE_DEG = 25.0
PORE_PRESSURE_PA = 0.0


def _metrics(observed_m: np.ndarray, predicted_m: np.ndarray) -> dict[str, float | None]:
    """Summarize one BPR site's model residuals in meters."""
    residual = predicted_m - observed_m
    correlation = (
        float(np.corrcoef(observed_m, predicted_m)[0, 1])
        if np.std(observed_m) > 0.0 and np.std(predicted_m) > 0.0
        else None
    )
    return {
        "rmse_m": float(np.sqrt(np.mean(residual**2))),
        "bias_m": float(np.mean(residual)),
        "correlation": correlation,
    }


def _load_observations(
    event_name: str,
    event: dict[str, object],
    *,
    corrected_observations: bool,
):
    """Load a raw or tide/drift-corrected Center/South pressure pair."""
    deployments = {deployment.slug: deployment for deployment in DEPLOYMENTS}
    if corrected_observations:
        from axialstress.historical_bpr import FOX_1997_1998_DEPLOYMENTS

        deployments.update(
            {deployment.slug: deployment for deployment in FOX_1997_1998_DEPLOYMENTS}
        )
        corrected_slugs = {
            "1998": ("fox_wc81_1997_center", "fox_wc82_1997_south"),
            "2011": ("nemo_2010_2011_center", "nemo_2009_2011_south"),
        }
        center_slug, south_slug = corrected_slugs[event_name]
        summary_path = PROCESSED_CORRECTED_DIR / "summary.json"
        observation_dir = PROCESSED_CORRECTED_DIR
    else:
        center_slug = str(event["center_slug"])
        south_slug = str(event["south_slug"])
        summary_path = PROCESSED_DIR / "summary.json"
        observation_dir = PROCESSED_DIR
    center = deployments[center_slug]
    south = deployments[south_slug]
    if not summary_path.is_file():
        target = (
            "historical-bpr-corrected-daily"
            if corrected_observations
            else "historical-bpr-daily"
        )
        raise FileNotFoundError(f"BPR daily data are missing; run make {target}")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    processed = summary.get("deployments", {})
    observation_metadata = {}
    for deployment in (center, south):
        entry = processed.get(deployment.slug, {})
        if Path(entry.get("source_file", "")).resolve() != deployment.path.resolve():
            raise ValueError(f"{deployment.slug} does not identify its expected source file")
        if corrected_observations:
            if not entry.get("corrected_source_channel"):
                raise ValueError(f"{deployment.slug} has no corrected observation channel")
            observation_metadata[deployment.slug] = {
                "corrected_source_channel": entry["corrected_source_channel"],
                "correction_components": entry["correction_components"],
            }
        elif entry.get("raw_channel") != deployment.raw_channel:
            raise ValueError(f"{deployment.slug} does not identify the expected raw channel")
    history = prepare_historical_maxwell_history(
        read_raw_daily_depths(
            observation_dir / f"{center_slug}.daily.csv",
            expected_unit=center.raw_unit,
        ),
        read_raw_daily_depths(
            observation_dir / f"{south_slug}.daily.csv",
            expected_unit=south.raw_unit,
        ),
        center_station=center.station,
        south_station=south.station,
        center_lat_lon_deg=(center.latitude, center.longitude),
        south_lat_lon_deg=(south.latitude, south.longitude),
        target_interval_days=TIME_STEP_DAYS,
    )
    return history, center, south, observation_metadata


def _sample_static_sites(
    surface_path: Path,
    center: object,
    south: object,
) -> tuple[float, float]:
    """Sample one-megapascal elastic uplift at the two BPR coordinates."""
    with h5py.File(surface_path, "r") as surface:
        vertices = np.asarray(surface["geometry/vertices"], dtype=float)
        triangles = np.asarray(surface["viz/topology/cells"], dtype=np.int64)
        displacement = np.asarray(surface["vertex_fields/displacement"], dtype=float)
    if displacement.ndim != 3 or displacement.shape[1:] != vertices.shape:
        raise ValueError("static surface displacement has an unexpected shape")
    if not np.all(np.isfinite(displacement)):
        raise ValueError("static surface displacement contains non-finite values")
    uplift_by_site = []
    for station in (center, south):
        east_m, north_m = local_east_north_offset_m(
            station.latitude,
            station.longitude,
            origin_latitude_deg=center.latitude,
            origin_longitude_deg=center.longitude,
        )
        uplift_by_site.append(
            interpolate_triangular_surface(
                vertices, triangles, displacement[-1], (east_m, north_m)
            )[2]
        )
    return float(uplift_by_site[0]), float(uplift_by_site[1])


def _read_static_stress(
    material_path: Path,
    vertices_m: np.ndarray,
    tetrahedra: np.ndarray,
) -> np.ndarray:
    """Map the static unit-pressure Cauchy stress field onto the Gmsh mesh."""
    with h5py.File(material_path, "r") as material:
        static_vertices = np.asarray(material["geometry/vertices"], dtype=float)
        static_cells = np.asarray(material["viz/topology/cells"], dtype=np.int64)
        stress = np.asarray(material["cell_fields/cauchy_stress"][-1], dtype=float)
    if (
        static_vertices.shape != vertices_m.shape
        or static_cells.shape != tetrahedra.shape
        or stress.shape != (len(static_cells), 6)
        or not np.all(np.isfinite(static_vertices))
        or not np.all(np.isfinite(stress))
    ):
        raise ValueError("static elastic stress field is missing or non-finite")
    vertex_keys = [tuple(row) for row in np.round(vertices_m, decimals=8)]
    static_vertex_keys = [tuple(row) for row in np.round(static_vertices, decimals=8)]
    if len(set(vertex_keys)) != len(vertices_m) or len(set(static_vertex_keys)) != len(
        static_vertices
    ):
        raise ValueError("mesh coordinates collide at the stress-remapping precision")
    vertex_index_by_key = {key: index for index, key in enumerate(vertex_keys)}
    if set(vertex_index_by_key) != set(static_vertex_keys):
        raise ValueError("static elastic stress vertices differ from the four-case mesh")

    cell_index_by_vertices = {
        tuple(sorted(int(vertex) for vertex in cell)): index
        for index, cell in enumerate(tetrahedra)
    }
    if len(cell_index_by_vertices) != len(tetrahedra):
        raise ValueError("four-case mesh contains duplicate tetrahedra")
    remapped_stress = np.empty_like(stress)
    assigned_cells: set[int] = set()
    for static_cell, cell_stress in zip(static_cells, stress, strict=True):
        try:
            mapped_vertices = tuple(
                sorted(
                    vertex_index_by_key[
                        tuple(np.round(static_vertices[int(vertex)], decimals=8))
                    ]
                    for vertex in static_cell
                )
            )
            mesh_cell_index = cell_index_by_vertices[mapped_vertices]
        except KeyError as exc:
            raise ValueError("static elastic stress cells differ from the four-case mesh") from exc
        if mesh_cell_index in assigned_cells:
            raise ValueError("static elastic stress contains duplicate tetrahedra")
        remapped_stress[mesh_cell_index] = cell_stress
        assigned_cells.add(mesh_cell_index)
    if len(assigned_cells) != len(tetrahedra):
        raise ValueError("static elastic stress does not cover every four-case tetrahedron")
    return remapped_stress


def _write_case_materials(
    mesh_path: Path,
    output_dir: Path,
) -> tuple[dict[str, Path], dict[str, dict[str, object]]]:
    """Create the three synthetic Maxwell material maps for the written cases."""
    vertices, tetrahedra, _ = _read_gmsh_tetrahedral_mesh(mesh_path)
    thermal_archives = {
        "td_maxwell": output_dir / "thermal_baseline.npz",
        "td_hydrothermal_maxwell": output_dir / "thermal_hydrothermal.npz",
    }
    thermal_metadata: dict[str, dict[str, object]] = {}
    for name, hydrothermal in (("td_maxwell", False), ("td_hydrothermal_maxwell", True)):
        iterations, relative_change, minimum, maximum, *_ = solve_written_thermal_model(
            mesh_path,
            thermal_archives[name],
            hydrothermal=hydrothermal,
        )
        thermal_metadata[name] = {
            "hydrothermal_conductivity": hydrothermal,
            "iterations": iterations,
            "relative_change": relative_change,
            "temperature_c_range": [minimum, maximum],
            "boundary_assumption": "30 C/km geotherm on outer faces; 1200 C reservoir",
        }

    database_paths = {
        "non_td_maxwell": output_dir / "materials" / "non_td_maxwell.spatialdb",
        "td_maxwell": output_dir / "materials" / "td_maxwell.spatialdb",
        "td_hydrothermal_maxwell": (
            output_dir / "materials" / "td_hydrothermal_maxwell.spatialdb"
        ),
    }
    database_paths["non_td_maxwell"].parent.mkdir(parents=True, exist_ok=True)
    write_generalized_maxwell_database(
        database_paths["non_td_maxwell"],
        vertices,
        tetrahedra,
        YOUNGS_MODULUS_PA,
        density_kg_m3=DENSITY_KG_M3,
        poisson_ratio=POISSON_RATIO,
        viscosity_pa_s_by_branch=REFERENCE_VISCOSITY_PA_S_BY_BRANCH,
        shear_modulus_ratio_by_branch=SHEAR_RATIO_BY_BRANCH,
    )

    for case_name, archive_path in thermal_archives.items():
        with np.load(archive_path, allow_pickle=False) as thermal:
            archive_vertices = np.asarray(thermal["vertices_m"], dtype=float)
            archive_cells = np.asarray(thermal["tetrahedra"], dtype=np.int64)
            temperature_c = np.asarray(thermal["temperature_c"], dtype=float)
        if not np.array_equal(archive_vertices, vertices) or not np.array_equal(
            archive_cells, tetrahedra
        ):
            raise ValueError("thermal and mechanics meshes do not match")
        cell_temperature_c = temperature_c[tetrahedra].mean(axis=1)
        youngs_modulus_pa = temperature_range_youngs_modulus_pa(cell_temperature_c)
        write_temperature_dependent_generalized_maxwell_database(
            database_paths[case_name],
            vertices,
            tetrahedra,
            temperature_c,
            youngs_modulus_pa,
            density_kg_m3=DENSITY_KG_M3,
            poisson_ratio=POISSON_RATIO,
            reference_viscosity_pa_s_by_branch=REFERENCE_VISCOSITY_PA_S_BY_BRANCH,
            reference_temperature_c=REFERENCE_TEMPERATURE_C,
            shear_modulus_ratio_by_branch=SHEAR_RATIO_BY_BRANCH,
        )
        database = np.atleast_2d(
            np.loadtxt(database_paths[case_name], comments="#", skiprows=13)
        )
        thermal_metadata[case_name]["youngs_modulus_gpa_range"] = [
            float(np.min(youngs_modulus_pa) / 1.0e9),
            float(np.max(youngs_modulus_pa) / 1.0e9),
        ]
        thermal_metadata[case_name]["youngs_modulus_law"] = (
            "linear decrease from 50 GPa at 0 C to 20 GPa at 1200 C; clipped"
        )
        thermal_metadata[case_name]["branch_viscosity_pa_s_range"] = [
            float(np.min(database[:, 6:9])),
            float(np.max(database[:, 6:9])),
        ]
    return database_paths, thermal_metadata


def _validate_run_times(times_s: np.ndarray, elapsed_seconds: np.ndarray) -> None:
    """Require PyLith outputs on every requested pressure-knot interval."""
    expected = elapsed_seconds[1:]
    if times_s.shape != expected.shape or not np.allclose(
        times_s, expected, rtol=0.0, atol=1.0e-3
    ):
        raise ValueError(
            "PyLith output does not match the BPR inversion grid: "
            f"got {len(times_s)} records, expected {len(expected)}"
        )


def _run_maxwell_case(
    case_name: str,
    material_database: Path,
    *,
    event_name: str,
    history: object,
    center: object,
    south: object,
    mesh_path: Path,
    output_dir: Path,
) -> dict[str, object]:
    """Fit Center pressure for one Maxwell case and evaluate South and failure."""
    elapsed_seconds = np.asarray(history.elapsed_years * SECONDS_PER_YEAR, dtype=float)
    time_step_s = history.time_step_s
    interval_count = len(elapsed_seconds) - 1
    unit_pressure = np.concatenate(([0.0], np.ones(interval_count, dtype=float)))
    center_slug = center.slug
    south_slug = south.slug
    stations = {center_slug: center, south_slug: south}
    response_dir = output_dir / "runs" / case_name / "unit_ramp"
    historical._configure_run(
        response_dir,
        mesh_path,
        material_database,
        elapsed_seconds,
        unit_pressure,
        initial_dt_s=time_step_s,
        history_description=f"Unit pressure ramp for the {case_name} BPR kernel",
    )
    historical._run_pylith(response_dir)
    response_times_s, response_sites_m = historical._read_surface_history(
        response_dir / "output" / "genmaxwell-surface.h5",
        center,
        stations,
    )
    _validate_run_times(response_times_s, elapsed_seconds)
    center_operator = ramp_response_operator(response_sites_m[center_slug])
    south_operator = ramp_response_operator(response_sites_m[south_slug])
    inversion = invert_pressure_history(center_operator, history.center_uplift_m[1:])
    pressure_mpa = np.concatenate(([0.0], inversion.pressure_mpa))

    forward_dir = output_dir / "runs" / case_name / "center_calibrated_history"
    historical._configure_run(
        forward_dir,
        mesh_path,
        material_database,
        elapsed_seconds,
        pressure_mpa,
        initial_dt_s=time_step_s,
        history_description=(
            f"GCV-smoothed pressure fitted to raw Center BPR for {case_name}"
        ),
    )
    historical._run_pylith(forward_dir)
    times_s, modeled_sites_m = historical._read_surface_history(
        forward_dir / "output" / "genmaxwell-surface.h5",
        center,
        stations,
    )
    _validate_run_times(times_s, elapsed_seconds)
    center_kernel_m = center_operator @ inversion.pressure_mpa
    south_kernel_m = south_operator @ inversion.pressure_mpa
    center_model_m = modeled_sites_m[center_slug]
    south_model_m = modeled_sites_m[south_slug]
    center_superposition_error = float(
        np.linalg.norm(center_model_m - center_kernel_m)
        / max(np.linalg.norm(center_model_m), np.finfo(float).eps)
    )
    south_superposition_error = float(
        np.linalg.norm(south_model_m - south_kernel_m)
        / max(np.linalg.norm(south_model_m), np.finfo(float).eps)
    )
    if max(center_superposition_error, south_superposition_error) > 0.02:
        raise ValueError(f"{case_name} forward run failed linear superposition")

    material_path = forward_dir / "output" / "genmaxwell-material.h5"
    analysis_dir = output_dir / "analysis" / case_name
    analysis_dir.mkdir(parents=True, exist_ok=True)
    failure = historical._analyze_failure_history(
        material_path,
        f"{event_name}_{case_name}",
        analysis_dir,
    )
    output_rows = _write_series(
        output_dir,
        case_name,
        event_name=event_name,
        failure_csv=analysis_dir / str(failure["history_csv"]),
        history=history,
        times_s=times_s,
        pressure_mpa=pressure_mpa,
        center_observed_m=history.center_uplift_m[1:],
        south_observed_m=history.south_uplift_m[1:],
        center_model_m=center_model_m,
        south_model_m=south_model_m,
    )
    material = np.atleast_2d(
        np.loadtxt(material_database, comments="#", skiprows=13)
    )
    modulus_pa = (
        2.0
        * (1.0 + POISSON_RATIO)
        * material[:, 3]
        * (material[:, 4] * 1000.0) ** 2
    )
    relaxation_times_s = generalized_maxwell_relaxation_times_s(
        modulus_pa,
        POISSON_RATIO,
        material[:, 6:9].T,
        material[:, 9:12].T,
    )
    maximum_output_step_s = float(np.max(np.diff(times_s)))
    minimum_relaxation_time_s = float(np.min(relaxation_times_s))
    if maximum_output_step_s > minimum_relaxation_time_s / 5.0:
        raise ValueError(f"{case_name} output interval exceeds one-fifth of relaxation time")
    return {
        "case": case_name,
        "rheology": (
            "three-branch generalized Maxwell with synthetic branch viscosities "
            "and fractions"
        ),
        "fit_site": "Center",
        "held_out_site": "South",
        "pressure_change_range_mpa": [
            float(np.min(inversion.pressure_mpa)),
            float(np.max(inversion.pressure_mpa)),
        ],
        "regularization_coefficient": inversion.regularization,
        "effective_fit_parameters": inversion.effective_parameters,
        "center_kernel_fit_rmse_m": inversion.rmse_m,
        "center": _metrics(history.center_uplift_m[1:], center_model_m),
        "south": _metrics(history.south_uplift_m[1:], south_model_m),
        "center_kernel_superposition_relative_l2_error": center_superposition_error,
        "south_kernel_superposition_relative_l2_error": south_superposition_error,
        "maximum_output_step_s": maximum_output_step_s,
        "minimum_branch_relaxation_time_s": minimum_relaxation_time_s,
        "one_fifth_relaxation_time_limit_passed": True,
        "failure_threshold_diagnostic": failure,
        "timeseries_csv": str(output_rows.relative_to(ROOT)),
        "run_directory": str(forward_dir.relative_to(ROOT)),
    }


def _write_series(
    output_dir: Path,
    case_name: str,
    *,
    event_name: str,
    failure_csv: Path,
    history: object,
    times_s: np.ndarray,
    pressure_mpa: np.ndarray,
    center_observed_m: np.ndarray,
    south_observed_m: np.ndarray,
    center_model_m: np.ndarray,
    south_model_m: np.ndarray,
) -> Path:
    """Write one case's fitted load, BPR comparison, and path history."""
    with failure_csv.open(encoding="utf-8", newline="") as stream:
        failure_rows = list(csv.DictReader(stream))
    if len(failure_rows) != len(times_s):
        raise ValueError("failure records do not match surface output times")
    rows = [
        {
            "time_utc": history.times_utc[index + 1].isoformat(),
            "elapsed_days": float(time_value / 86_400.0),
            "pressure_change_mpa": float(pressure_mpa[index + 1]),
            "center_observed_uplift_m": float(center_observed_m[index]),
            "center_model_uplift_m": float(center_model_m[index]),
            "south_observed_uplift_m": float(south_observed_m[index]),
            "south_model_uplift_m": float(south_model_m[index]),
            "cavity_to_surface_shear_path_found": failure_rows[index][
                "cavity_to_surface_shear_path_found"
            ],
            "maximum_cavity_tensile_stress_pa": failure_rows[index][
                "maximum_cavity_tensile_stress_pa"
            ],
        }
        for index, time_value in enumerate(times_s)
    ]
    series_path = (
        output_dir
        / "analysis"
        / case_name
        / f"historical_four_case_{event_name}_{case_name}.csv"
    )
    with series_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return series_path


def _run_elastic_case(
    *,
    event_name: str,
    history: object,
    center: object,
    south: object,
    elastic_surface: Path,
    elastic_material: Path,
    mesh_path: Path,
    output_dir: Path,
) -> dict[str, object]:
    """Fit elastic pressure with a static operator and scale unit-load stress."""
    center_compliance_m_per_mpa, south_compliance_m_per_mpa = _sample_static_sites(
        elastic_surface, center, south
    )
    if center_compliance_m_per_mpa <= 0.0 or south_compliance_m_per_mpa <= 0.0:
        raise ValueError("static unit-load BPR compliance must be positive")
    interval_count = len(history.elapsed_years) - 1
    center_operator = np.eye(interval_count) * center_compliance_m_per_mpa
    inversion = invert_pressure_history(center_operator, history.center_uplift_m[1:])
    pressure_mpa = np.concatenate(([0.0], inversion.pressure_mpa))
    center_model_m = inversion.predicted_uplift_m
    south_model_m = south_compliance_m_per_mpa * inversion.pressure_mpa

    vertices, tetrahedra, _ = _read_gmsh_tetrahedral_mesh(mesh_path)
    unit_stress = _read_static_stress(elastic_material, vertices, tetrahedra)
    stress_history = unit_stress[np.newaxis, :, :] * pressure_mpa[1:, np.newaxis, np.newaxis]
    elapsed_seconds = np.asarray(history.elapsed_years[1:] * SECONDS_PER_YEAR)
    failure = analyze_stress_history(
        vertices,
        tetrahedra,
        stress_history,
        elapsed_seconds,
        cohesion_pa=COHESION_PA,
        friction_angle_deg=FRICTION_ANGLE_DEG,
        pore_pressure_pa=PORE_PRESSURE_PA,
    )
    failure_csv = (
        output_dir
        / "analysis"
        / "elastic"
        / f"historical_four_case_{event_name}_elastic_failure.csv"
    )
    failure_csv.parent.mkdir(parents=True, exist_ok=True)
    failure_rows = [
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
        }
        for record in failure["records"]
    ]
    with failure_csv.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(failure_rows[0]))
        writer.writeheader()
        writer.writerows(failure_rows)
    series_path = _write_series(
        output_dir,
        "elastic",
        event_name=event_name,
        failure_csv=failure_csv,
        history=history,
        times_s=elapsed_seconds,
        pressure_mpa=pressure_mpa,
        center_observed_m=history.center_uplift_m[1:],
        south_observed_m=history.south_uplift_m[1:],
        center_model_m=center_model_m,
        south_model_m=south_model_m,
    )
    return {
        "case": "elastic",
        "rheology": "non-temperature-dependent linear elasticity",
        "fit_site": "Center",
        "held_out_site": "South",
        "static_center_compliance_m_per_mpa": center_compliance_m_per_mpa,
        "static_south_compliance_m_per_mpa": south_compliance_m_per_mpa,
        "pressure_change_range_mpa": [
            float(np.min(inversion.pressure_mpa)),
            float(np.max(inversion.pressure_mpa)),
        ],
        "regularization_coefficient": inversion.regularization,
        "effective_fit_parameters": inversion.effective_parameters,
        "center_kernel_fit_rmse_m": inversion.rmse_m,
        "center": _metrics(history.center_uplift_m[1:], center_model_m),
        "south": _metrics(history.south_uplift_m[1:], south_model_m),
        "failure_threshold_diagnostic": {
            key: value for key, value in failure.items() if key != "records"
        },
        "timeseries_csv": str(series_path.relative_to(ROOT)),
        "static_stress_is_scaled_by_fitted_pressure": True,
        "run_directory": str(ELASTIC_STEP_DIR.relative_to(ROOT)),
    }


def _plot_results(
    history: object,
    figure_stem: Path,
    results: list[dict[str, object]],
    *,
    event_name: str,
    event: dict[str, object],
    corrected_observations: bool,
) -> tuple[Path, Path]:
    """Plot fits, pressure histories, and saved failure-path states."""
    figure_stem.parent.mkdir(parents=True, exist_ok=True)
    figure, axes = plt.subplots(4, 1, figsize=(11.0, 10.5), sharex=True)
    axes[0].set_title("Center BPR fit")
    axes[1].set_title("South BPR held-out prediction")
    axes[2].set_title("Center-fitted pressure change")
    axes[3].set_title("Mohr–Coulomb path at saved stress records")
    for axis in axes:
        axis.grid(True, alpha=0.25)
    dates = history.times_utc[1:]
    observation_label = "corrected BPR" if corrected_observations else "raw BPR"
    axes[0].plot(
        dates,
        history.center_uplift_m[1:],
        color="black",
        label=f"Center {observation_label}",
    )
    axes[1].plot(
        dates,
        history.south_uplift_m[1:],
        color="black",
        label=f"South {observation_label}",
    )
    eruption_date = event["eruption_date_utc"]
    eruption_label = str(event["eruption_label"])
    for axis in axes[:-1]:
        axis.axvline(eruption_date, color="0.35", linestyle=":", linewidth=1.1)
    axes[-1].axvline(
        eruption_date,
        color="0.35",
        linestyle=":",
        linewidth=1.1,
        label=eruption_label,
    )
    for result in results:
        case_name = str(result["case"])
        case_label = CASE_LABELS[case_name]
        series_path = ROOT / str(result["timeseries_csv"])
        with series_path.open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        case_dates = [history.times_utc[index + 1] for index in range(len(rows))]
        axes[0].plot(
            case_dates,
            [float(row["center_model_uplift_m"]) for row in rows],
            label=case_label,
        )
        axes[1].plot(
            case_dates,
            [float(row["south_model_uplift_m"]) for row in rows],
            label=case_label,
        )
        axes[2].plot(
            case_dates,
            [float(row["pressure_change_mpa"]) for row in rows],
            label=case_label,
        )
        axes[3].step(
            case_dates,
            [
                float(row["cavity_to_surface_shear_path_found"] == "True")
                for row in rows
            ],
            where="post",
            label=case_label,
        )
    axes[0].set_ylabel("Uplift (m)")
    axes[1].set_ylabel("Uplift (m)")
    axes[2].set_ylabel("Pressure (MPa)")
    axes[3].set_ylabel("Path found")
    axes[3].set_yticks((0, 1))
    axes[3].set_yticklabels(("No", "Yes"))
    axes[3].set_xlabel("Date (UTC)")
    axes[0].legend(ncol=3, fontsize=8)
    axes[1].legend(ncol=3, fontsize=8)
    axes[2].legend(ncol=4, fontsize=8)
    axes[3].legend(ncol=3, fontsize=8)
    axes[-1].xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    observation_source = "corrected" if corrected_observations else "raw"
    figure.suptitle(
        f"{event_name} {observation_source} BPR pressure calibration across four "
        "written rheologies\n"
        "project-directed 50-to-20 GPa modulus; synthetic Maxwell branches; South held out",
        fontsize=12,
    )
    figure.tight_layout(rect=(0, 0, 1, 0.96))
    png_path = figure_stem.with_suffix(".png")
    pdf_path = figure_stem.with_suffix(".pdf")
    figure.savefig(png_path, dpi=180)
    figure.savefig(pdf_path)
    plt.close(figure)
    return png_path, pdf_path


def main() -> None:
    """Run Center-calibrated pressure checks for the four rheology cases."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mesh", type=Path, default=DEFAULT_MESH)
    parser.add_argument(
        "--elastic-surface",
        type=Path,
        default=ELASTIC_STEP_DIR / "output" / "ellipsoid-surface.h5",
    )
    parser.add_argument(
        "--elastic-material",
        type=Path,
        default=ELASTIC_STEP_DIR / "output" / "ellipsoid-material.h5",
    )
    parser.add_argument("--event", choices=tuple(EVENTS), default="2011")
    parser.add_argument(
        "--corrected-observations",
        action="store_true",
        help="use MGDS predicted-tide and available MPR drift-corrected channels",
    )
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--figure-stem", type=Path)
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="replace prior generated output beneath data/processed/",
    )
    args = parser.parse_args()
    event = EVENTS[args.event]
    eruption_date = event["eruption_date_utc"]
    if args.corrected_observations:
        args.output_dir = args.output_dir or (
            PROCESSED_DIR / f"historical_four_case_bpr_calibration_{args.event}_corrected"
        )
        args.figure_stem = args.figure_stem or (
            ROOT / "figures" / f"historical_four_case_bpr_calibration_{args.event}_corrected"
        )
    else:
        args.output_dir = args.output_dir or event["output_dir"]
        args.figure_stem = args.figure_stem or event["figure_stem"]
    args.mesh = args.mesh.resolve()
    args.elastic_surface = args.elastic_surface.resolve()
    args.elastic_material = args.elastic_material.resolve()
    args.output_dir = args.output_dir.resolve()
    args.figure_stem = args.figure_stem.resolve()
    for path in (args.mesh, args.elastic_surface, args.elastic_material):
        if not path.is_file():
            raise FileNotFoundError(path)
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        if not args.overwrite:
            raise FileExistsError(
                f"output directory is not empty; choose --overwrite or a new path: "
                f"{args.output_dir}"
            )
        processed_root = (ROOT / "data" / "processed").resolve()
        try:
            args.output_dir.relative_to(processed_root)
        except ValueError as exc:
            raise ValueError("--overwrite is limited to data/processed outputs") from exc
        if args.output_dir == processed_root:
            raise ValueError("--overwrite cannot remove the processed-data root")
        shutil.rmtree(args.output_dir)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    started = time.perf_counter()
    history, center, south, observation_metadata = _load_observations(
        args.event,
        event,
        corrected_observations=args.corrected_observations,
    )
    elapsed_seconds = np.asarray(history.elapsed_years * SECONDS_PER_YEAR, dtype=float)
    if elapsed_seconds[0] != 0.0 or not np.allclose(
        np.diff(elapsed_seconds), history.time_step_s, rtol=0.0, atol=1.0e-3
    ):
        raise ValueError("raw BPR inversion times must form a uniform grid from zero")
    database_paths, thermal_metadata = _write_case_materials(args.mesh, args.output_dir)

    results = [
        _run_elastic_case(
            event_name=args.event,
            history=history,
            center=center,
            south=south,
            elastic_surface=args.elastic_surface,
            elastic_material=args.elastic_material,
            mesh_path=args.mesh,
            output_dir=args.output_dir,
        )
    ]
    for case_name, database_path in database_paths.items():
        result = _run_maxwell_case(
            case_name,
            database_path,
            event_name=args.event,
            history=history,
            center=center,
            south=south,
            mesh_path=args.mesh,
            output_dir=args.output_dir,
        )
        result["thermal_material_mapping"] = thermal_metadata.get(case_name)
        result["material_assumptions"] = {
            "youngs_modulus_pa": (
                "linear 50-to-20 GPa project interpolation"
                if case_name.startswith("td_")
                else YOUNGS_MODULUS_PA
            ),
            "reference_viscosity_pa_s_by_branch": REFERENCE_VISCOSITY_PA_S_BY_BRANCH.tolist(),
            "shear_modulus_ratio_by_branch": SHEAR_RATIO_BY_BRANCH.tolist(),
            "poisson_ratio": POISSON_RATIO,
            "density_kg_m3": DENSITY_KG_M3,
            "branch_parameters_are_synthetic": True,
        }
        results.append(result)

    png_path, pdf_path = _plot_results(
        history,
        args.figure_stem,
        results,
        event_name=args.event,
        event=event,
        corrected_observations=args.corrected_observations,
    )
    summary = {
        "method": (
            "Center BPR pressure inversion per rheology with held-out South validation"
        ),
        "observation_provenance": (
            "MGDS corrected observation channels"
            if args.corrected_observations
            else "original raw MGDS/NCEI BPR channels"
        ),
        "observation_processing": (
            "MGDS predicted-tide channel and MPR drift-corrected channel where "
            "available; no low-pass filter"
            if args.corrected_observations
            else "original raw channel; no tide or drift correction"
        ),
        "cabaniss_model_output_used": False,
        "paper_reported_model_values_used": False,
        "event_window": args.event,
        "eruption_date_utc": eruption_date.isoformat(),
        "center_calibration_includes_post_eruption_data": True,
        "center_station": {
            "name": center.station,
            "slug": center.slug,
            "archive": center.archive,
            "source_file": str(center.path.relative_to(ROOT)),
            "raw_channel": center.raw_channel,
            "correction": observation_metadata.get(center.slug),
        },
        "south_station": {
            "name": south.station,
            "slug": south.slug,
            "archive": south.archive,
            "source_file": str(south.path.relative_to(ROOT)),
            "raw_channel": south.raw_channel,
            "correction": observation_metadata.get(south.slug),
        },
        "archive_duplicate_used": False,
        "overlap_start_utc": history.times_utc[0].isoformat(),
        "overlap_end_utc": history.times_utc[-1].isoformat(),
        "paired_observation_count": history.paired_daily_samples,
        "inversion_interval_days": TIME_STEP_DAYS,
        "uniform_pressure_step_days": history.time_step_s / 86_400.0,
        "maximum_observation_gap_days": history.maximum_observation_gap_days,
        "mesh_tetrahedra": len(_read_gmsh_tetrahedral_mesh(args.mesh)[1]),
        "mesh_converged": False,
        "boundary_assumption": (
            "fixed base and lateral roller boundaries; Winkler foundation absent"
        ),
        "failure_proxy": {
            "cohesion_pa": COHESION_PA,
            "friction_angle_deg": FRICTION_ANGLE_DEG,
            "friction_interpretation": "friction angle used directly as phi",
            "pore_pressure_pa": PORE_PRESSURE_PA,
            "tensile_strength_assigned": False,
        },
        "pressure_inversion_assumption": (
            "second-difference Tikhonov smoothing selected by generalized cross-validation"
        ),
        "failure_onset_is_an_independent_eruption_prediction": False,
        "youngs_modulus_mapping": {
            "law": (
                "linear decrease from 50 GPa at 0 C to 20 GPa at 1200 C; "
                "clipped to those endpoint values"
            ),
            "source": "project-owner model setup direction",
            "printed_eq16_used": False,
        },
        "thermal_solves": thermal_metadata,
        "cases": results,
        "limitations": [
            "synthetic Maxwell branch viscosities and fractions",
            "the owner-directed linear modulus interpolation is an explicit assumption "
            "because printed Eq. 16 conflicts with the brittle/ductile labels",
            "static ellipsoid compliance and held-out spatial predictions use a nonconverged mesh",
            (
                "tide residuals and non-tidal ocean variability remain; the 1998 and "
                "2011 South channels have no MPR drift correction"
                if args.corrected_observations
                else "raw daily records retain ocean variability and instrument drift"
            ),
            "pressure is fitted independently for each case and is not a measured magma pressure",
            "the Center fit includes the eruption deflation and therefore cannot "
            "independently predict eruption timing",
            "failure uses provisional cohesion, direct friction-angle interpretation, "
            "and zero pore pressure",
        ],
        "figures": [str(png_path.relative_to(ROOT)), str(pdf_path.relative_to(ROOT))],
        "runtime_seconds": round(time.perf_counter() - started, 2),
    }
    summary_path = args.output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"wrote {summary_path}, {png_path}, and {pdf_path}")


if __name__ == "__main__":
    main()
