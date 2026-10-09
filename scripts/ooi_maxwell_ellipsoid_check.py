"""Drive an ellipsoid Maxwell run with pressure inferred from independent OOI BPRs."""

from __future__ import annotations

import csv
import json
import re
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path
from tempfile import TemporaryDirectory

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
from axialstress.ooi_pressure_history import (
    OoiPressureHistory,
    read_monthly_ooi_pressure_history,
    write_normalized_time_history,
)
from axialstress.surface_interpolation import interpolate_triangular_surface

ROOT = Path(__file__).resolve().parents[1]
STEP_DIR = ROOT / "pylith" / "step06_maxwell_ellipsoid"
ELASTIC_STEP_DIR = ROOT / "pylith" / "step05_ellipsoid_elastic"
PYLITH_ROOT = ROOT / "pylith" / "pylith-5.0.2-linux-x86_64"
SUMMARY_PATH = ROOT / "data" / "processed" / "ooi_maxwell_ellipsoid_summary.json"
TIMESERIES_PATH = ROOT / "data" / "processed" / "ooi_maxwell_ellipsoid_timeseries.csv"
PRESSURE_AMPLITUDE_PA = -1.0e6
SECONDS_PER_YEAR = 365.25 * 24.0 * 3600.0
YOUNGS_MODULUS_PA = 50.0e9
POISSON_RATIO = 0.25
VISCOSITY_PA_S = 1.0e18
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


def _read_surface_history(
    surface_path: Path,
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

    east_offset, north_offset = local_east_north_offset_m(
        EAST_CALDERA_LAT_LON_DEG[0],
        EAST_CALDERA_LAT_LON_DEG[1],
        origin_latitude_deg=CENTRAL_CALDERA_LAT_LON_DEG[0],
        origin_longitude_deg=CENTRAL_CALDERA_LAT_LON_DEG[1],
    )
    central_uplift = np.asarray(
        [
            interpolate_triangular_surface(vertices, triangles, field, (0.0, 0.0))[2]
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


def _configure_run(run_dir: Path, history: OoiPressureHistory) -> None:
    """Copy the Maxwell inputs and connect its cavity traction to TimeHistory."""
    for filename in (
        "step06.cfg",
        "pylithapp.cfg",
        "bc_zero.spatialdb",
        "material_initial.spatialdb",
    ):
        shutil.copy2(STEP_DIR / filename, run_dir / filename)
    duration_s = (history.times_utc[-1] - history.times_utc[0]).total_seconds()
    step_configuration = (run_dir / "step06.cfg").read_text(encoding="utf-8")
    step_configuration, replacements = re.subn(
        r"(?m)^end_time\s*=.*$", f"end_time = {duration_s:.12g}*s", step_configuration
    )
    if replacements != 1:
        raise ValueError("could not set the observation-window PyLith end time")
    cavity_database_line = "db_auxiliary_field.iohandler.filename = bc_cavity.spatialdb"
    if step_configuration.count(cavity_database_line) != 1:
        raise ValueError("could not connect the OOI history to the cavity traction")
    step_configuration = step_configuration.replace(
        cavity_database_line,
        "use_time_history = True\n"
        f"{cavity_database_line}\n"
        "time_history = spatialdata.spatialdb.TimeHistory\n"
        "time_history.description = Monthly OOI-inferred elastic pressure changes\n"
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
) -> tuple[float, float, float | None, float | None]:
    """Save model and monthly observed uplift together and return fit metrics."""
    model_years = times_s / SECONDS_PER_YEAR
    central_observed_m = np.interp(
        model_years, history.elapsed_years, history.central_uplift_m
    )
    east_observed_m = np.interp(model_years, history.elapsed_years, history.east_uplift_m)
    pressure_mpa = np.interp(model_years, history.elapsed_years, history.pressure_change_mpa)
    with TIMESERIES_PATH.open("w", encoding="utf-8", newline="") as stream:
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


def main() -> None:
    """Run the OOI-derived pressure history through the ellipsoid Maxwell model."""
    if not (PYLITH_ROOT / "setup.sh").is_file():
        raise SystemExit("PyLith is not installed; run make install-pylith first")
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
        for filename in (
            "step05.cfg",
            "pylithapp.cfg",
            "bc_cavity.spatialdb",
            "bc_zero.spatialdb",
            "mat_elastic.spatialdb",
        ):
            shutil.copy2(ELASTIC_STEP_DIR / filename, elastic_dir / filename)
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
        _configure_run(maxwell_dir, history)
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
            history, times_s, central_model_m, east_model_m
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
            "youngs_modulus_pa": YOUNGS_MODULUS_PA,
            "poisson_ratio": POISSON_RATIO,
            "viscosity_pa_s": VISCOSITY_PA_S,
            "maxwell_time_s": VISCOSITY_PA_S / (YOUNGS_MODULUS_PA / (2.0 * (1.0 + POISSON_RATIO))),
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
                "not recalibrated to viscoelastic response; failure paths and tensile stresses "
                "are provisional postprocessing diagnostics, not eruption predictions"
            ),
            "runtime_seconds": round(time.perf_counter() - started, 2),
        }

    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"wrote {SUMMARY_PATH} and {TIMESERIES_PATH}")


if __name__ == "__main__":
    main()
