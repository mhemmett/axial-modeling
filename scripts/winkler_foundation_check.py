"""Run a bounded PyLith outer iteration for an elastic Winkler base."""

from __future__ import annotations

import argparse
import json
import math
import os
import shlex
import subprocess
import sys
from pathlib import Path

import h5py
import numpy as np

from axialstress.ellipsoid_bpr_calibration import read_ellipsoid_unit_response
from axialstress.winkler import bottom_normal_traction_pa

ROOT = Path(__file__).resolve().parents[1]
STEP_DIR = ROOT / "pylith" / "step16_winkler_foundation"
OUTPUT_DIR = STEP_DIR / "output"
SUMMARY_PATH = ROOT / "data" / "processed" / "winkler_foundation_check.json"
CRUST_DENSITY_KG_M3 = 2_700.0
MANTLE_DENSITY_KG_M3 = 3_300.0
CRUST_THICKNESS_M = 6_000.0
GRAVITY_M_S2 = 9.81
MODEL_DEPTH_M = 10_000.0
EFFECTIVE_COLUMN_DENSITY_KG_M3 = (
    CRUST_DENSITY_KG_M3 * CRUST_THICKNESS_M
    + MANTLE_DENSITY_KG_M3 * (MODEL_DEPTH_M - CRUST_THICKNESS_M)
) / MODEL_DEPTH_M
LITHOSTATIC_PRESTRESS_PA = (
    EFFECTIVE_COLUMN_DENSITY_KG_M3 * GRAVITY_M_S2 * MODEL_DEPTH_M
)
_EQUILIBRIUM_READY = False


def _read_domain(path: Path) -> tuple[np.ndarray, np.ndarray]:
    """Read PyLith volume coordinates and final displacement."""
    with h5py.File(path, "r") as h5file:
        vertices = np.asarray(h5file["geometry/vertices"], dtype=float)
        displacement = np.asarray(h5file["vertex_fields/displacement"], dtype=float)
        times = np.asarray(h5file["time"], dtype=float).reshape(-1)
    if displacement.ndim == 3:
        displacement = displacement[-1]
    if displacement.shape != vertices.shape:
        raise ValueError("PyLith displacement values do not match volume vertices")
    if not np.all(np.isfinite(vertices)) or not np.all(np.isfinite(displacement)):
        raise ValueError("PyLith volume output contains non-finite values")
    if not len(times) or not np.all(np.isfinite(times)) or times[-1] <= 0.0:
        raise ValueError("PyLith Winkler solve did not write a valid final time")
    return vertices, displacement


def _ensure_mesh() -> Path:
    """Generate the diagnostic mesh with a single-point rigid-mode gauge."""
    mesh_path = STEP_DIR / "mesh" / "axial_ellipsoid.msh"
    mesh_path.parent.mkdir(parents=True, exist_ok=True)
    log_path = OUTPUT_DIR / "mesh.log"
    command = [
        sys.executable,
        str(ROOT / "meshing" / "axial_ellipsoid_bpr.py"),
        "--output",
        str(mesh_path),
        "--mark-base-anchor",
    ]
    with log_path.open("w", encoding="utf-8") as log_file:
        result = subprocess.run(
            command,
            cwd=ROOT,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            check=False,
        )
    if result.returncode:
        tail = log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-40:]
        raise RuntimeError("Winkler mesh generation failed:\n" + "\n".join(tail))
    return mesh_path


