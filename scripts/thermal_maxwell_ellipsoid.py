"""Pass a written-law thermal viscosity field into a PyLith Maxwell smoke run."""

from __future__ import annotations

import json
import re
import shlex
import shutil
import subprocess
import sys
import time
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
from axialstress.material_database import write_temperature_dependent_maxwell_database
from axialstress.surface_interpolation import interpolate_triangular_surface
from axialstress.thermal import temperature_dependent_viscosity_pa_s
from axialstress.thermal_fem import solve_steady_temperature_tetrahedral

ROOT = Path(__file__).resolve().parents[1]
STEP_DIR = ROOT / "pylith" / "step06_maxwell_ellipsoid"
PYLITH_ROOT = ROOT / "pylith" / "pylith-5.0.2-linux-x86_64"
SUMMARY_PATH = ROOT / "data" / "processed" / "thermal_maxwell_ellipsoid_summary.json"
YOUNGS_MODULUS_PA = 50.0e9
POISSON_RATIO = 0.25
DENSITY_KG_M3 = 2800.0
SURFACE_TEMPERATURE_C = 0.0
CAVITY_TEMPERATURE_C = 1200.0
GEOTHERM_C_PER_KM = 30.0
THERMAL_CONDUCTIVITY_W_MK = 3.0
END_TIME_S = 63_115_200.0


def _generate_mesh(mesh_path: Path, log_path: Path) -> int:
    """Generate the standard ellipsoid mesh and return its tetrahedron count."""
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


def _read_mesh_and_boundaries(
    mesh_path: Path,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[int, float]]:
    """Read vertices, linear tetrahedra, depths, and written thermal boundaries."""
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
        boundary_groups = 0
        maximum_z = float(np.max(vertices[:, 2]))
        for dimension, physical_tag in gmsh.model.getPhysicalGroups(2):
            if dimension != 2:
                continue
            name = gmsh.model.getPhysicalName(dimension, physical_tag)
            if name not in ("top", "bottom", "x_neg", "x_pos", "y_neg", "y_pos", "cavity"):
                continue
            boundary_groups += 1
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
    if not len(tetrahedra) or boundary_groups != 7:
        raise ValueError("ellipsoid mesh is missing tetrahedra or a labeled boundary group")
    depth_m = float(np.max(vertices[:, 2])) - vertices[:, 2]
    return vertices, tetrahedra, depth_m, boundary_values


def _run_pylith(run_dir: Path) -> str:
    """Run the two-year Maxwell solve and return its log text."""
    log_path = run_dir / "output" / "thermal_maxwell.log"
    command = (
        f"cd {shlex.quote(str(PYLITH_ROOT))} && source setup.sh && "
        f"cd {shlex.quote(str(run_dir))} && timeout 300 pylith step06.cfg"
    )
    with log_path.open("w", encoding="utf-8") as log:
        completed = subprocess.run(
            ["bash", "-lc", command],
            cwd=ROOT,
            stdout=log,
            stderr=subprocess.STDOUT,
            check=False,
        )
    log_text = log_path.read_text(encoding="utf-8", errors="replace")
    if completed.returncode:
        tail = "\n".join(log_text.splitlines()[-40:])
        raise RuntimeError(f"PyLith thermal-viscosity run failed:\n{tail}")
    return log_text


