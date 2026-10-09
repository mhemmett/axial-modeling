"""Drive an ellipsoid Maxwell run with pressure inferred from independent OOI BPRs."""

from __future__ import annotations

import argparse
import csv
import json
import re
import shlex
import shutil
import subprocess
import sys
import time
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

import gmsh
import h5py
import numpy as np

from axialstress.bpr_mogi_calibration import (
    CENTRAL_CALDERA_LAT_LON_DEG,
    EAST_CALDERA_LAT_LON_DEG,
    local_east_north_offset_m,
)
from axialstress.bpr_observations import (
    latest_processed_bpr_path,
    read_processed_bpr_series,
)
from axialstress.ellipsoid_bpr_calibration import (
    calibrate_ellipsoid_to_bpr,
    read_ellipsoid_unit_response,
)
from axialstress.failure_analysis import analyze_stress_history
from axialstress.historical_bpr import DEPLOYMENTS, PROCESSED_DIR
from axialstress.historical_maxwell_pressure import (
    HistoricalMaxwellHistory,
    prepare_historical_maxwell_history,
    read_raw_daily_depths,
)
from axialstress.material_database import (
    write_elastic_database,
    write_temperature_dependent_maxwell_database,
)
from axialstress.maxwell_pressure_inversion import (
    invert_pressure_history,
    ramp_response_operator,
)
from axialstress.ooi_pressure_history import (
    OoiPressureHistory,
    read_monthly_ooi_pressure_history,
    write_normalized_time_history,
)
from axialstress.surface_interpolation import interpolate_triangular_surface
from axialstress.thermal import (
    evaluate_eq16_youngs_modulus_pa,
    hydrothermal_conductivity_w_mk,
    temperature_dependent_viscosity_pa_s,
)
from axialstress.thermal_fem import solve_steady_temperature_tetrahedral

ROOT = Path(__file__).resolve().parents[1]
STEP_DIR = ROOT / "pylith" / "step06_maxwell_ellipsoid"
ELASTIC_STEP_DIR = ROOT / "pylith" / "step05_ellipsoid_elastic"
PYLITH_ROOT = ROOT / "pylith" / "pylith-5.0.2-linux-x86_64"
SUMMARY_PATH = ROOT / "data" / "processed" / "ooi_maxwell_ellipsoid_summary.json"
TIMESERIES_PATH = ROOT / "data" / "processed" / "ooi_maxwell_ellipsoid_timeseries.csv"
EQ16_SUMMARY_PATH = (
    ROOT / "data" / "processed" / "ooi_eq16_hydrothermal_maxwell_summary.json"
)
EQ16_TIMESERIES_PATH = (
    ROOT / "data" / "processed" / "ooi_eq16_hydrothermal_maxwell_timeseries.csv"
)
INVERSE_SUMMARY_PATH = (
    ROOT / "data" / "processed" / "ooi_maxwell_viscoelastic_inversion_summary.json"
)
INVERSE_TIMESERIES_PATH = (
    ROOT / "data" / "processed" / "ooi_maxwell_viscoelastic_inversion_timeseries.csv"
)
HISTORICAL_INVERSE_DIR = PROCESSED_DIR / "maxwell_pressure_inversion"
PRESSURE_AMPLITUDE_PA = -1.0e6
SECONDS_PER_YEAR = 365.25 * 24.0 * 3600.0
YOUNGS_MODULUS_PA = 50.0e9
POISSON_RATIO = 0.25
VISCOSITY_PA_S = 1.0e18
DENSITY_KG_M3 = 2800.0
SURFACE_TEMPERATURE_C = 0.0
CAVITY_TEMPERATURE_C = 1200.0
GEOTHERM_C_PER_KM = 30.0
THERMAL_CONDUCTIVITY_W_MK = 3.0
HYDROTHERMAL_NUSSELT_NUMBER = 8.0
HYDROTHERMAL_SMOOTHING_COEFFICIENT = 0.75
HYDROTHERMAL_CUTOFF_TEMPERATURE_C = 600.0
HYDROTHERMAL_CUTOFF_DEPTH_M = 6000.0
COHESION_PA = 1.0e6
FRICTION_ANGLE_DEG = 25.0
PORE_PRESSURE_PA = 0.0


def _generate_mesh(mesh_path: Path, log_path: Path) -> int:
    """Generate the coarse ellipsoid mesh and return its tetrahedron count."""
    mesh_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as log:
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "meshing" / "axial_ellipsoid_bpr.py"),
                "--output",
                str(mesh_path),
            ],
            cwd=ROOT,
            stdout=log,
            stderr=subprocess.STDOUT,
            check=True,
        )
    match = re.search(r"Wrote .*: (\d+) tetrahedra", log_path.read_text(encoding="utf-8"))
    if match is None:
        raise RuntimeError(f"mesh count missing from {log_path}")
    return int(match.group(1))


def _read_mesh_and_thermal_boundaries(
    mesh_path: Path,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[int, float]]:
    """Read the ellipsoid tetrahedra and the stated thermal boundary values."""
    gmsh.initialize()
    try:
        gmsh.open(str(mesh_path))
        node_tags, coordinates, _ = gmsh.model.mesh.getNodes()
        vertices = np.asarray(coordinates, dtype=float).reshape(-1, 3)
        vertex_index = {int(tag): index for index, tag in enumerate(node_tags)}
        element_types, _, element_nodes = gmsh.model.mesh.getElements(3)
        cells: list[list[int]] = []
        for element_type, node_tags_for_type in zip(
            element_types, element_nodes, strict=True
        ):
            _, dimension, order, nodes_per_cell, _, _ = gmsh.model.mesh.getElementProperties(
                int(element_type)
            )
            if dimension == 3 and order == 1 and nodes_per_cell == 4:
                cells.extend(
                    [vertex_index[int(tag)] for tag in cell]
                    for cell in node_tags_for_type.reshape(-1, 4)
                )

        boundary_values: dict[int, float] = {}
        boundary_names = {"top", "bottom", "x_neg", "x_pos", "y_neg", "y_pos", "cavity"}
        maximum_z = float(np.max(vertices[:, 2]))
        found_boundaries: set[str] = set()
        for dimension, physical_tag in gmsh.model.getPhysicalGroups(2):
            if dimension != 2:
                continue
            name = gmsh.model.getPhysicalName(dimension, physical_tag)
            if name not in boundary_names:
                continue
            found_boundaries.add(name)
            for entity_tag in gmsh.model.getEntitiesForPhysicalGroup(dimension, physical_tag):
                tags, _, _ = gmsh.model.mesh.getNodes(
                    dimension, int(entity_tag), includeBoundary=True
                )
                for tag in tags:
                    index = vertex_index[int(tag)]
                    depth_m = maximum_z - vertices[index, 2]
                    if name == "top":
                        value_c = SURFACE_TEMPERATURE_C
                    elif name == "cavity":
                        value_c = CAVITY_TEMPERATURE_C
                    else:
                        value_c = GEOTHERM_C_PER_KM * depth_m / 1000.0
                    existing = boundary_values.get(index)
                    if existing is not None and not np.isclose(
                        existing, value_c, rtol=0.0, atol=1.0e-8
                    ):
                        raise ValueError(
                            "thermal boundary temperatures conflict at a shared vertex"
                        )
                    boundary_values[index] = value_c
    finally:
        gmsh.finalize()

    tetrahedra = np.asarray(cells, dtype=np.int64)
    if not len(tetrahedra) or found_boundaries != boundary_names:
        raise ValueError("ellipsoid mesh is missing tetrahedra or a thermal boundary group")
    depth_m = float(np.max(vertices[:, 2])) - vertices[:, 2]
    return vertices, tetrahedra, depth_m, boundary_values