def _read_bottom_mesh(
    mesh_path: Path,
) -> tuple[np.ndarray, np.ndarray, float, np.ndarray]:
    """Read bottom vertices, area weights, total area, and anchor coordinates."""
    import gmsh

    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.open(str(mesh_path))
        node_tags, coordinates = gmsh.model.mesh.getNodesForPhysicalGroup(2, 103)
        node_tags = np.asarray(node_tags, dtype=np.int64)
        coordinates_m = np.asarray(coordinates, dtype=float).reshape(-1, 3)
        if node_tags.size < 3 or np.unique(node_tags).size != node_tags.size:
            raise ValueError("Gmsh bottom group must contain at least three unique nodes")
        tag_to_index = {int(tag): index for index, tag in enumerate(node_tags)}
        area_weights_m2 = np.zeros(node_tags.size, dtype=float)
        for entity in gmsh.model.getEntitiesForPhysicalGroup(2, 103):
            element_types, _, connectivity = gmsh.model.mesh.getElements(2, entity)
            for element_type, element_nodes in zip(
                element_types, connectivity, strict=True
            ):
                name, dimension, order, nodes_per_element, _, _ = (
                    gmsh.model.mesh.getElementProperties(int(element_type))
                )
                if dimension != 2 or order != 1 or name != "Triangle 3":
                    continue
                triangles = np.asarray(element_nodes, dtype=np.int64).reshape(
                    -1, nodes_per_element
                )
                triangle_indices = np.asarray(
                    [[tag_to_index[int(tag)] for tag in row] for row in triangles],
                    dtype=np.int64,
                )
                triangle_coordinates = coordinates_m[triangle_indices]
                areas_m2 = 0.5 * np.linalg.norm(
                    np.cross(
                        triangle_coordinates[:, 1] - triangle_coordinates[:, 0],
                        triangle_coordinates[:, 2] - triangle_coordinates[:, 0],
                    ),
                    axis=1,
                )
                if not np.all(np.isfinite(areas_m2)) or np.any(areas_m2 <= 0.0):
                    raise ValueError("Gmsh bottom group contains an invalid triangle")
                for local_vertex in range(3):
                    np.add.at(
                        area_weights_m2,
                        triangle_indices[:, local_vertex],
                        areas_m2 / 3.0,
                    )
        base_area_m2 = float(np.sum(area_weights_m2))
        if base_area_m2 <= 0.0 or np.any(area_weights_m2 <= 0.0):
            raise ValueError("Gmsh bottom group has invalid lumped area weights")
        anchor_tags, anchor_coordinates = gmsh.model.mesh.getNodesForPhysicalGroup(2, 108)
        anchor_coordinates_m = np.asarray(anchor_coordinates, dtype=float).reshape(-1, 3)
        if len(anchor_tags) < 3 or anchor_coordinates_m.shape[0] < 3:
            raise ValueError("Gmsh base-anchor group must contain a triangular patch")
        return coordinates_m, area_weights_m2, base_area_m2, anchor_coordinates_m
    finally:
        gmsh.finalize()


def _match_vertices(
    model_vertices_m: np.ndarray,
    boundary_coordinates_m: np.ndarray,
) -> np.ndarray:
    """Map Gmsh boundary points to matching PyLith volume vertices."""
    distances = np.linalg.norm(
        boundary_coordinates_m[:, None, :] - model_vertices_m[None, :, :], axis=2
    )
    indices = np.argmin(distances, axis=1)
    nearest_distances = distances[np.arange(len(indices)), indices]
    if np.any(nearest_distances > 1.0e-6):
        raise ValueError("Gmsh bottom nodes do not match PyLith volume coordinates")
    if np.unique(indices).size != indices.size:
        raise ValueError("multiple Gmsh bottom nodes map to one PyLith vertex")
    return indices


def _write_anchor_database(path: Path, anchor_coordinates_m: np.ndarray) -> None:
    """Write zero vertical displacement at every node on the gauge patch."""
    header = f"""#SPATIAL.ascii 1
SimpleDB {{
  num-values = 3
  value-names = initial_amplitude_x initial_amplitude_y initial_amplitude_z
  value-units = m m m
  num-locs = {anchor_coordinates_m.shape[0]}
  data-dim = 3
  space-dim = 3
  cs-data = cartesian {{
    to-meters = 1.0
    space-dim = 3
  }}
}}
"""
    with path.open("w", encoding="utf-8") as stream:
        stream.write(header)
        for coordinate in anchor_coordinates_m:
            values = (*coordinate, 0.0, 0.0, 0.0)
            stream.write(" ".join(f"{value:.17e}" for value in values) + "\n")


