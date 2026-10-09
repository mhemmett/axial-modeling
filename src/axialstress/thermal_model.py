"""Solve the written steady thermal model on a PyLith tetrahedral mesh."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from axialstress.thermal import hydrothermal_conductivity_w_mk
from axialstress.thermal_fem import solve_steady_temperature_tetrahedral

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]
OUTER_BOUNDARIES = ("top", "bottom", "x_neg", "x_pos", "y_neg", "y_pos")
REQUIRED_BOUNDARIES = (*OUTER_BOUNDARIES, "cavity")


def geothermal_dirichlet_conditions(
    vertices_m: FloatArray,
    boundary_nodes: Mapping[str, Sequence[int]],
    *,
    background_gradient_c_km: float = 30.0,
    reservoir_temperature_c: float = 1200.0,
) -> dict[int, float]:
    """Build outer-geotherm and reservoir-temperature boundary values.

    Parameters
    ----------
    vertices_m : array_like
        Cartesian coordinates with shape ``(nvertices, 3)`` and a zero-depth
        surface at ``z = 0``, in meters.
    boundary_nodes : mapping
        Physical boundary names mapped to zero-based vertex indices. The
        required names are ``top``, ``bottom``, ``x_neg``, ``x_pos``, ``y_neg``,
        ``y_pos``, and ``cavity``.
    background_gradient_c_km : float
        Positive-down geotherm on the external boundaries, in degrees Celsius
        per kilometer.
    reservoir_temperature_c : float
        Prescribed temperature on the reservoir surface, in degrees Celsius.

    Returns
    -------
    dict[int, float]
        Dirichlet temperatures keyed by zero-based vertex index.

    Raises
    ------
    ValueError
        If the geometry, boundary names, or temperatures are invalid.
    """
    vertices = np.asarray(vertices_m, dtype=float)
    if vertices.ndim != 2 or vertices.shape[1] != 3 or len(vertices) < 4:
        raise ValueError("vertices_m must have shape (n, 3) with at least four points")
    if not np.all(np.isfinite(vertices)):
        raise ValueError("vertex coordinates must be finite")
    if np.any(vertices[:, 2] > 1.0e-8):
        raise ValueError("the mesh must lie at or below the z = 0 surface")
    if not np.isfinite(background_gradient_c_km) or background_gradient_c_km < 0.0:
        raise ValueError("background geotherm must be finite and nonnegative")
    if not np.isfinite(reservoir_temperature_c):
        raise ValueError("reservoir temperature must be finite")
    if set(boundary_nodes) != set(REQUIRED_BOUNDARIES):
        missing = sorted(set(REQUIRED_BOUNDARIES) - set(boundary_nodes))
        extra = sorted(set(boundary_nodes) - set(REQUIRED_BOUNDARIES))
        raise ValueError(
            f"boundary names differ from the required set; missing={missing}, extra={extra}"
        )

    values: dict[int, float] = {}
    for name in OUTER_BOUNDARIES:
        indices = np.asarray(boundary_nodes[name], dtype=np.int64)
        if indices.ndim != 1 or indices.size == 0:
            raise ValueError(f"boundary {name!r} must contain at least one node")
        if np.any(indices < 0) or np.any(indices >= len(vertices)):
            raise ValueError(f"boundary {name!r} contains an invalid node index")
        for index in indices:
            node = int(index)
            depth_km = max(0.0, -float(vertices[node, 2])) / 1000.0
            temperature_c = background_gradient_c_km * depth_km
            previous = values.get(node)
            if previous is not None and not np.isclose(
                previous, temperature_c, atol=1.0e-10
            ):
                raise ValueError(
                    f"outer boundaries assign inconsistent temperatures at node {node}"
                )
            values[node] = temperature_c

    cavity_indices = np.asarray(boundary_nodes["cavity"], dtype=np.int64)
    if cavity_indices.ndim != 1 or cavity_indices.size == 0:
        raise ValueError("boundary 'cavity' must contain at least one node")
    if np.any(cavity_indices < 0) or np.any(cavity_indices >= len(vertices)):
        raise ValueError("boundary 'cavity' contains an invalid node index")
    overlap = set(map(int, cavity_indices)) & set(values)
    if overlap:
        raise ValueError(f"reservoir and outer boundaries overlap at nodes {sorted(overlap)}")
    values.update({int(index): reservoir_temperature_c for index in cavity_indices})
    return values


def _read_gmsh_tetrahedral_mesh(
    mesh_path: str | Path,
) -> tuple[FloatArray, IntArray, dict[str, NDArray[np.int64]]]:
    """Read first-order tetrahedra and named two-dimensional physical groups."""
    try:
        import gmsh
    except ImportError as exc:
        raise RuntimeError("Gmsh's Python API is required; install environment.yml") from exc

    names_by_tag = {
        101: "cavity",
        102: "top",
        103: "bottom",
        104: "x_neg",
        105: "x_pos",
        106: "y_neg",
        107: "y_pos",
    }
    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.open(str(mesh_path))
        node_tags, coordinates, _ = gmsh.model.mesh.getNodes()
        vertices = np.asarray(coordinates, dtype=float).reshape(-1, 3)
        index_by_tag = {int(tag): index for index, tag in enumerate(node_tags)}

        element_types, _, element_nodes = gmsh.model.mesh.getElements(3)
        tetrahedra: list[list[int]] = []
        for element_type, tags in zip(element_types, element_nodes, strict=True):
            _, dimension, order, node_count, _, _ = gmsh.model.mesh.getElementProperties(
                int(element_type)
            )
            if dimension != 3:
                continue
            if order != 1 or node_count != 4:
                raise ValueError("thermal model requires first-order tetrahedra")
            tetrahedra.extend(
                [[index_by_tag[int(tag)] for tag in cell] for cell in tags.reshape(-1, 4)]
            )
        if not tetrahedra:
            raise ValueError("mesh contains no tetrahedra")

        boundary_nodes: dict[str, set[int]] = {name: set() for name in REQUIRED_BOUNDARIES}
        for dimension, physical_tag in gmsh.model.getPhysicalGroups(2):
            name = names_by_tag.get(int(physical_tag))
            if dimension != 2 or name is None:
                continue
            for entity_tag in gmsh.model.getEntitiesForPhysicalGroup(dimension, physical_tag):
                tags, _, _ = gmsh.model.mesh.getNodes(
                    dimension, int(entity_tag), includeBoundary=True
                )
                boundary_nodes[name].update(index_by_tag[int(tag)] for tag in tags)
    finally:
        gmsh.finalize()

    return (
        vertices,
        np.asarray(tetrahedra, dtype=np.int64),
        {
            name: np.asarray(sorted(indices), dtype=np.int64)
            for name, indices in boundary_nodes.items()
        },
    )


def solve_written_thermal_model(
    mesh_path: str | Path,
    output_path: str | Path,
    *,
    hydrothermal: bool = False,
    background_gradient_c_km: float = 30.0,
    reservoir_temperature_c: float = 1200.0,
) -> tuple[int, float, float, float, float, float, float]:
    """Solve the steady geotherm and save its mesh-aligned temperature field.

    The source describes a zero-source steady heat equation, a 30 °C/km
    background geotherm, and a 1200 °C reservoir boundary. Because it does not
    fully specify lateral and basal thermal conditions, this utility applies
    the background geotherm to all six external faces and records that choice
    as a modeling assumption.

    Parameters
    ----------
    mesh_path : str or pathlib.Path
        Gmsh mesh with the project's named physical boundary groups.
    output_path : str or pathlib.Path
        Destination for a compressed NumPy archive; parent directories are
        created as needed.
    hydrothermal : bool
        Apply the printed conductivity Eq. 22 when true; otherwise use the
        reference conductivity of 3 W/(m K).
    background_gradient_c_km : float
        External positive-down geotherm, in degrees Celsius per kilometer.
    reservoir_temperature_c : float
        Reservoir-surface temperature, in degrees Celsius.

    Returns
    -------
    tuple[int, float, float, float, float, float, float]
        Picard iterations, relative change, minimum and maximum temperatures,
        maximum free-node residual, relative heat-balance error, and net
        boundary heat rate.
    """
    vertices, cells, boundaries = _read_gmsh_tetrahedral_mesh(mesh_path)
    depth_m = np.maximum(0.0, -vertices[:, 2])
    boundary_temperature = geothermal_dirichlet_conditions(
        vertices,
        boundaries,
        background_gradient_c_km=background_gradient_c_km,
        reservoir_temperature_c=reservoir_temperature_c,
    )

    def conductivity(temperature_c: FloatArray, element_depth_m: FloatArray) -> FloatArray:
        if hydrothermal:
            return hydrothermal_conductivity_w_mk(temperature_c, element_depth_m)
        return np.full_like(temperature_c, 3.0)

    solution = solve_steady_temperature_tetrahedral(
        vertices,
        cells,
        depth_m,
        boundary_temperature,
        conductivity=conductivity,
        heat_production_w_m3=0.0,
    )
    cell_temperature = solution.temperature_c[cells].mean(axis=1)
    cell_depth_m = depth_m[cells].mean(axis=1)
    cell_conductivity = conductivity(cell_temperature, cell_depth_m)
    centroids = vertices[cells].mean(axis=1)

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        destination,
        vertices_m=vertices,
        tetrahedra=cells,
        depth_at_vertices_m=depth_m,
        temperature_c=solution.temperature_c,
        cell_centroids_m=centroids,
        cell_temperature_c=cell_temperature,
        cell_conductivity_w_mk=cell_conductivity,
        dirichlet_indices=np.fromiter(boundary_temperature, dtype=np.int64),
        dirichlet_temperature_c=np.fromiter(boundary_temperature.values(), dtype=float),
        iterations=np.asarray(solution.iterations),
        relative_change=np.asarray(solution.relative_change),
        hydrothermal=np.asarray(hydrothermal),
        background_gradient_c_km=np.asarray(background_gradient_c_km),
        reservoir_temperature_c=np.asarray(reservoir_temperature_c),
        max_free_residual_w=np.asarray(solution.max_free_residual_w),
        relative_energy_imbalance=np.asarray(solution.relative_energy_imbalance),
        net_boundary_heat_rate_w=np.asarray(solution.net_boundary_heat_rate_w),
    )
    return (
        solution.iterations,
        solution.relative_change,
        float(np.min(solution.temperature_c)),
        float(np.max(solution.temperature_c)),
        solution.max_free_residual_w,
        solution.relative_energy_imbalance,
        solution.net_boundary_heat_rate_w,
    )


def main() -> None:
    """Solve the baseline or hydrothermal steady model on a Gmsh mesh."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mesh", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--hydrothermal", action="store_true")
    args = parser.parse_args()
    (
        iterations,
        change,
        minimum,
        maximum,
        free_residual,
        energy_imbalance,
        net_boundary_rate,
    ) = solve_written_thermal_model(args.mesh, args.output, hydrothermal=args.hydrothermal)
    case = "hydrothermal" if args.hydrothermal else "baseline"
    print(
        f"{case} steady thermal solve converged in {iterations} Picard iteration(s); "
        f"relative change={change:.3e}, temperature=[{minimum:.6g}, {maximum:.6g}] °C; "
        f"max free-node residual={free_residual:.3e} W, "
        f"relative heat-balance error={energy_imbalance:.3e}, "
        f"net boundary rate={net_boundary_rate:.3e} W; "
        f"wrote {args.output}."
    )


if __name__ == "__main__":
    main()
