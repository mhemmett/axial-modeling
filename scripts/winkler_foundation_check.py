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
    if not len(times) or not np.isclose(times[-1], 1.0, rtol=0.0, atol=1.0e-12):
        raise ValueError("PyLith Winkler solve did not reach the configured 1 s end time")
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


def _run_pylith(nodes: int, config_name: str) -> None:
    """Run one static PyLith configuration with the repository binary."""
    command = (
        f"source {shlex.quote(str(ROOT / 'scripts' / 'activate.sh'))} && "
        f"cd {shlex.quote(str(STEP_DIR))} && "
        f"timeout 300 pylith --nodes={nodes} {shlex.quote(config_name)}"
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
    nodes: int = 8,
    max_iterations: int = 12,
    relaxation: float = 1.0,
    absolute_tolerance_pa: float = 0.1,
    relative_tolerance: float = 1.0e-6,
) -> dict[str, object]:
    """Iterate the base traction until it matches the displacement spring law.

    Parameters
    ----------
    stiffness_pa_per_m : float
        Diagnostic Winkler area stiffness, in Pa/m. This is not an Axial
        Seamount estimate.
    nodes : int, optional
        PyLith MPI process count.
    max_iterations : int, optional
        Maximum number of static PyLith solves.
    relaxation : float, optional
        Fraction of the fixed-point traction residual applied each iteration.
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
        relaxation,
        absolute_tolerance_pa,
        relative_tolerance,
    )
    if not all(math.isfinite(value) for value in numeric_inputs):
        raise ValueError("Winkler solve parameters must be finite")
    if stiffness_pa_per_m <= 0.0:
        raise ValueError("stiffness_pa_per_m must be positive")
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
    anchor_database_path = OUTPUT_DIR / "base-anchor.spatialdb"
    _write_anchor_database(anchor_database_path, anchor_coordinates_m)

    _run_pylith(nodes, "fixed_base.cfg")
    fixed_domain = OUTPUT_DIR / "fixed-base-domain.h5"
    fixed_surface = OUTPUT_DIR / "fixed-base-surface.h5"
    fixed_material = OUTPUT_DIR / "fixed-base-material.h5"
    _validate_stress(fixed_material)
    fixed_vertices, _ = _read_domain(fixed_domain)
    fixed_central_vector, fixed_east_vector = read_ellipsoid_unit_response(fixed_surface)
    baseline_central_up_m = float(fixed_central_vector[2])
    baseline_east_up_m = float(fixed_east_vector[2])

    applied_normal_pa = np.zeros(bottom_coordinates_m.shape[0], dtype=float)
    iteration_records: list[dict[str, float | int]] = []
    final_vertices = np.empty((0, 3))
    final_displacement = np.empty((0, 3))
    final_bottom_indices = np.empty(0, dtype=np.int64)
    final_offset_pa = 0.0
    converged = False

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
        final_offset_pa = stiffness_pa_per_m * float(
            np.average(vertical_displacement_m, weights=area_weights_m2)
        )
        target_normal_pa = np.asarray(
            [
                bottom_normal_traction_pa(
                    value,
                    stiffness_pa_per_m,
                    vertical_offset_pa=final_offset_pa,
                )
                for value in vertical_displacement_m
            ],
            dtype=float,
        )
        residual_pa = target_normal_pa - applied_normal_pa
        max_residual_pa = float(np.max(np.abs(residual_pa)))
        max_target_pa = float(np.max(np.abs(target_normal_pa)))
        tolerance_pa = absolute_tolerance_pa + relative_tolerance * max_target_pa
        iteration_records.append(
            {
                "iteration": iteration,
                "max_abs_vertical_displacement_m": float(
                    np.max(np.abs(vertical_displacement_m))
                ),
                "max_target_normal_traction_pa": max_target_pa,
                "max_abs_traction_residual_pa": max_residual_pa,
                "convergence_tolerance_pa": tolerance_pa,
            }
        )
        if max_residual_pa <= tolerance_pa:
            converged = True
            break
        applied_normal_pa += relaxation * residual_pa

    if not converged:
        raise RuntimeError(
            f"Winkler traction failed to converge in {max_iterations} solves; "
            f"final max residual was {iteration_records[-1]['max_abs_traction_residual_pa']:.6g} Pa"
        )

    surface_path = OUTPUT_DIR / "winkler-surface.h5"
    material_path = OUTPUT_DIR / "winkler-material.h5"
    _validate_stress(material_path)
    central_vector, east_vector = read_ellipsoid_unit_response(surface_path)
    central_up_m = float(central_vector[2])
    east_up_m = float(east_vector[2])
    summary: dict[str, object] = {
        "method": "outer iteration of PyLith Neumann traction with Galgana Winkler law",
        "scientific_status": "boundary-kernel verification only; not an Axial stiffness estimate",
        "source_equation": (
            "global t_z = -k_W * u_z + t_z0; no prestress is modeled "
            "in this incremental solve"
        ),
        "bottom_boundary_normal_convention": (
            "outward normal is downward; local normal traction is "
            "k_W*u_z - t_z0"
        ),
        "area_stiffness_pa_per_m": stiffness_pa_per_m,
        "area_stiffness_ratio_to_E_over_H": stiffness_pa_per_m * 10_000.0 / 50.0e9,
        "vertical_traction_offset_pa": final_offset_pa,
        "offset_assumption": (
            "each incremental traction field is area-centered to balance its "
            "vertical resultant; this is not a lithostatic prestress calculation"
        ),
        "rigid_translation_gauge": (
            "500 m by 500 m bottom patch with zero vertical displacement; "
            "spring traction is omitted on that patch"
        ),
        "youngs_modulus_pa": 50.0e9,
        "poisson_ratio": 0.25,
        "cavity_overpressure_mpa": 1.0,
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
            str(material_path),
        ],
        "provenance": "no BPR data or paper-produced numerical results used",
        "limitations": [
            "Axial density contrast for the Galgana coefficient is unresolved",
            (
                "the offset is force-balanced for this incremental solve, "
                "not derived from lithostatic prestress"
            ),
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
        "--nodes",
        type=int,
        choices=(8,),
        default=int(os.environ.get("PYLITH_NODES", "8")),
        help="PyLith MPI ranks; this project requires 8",
    )
    parser.add_argument("--max-iterations", type=int, default=12)
    parser.add_argument("--relaxation", type=float, default=1.0)
    parser.add_argument("--absolute-tolerance-pa", type=float, default=0.1)
    parser.add_argument("--relative-tolerance", type=float, default=1.0e-6)
    args = parser.parse_args()
    summary = run_check(
        args.stiffness_pa_per_m,
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
