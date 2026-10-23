"""Shared PyLith helpers for Center BPR pressure histories."""

from __future__ import annotations

import csv
import os
import re
import shlex
import shutil
import subprocess
from pathlib import Path

import h5py
import numpy as np

from axialstress.coordinates import local_east_north_offset_m
from axialstress.failure_analysis import analyze_pylith_material_history
from axialstress.surface_interpolation import interpolate_triangular_surface

ROOT = Path(__file__).resolve().parents[1]
MATERIAL_STEP_DIR = ROOT / "pylith" / "step12_generalized_maxwell_ellipsoid"
ELASTIC_SURFACE = (
    ROOT / "pylith" / "step05_ellipsoid_elastic" / "output" / "ellipsoid-surface.h5"
)
PYLITH_ROOT = ROOT / "pylith" / "pylith-5.0.2-linux-x86_64"
INITIAL_DT_S = 7.0 * 86_400.0
FAILURE_COHESION_PA = 1.0e6
FAILURE_FRICTION_ANGLE_DEG = 25.0
FAILURE_PORE_PRESSURE_PA = 0.0
YOUNGS_MODULUS_PA = 50.0e9
POISSON_RATIO = 0.25


def _write_pressure_history(
    path: Path,
    elapsed_seconds: np.ndarray,
    pressure_mpa: np.ndarray,
    *,
    support_interval_s: float = INITIAL_DT_S,
) -> None:
    """Write a pressure series with a constant terminal support interval."""
    if (
        elapsed_seconds.ndim != 1
        or elapsed_seconds.shape != pressure_mpa.shape
        or len(elapsed_seconds) < 2
        or not np.all(np.isfinite(elapsed_seconds))
        or not np.all(np.isfinite(pressure_mpa))
        or np.any(np.diff(elapsed_seconds) <= 0.0)
        or not np.isfinite(support_interval_s)
        or support_interval_s <= 0.0
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
                f"{elapsed_s / (365.25 * 86_400.0):.12g} "
                f"{pressure_value_mpa:.12g}\n"
            )
        terminal_support_s = elapsed_seconds[-1] + support_interval_s
        stream.write(
            f"{terminal_support_s / (365.25 * 86_400.0):.12g} "
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
    *,
    initial_dt_s: float = INITIAL_DT_S,
    history_description: str = "Raw Center BPR pressure inferred with static elastic compliance",
) -> None:
    """Create a local generalized Maxwell case with Center BPR forcing."""
    (run_dir / "mesh").mkdir(parents=True, exist_ok=True)
    (run_dir / "output").mkdir(parents=True, exist_ok=True)
    shutil.copy2(mesh_path, run_dir / "mesh" / "axial_ellipsoid.msh")
    shutil.copy2(
        material_database,
        run_dir / "output" / "genmaxwell-material.spatialdb",
    )
    shutil.copy2(
        ROOT / "pylith" / "step06_maxwell_ellipsoid" / "bc_zero.spatialdb",
        run_dir / "output" / "bc_zero.spatialdb",
    )
    _write_cavity_database(run_dir / "output" / "bc_cavity.spatialdb")
    if not np.isfinite(initial_dt_s) or initial_dt_s <= 0.0:
        raise ValueError("initial time step must be finite and positive")
    _write_pressure_history(
        run_dir / "output" / "pressure.timedb",
        elapsed_seconds,
        pressure_mpa,
        support_interval_s=initial_dt_s,
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
        f"initial_dt = {min(initial_dt_s, duration_s):.12g}*s",
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
        f"time_history.description = {history_description}\n"
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
    pylith_config = (MATERIAL_STEP_DIR / "pylithapp.cfg").read_text(
        encoding="utf-8"
    )
    (run_dir / "pylithapp.cfg").write_text(pylith_config, encoding="utf-8")


def _run_pylith(run_dir: Path) -> None:
    """Run one bounded PyLith history with eight MPI ranks."""
    log_path = run_dir / "output" / "pylith.log"
    nodes = int(os.environ.get("PYLITH_NODES", "8"))
    if nodes != 8:
        raise ValueError("this project runs PyLith with exactly 8 MPI ranks")
    command = (
        f"cd {shlex.quote(str(PYLITH_ROOT))} && source setup.sh && "
        f"cd {shlex.quote(str(run_dir))} && "
        "timeout 300 pylith --nodes=8 generalized_maxwell.cfg"
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
        tail = "\n".join(
            log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-50:]
        )
        raise RuntimeError(f"PyLith pressure-history run failed:\n{tail}")


def _read_surface_history(
    path: Path,
    reference_station: object,
    stations: dict[str, object],
) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """Sample saved vertical displacement at the Center BPR coordinate."""
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
    """Write failure diagnostics for each saved Center-driven stress state."""
    analysis = analyze_pylith_material_history(
        material_path,
        cohesion_pa=FAILURE_COHESION_PA,
        friction_angle_deg=FAILURE_FRICTION_ANGLE_DEG,
        pore_pressure_pa=FAILURE_PORE_PRESSURE_PA,
    )
    records = analysis.pop("records")
    path = output_dir / f"center_bpr_{event}_failure.csv"
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
            "joint_eruption_criterion_met": record["joint_eruption_criterion_met"],
        }
        for record in records
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    analysis["history_csv"] = path.name
    analysis["record_count"] = len(records)
    return analysis