def _write_uniform_displacement_database(path: Path, displacement_x_m: float) -> None:
    """Write a spatially uniform x displacement in meters."""
    header = """#SPATIAL.ascii 1
SimpleDB {
  num-values = 3
  value-names = initial_amplitude_x initial_amplitude_y initial_amplitude_z
  value-units = m m m
  num-locs = 1
  data-dim = 0
  space-dim = 3
  cs-data = cartesian {
    to-meters = 1.0
    space-dim = 3
  }
}
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as stream:
        stream.write(header)
        stream.write(f"0.0 0.0 0.0 {displacement_x_m:.17e} 0.0 0.0\n")


def _lithostatic_pressure_pa(z_m: float) -> float:
    """Return compressive lithostatic pressure at elevation ``z_m`` in Pa."""
    depth_m = max(0.0, -float(z_m))
    return EFFECTIVE_COLUMN_DENSITY_KG_M3 * GRAVITY_M_S2 * depth_m


def _write_cavity_pressure_database(path: Path, overpressure_mpa: float) -> None:
    """Write depth-linear hydrostatic pressure plus cavity overpressure."""
    value_names = (
        "initial_amplitude_normal initial_amplitude_tangential_1 "
        "initial_amplitude_tangential_2"
    )
    header = """#SPATIAL.ascii 1
SimpleDB {
  num-values = 3
  value-names = __VALUE_NAMES__
  value-units = Pa Pa Pa
  num-locs = 2
  data-dim = 1
  space-dim = 3
  cs-data = cartesian {
    to-meters = 1.0
    space-dim = 3
  }
}
""".replace("__VALUE_NAMES__", value_names)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as stream:
        stream.write(header)
        for z_m in (0.0, -MODEL_DEPTH_M):
            normal_traction_pa = -(
                _lithostatic_pressure_pa(z_m) + overpressure_mpa * 1.0e6
            )
            stream.write(
                f"0.0 0.0 {z_m:.17e} {normal_traction_pa:.17e} 0.0 0.0\n"
            )


def _write_traction_database(
    path: Path,
    bottom_coordinates_m: np.ndarray,
    normal_traction_pa: np.ndarray,
) -> None:
    """Write nodal bottom-normal traction amplitudes in PyLith ASCII format."""
    if normal_traction_pa.shape != (bottom_coordinates_m.shape[0],):
        raise ValueError("bottom traction values do not match the boundary vertices")
    if not np.all(np.isfinite(normal_traction_pa)):
        raise ValueError("bottom traction contains non-finite values")
    path.parent.mkdir(parents=True, exist_ok=True)
    value_names = (
        "initial_amplitude_normal initial_amplitude_tangential_1 "
        "initial_amplitude_tangential_2"
    )
    header = f"""#SPATIAL.ascii 1
SimpleDB {{
  num-values = 3
  value-names = {value_names}
  value-units = Pa Pa Pa
  num-locs = {bottom_coordinates_m.shape[0]}
  data-dim = 3
  space-dim = 3
  cs-data = cartesian {{
    to-meters = 1.0
    space-dim = 3
  }}
}}
"""
    with path.open("w", encoding="utf-8") as stream:
        stream.write(header)
        for coordinate, normal_value in zip(
            bottom_coordinates_m, normal_traction_pa, strict=True
        ):
            values = (*coordinate, float(normal_value), 0.0, 0.0)
            stream.write(" ".join(f"{value:.17e}" for value in values) + "\n")


def _write_reference_material_database(
    path: Path, density_kg_m3: float, z_limits_m: tuple[float, float]
) -> None:
    """Write elastic properties and linear lithostatic reference stress."""
    youngs_modulus_pa = 50.0e9
    poisson_ratio = 0.25
    shear_modulus_pa = youngs_modulus_pa / (2.0 * (1.0 + poisson_ratio))
    bulk_modulus_pa = youngs_modulus_pa / (3.0 * (1.0 - 2.0 * poisson_ratio))
    vs_m_s = math.sqrt(shear_modulus_pa / density_kg_m3)
    vp_m_s = math.sqrt((bulk_modulus_pa + 4.0 * shear_modulus_pa / 3.0) / density_kg_m3)
    value_names = (
        "density vs vp reference_stress_xx reference_stress_yy "
        "reference_stress_zz reference_stress_xy reference_stress_yz "
        "reference_stress_xz reference_strain_xx reference_strain_yy "
        "reference_strain_zz reference_strain_xy reference_strain_yz "
        "reference_strain_xz"
    )
    value_units = "kg/m**3 m/s m/s " + "Pa " * 6 + "none " * 6
    header = f"""#SPATIAL.ascii 1