def _solve_eq16_hydrothermal_field(
    mesh_path: Path,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, int, float]:
    """Solve the steady hydrothermal field and evaluate printed E(T) per cell."""
    vertices, tetrahedra, depth_m, boundary_values = _read_mesh_and_thermal_boundaries(
        mesh_path
    )
    thermal = solve_steady_temperature_tetrahedral(
        vertices,
        tetrahedra,
        depth_m,
        boundary_values,
        conductivity=lambda temperature_c, cell_depth_m: hydrothermal_conductivity_w_mk(
            temperature_c,
            cell_depth_m,
            reference_conductivity_w_mk=THERMAL_CONDUCTIVITY_W_MK,
            nusselt_number=HYDROTHERMAL_NUSSELT_NUMBER,
            smoothing_coefficient=HYDROTHERMAL_SMOOTHING_COEFFICIENT,
            cutoff_temperature_c=HYDROTHERMAL_CUTOFF_TEMPERATURE_C,
            cutoff_depth_m=HYDROTHERMAL_CUTOFF_DEPTH_M,
        ),
        heat_production_w_m3=0.0,
    )
    cell_temperature_c = thermal.temperature_c[tetrahedra].mean(axis=1)
    cell_depth_m = depth_m[tetrahedra].mean(axis=1)
    cell_conductivity_w_mk = hydrothermal_conductivity_w_mk(
        cell_temperature_c,
        cell_depth_m,
        reference_conductivity_w_mk=THERMAL_CONDUCTIVITY_W_MK,
        nusselt_number=HYDROTHERMAL_NUSSELT_NUMBER,
        smoothing_coefficient=HYDROTHERMAL_SMOOTHING_COEFFICIENT,
        cutoff_temperature_c=HYDROTHERMAL_CUTOFF_TEMPERATURE_C,
        cutoff_depth_m=HYDROTHERMAL_CUTOFF_DEPTH_M,
    )
    youngs_modulus_pa = evaluate_eq16_youngs_modulus_pa(cell_temperature_c)
    return (
        vertices,
        tetrahedra,
        thermal.temperature_c,
        youngs_modulus_pa,
        cell_conductivity_w_mk,
        thermal.iterations,
        thermal.relative_change,
    )


def _set_nearest_material_query(config_path: Path, database_filename: str) -> None:
    """Set piecewise-constant interpolation for cell-centered material data."""
    config = config_path.read_text(encoding="utf-8")
    database_line = f"db_auxiliary_field.iohandler.filename = {database_filename}"
    if config.count(database_line) != 1:
        raise ValueError(f"could not find the material database path {database_filename}")
    query_line = "db_auxiliary_field.query_type = nearest"
    if query_line not in config:
        config = config.replace(database_line, f"{query_line}\n{database_line}")
    config_path.write_text(config, encoding="utf-8")