def main() -> None:
    """Solve steady temperature, write viscosity properties, and check creep."""
    if not (PYLITH_ROOT / "setup.sh").is_file():
        raise SystemExit("PyLith is not installed; run make install-pylith first")
    started = time.perf_counter()
    with TemporaryDirectory(prefix="axial-thermal-maxwell-") as temporary:
        run_dir = Path(temporary)
        for directory in ("mesh", "output"):
            (run_dir / directory).mkdir()
        mesh_path = run_dir / "mesh" / "axial_ellipsoid.msh"
        tetrahedron_count = _generate_mesh(mesh_path, run_dir / "output" / "mesh.log")
        vertices, tetrahedra, depth_m, boundary_values = _read_mesh_and_boundaries(mesh_path)
        thermal = solve_steady_temperature_tetrahedral(
            vertices,
            tetrahedra,
            depth_m,
            boundary_values,
            conductivity=lambda temperature_c, depth: THERMAL_CONDUCTIVITY_W_MK,
            heat_production_w_m3=0.0,
        )
        write_temperature_dependent_maxwell_database(
            run_dir / "material_initial.spatialdb",
            vertices,
            tetrahedra,
            thermal.temperature_c,
            YOUNGS_MODULUS_PA,
            density_kg_m3=DENSITY_KG_M3,
            poisson_ratio=POISSON_RATIO,
        )
        cell_temperature_c = thermal.temperature_c[tetrahedra].mean(axis=1)
        cell_viscosity_pa_s = temperature_dependent_viscosity_pa_s(cell_temperature_c)

        for filename in (
            "step06.cfg",
            "bc_cavity.spatialdb",
            "bc_zero.spatialdb",
        ):
            shutil.copy2(STEP_DIR / filename, run_dir / filename)
        pylithapp = (STEP_DIR / "pylithapp.cfg").read_text(encoding="utf-8")
        pylithapp = pylithapp.replace(
            "db_auxiliary_field.iohandler.filename = material_initial.spatialdb",
            "db_auxiliary_field.query_type = nearest\n"
            "db_auxiliary_field.iohandler.filename = material_initial.spatialdb",
        )
        (run_dir / "pylithapp.cfg").write_text(pylithapp, encoding="utf-8")
        _run_pylith(run_dir)

        surface_path = run_dir / "output" / "maxwell-surface.h5"
        material_path = run_dir / "output" / "maxwell-material.h5"
        with h5py.File(surface_path, "r") as surface:
            times_s = np.asarray(surface["time"], dtype=float).reshape(-1)
            surface_vertices = np.asarray(surface["geometry/vertices"], dtype=float)
            triangles = np.asarray(surface["viz/topology/cells"], dtype=np.int64)
            displacement = np.asarray(surface["vertex_fields/displacement"], dtype=float)
        if not np.isclose(times_s[-1], END_TIME_S, rtol=0.0, atol=1.0e-5):
            raise SystemExit(f"PyLith ended at {times_s[-1]:g} s, expected {END_TIME_S:g} s")
        if displacement.shape != (len(times_s), *surface_vertices.shape):
            raise SystemExit("PyLith surface displacement has an unexpected shape")
        if not np.all(np.isfinite(displacement)):
            raise SystemExit("PyLith surface displacement contains non-finite values")

        east_offset, north_offset = local_east_north_offset_m(
            EAST_CALDERA_LAT_LON_DEG[0],
            EAST_CALDERA_LAT_LON_DEG[1],
            origin_latitude_deg=CENTRAL_CALDERA_LAT_LON_DEG[0],
            origin_longitude_deg=CENTRAL_CALDERA_LAT_LON_DEG[1],
        )
        central_uplift = np.asarray(
            [
                interpolate_triangular_surface(
                    surface_vertices, triangles, value, (0.0, 0.0)
                )[2]
                for value in displacement
            ]
        )
        east_uplift = np.asarray(
            [
                interpolate_triangular_surface(
                    surface_vertices, triangles, value, (east_offset, north_offset)
                )[2]
                for value in displacement
            ]
        )
        with h5py.File(material_path, "r") as material:
            stress = np.asarray(material["cell_fields/cauchy_stress"], dtype=float)
            viscous_strain = np.asarray(material["cell_fields/viscous_strain"], dtype=float)
        if not np.all(np.isfinite(stress)) or np.max(np.abs(stress)) <= 0.0:
            raise SystemExit("PyLith stress is non-finite or zero")
        if not np.all(np.isfinite(viscous_strain)) or np.max(
            np.abs(viscous_strain[-1])
        ) <= 0.0:
            raise SystemExit("PyLith viscous strain is non-finite or zero")
        if central_uplift[0] <= 0.0 or central_uplift[-1] <= central_uplift[0]:
            raise SystemExit(
                "temperature-dependent viscosity run did not produce positive net uplift"
            )
        central_steps = np.diff(central_uplift)
        max_uplift_decrease_m = max(0.0, float(-np.min(central_steps)))

        summary = {
            "method": "steady conduction to cell-centered Eq. 15 viscosity, then PyLith Maxwell",
            "mesh_tetrahedra": tetrahedron_count,
            "thermal_boundary_groups": 7,
            "thermal_boundary_assumptions": {
                "top_temperature_c": SURFACE_TEMPERATURE_C,
                "cavity_temperature_c": CAVITY_TEMPERATURE_C,
                "side_and_base_geotherm_c_per_km": GEOTHERM_C_PER_KM,
                "side_and_base_geotherm_status": "explicit extension assumption",
                "conductivity_w_mk": THERMAL_CONDUCTIVITY_W_MK,
                "heat_production_w_m3": 0.0,
            },
            "thermal_iterations": thermal.iterations,
            "thermal_relative_change": thermal.relative_change,
            "temperature_range_c": [
                float(np.min(thermal.temperature_c)),
                float(np.max(thermal.temperature_c)),
            ],
            "viscosity_range_pa_s": [
                float(np.min(cell_viscosity_pa_s)),
                float(np.max(cell_viscosity_pa_s)),
            ],
            "youngs_modulus_pa": YOUNGS_MODULUS_PA,
            "youngs_modulus_status": "uniform assumption; Eq. 16 remains unresolved",
            "poisson_ratio": POISSON_RATIO,
            "density_kg_m3": DENSITY_KG_M3,
            "end_time_s": float(times_s[-1]),
            "output_steps": len(times_s),
            "central_initial_uplift_m": float(central_uplift[0]),
            "central_final_uplift_m": float(central_uplift[-1]),
            "central_uplift_monotone": bool(np.all(central_steps >= -1.0e-9)),
            "max_single_step_central_uplift_decrease_m": max_uplift_decrease_m,
            "east_initial_uplift_m": float(east_uplift[0]),
            "east_final_uplift_m": float(east_uplift[-1]),
            "peak_abs_cauchy_stress_pa": float(np.max(np.abs(stress))),
            "peak_abs_final_viscous_strain": float(
                np.max(np.abs(viscous_strain[-1]))
            ),
            "one_way_material_transfer": True,
            "generalized_maxwell_branches": False,
            "temperature_mechanical_feedback": False,
            "observations_used": False,
            "runtime_seconds": round(time.perf_counter() - started, 2),
        }

    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"wrote {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