SimpleDB {{
  num-values = 15
  value-names = {value_names}
  value-units = {value_units}
  num-locs = 2
  data-dim = 1
  space-dim = 3
  cs-data = cartesian {{
    to-meters = 1.0
    space-dim = 3
  }}
}}
"""
    with path.open("w", encoding="utf-8") as stream:
        stream.write(header)
        for z_m in z_limits_m:
            pressure_pa = _lithostatic_pressure_pa(z_m)
            values = (
                density_kg_m3,
                vs_m_s,
                vp_m_s,
                -pressure_pa,
                -pressure_pa,
                -pressure_pa,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
            )
            stream.write(
                " ".join(f"{value:.17e}" for value in (0.0, 0.0, z_m, *values))
                + "\n"
            )


def _prepare_lithostatic_equilibrium(
    nodes: int,
    bottom_coordinates_m: np.ndarray,
    anchor_coordinates_m: np.ndarray,
) -> dict[str, float]:
    """Solve the zero-perturbation gravity and reference-stress state once."""
    global _EQUILIBRIUM_READY
    if _EQUILIBRIUM_READY:
        return {}
    _write_reference_material_database(
        OUTPUT_DIR / "reference-state.spatialdb",
        EFFECTIVE_COLUMN_DENSITY_KG_M3,
        (0.0, -MODEL_DEPTH_M),
    )
    _write_anchor_database(OUTPUT_DIR / "base-anchor.spatialdb", anchor_coordinates_m)
    _write_uniform_displacement_database(OUTPUT_DIR / "tectonic-x-neg.spatialdb", 0.0)
    _write_uniform_displacement_database(OUTPUT_DIR / "tectonic-x-pos.spatialdb", 0.0)
    _write_cavity_pressure_database(OUTPUT_DIR / "cavity-pressure.spatialdb", 0.0)
    _write_traction_database(
        OUTPUT_DIR / "winkler-traction.spatialdb",
        bottom_coordinates_m,
        np.full(bottom_coordinates_m.shape[0], -LITHOSTATIC_PRESTRESS_PA),
    )
    equilibrium_snes_atol = 1.0e4
    equilibrium_residuals: dict[str, float] = {
        "snes_absolute_tolerance": equilibrium_snes_atol
    }
    for treatment, config_name in (
        ("fixed-base", "fixed_base_equilibrium.cfg"),
        ("winkler", "equilibrium.cfg"),
    ):
        _run_pylith(
            nodes,
            config_name,
            petsc_options=(f"--petsc.snes_atol={equilibrium_snes_atol:.1f}",),
        )
        log_path = OUTPUT_DIR / f"{Path(config_name).stem}.log"
        residual_norm = _first_snes_residual(log_path)
        equilibrium_residuals[f"{treatment}_initial_residual_norm"] = residual_norm
        if residual_norm > equilibrium_snes_atol:
            raise RuntimeError(
                f"{treatment} gravity/reference residual {residual_norm:.6g} "
                f"exceeds equilibrium tolerance {equilibrium_snes_atol:.6g}"
            )
    for treatment in ("fixed-base", "winkler"):
        domain_path = OUTPUT_DIR / f"{treatment}-equilibrium-domain.h5"
        _, displacement = _read_domain(domain_path)
        max_displacement_m = float(np.max(np.linalg.norm(displacement, axis=1)))
        equilibrium_residuals[f"{treatment}_max_displacement_m"] = max_displacement_m
        if max_displacement_m > 1.0e-6:
            raise RuntimeError(
                f"{treatment} gravity/reference state moved {max_displacement_m:.6g} m; "
                "expected a near-zero equilibrium displacement"
            )
        _validate_stress(OUTPUT_DIR / f"{treatment}-equilibrium-material.h5")
    _EQUILIBRIUM_READY = True
    return equilibrium_residuals


def _first_snes_residual(log_path: Path) -> float:
    """Read the first PyLith SNES residual norm from a run log."""
    prefix = "0 SNES Function norm "
    for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if prefix in line:
            return float(line.rsplit(prefix, 1)[1])
    raise ValueError(f"PyLith log has no initial SNES residual: {log_path}")


def _run_pylith(
    nodes: int, config_name: str, *, petsc_options: tuple[str, ...] = ()
) -> None:
    """Run one static PyLith configuration with the repository binary."""
    command = (
        "unset PYTHONHOME PYTHONPATH && "
        f"source {shlex.quote(str(ROOT / 'scripts' / 'activate.sh'))} && "
        f"cd {shlex.quote(str(STEP_DIR))} && "
        f"timeout 300 pylith --nodes={nodes} {shlex.quote(config_name)} "
        + " ".join(shlex.quote(option) for option in petsc_options)
    )
    log_path = OUTPUT_DIR / f"{Path(config_name).stem}.log"
    with log_path.open("w", encoding="utf-8") as log_file:
        result = subprocess.run(
            ["bash", "-lc", command],
            cwd=ROOT,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            check=False,
        )
    if result.returncode:
        tail = log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-50:]
        raise RuntimeError(
            "PyLith Winkler solve failed; last log lines:\n" + "\n".join(tail)
        )


def run_check(
    stiffness_pa_per_m: float,
    *,
    tectonic_velocity_mm_per_year_per_face: float = 0.0,
    cavity_pressure_mpa: float = 1.0,
    nodes: int = 8,
    max_iterations: int = 20,
    relaxation: float = 0.1,
    absolute_tolerance_pa: float = 1.0,
    relative_tolerance: float = 1.0e-6,
) -> dict[str, object]:
    """Iterate the base traction until it matches the displacement spring law.

    Parameters
    ----------
    stiffness_pa_per_m : float
        Diagnostic Winkler area stiffness, in Pa/m. This is not an Axial
        Seamount estimate.
    tectonic_velocity_mm_per_year_per_face : float, optional
        Opposing x-face velocity magnitude, represented by one year of
        prescribed displacement. The project x/east direction is provisional.
    cavity_pressure_mpa : float, optional
        Static reservoir overpressure applied to the cavity boundary, in MPa.
    nodes : int, optional
        PyLith MPI process count.
    max_iterations : int, optional
        Maximum number of static PyLith solves.
    relaxation : float, optional
        Initial fraction of the fixed-point traction residual. Aitken relaxation
        updates this value within bounded limits after the first solve.
    absolute_tolerance_pa : float, optional
        Absolute traction residual threshold, in Pa.
    relative_tolerance : float, optional
        Residual threshold relative to the maximum target traction.

    Returns
    -------
    dict
        Solver configuration, iteration residuals, and fixed-base comparison.
    """
    numeric_inputs = (
        stiffness_pa_per_m,
        tectonic_velocity_mm_per_year_per_face,
        cavity_pressure_mpa,
        relaxation,
        absolute_tolerance_pa,
        relative_tolerance,
    )
    if not all(math.isfinite(value) for value in numeric_inputs):
        raise ValueError("Winkler solve parameters must be finite")
    if stiffness_pa_per_m <= 0.0:
        raise ValueError("stiffness_pa_per_m must be positive")
    if cavity_pressure_mpa < 0.0:
        raise ValueError("cavity_pressure_mpa must be nonnegative")
    if nodes != 8 or max_iterations <= 0:
        raise ValueError("nodes must be 8 and max_iterations must be positive")
    if not 0.0 < relaxation <= 1.0:
        raise ValueError("relaxation must be in (0, 1]")
    if absolute_tolerance_pa <= 0.0 or relative_tolerance <= 0.0:
        raise ValueError("convergence tolerances must be positive")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    mesh_path = _ensure_mesh()
    (
        bottom_coordinates_m,
        area_weights_m2,
        bottom_area_m2,
        anchor_coordinates_m,
    ) = _read_bottom_mesh(mesh_path)
    equilibrium_residuals = _prepare_lithostatic_equilibrium(
        nodes,
        bottom_coordinates_m,
        anchor_coordinates_m,
    )
    displacement_m = tectonic_velocity_mm_per_year_per_face * 1.0e-3
    _write_uniform_displacement_database(
        OUTPUT_DIR / "tectonic-x-neg.spatialdb", -displacement_m
    )
    _write_uniform_displacement_database(
        OUTPUT_DIR / "tectonic-x-pos.spatialdb", displacement_m
    )
    _write_cavity_pressure_database(
        OUTPUT_DIR / "cavity-pressure.spatialdb", cavity_pressure_mpa
    )

    _run_pylith(nodes, "fixed_base.cfg")
    fixed_domain = OUTPUT_DIR / "fixed-base-domain.h5"
    fixed_surface = OUTPUT_DIR / "fixed-base-surface.h5"
    _validate_stress(OUTPUT_DIR / "fixed-base-material.h5")
    fixed_vertices, _ = _read_domain(fixed_domain)
    fixed_central_vector, fixed_east_vector = read_ellipsoid_unit_response(fixed_surface)
    baseline_central_up_m = float(fixed_central_vector[2])
    baseline_east_up_m = float(fixed_east_vector[2])

    applied_normal_pa = np.full(
        bottom_coordinates_m.shape[0], -LITHOSTATIC_PRESTRESS_PA
    )
    iteration_records: list[dict[str, float | int]] = []
    final_vertices = np.empty((0, 3))
    final_displacement = np.empty((0, 3))
    final_bottom_indices = np.empty(0, dtype=np.int64)
    converged = False
    previous_residual_pa: np.ndarray | None = None
    relaxation_factor = relaxation

    for iteration in range(1, max_iterations + 1):
        _write_traction_database(
            OUTPUT_DIR / "winkler-traction.spatialdb",
            bottom_coordinates_m,
            applied_normal_pa,
        )
        _run_pylith(nodes, "winkler.cfg")
        domain_path = OUTPUT_DIR / "winkler-domain.h5"
        final_vertices, final_displacement = _read_domain(domain_path)
        if not np.array_equal(final_vertices, fixed_vertices):
            raise ValueError("fixed-base and Winkler runs used different mesh coordinates")
        final_bottom_indices = _match_vertices(final_vertices, bottom_coordinates_m)
        vertical_displacement_m = final_displacement[final_bottom_indices, 2]
        target_normal_pa = np.asarray(
            [
                bottom_normal_traction_pa(
                    value,
                    stiffness_pa_per_m,
                    vertical_offset_pa=LITHOSTATIC_PRESTRESS_PA,
                )
                for value in vertical_displacement_m
            ],
            dtype=float,
        )
        residual_pa = target_normal_pa - applied_normal_pa
        max_residual_pa = float(np.max(np.abs(residual_pa)))
        max_target_pa = float(np.max(np.abs(target_normal_pa)))
        target_increment_pa = target_normal_pa + LITHOSTATIC_PRESTRESS_PA
        max_target_increment_pa = float(np.max(np.abs(target_increment_pa)))
        tolerance_pa = absolute_tolerance_pa + relative_tolerance * max_target_increment_pa
        iteration_records.append(
            {
                "iteration": iteration,
                "max_abs_vertical_displacement_m": float(
                    np.max(np.abs(vertical_displacement_m))
                ),
                "max_target_normal_traction_pa": max_target_pa,
                "max_target_incremental_traction_pa": max_target_increment_pa,
                "max_abs_traction_residual_pa": max_residual_pa,
                "convergence_tolerance_pa": tolerance_pa,
                "relaxation_factor": relaxation_factor,
            }
        )
        if max_residual_pa <= tolerance_pa:
            converged = True
            break
        applied_normal_pa += relaxation_factor * residual_pa
        if previous_residual_pa is not None:
            residual_change_pa = residual_pa - previous_residual_pa
            denominator = float(np.dot(residual_change_pa, residual_change_pa))
            if denominator > np.finfo(float).tiny:
                aitken_factor = -relaxation_factor * float(
                    np.dot(previous_residual_pa, residual_change_pa)
                ) / denominator
                if math.isfinite(aitken_factor):
                    relaxation_factor = min(0.25, max(0.01, aitken_factor))
        previous_residual_pa = residual_pa.copy()

    if not converged:
        raise RuntimeError(
            f"Winkler traction failed to converge in {max_iterations} solves; "
            f"iteration records: {json.dumps(iteration_records)}"
        )

    surface_path = OUTPUT_DIR / "winkler-surface.h5"
    _validate_stress(OUTPUT_DIR / "winkler-material.h5")
    central_vector, east_vector = read_ellipsoid_unit_response(surface_path)
    central_up_m = float(central_vector[2])
    east_up_m = float(east_vector[2])
    summary: dict[str, object] = {
        "method": "outer iteration of PyLith Neumann traction with Galgana Winkler law",
        "scientific_status": (
            "lithostatic gravity/reference-stress equilibrium plus a regional "
            "finite-spring perturbation"
        ),
        "source_equation": (
            "global t_z = -k_W * u_z + t_z0, with gravity, column-mean density, "
            "and matching hydrostatic cavity/base tractions initialized"
        ),
        "bottom_boundary_normal_convention": (
            "outward normal is downward; local normal traction is "
            "k_W*u_z - t_z0"
        ),
        "area_stiffness_pa_per_m": stiffness_pa_per_m,
        "outer_iteration_relaxation": {
            "initial_factor": relaxation,
            "update": "bounded vector Aitken delta-squared acceleration",
            "factor_limits": [0.01, 0.25],
        },
        "area_stiffness_ratio_to_E_over_H": stiffness_pa_per_m * 10_000.0 / 50.0e9,
        "basal_prestress_global_up_pa": LITHOSTATIC_PRESTRESS_PA,
        "basal_prestress_bottom_normal_pa": -LITHOSTATIC_PRESTRESS_PA,
        "lithostatic_equilibrium_diagnostics": equilibrium_residuals,
        "equilibrium_density_kg_m3": EFFECTIVE_COLUMN_DENSITY_KG_M3,
        "equilibrium_density_basis": (
            "depth average of the 2700 kg/m3, 6 km crust and 3300 kg/m3, "
            "4 km mantle column used to calibrate basal prestress"
        ),
        "rigid_translation_gauge": (
            "500 m by 500 m bottom patch with zero vertical displacement; "
            "spring traction is omitted on that patch"
        ),
        "youngs_modulus_pa": 50.0e9,
        "poisson_ratio": 0.25,
        "cavity_overpressure_mpa": cavity_pressure_mpa,
        "tectonic_loading": {
            "axis": (
                "project +x/east direction; geographic ridge-normal alignment is "
                "not reconciled"
            ),
            "per_face_velocity_mm_per_year": tectonic_velocity_mm_per_year_per_face,
            "full_spreading_rate_mm_per_year": (
                2.0 * tectonic_velocity_mm_per_year_per_face
            ),
            "opposing_face_displacement_m_after_one_year": displacement_m,
        },
        "geometry": "50 km x 50 km x 10 km box with 6 km x 3 km x 1 km ellipsoidal cavity",
        "mesh_tetrahedra": int(_count_tetrahedra(mesh_path)),
        "mpi_ranks": nodes,
        "converged": converged,
        "iterations": iteration_records,
        "maximum_bottom_vertical_displacement_m": float(
            np.max(np.abs(final_displacement[final_bottom_indices, 2]))
        ),
        "bottom_area_m2": bottom_area_m2,
        "area_weighted_mean_bottom_vertical_displacement_m": float(
            np.average(
                final_displacement[final_bottom_indices, 2],
                weights=area_weights_m2,
            )
        ),
        "central_vertical_compliance_m_per_mpa": central_up_m,
        "east_vertical_compliance_m_per_mpa": east_up_m,
        "fixed_base_central_vertical_compliance_m_per_mpa": baseline_central_up_m,
        "fixed_base_east_vertical_compliance_m_per_mpa": baseline_east_up_m,
        "central_compliance_fractional_change": (
            central_up_m / baseline_central_up_m - 1.0
        ),
        "east_compliance_fractional_change": (
            east_up_m / baseline_east_up_m - 1.0
        ),
        "model_outputs": [
            str(fixed_domain),
            str(fixed_surface),
            str(OUTPUT_DIR / "winkler-domain.h5"),
            str(surface_path),
            str(OUTPUT_DIR / "fixed-base-equilibrium-material.h5"),
            str(OUTPUT_DIR / "winkler-equilibrium-material.h5"),
        ],
        "provenance": "no BPR data or paper-produced numerical results used",
        "limitations": [
            "the regional upper-mantle density is a prior, not an Axial-depth measurement",
            "the 500 m by 500 m fixed gauge patch omits basal spring traction",
            "the nodal SimpleDB uses nearest-point traction sampling",
            "the mesh is not converged and uses uniform 50 GPa elasticity",
            "the check does not recalibrate historical pressure or recompute failure paths",
        ],
    }
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def _validate_stress(path: Path) -> None:
    """Reject missing, non-finite, or zero PyLith stress output."""
    with h5py.File(path, "r") as h5file:
        stress = np.asarray(h5file["cell_fields/cauchy_stress"], dtype=float)
    if not np.all(np.isfinite(stress)) or np.max(np.abs(stress)) <= 0.0:
        raise ValueError("PyLith Winkler run produced invalid Cauchy stress")


def _count_tetrahedra(mesh_path: Path) -> int:
    """Count tetrahedra in the generated Gmsh mesh."""
    import gmsh

    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.open(str(mesh_path))
        tetrahedra = 0
        element_types, element_tags, _ = gmsh.model.mesh.getElements(3)
        for element_type, tags in zip(element_types, element_tags, strict=True):
            name, dimension, order, _, _, _ = gmsh.model.mesh.getElementProperties(
                int(element_type)
            )
            if dimension == 3 and order == 1 and name.startswith("Tetrahedron"):
                tetrahedra += len(tags)
        if tetrahedra <= 0:
            raise ValueError(f"mesh has no first-order tetrahedra: {mesh_path}")
        return tetrahedra
    finally:
        gmsh.finalize()


def main() -> None:
    """Run one configurable, bounded static Winkler response check."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stiffness-pa-per-m", type=float, required=True)
    parser.add_argument(
        "--tectonic-velocity-mm-per-year-per-face", type=float, default=0.0,
        help="opposing x-face velocity magnitude; applied as one year of displacement",
    )
    parser.add_argument("--cavity-pressure-mpa", type=float, default=1.0)
    parser.add_argument(
        "--nodes",
        type=int,
        choices=(8,),
        default=int(os.environ.get("PYLITH_NODES", "8")),
        help="PyLith MPI ranks; this project requires 8",
    )
    parser.add_argument("--max-iterations", type=int, default=20)
    parser.add_argument("--relaxation", type=float, default=0.1)
    parser.add_argument("--absolute-tolerance-pa", type=float, default=1.0)
    parser.add_argument("--relative-tolerance", type=float, default=1.0e-6)
    args = parser.parse_args()
    summary = run_check(
        args.stiffness_pa_per_m,
        tectonic_velocity_mm_per_year_per_face=(
            args.tectonic_velocity_mm_per_year_per_face
        ),
        cavity_pressure_mpa=args.cavity_pressure_mpa,
        nodes=args.nodes,
        max_iterations=args.max_iterations,
        relaxation=args.relaxation,
        absolute_tolerance_pa=args.absolute_tolerance_pa,
        relative_tolerance=args.relative_tolerance,
    )
    print(json.dumps(summary, indent=2))
    print(f"wrote {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