def _read_surface_history(
    surface_path: Path,
    *,
    fitted_lat_lon_deg: tuple[float, float] = CENTRAL_CALDERA_LAT_LON_DEG,
    held_out_lat_lon_deg: tuple[float, float] = EAST_CALDERA_LAT_LON_DEG,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Read finite surface displacement records and sample both BPR locations."""
    with h5py.File(surface_path, "r") as surface:
        required = (
            "time",
            "geometry/vertices",
            "viz/topology/cells",
            "vertex_fields/displacement",
        )
        missing = [name for name in required if name not in surface]
        if missing:
            raise ValueError(f"PyLith surface output is missing datasets: {missing}")
        times_s = np.asarray(surface["time"], dtype=float).reshape(-1)
        vertices = np.asarray(surface["geometry/vertices"], dtype=float)
        triangles = np.asarray(surface["viz/topology/cells"], dtype=np.int64)
        displacement = np.asarray(surface["vertex_fields/displacement"], dtype=float)
    if not len(times_s) or np.any(np.diff(times_s) <= 0.0):
        raise ValueError("PyLith surface output times must be nonempty and increasing")
    if displacement.shape != (len(times_s), *vertices.shape):
        raise ValueError("PyLith surface displacement has an unexpected shape")
    if not np.all(np.isfinite(displacement)):
        raise ValueError("PyLith surface displacement contains non-finite values")

    center_east_offset, center_north_offset = local_east_north_offset_m(
        fitted_lat_lon_deg[0],
        fitted_lat_lon_deg[1],
        origin_latitude_deg=CENTRAL_CALDERA_LAT_LON_DEG[0],
        origin_longitude_deg=CENTRAL_CALDERA_LAT_LON_DEG[1],
    )
    east_offset, north_offset = local_east_north_offset_m(
        held_out_lat_lon_deg[0],
        held_out_lat_lon_deg[1],
        origin_latitude_deg=CENTRAL_CALDERA_LAT_LON_DEG[0],
        origin_longitude_deg=CENTRAL_CALDERA_LAT_LON_DEG[1],
    )
    central_uplift = np.asarray(
        [
            interpolate_triangular_surface(
                vertices,
                triangles,
                field,
                (center_east_offset, center_north_offset),
            )[2]
            for field in displacement
        ]
    )
    east_uplift = np.asarray(
        [
            interpolate_triangular_surface(
                vertices, triangles, field, (east_offset, north_offset)
            )[2]
            for field in displacement
        ]
    )
    return times_s, vertices, displacement, central_uplift, east_uplift


def _write_pressure_database(path: Path) -> None:
    """Write a spatial database with a normalized cavity pressure history."""
    value_names = (
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
        f"  value-names = {' '.join(value_names)}",
        "  value-units = Pa Pa Pa Pa Pa Pa s",
        "  num-locs = 1",
        "  data-dim = 0",
        "  space-dim = 3",
        "  cs-data = cartesian {",
        "    to-meters = 1.0",
        "    space-dim = 3",
        "  }",
        "}",
        f"0.0 0.0 0.0 0.0 0.0 0.0 {PRESSURE_AMPLITUDE_PA:.12g} 0.0 0.0 0.0",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _configure_run(
    run_dir: Path,
    history: OoiPressureHistory | HistoricalMaxwellHistory,
    *,
    material_database_path: Path | None = None,
    time_step_s: float | None = None,
    history_description: str = "Monthly OOI-inferred elastic pressure changes",
) -> None:
    """Copy the Maxwell inputs and connect its cavity traction to TimeHistory."""
    for filename in (
        "step06.cfg",
        "pylithapp.cfg",
        "bc_zero.spatialdb",
    ):
        shutil.copy2(STEP_DIR / filename, run_dir / filename)
    if material_database_path is None:
        shutil.copy2(STEP_DIR / "material_initial.spatialdb", run_dir)
    else:
        shutil.copy2(material_database_path, run_dir / "material_initial.spatialdb")
        _set_nearest_material_query(
            run_dir / "pylithapp.cfg", "material_initial.spatialdb"
        )
    duration_s = (history.times_utc[-1] - history.times_utc[0]).total_seconds()
    step_configuration = (run_dir / "step06.cfg").read_text(encoding="utf-8")
    step_configuration, replacements = re.subn(
        r"(?m)^end_time\s*=.*$", f"end_time = {duration_s:.12g}*s", step_configuration
    )
    if replacements != 1:
        raise ValueError("could not set the observation-window PyLith end time")
    if time_step_s is not None:
        if not np.isfinite(time_step_s) or time_step_s <= 0.0:
            raise ValueError("PyLith history time step must be finite and positive")
        step_configuration, replacements = re.subn(
            r"(?m)^initial_dt\s*=.*$",
            f"initial_dt = {time_step_s:.12g}*s",
            step_configuration,
        )
        if replacements != 1:
            raise ValueError("could not set the uniform PyLith history time step")
    cavity_database_line = "db_auxiliary_field.iohandler.filename = bc_cavity.spatialdb"
    if step_configuration.count(cavity_database_line) != 1:
        raise ValueError("could not connect the BPR history to the cavity traction")
    step_configuration = step_configuration.replace(
        cavity_database_line,
        "use_time_history = True\n"
        f"{cavity_database_line}\n"
        "time_history = spatialdata.spatialdb.TimeHistory\n"
        f"time_history.description = {history_description}\n"
        "time_history.filename = pressure.timedb",
    )
    (run_dir / "step06.cfg").write_text(step_configuration, encoding="utf-8")
    _write_pressure_database(run_dir / "bc_cavity.spatialdb")
    write_normalized_time_history(run_dir / "pressure.timedb", history)


def _run_pylith(run_dir: Path, config_filename: str = "step06.cfg") -> None:
    """Run the bounded Maxwell history and preserve a readable local log."""
    log_path = run_dir / "output" / "pylith.log"
    command = (
        f"cd {shlex.quote(str(PYLITH_ROOT))} && source setup.sh && "
        f"cd {shlex.quote(str(run_dir))} && "
        f"timeout 300 pylith {shlex.quote(config_filename)}"
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
        raise RuntimeError(f"PyLith OOI pressure-history run failed:\n{tail}")


def _write_calibration_csv(path: Path, calibration) -> None:
    """Write the OOI calibration columns consumed by the monthly reducer."""
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(
            [
                "time_utc",
                "central_relative_uplift_m",
                "central_elastic_fit_m",
                "east_relative_uplift_m",
                "east_elastic_prediction_m",
                "east_residual_m",
                "inferred_pressure_change_mpa",
                "central_ooi_qc_aggregate",
                "east_ooi_qc_aggregate",
            ]
        )
        for index, time_utc in enumerate(calibration.times_utc):
            writer.writerow(
                [
                    time_utc.isoformat().replace("+00:00", "Z"),
                    calibration.central_uplift_m[index],
                    calibration.central_prediction_m[index],
                    calibration.east_uplift_m[index],
                    calibration.east_prediction_m[index],
                    calibration.east_residual_m[index],
                    calibration.pressure_change_mpa[index],
                    calibration.central_quality_codes[index],
                    calibration.east_quality_codes[index],
                ]
            )


def _write_model_timeseries(
    history: OoiPressureHistory,
    times_s: np.ndarray,
    central_model_m: np.ndarray,
    east_model_m: np.ndarray,
    output_path: Path,
) -> tuple[float, float, float | None, float | None]:
    """Save model and monthly observed uplift together and return fit metrics."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    model_years = times_s / SECONDS_PER_YEAR
    central_observed_m = np.interp(
        model_years, history.elapsed_years, history.central_uplift_m
    )
    east_observed_m = np.interp(model_years, history.elapsed_years, history.east_uplift_m)
    pressure_mpa = np.interp(model_years, history.elapsed_years, history.pressure_change_mpa)
    with output_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(
            [
                "elapsed_years",
                "time_s",
                "inferred_pressure_change_mpa",
                "central_ooi_monthly_mean_uplift_m",
                "central_pylith_uplift_m",
                "east_ooi_monthly_mean_uplift_m",
                "east_pylith_uplift_m",
            ]
        )
        writer.writerows(
            zip(
                model_years,
                times_s,
                pressure_mpa,
                central_observed_m,
                central_model_m,
                east_observed_m,
                east_model_m,
                strict=True,
            )
        )
    central_residual = central_model_m - central_observed_m
    east_residual = east_model_m - east_observed_m
    central_correlation = (
        float(np.corrcoef(central_model_m, central_observed_m)[0, 1])
        if np.std(central_model_m) > 0.0 and np.std(central_observed_m) > 0.0
        else None
    )
    east_correlation = (
        float(np.corrcoef(east_model_m, east_observed_m)[0, 1])
        if np.std(east_model_m) > 0.0 and np.std(east_observed_m) > 0.0
        else None
    )
    return (
        float(np.sqrt(np.mean(central_residual**2))),
        float(np.sqrt(np.mean(east_residual**2))),
        central_correlation,
        east_correlation,
    )


def _uniform_ooi_history(
    monthly_history: OoiPressureHistory,
) -> tuple[OoiPressureHistory, float]:
    """Interpolate monthly OOI means to a uniform, approximately 30-day grid."""
    start_time = monthly_history.times_utc[0]
    duration_s = (monthly_history.times_utc[-1] - start_time).total_seconds()
    if duration_s <= 0.0:
        raise ValueError("OOI observations must span a positive time interval")
    interval_count = max(5, int(round(duration_s / (30.0 * 86400.0))))
    time_step_s = duration_s / interval_count
    elapsed_years = np.linspace(
        0.0, duration_s / SECONDS_PER_YEAR, interval_count + 1, dtype=float
    )
    times_utc = tuple(
        start_time + timedelta(seconds=float(time_year * SECONDS_PER_YEAR))
        for time_year in elapsed_years
    )
    central_uplift_m = np.interp(
        elapsed_years, monthly_history.elapsed_years, monthly_history.central_uplift_m
    )
    east_uplift_m = np.interp(
        elapsed_years, monthly_history.elapsed_years, monthly_history.east_uplift_m
    )
    pressure_history = OoiPressureHistory(
        times_utc=times_utc,
        elapsed_years=elapsed_years,
        pressure_change_mpa=np.zeros(interval_count + 1, dtype=float),
        central_uplift_m=central_uplift_m,
        east_uplift_m=east_uplift_m,
        monthly_record_counts=tuple(1 for _ in times_utc),
        central_qc_codes=monthly_history.central_qc_codes,
        east_qc_codes=monthly_history.east_qc_codes,
    )
    return pressure_history, time_step_s


def _ooi_history_with_pressure(
    observations: OoiPressureHistory, pressure_mpa: np.ndarray
) -> OoiPressureHistory:
    """Return the uniform OOI history with one pressure value per time knot."""
    pressure = np.asarray(pressure_mpa, dtype=float)
    if pressure.shape != observations.elapsed_years.shape or not np.all(
        np.isfinite(pressure)
    ):
        raise ValueError("OOI pressure values must match the finite observation grid")
    return OoiPressureHistory(
        times_utc=observations.times_utc,
        elapsed_years=observations.elapsed_years,
        pressure_change_mpa=pressure,
        central_uplift_m=observations.central_uplift_m,
        east_uplift_m=observations.east_uplift_m,
        monthly_record_counts=observations.monthly_record_counts,
        central_qc_codes=observations.central_qc_codes,
        east_qc_codes=observations.east_qc_codes,
    )


def run_viscoelastic_pressure_inversion() -> None:
    """Invert OOI Central uplift from a PyLith one-branch Maxwell ramp kernel."""
    if not (PYLITH_ROOT / "setup.sh").is_file():
        raise SystemExit("PyLith is not installed; run make install-pylith first")
    calibration_csv = ROOT / "data" / "processed" / "ooi_ellipsoid_elastic_calibration.csv"
    if not calibration_csv.is_file():
        raise SystemExit(
            "missing monthly OOI uplift; run make ellipsoid-bpr-check first"
        )
    monthly_history = read_monthly_ooi_pressure_history(calibration_csv)
    observations, time_step_s = _uniform_ooi_history(monthly_history)
    interval_count = len(observations.elapsed_years) - 1
    unit_ramp_pressure = _ooi_history_with_pressure(
        observations,
        np.concatenate(([0.0], np.ones(interval_count, dtype=float))),
    )
    started = time.perf_counter()
    with TemporaryDirectory(prefix="axial-ooi-maxwell-inverse-") as temporary:
        work_dir = Path(temporary)
        response_dir = work_dir / "unit_ramp"
        forward_dir = work_dir / "inferred_history"
        for directory in (response_dir, forward_dir):
            for subdirectory in ("mesh", "output"):
                (directory / subdirectory).mkdir(parents=True)

        mesh_path = response_dir / "mesh" / "axial_ellipsoid.msh"
        mesh_tetrahedra = _generate_mesh(mesh_path, response_dir / "output" / "mesh.log")
        _configure_run(
            response_dir,
            unit_ramp_pressure,
            time_step_s=time_step_s,
            history_description="Unit pressure ramp for Maxwell inversion kernel",
        )
        _run_pylith(response_dir)
        (
            response_times_s,
            _,
            _,
            central_ramp_response_m,
            east_ramp_response_m,
        ) = _read_surface_history(response_dir / "output" / "maxwell-surface.h5")
        if len(response_times_s) != interval_count or not np.allclose(
            np.diff(response_times_s), time_step_s, rtol=0.0, atol=1.0e-3
        ):
            raise RuntimeError(
                "PyLith unit-ramp output does not match the uniform OOI grid: "
                f"{len(response_times_s)} records for {interval_count + 1} knots; "
                f"first output intervals are {np.diff(response_times_s)[:8].tolist()} s "
                f"(requested {time_step_s:g} s)"
            )

        central_operator = ramp_response_operator(central_ramp_response_m)
        east_operator = ramp_response_operator(east_ramp_response_m)
        inversion = invert_pressure_history(
            central_operator,
            observations.central_uplift_m[1:],
        )
        inferred_history = _ooi_history_with_pressure(
            observations,
            np.concatenate(([0.0], inversion.pressure_mpa)),
        )

        shutil.copy2(mesh_path, forward_dir / "mesh" / mesh_path.name)
        _configure_run(
            forward_dir,
            inferred_history,
            time_step_s=time_step_s,
            history_description="GCV-smoothed pressure inferred from OOI Central uplift",
        )
        _run_pylith(forward_dir)
        (
            times_s,
            surface_vertices,
            displacement,
            central_model_m,
            east_model_m,
        ) = _read_surface_history(forward_dir / "output" / "maxwell-surface.h5")
        expected_end_time_s = (
            observations.times_utc[-1] - observations.times_utc[0]
        ).total_seconds()
        if not np.isclose(times_s[-1], expected_end_time_s, rtol=0.0, atol=1.0e-3):
            raise SystemExit(
                f"PyLith ended at {times_s[-1]:g} s, expected {expected_end_time_s:g} s"
            )
        if not np.all(np.isfinite(displacement)):
            raise SystemExit("PyLith displacement contains non-finite values")

        kernel_central_prediction = central_operator @ inversion.pressure_mpa
        kernel_east_prediction = east_operator @ inversion.pressure_mpa
        central_superposition_error = float(
            np.linalg.norm(central_model_m - kernel_central_prediction)
            / max(np.linalg.norm(central_model_m), np.finfo(float).eps)
        )
        east_superposition_error = float(
            np.linalg.norm(east_model_m - kernel_east_prediction)
            / max(np.linalg.norm(east_model_m), np.finfo(float).eps)
        )
        if max(central_superposition_error, east_superposition_error) > 0.02:
            raise RuntimeError(
                "PyLith forward history differs from its linear ramp-kernel prediction "
                f"(Central={central_superposition_error:.3g}, "
                f"Eastern={east_superposition_error:.3g})"
            )

        central_rmse, east_rmse, central_corr, east_corr = _write_model_timeseries(
            inferred_history,
            times_s,
            central_model_m,
            east_model_m,
            INVERSE_TIMESERIES_PATH,
        )
        material_path = forward_dir / "output" / "maxwell-material.h5"
        with h5py.File(material_path, "r") as material:
            material_vertices = np.asarray(material["geometry/vertices"], dtype=float)
            tetrahedra = np.asarray(material["viz/topology/cells"], dtype=np.int64)
            stress = np.asarray(material["cell_fields/cauchy_stress"], dtype=float)
            viscous_strain = np.asarray(material["cell_fields/viscous_strain"], dtype=float)
        if not np.all(np.isfinite(stress)) or not np.all(np.isfinite(viscous_strain)):
            raise SystemExit("PyLith stress or viscous strain contains non-finite values")
        peak_stress_pa = float(np.max(np.abs(stress)))
        peak_final_viscous_strain = float(np.max(np.abs(viscous_strain[-1])))
        if peak_stress_pa <= 0.0 or peak_final_viscous_strain <= 0.0:
            raise SystemExit("PyLith stress or final viscous strain is zero")

        failure_history = analyze_stress_history(
            material_vertices,
            tetrahedra,
            stress,
            times_s,
            cohesion_pa=COHESION_PA,
            friction_angle_deg=FRICTION_ANGLE_DEG,
            pore_pressure_pa=PORE_PRESSURE_PA,
        )
        failure_records = [
            {
                "time_s": record["time_s"],
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
            for record in failure_history["records"]
        ]
        failure_summary = {
            "cohesion_pa": COHESION_PA,
            "friction_angle_deg": FRICTION_ANGLE_DEG,
            "friction_interpretation": "tabulated 25 degrees used directly as phi",
            "pore_pressure_pa": PORE_PRESSURE_PA,
            "tensile_cutoff_applied_to_shear_path": False,
            "record_count": len(failure_records),
            "first_cavity_to_surface_shear_path_time_s": failure_history[
                "first_cavity_to_surface_shear_path_time_s"
            ],
            "first_cavity_to_surface_shear_path_interpolated_time_s": failure_history[
                "first_cavity_to_surface_shear_path_interpolated_time_s"
            ],
            "interpolated_path_bracket": failure_history["interpolated_path_bracket"],
            "interpolation_method": failure_history["interpolation_method"],
            "interpolation_limitation": failure_history["interpolation_limitation"],
            "maximum_shear_yield_cell_count": max(
                row["mohr_coulomb_shear_yield_cell_count"] for row in failure_records
            ),
            "maximum_cavity_tensile_stress_pa": max(
                row["maximum_cavity_tensile_stress_pa"] for row in failure_records
            ),
            "records": failure_records,
        }
        max_observation_gap_days = max(
            (later - earlier).total_seconds() / 86400.0
            for earlier, later in zip(
                monthly_history.times_utc,
                monthly_history.times_utc[1:],
                strict=False,
            )
        )
        summary = {
            "method": "OOI Central pressure inversion from a PyLith one-branch Maxwell ramp kernel",
            "observation_provenance": "independent OOI BPR records only",
            "paper_publication_data_used": False,
            "input_record_start_utc": observations.times_utc[0].isoformat(),
            "input_record_end_utc": observations.times_utc[-1].isoformat(),
            "input_monthly_samples": len(monthly_history.times_utc),
            "uniform_pressure_samples": len(observations.times_utc),
            "uniform_time_step_s": time_step_s,
            "maximum_observation_gap_days": max_observation_gap_days,
            "observation_interpolation": (
                "calendar-month OOI means linearly interpolated to a uniform grid; "
                "months with no common records remain linearly bridged"
            ),
            "ooi_aggregate_quality_codes_retained": {
                "central": list(observations.central_qc_codes),
                "east": list(observations.east_qc_codes),
                "filter_applied": False,
                "interpretation": "NOT_EVALUATED",
            },
            "pressure_inversion": {
                "fitted_site": "Central BPR",
                "held_out_site": "Eastern BPR",
                "response_method": "PyLith unit-pressure ramp followed by fixed-pressure creep",
                "regularization_method": (
                    "second-difference Tikhonov penalty; coefficient selected by "
                    "generalized cross-validation"
                ),
                "regularization_coefficient": inversion.regularization,
                "effective_fit_parameters": inversion.effective_parameters,
                "pressure_change_range_mpa": [
                    float(np.min(inversion.pressure_mpa)),
                    float(np.max(inversion.pressure_mpa)),
                ],
                "central_kernel_fit_rmse_m": inversion.rmse_m,
                "central_linear_superposition_relative_l2_error": central_superposition_error,
                "eastern_linear_superposition_relative_l2_error": east_superposition_error,
            },
            "material_assumptions": {
                "rheology": "one-branch isotropic linear Maxwell",
                "youngs_modulus_pa": YOUNGS_MODULUS_PA,
                "viscosity_pa_s": VISCOSITY_PA_S,
                "poisson_ratio": POISSON_RATIO,
                "density_kg_m3": DENSITY_KG_M3,
                "temperature_dependence": False,
                "thermal_feedback": False,
                "mesh_tetrahedra": mesh_tetrahedra,
                "compliance_mesh_converged": False,
            },
            "output_records": len(times_s),
            "central_rmse_m": central_rmse,
            "central_correlation": central_corr,
            "east_rmse_m": east_rmse,
            "east_correlation": east_corr,
            "peak_abs_cauchy_stress_pa": peak_stress_pa,
            "peak_abs_final_viscous_strain": peak_final_viscous_strain,
            "failure_threshold_diagnostic": failure_summary,
            "plot_title": "OOI pressure history inferred with a Maxwell response kernel",
            "plot_note": (
                "Central-only pressure inversion; Eastern held out. Single uniform Maxwell branch, "
                "GCV second-difference smoothing, and coarse ellipsoid mesh. OOI QC 2 "
                "(NOT_EVALUATED) retained. Failure proxy is provisional; no tensile cutoff."
            ),
            "interpretation": (
                "This pressure history matches the Central uplift under an assumed one-branch "
                "Maxwell model. The Eastern comparison is held out, while branch properties, "
                "thermal feedback, and mesh convergence remain unresolved."
            ),
            "runtime_seconds": round(time.perf_counter() - started, 2),
        }

    INVERSE_SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    INVERSE_SUMMARY_PATH.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"wrote {INVERSE_SUMMARY_PATH} and {INVERSE_TIMESERIES_PATH}")


def run_historical_viscoelastic_pressure_inversion() -> None:
    """Check raw Center/South BPR pairs across the 1998 and 2011 eruptions."""
    if not (PYLITH_ROOT / "setup.sh").is_file():
        raise SystemExit("PyLith is not installed; run make install-pylith first")
    daily_summary_path = PROCESSED_DIR / "summary.json"
    if not daily_summary_path.is_file():
        raise SystemExit("missing raw BPR daily summaries; run make historical-bpr-daily first")
    daily_summary = json.loads(daily_summary_path.read_text(encoding="utf-8"))
    processed_deployments = daily_summary.get("deployments", {})
    deployments = {deployment.slug: deployment for deployment in DEPLOYMENTS}
    event_pairs = (
        ("1998", "wc81_1997", "wc82a_1997", "1998-01-25"),
        (
            "2011",
            "nemo_2010_2011_center",
            "nemo_2009_2011_south",
            "2011-04-06",
        ),
    )
    for _, center_slug, south_slug, _ in event_pairs:
        for slug in (center_slug, south_slug):
            deployment = deployments[slug]
            source = processed_deployments.get(slug, {})
            if (
                Path(source.get("source_file", "")).resolve() != deployment.path.resolve()
                or source.get("raw_channel") != deployment.raw_channel
            ):
                raise SystemExit(
                    f"{slug} daily data do not record the expected original raw channel"
                )

    HISTORICAL_INVERSE_DIR.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    event_summaries: list[dict[str, object]] = []
    with TemporaryDirectory(prefix="axial-historical-maxwell-inverse-") as temporary:
        work_dir = Path(temporary)
        (work_dir / "output").mkdir()
        mesh_path = work_dir / "mesh" / "axial_ellipsoid.msh"
        mesh_log = work_dir / "output" / "mesh.log"
        mesh_tetrahedra = _generate_mesh(mesh_path, mesh_log)
        for event, center_slug, south_slug, eruption_date in event_pairs:
            center_deployment = deployments[center_slug]
            south_deployment = deployments[south_slug]
            center_path = PROCESSED_DIR / f"{center_slug}.daily.csv"
            south_path = PROCESSED_DIR / f"{south_slug}.daily.csv"
            if not center_path.is_file() or not south_path.is_file():
                raise SystemExit(
                    "missing raw-derived daily BPR series; "
                    "run make historical-bpr-daily"
                )
            history = prepare_historical_maxwell_history(
                read_raw_daily_depths(center_path, expected_unit=center_deployment.raw_unit),
                read_raw_daily_depths(south_path, expected_unit=south_deployment.raw_unit),
                center_station=center_deployment.station,
                south_station=south_deployment.station,
                center_lat_lon_deg=(center_deployment.latitude, center_deployment.longitude),
                south_lat_lon_deg=(south_deployment.latitude, south_deployment.longitude),
            )
            interval_count = len(history.elapsed_years) - 1
            unit_ramp = replace(
                history,
                pressure_change_mpa=np.concatenate(
                    ([0.0], np.ones(interval_count, dtype=float))
                ),
            )
            event_dir = work_dir / event
            response_dir = event_dir / "unit_ramp"
            forward_dir = event_dir / "inferred_history"
            for directory in (response_dir, forward_dir):
                for subdirectory in ("mesh", "output"):
                    (directory / subdirectory).mkdir(parents=True)
                shutil.copy2(mesh_path, directory / "mesh" / mesh_path.name)

            _configure_run(
                response_dir,
                unit_ramp,
                time_step_s=history.time_step_s,
                history_description=f"Unit pressure ramp for raw {event} BPR inversion",
            )
            _run_pylith(response_dir)
            response = _read_surface_history(
                response_dir / "output" / "maxwell-surface.h5",
                fitted_lat_lon_deg=history.center_lat_lon_deg,
                held_out_lat_lon_deg=history.south_lat_lon_deg,
            )
            response_times_s, _, _, center_ramp_m, south_ramp_m = response
            if len(response_times_s) != interval_count or not np.allclose(
                np.diff(response_times_s), history.time_step_s, rtol=0.0, atol=1.0e-3
            ):
                raise RuntimeError(
                    f"raw {event} unit-ramp output does not match its uniform time grid"
                )

            center_operator = ramp_response_operator(center_ramp_m)
            south_operator = ramp_response_operator(south_ramp_m)
            inversion = invert_pressure_history(
                center_operator,
                history.center_uplift_m[1:],
            )
            pressure = np.concatenate(([0.0], inversion.pressure_mpa))
            inferred_history = replace(history, pressure_change_mpa=pressure)
            _configure_run(
                forward_dir,
                inferred_history,
                time_step_s=history.time_step_s,
                history_description=f"GCV-smoothed pressure inferred from raw {event} Center BPR",
            )
            _run_pylith(forward_dir)
            forward = _read_surface_history(
                forward_dir / "output" / "maxwell-surface.h5",
                fitted_lat_lon_deg=history.center_lat_lon_deg,
                held_out_lat_lon_deg=history.south_lat_lon_deg,
            )
            times_s, _, _, center_model_m, south_model_m = forward
            expected_duration_s = history.elapsed_years[-1] * SECONDS_PER_YEAR
            if not np.isclose(times_s[-1], expected_duration_s, rtol=0.0, atol=1.0e-3):
                raise RuntimeError(f"raw {event} PyLith history ended before the BPR overlap")

            center_kernel_m = center_operator @ inversion.pressure_mpa
            south_kernel_m = south_operator @ inversion.pressure_mpa
            center_superposition_error = float(
                np.linalg.norm(center_model_m - center_kernel_m)
                / max(np.linalg.norm(center_model_m), np.finfo(float).eps)
            )
            south_superposition_error = float(
                np.linalg.norm(south_model_m - south_kernel_m)
                / max(np.linalg.norm(south_model_m), np.finfo(float).eps)
            )
            if max(center_superposition_error, south_superposition_error) > 0.02:
                raise RuntimeError(
                    f"raw {event} pressure history fails linear superposition: "
                    f"Center={center_superposition_error:.3g}, "
                    f"South={south_superposition_error:.3g}"
                )

            center_observed_m = history.center_uplift_m[1:]
            south_observed_m = history.south_uplift_m[1:]

            def fit_metrics(observed: np.ndarray, predicted: np.ndarray) -> dict[str, float | None]:
                correlation = (
                    float(np.corrcoef(observed, predicted)[0, 1])
                    if np.std(observed) > 0.0 and np.std(predicted) > 0.0
                    else None
                )
                return {
                    "rmse_m": float(np.sqrt(np.mean((predicted - observed) ** 2))),
                    "bias_m": float(np.mean(predicted - observed)),
                    "correlation": correlation,
                }

            timeseries_path = HISTORICAL_INVERSE_DIR / f"{event}_timeseries.csv"
            with timeseries_path.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.writer(stream)
                writer.writerow(
                    [
                        "time_utc",
                        "elapsed_days",
                        "inferred_pressure_change_mpa",
                        "center_observed_uplift_m",
                        "center_pylith_uplift_m",
                        "south_observed_uplift_m",
                        "south_pylith_uplift_m",
                    ]
                )
                for index, model_time_s in enumerate(times_s):
                    writer.writerow(
                        [
                            history.times_utc[index + 1].isoformat(),
                            model_time_s / 86400.0,
                            inversion.pressure_mpa[index],
                            center_observed_m[index],
                            center_model_m[index],
                            south_observed_m[index],
                            south_model_m[index],
                        ]
                    )

            daily_manifest = daily_summary["deployments"]
            source_records = {
                "center": {
                    "deployment_slug": center_slug,
                    "station": center_deployment.station,
                    "source_file": daily_manifest[center_slug]["source_file"],
                    "raw_channel": center_deployment.raw_channel,
                    "raw_unit": center_deployment.raw_unit,
                },
                "south": {
                    "deployment_slug": south_slug,
                    "station": south_deployment.station,
                    "source_file": daily_manifest[south_slug]["source_file"],
                    "raw_channel": south_deployment.raw_channel,
                    "raw_unit": south_deployment.raw_unit,
                },
            }
            summary = {
                "event": event,
                "eruption_date_utc": eruption_date,
                "method": "Center-fitted one-branch Maxwell response-kernel pressure inversion",
                "observation_provenance": (
                    "original raw NCEI pressure and MGDS Depth/RawDep channels only"
                ),
                "paper_publication_data_used": False,
                "source_records": source_records,
                "paired_daily_records": history.paired_daily_samples,
                "overlap_start_utc": history.times_utc[0].isoformat(),
                "overlap_end_utc": history.times_utc[-1].isoformat(),
                "maximum_observation_gap_days": history.maximum_observation_gap_days,
                "daily_coverage_threshold": 0.75,
                "tide_ocean_and_drift_correction_applied": False,
                "interpolation": (
                    "shared valid daily means linearly interpolated to a uniform "
                    "seven-day grid"
                ),
                "uniform_time_step_days": history.time_step_s / 86400.0,
                "pressure_inversion": {
                    "fitted_site": center_deployment.station,
                    "held_out_site": south_deployment.station,
                    "regularization_method": (
                        "second-difference Tikhonov penalty; coefficient selected by "
                        "generalized cross-validation"
                    ),
                    "regularization_coefficient": inversion.regularization,
                    "effective_fit_parameters": inversion.effective_parameters,
                    "pressure_change_range_mpa": [
                        float(np.min(inversion.pressure_mpa)),
                        float(np.max(inversion.pressure_mpa)),
                    ],
                    "center_kernel_fit_rmse_m": inversion.rmse_m,
                    "center_linear_superposition_relative_l2_error": center_superposition_error,
                    "south_linear_superposition_relative_l2_error": south_superposition_error,
                },
                "center_forward_metrics": fit_metrics(center_observed_m, center_model_m),
                "south_holdout_metrics": fit_metrics(south_observed_m, south_model_m),
                "material_assumptions": {
                    "rheology": "one-branch isotropic linear Maxwell",
                    "youngs_modulus_pa": YOUNGS_MODULUS_PA,
                    "viscosity_pa_s": VISCOSITY_PA_S,
                    "poisson_ratio": POISSON_RATIO,
                    "mesh_tetrahedra": mesh_tetrahedra,
                    "compliance_mesh_converged": False,
                    "temperature_dependence": False,
                    "thermal_feedback": False,
                },
                "timeseries_path": str(timeseries_path),
            }
            summary_path = HISTORICAL_INVERSE_DIR / f"{event}_summary.json"
            summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
            event_summaries.append(summary)
            print(json.dumps(summary, indent=2))

    combined = {
        "method": "Raw historical BPR pressure inversion using PyLith Maxwell response kernels",
        "paper_publication_data_used": False,
        "event_checks": event_summaries,
        "runtime_seconds": round(time.perf_counter() - started, 2),
    }
    combined_path = HISTORICAL_INVERSE_DIR / "summary.json"
    combined_path.write_text(json.dumps(combined, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {combined_path}")


def main(*, eq16_hydrothermal: bool = False) -> None:
    """Run OOI pressure history with uniform or diagnostic thermal properties."""
    if not (PYLITH_ROOT / "setup.sh").is_file():
        raise SystemExit("PyLith is not installed; run make install-pylith first")
    summary_path = EQ16_SUMMARY_PATH if eq16_hydrothermal else SUMMARY_PATH
    timeseries_path = EQ16_TIMESERIES_PATH if eq16_hydrothermal else TIMESERIES_PATH
    central_bpr = read_processed_bpr_series(
        "central", latest_processed_bpr_path("central")
    )
    east_bpr = read_processed_bpr_series("east", latest_processed_bpr_path("east"))
    started = time.perf_counter()
    with TemporaryDirectory(prefix="axial-ooi-maxwell-") as temporary:
        run_dir = Path(temporary)
        elastic_dir = run_dir / "elastic"
        maxwell_dir = run_dir / "maxwell"
        for directory in ("mesh", "output"):
            (elastic_dir / directory).mkdir(parents=True)
            (maxwell_dir / directory).mkdir(parents=True)
        mesh_path = elastic_dir / "mesh" / "axial_ellipsoid.msh"
        tetrahedron_count = _generate_mesh(
            mesh_path, elastic_dir / "output" / "mesh.log"
        )
        thermal_fields = None
        thermal_diagnostics = None
        if eq16_hydrothermal:
            (
                thermal_vertices,
                thermal_tetrahedra,
                thermal_temperature_c,
                cell_youngs_modulus_pa,
                cell_conductivity_w_mk,
                thermal_iterations,
                thermal_relative_change,
            ) = _solve_eq16_hydrothermal_field(mesh_path)
            cell_temperature_c = thermal_temperature_c[thermal_tetrahedra].mean(axis=1)
            cell_viscosity_pa_s = temperature_dependent_viscosity_pa_s(
                cell_temperature_c
            )
            cell_shear_modulus_pa = cell_youngs_modulus_pa / (2.0 * (1.0 + POISSON_RATIO))
            thermal_fields = (
                thermal_vertices,
                thermal_tetrahedra,
                thermal_temperature_c,
                cell_youngs_modulus_pa,
            )
            thermal_diagnostics = {
                "temperature_c_range": [
                    float(np.min(thermal_temperature_c)),
                    float(np.max(thermal_temperature_c)),
                ],
                "youngs_modulus_pa_range": [
                    float(np.min(cell_youngs_modulus_pa)),
                    float(np.max(cell_youngs_modulus_pa)),
                ],
                "viscosity_pa_s_range": [
                    float(np.min(cell_viscosity_pa_s)),
                    float(np.max(cell_viscosity_pa_s)),
                ],
                "maxwell_time_s_range": [
                    float(np.min(cell_viscosity_pa_s / cell_shear_modulus_pa)),
                    float(np.max(cell_viscosity_pa_s / cell_shear_modulus_pa)),
                ],
                "conductivity_w_mk_range": [
                    float(np.min(cell_conductivity_w_mk)),
                    float(np.max(cell_conductivity_w_mk)),
                ],
                "thermal_boundary_conditions": {
                    "top_temperature_c": SURFACE_TEMPERATURE_C,
                    "cavity_temperature_c": CAVITY_TEMPERATURE_C,
                    "side_and_base_geotherm_c_per_km": GEOTHERM_C_PER_KM,
                },
                "steady_solver_iterations": thermal_iterations,
                "steady_solver_relative_change": thermal_relative_change,
            }
        for filename in (
            "step05.cfg",
            "pylithapp.cfg",
            "bc_cavity.spatialdb",
            "bc_zero.spatialdb",
        ):
            shutil.copy2(ELASTIC_STEP_DIR / filename, elastic_dir / filename)
        if thermal_fields is None:
            shutil.copy2(ELASTIC_STEP_DIR / "mat_elastic.spatialdb", elastic_dir)
        else:
            thermal_vertices, thermal_tetrahedra, _, cell_youngs_modulus_pa = thermal_fields
            write_elastic_database(
                elastic_dir / "mat_elastic.spatialdb",
                thermal_vertices,
                thermal_tetrahedra,
                cell_youngs_modulus_pa,
                density_kg_m3=DENSITY_KG_M3,
                poisson_ratio=POISSON_RATIO,
            )
            _set_nearest_material_query(
                elastic_dir / "pylithapp.cfg", "mat_elastic.spatialdb"
            )
        _run_pylith(elastic_dir, "step05.cfg")
        central_response, east_response = read_ellipsoid_unit_response(
            elastic_dir / "output" / "ellipsoid-surface.h5"
        )
        calibration = calibrate_ellipsoid_to_bpr(
            central_bpr,
            east_bpr,
            central_unit_response_m=float(central_response[2]),
            east_unit_response_m=float(east_response[2]),
        )
        calibration_csv = run_dir / "ooi_ellipsoid_elastic_calibration.csv"
        _write_calibration_csv(calibration_csv, calibration)
        history = read_monthly_ooi_pressure_history(calibration_csv)
        shutil.copy2(mesh_path, maxwell_dir / "mesh" / mesh_path.name)
        if thermal_fields is None:
            _configure_run(maxwell_dir, history)
        else:
            thermal_vertices, thermal_tetrahedra, thermal_temperature_c, cell_youngs_modulus_pa = (
                thermal_fields
            )
            maxwell_material_path = run_dir / "eq16_maxwell_material.spatialdb"
            write_temperature_dependent_maxwell_database(
                maxwell_material_path,
                thermal_vertices,
                thermal_tetrahedra,
                thermal_temperature_c,
                cell_youngs_modulus_pa,
                density_kg_m3=DENSITY_KG_M3,
                poisson_ratio=POISSON_RATIO,
            )
            _configure_run(
                maxwell_dir,
                history,
                material_database_path=maxwell_material_path,
            )
        _run_pylith(maxwell_dir)
        (
            times_s,
            surface_vertices,
            displacement,
            central_model_m,
            east_model_m,
        ) = _read_surface_history(maxwell_dir / "output" / "maxwell-surface.h5")
        del surface_vertices
        end_time_s = (history.times_utc[-1] - history.times_utc[0]).total_seconds()
        if not np.isclose(times_s[-1], end_time_s, rtol=0.0, atol=1.0e-4):
            raise SystemExit(f"PyLith ended at {times_s[-1]:g} s, expected {end_time_s:g} s")
        material_path = maxwell_dir / "output" / "maxwell-material.h5"
        with h5py.File(material_path, "r") as material:
            material_vertices = np.asarray(material["geometry/vertices"], dtype=float)
            tetrahedra = np.asarray(material["viz/topology/cells"], dtype=np.int64)
            stress = np.asarray(material["cell_fields/cauchy_stress"], dtype=float)
            viscous_strain = np.asarray(material["cell_fields/viscous_strain"], dtype=float)
        if not np.all(np.isfinite(stress)) or not np.all(np.isfinite(viscous_strain)):
            raise SystemExit("PyLith stress or viscous strain contains non-finite values")
        peak_stress_pa = float(np.max(np.abs(stress)))
        peak_final_viscous_strain = float(np.max(np.abs(viscous_strain[-1])))
        if peak_stress_pa <= 0.0 or peak_final_viscous_strain <= 0.0:
            debug_path = ROOT / "data" / "processed" / "ooi_maxwell_failed_run"
            if debug_path.exists():
                shutil.rmtree(debug_path)
            shutil.copytree(run_dir, debug_path)
            raise SystemExit(
                "PyLith did not write nonzero stress and viscous strain "
                f"(stress={peak_stress_pa:g} Pa, viscous_strain="
                f"{peak_final_viscous_strain:g}); run files copied to {debug_path}"
            )
        if not np.all(np.isfinite(displacement)):
            raise SystemExit("PyLith displacement contains non-finite values")

        central_rmse, east_rmse, central_corr, east_corr = _write_model_timeseries(
            history, times_s, central_model_m, east_model_m, timeseries_path
        )
        failure_history = analyze_stress_history(
            material_vertices,
            tetrahedra,
            stress,
            times_s,
            cohesion_pa=COHESION_PA,
            friction_angle_deg=FRICTION_ANGLE_DEG,
            pore_pressure_pa=PORE_PRESSURE_PA,
        )
        failure_records = [
            {
                "time_s": record["time_s"],
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
            for record in failure_history["records"]
        ]
        if len(failure_records) != len(times_s):
            raise SystemExit("failure analysis did not cover every PyLith stress record")
        first_failure_path_time_s = failure_history[
            "first_cavity_to_surface_shear_path_time_s"
        ]
        failure_summary = {
            "cohesion_pa": COHESION_PA,
            "friction_angle_deg": FRICTION_ANGLE_DEG,
            "friction_interpretation": "tabulated 25 degrees used directly as phi",
            "pore_pressure_pa": PORE_PRESSURE_PA,
            "tensile_cutoff_applied_to_shear_path": False,
            "record_count": len(failure_records),
            "first_cavity_to_surface_shear_path_time_s": first_failure_path_time_s,
            "first_cavity_to_surface_shear_path_interpolated_time_s": (
                failure_history[
                    "first_cavity_to_surface_shear_path_interpolated_time_s"
                ]
            ),
            "interpolated_path_bracket": failure_history[
                "interpolated_path_bracket"
            ],
            "interpolation_method": failure_history["interpolation_method"],
            "interpolation_limitation": failure_history[
                "interpolation_limitation"
            ],
            "maximum_shear_yield_cell_count": max(
                record["mohr_coulomb_shear_yield_cell_count"]
                for record in failure_records
            ),
            "maximum_cavity_tensile_stress_pa": max(
                record["maximum_cavity_tensile_stress_pa"]
                for record in failure_records
            ),
            "records": failure_records,
        }
        material_summary = (
            {
                "youngs_modulus_pa": None,
                "viscosity_pa_s": None,
                "thermal_property_model": {
                    "temperature_field": "steady tetrahedral Eq. 14 with Q = 0",
                    "conductivity_law": "hydrothermal Eq. 22",
                    "youngs_modulus_law": "Eq. 16 as printed; source inconsistency unresolved",
                    "viscosity_law": "Eq. 15 evaluated at absolute temperature",
                    "feedback": "one-way steady field; no deformation or viscous-heating update",
                    "calibration_and_maxwell_use_same_cellwise_modulus": True,
                    **thermal_diagnostics,
                },
            }
            if thermal_diagnostics is not None
            else {
                "youngs_modulus_pa": YOUNGS_MODULUS_PA,
                "viscosity_pa_s": VISCOSITY_PA_S,
                "thermal_property_model": None,
            }
        )
        summary = {
            "method": (
                "monthly OOI uplift converted to elastic pressure, then applied "
                "to Maxwell ellipsoid"
            ),
            "observation_provenance": "independent OOI BPR records only",
            "observations_used": True,
            "paper_publication_data_used": False,
            "input_record_start_utc": history.times_utc[0].isoformat(),
            "input_record_end_utc": history.times_utc[-1].isoformat(),
            "monthly_pressure_samples": len(history.elapsed_years),
            "monthly_sample_count_range": [
                int(min(history.monthly_record_counts[1:])),
                int(max(history.monthly_record_counts[1:])),
            ],
            "maximum_pressure_sample_gap_days": float(
                max(
                    (later - earlier).total_seconds() / 86400.0
                    for earlier, later in zip(
                        history.times_utc, history.times_utc[1:], strict=False
                    )
                )
            ),
            "monthly_sampling_method": (
                "calendar-month means; months without common finite records are omitted "
                "and interpolated linearly by the time-history database"
            ),
            "ooi_aggregate_quality_codes_retained": {
                "central": list(history.central_qc_codes),
                "east": list(history.east_qc_codes),
                "filter_applied": False,
                "interpretation": "NOT_EVALUATED",
            },
            "static_elastic_compliance_m_per_mpa": calibration.central_compliance_m_per_mpa,
            "static_pressure_fit_is_provisional": True,
            "pressure_calibration_matches_maxwell_elastic_field": eq16_hydrothermal,
            "pressure_change_range_mpa": [
                float(np.min(history.pressure_change_mpa)),
                float(np.max(history.pressure_change_mpa)),
            ],
            "pressure_time_history_interpolation": "linear between month-end samples",
            "pressure_history_units": "relative MPa from zero at first common OOI sample",
            "static_east_rmse_m": float(np.sqrt(np.mean(calibration.east_residual_m**2))),
            "static_east_correlation": calibration.summary()["east_correlation"],
            "mesh_tetrahedra": tetrahedron_count,
            "mesh_resolution_status": "coarse; ellipsoid compliance is not mesh converged",
            **material_summary,
            "poisson_ratio": POISSON_RATIO,
            "density_kg_m3": DENSITY_KG_M3,
            "maxwell_time_s": (
                None
                if eq16_hydrothermal
                else VISCOSITY_PA_S
                / (YOUNGS_MODULUS_PA / (2.0 * (1.0 + POISSON_RATIO)))
            ),
            "output_records": len(times_s),
            "end_time_s": float(times_s[-1]),
            "central_rmse_m": central_rmse,
            "central_correlation": central_corr,
            "east_rmse_m": east_rmse,
            "east_correlation": east_corr,
            "peak_abs_cauchy_stress_pa": peak_stress_pa,
            "peak_abs_final_viscous_strain": peak_final_viscous_strain,
            "failure_threshold_diagnostic": failure_summary,
            "interpretation": (
                "forward Maxwell check; pressure history comes from a static elastic fit, "
                "using the same spatial Young's modulus in both solves; not recalibrated to "
                "viscoelastic response; failure paths and tensile stresses are provisional "
                "postprocessing diagnostics, not eruption predictions"
                if eq16_hydrothermal
                else "forward Maxwell check; pressure history comes from a static elastic fit, "
                "not recalibrated to viscoelastic response; failure paths and tensile stresses "
                "are provisional postprocessing diagnostics, not eruption predictions"
            ),
            "runtime_seconds": round(time.perf_counter() - started, 2),
        }

    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"wrote {summary_path} and {timeseries_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--eq16-hydrothermal",
        action="store_true",
        help="use Eq. 22 temperature and Eq. 16 modulus in static and Maxwell solves",
    )
    parser.add_argument(
        "--viscoelastic-pressure-inversion",
        action="store_true",
        help="infer OOI pressure from a one-branch Maxwell ramp-response kernel",
    )
    parser.add_argument(
        "--historical-viscoelastic-pressure-inversion",
        action="store_true",
        help="invert raw 1998 and 2011 Center/South BPR pairs with Maxwell kernels",
    )
    arguments = parser.parse_args()
    if arguments.historical_viscoelastic_pressure_inversion:
        if arguments.eq16_hydrothermal or arguments.viscoelastic_pressure_inversion:
            parser.error("historical and OOI diagnostic options cannot be combined")
        run_historical_viscoelastic_pressure_inversion()
        raise SystemExit(0)
    if arguments.viscoelastic_pressure_inversion:
        if arguments.eq16_hydrothermal:
            parser.error("the Maxwell pressure inversion uses the uniform one-branch material")
        run_viscoelastic_pressure_inversion()
    else:
        main(eq16_hydrothermal=arguments.eq16_hydrothermal)
