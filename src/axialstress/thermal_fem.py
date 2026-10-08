"""Solve steady heat conduction on linear tetrahedral meshes.

The module uses linear tetrahedron finite elements and Picard iteration for
temperature-dependent conductivity. It accepts boundary values from the caller
because the complete three-dimensional model boundary conditions remain open.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import spsolve

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]
Conductivity = Callable[[FloatArray, FloatArray], FloatArray | float]


@dataclass(frozen=True)
class ThermalSolution:
    """Steady temperatures and nonlinear solver diagnostics."""

    temperature_c: FloatArray
    iterations: int
    relative_change: float


def _mesh_geometry(
    vertices_m: FloatArray,
    tetrahedra: IntArray,
) -> tuple[FloatArray, FloatArray, FloatArray]:
    """Return element volumes, shape gradients, and centroids."""
    element_vertices = vertices_m[tetrahedra]
    affine = np.concatenate(
        (np.ones((*element_vertices.shape[:2], 1)), element_vertices), axis=2
    )
    determinants = np.linalg.det(affine)
    volumes = np.abs(determinants) / 6.0
    if np.any(volumes <= np.finfo(float).tiny):
        raise ValueError("tetrahedra must have nonzero volume")
    inverse = np.linalg.inv(affine)
    gradients = np.transpose(inverse[:, 1:, :], (0, 2, 1))
    centroids = element_vertices.mean(axis=1)
    return volumes, gradients, centroids


def _element_conductivity(
    conductivity: Conductivity,
    temperature_c: FloatArray,
    depth_m: FloatArray,
) -> FloatArray:
    """Evaluate and validate conductivity at element centroids."""
    values = np.asarray(conductivity(temperature_c, depth_m), dtype=float)
    try:
        values = np.broadcast_to(values, temperature_c.shape)
    except ValueError as exc:
        raise ValueError("conductivity must return a scalar or one value per tetrahedron") from exc
    if not np.all(np.isfinite(values)) or np.any(values <= 0.0):
        raise ValueError("conductivity must be finite and positive")
    return values


def solve_steady_temperature_tetrahedral(
    vertices_m: FloatArray,
    tetrahedra: IntArray,
    depth_at_vertices_m: FloatArray,
    dirichlet_temperature_c: Mapping[int, float],
    *,
    conductivity: Conductivity,
    heat_production_w_m3: float = 0.0,
    tolerance: float = 1.0e-9,
    max_iterations: int = 100,
    relaxation: float = 1.0,
) -> ThermalSolution:
    """Solve steady conduction with linear tetrahedron finite elements.

    The weak form is ``-div(k grad(T)) = Q``. Conductivity is evaluated at
    element centroids from their mean temperature and positive-down depth.

    Parameters
    ----------
    vertices_m : array_like
        Mesh coordinates with shape ``(nvertices, 3)``, in meters.
    tetrahedra : array_like
        Zero-based tetrahedron vertex indices with shape ``(nelements, 4)``.
    depth_at_vertices_m : array_like
        Positive-down depth at each vertex, in meters.
    dirichlet_temperature_c : mapping
        Mapping from fixed vertex index to temperature in degrees Celsius.
    conductivity : callable
        Function of element temperature in degrees Celsius and positive-down
        depth in meters, returning conductivity in watts per meter-kelvin.
    heat_production_w_m3 : float
        Uniform heat production in watts per cubic meter.
    tolerance : float
        Relative Picard-iteration tolerance.
    max_iterations : int
        Maximum nonlinear iterations.
    relaxation : float
        Picard update fraction in ``(0, 1]``.

    Returns
    -------
    ThermalSolution
        Nodal temperatures and nonlinear convergence diagnostics.

    Raises
    ------
    ValueError
        If the mesh, boundary conditions, or physical inputs are invalid.
    RuntimeError
        If the nonlinear conductivity iteration does not converge.
    """
    vertices = np.asarray(vertices_m, dtype=float)
    cells = np.asarray(tetrahedra, dtype=np.int64)
    depths = np.asarray(depth_at_vertices_m, dtype=float)
    if vertices.ndim != 2 or vertices.shape[1] != 3 or vertices.shape[0] < 4:
        raise ValueError("vertices must have shape (n, 3) with at least four points")
    if cells.ndim != 2 or cells.shape[1] != 4 or cells.shape[0] == 0:
        raise ValueError("tetrahedra must have shape (m, 4) with at least one element")
    if np.any(cells < 0) or np.any(cells >= len(vertices)):
        raise ValueError("tetrahedra contain invalid vertex indices")
    if depths.shape != (len(vertices),):
        raise ValueError("depth_at_vertices_m must have one value per vertex")
    if not np.all(np.isfinite(vertices)) or not np.all(np.isfinite(depths)):
        raise ValueError("mesh coordinates and depths must be finite")
    if np.any(depths < 0.0):
        raise ValueError("depths must be positive-down and nonnegative")
    if not dirichlet_temperature_c:
        raise ValueError("at least one Dirichlet temperature is required")
    fixed_indices = np.fromiter(dirichlet_temperature_c.keys(), dtype=np.int64)
    fixed_values = np.fromiter(dirichlet_temperature_c.values(), dtype=float)
    if np.any(fixed_indices < 0) or np.any(fixed_indices >= len(vertices)):
        raise ValueError("Dirichlet boundary conditions contain invalid vertex indices")
    if not np.all(np.isfinite(fixed_values)):
        raise ValueError("Dirichlet temperatures must be finite")
    if not np.isfinite(heat_production_w_m3):
        raise ValueError("heat production must be finite")
    if not np.isfinite(tolerance) or tolerance <= 0.0:
        raise ValueError("tolerance must be positive")
    if max_iterations < 1:
        raise ValueError("max_iterations must be positive")
    if not np.isfinite(relaxation) or not 0.0 < relaxation <= 1.0:
        raise ValueError("relaxation must be in (0, 1]")

    volumes, gradients, centroids = _mesh_geometry(vertices, cells)
    element_depth = depths[cells].mean(axis=1)
    fixed_mask = np.zeros(len(vertices), dtype=bool)
    fixed_mask[fixed_indices] = True
    free_indices = np.flatnonzero(~fixed_mask)
    temperature = np.empty(len(vertices), dtype=float)
    temperature[fixed_indices] = fixed_values
    if free_indices.size:
        distances = np.linalg.norm(
            vertices[free_indices, None, :] - vertices[fixed_indices][None, :, :],
            axis=2,
        )
        nearest = np.argmin(distances, axis=1)
        temperature[free_indices] = fixed_values[nearest]

    local_rows = np.repeat(cells, 4, axis=1).reshape(-1)
    local_cols = np.tile(cells, (1, 4)).reshape(-1)
    load = np.zeros(len(vertices), dtype=float)
    np.add.at(load, cells.reshape(-1), np.repeat(heat_production_w_m3 * volumes / 4.0, 4))

    for iteration in range(1, max_iterations + 1):
        cell_temperature = temperature[cells].mean(axis=1)
        conductivity_values = _element_conductivity(
            conductivity, cell_temperature, element_depth
        )
        local_matrices = (
            volumes[:, None, None]
            * conductivity_values[:, None, None]
            * np.einsum("eik,ejk->eij", gradients, gradients)
        )
        matrix = coo_matrix(
            (local_matrices.reshape(-1), (local_rows, local_cols)),
            shape=(len(vertices), len(vertices)),
        ).tocsr()
        next_temperature = temperature.copy()
        next_temperature[fixed_indices] = fixed_values
        if free_indices.size:
            free_matrix = matrix[free_indices]
            rhs = load[free_indices] - free_matrix[:, fixed_indices] @ fixed_values
            next_temperature[free_indices] = spsolve(
                free_matrix[:, free_indices], rhs
            )
            if not np.all(np.isfinite(next_temperature[free_indices])):
                raise RuntimeError("thermal solve produced non-finite temperatures")
        updated_temperature = temperature + relaxation * (next_temperature - temperature)
        updated_temperature[fixed_indices] = fixed_values
        scale = max(1.0, float(np.max(np.abs(updated_temperature))))
        relative_change = float(
            np.max(np.abs(updated_temperature - temperature)) / scale
        )
        temperature = updated_temperature
        if relative_change <= tolerance:
            return ThermalSolution(temperature, iteration, relative_change)

    raise RuntimeError(
        f"thermal conductivity iteration did not converge in {max_iterations} steps"
    )
