"""Interpolate nodal fields inside unstructured linear tetrahedral meshes."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]


def interpolate_tetrahedral_field(
    vertices_m: FloatArray,
    tetrahedra: IntArray,
    values_at_vertices: FloatArray,
    points_m: FloatArray,
    *,
    weight_tolerance: float = 1.0e-10,
) -> FloatArray:
    """Interpolate a nodal field at points inside a tetrahedral mesh.

    Parameters
    ----------
    vertices_m : array_like, shape (nvertices, 3)
        Source mesh coordinates in meters.
    tetrahedra : array_like, shape (nelements, 4)
        Zero-based source tetrahedron vertex indices.
    values_at_vertices : array_like, shape (nvertices, ...)
        Scalar or vector nodal field values.
    points_m : array_like, shape (npoints, 3)
        Target coordinates in meters.
    weight_tolerance : float, optional
        Barycentric-coordinate tolerance for including tetrahedron boundaries.

    Returns
    -------
    numpy.ndarray
        Interpolated values with shape ``(npoints, ...)``.

    Raises
    ------
    ValueError
        If the mesh or fields are invalid, or a target lies outside the mesh.
    """
    vertices = np.asarray(vertices_m, dtype=float)
    cells = np.asarray(tetrahedra, dtype=np.int64)
    values = np.asarray(values_at_vertices, dtype=float)
    points = np.asarray(points_m, dtype=float)
    if vertices.ndim != 2 or vertices.shape[1] != 3 or len(vertices) < 4:
        raise ValueError("vertices_m must have shape (n, 3) with at least four points")
    if cells.ndim != 2 or cells.shape[1] != 4 or not len(cells):
        raise ValueError("tetrahedra must have nonempty shape (m, 4)")
    if np.any(cells < 0) or np.any(cells >= len(vertices)):
        raise ValueError("tetrahedra contain invalid vertex indices")
    if values.ndim < 1 or values.shape[0] != len(vertices):
        raise ValueError("values_at_vertices must have one leading value per vertex")
    if points.ndim != 2 or points.shape[1] != 3:
        raise ValueError("points_m must have shape (n, 3)")
    if not np.all(np.isfinite(vertices)) or not np.all(np.isfinite(values)):
        raise ValueError("source coordinates and values must be finite")
    if not np.all(np.isfinite(points)):
        raise ValueError("target coordinates must be finite")
    if not np.isfinite(weight_tolerance) or weight_tolerance <= 0.0:
        raise ValueError("weight_tolerance must be finite and positive")

    element_vertices = vertices[cells]
    edge_matrices = np.swapaxes(
        element_vertices[:, 1:, :] - element_vertices[:, :1, :], 1, 2
    )
    determinants = np.linalg.det(edge_matrices)
    if np.any(determinants == 0.0):
        raise ValueError("source mesh contains a degenerate tetrahedron")
    inverse_edges = np.linalg.inv(edge_matrices)
    lower = np.min(element_vertices, axis=1)
    upper = np.max(element_vertices, axis=1)
    sorted_indices = np.argsort(lower[:, 0])
    sorted_lower_x = lower[sorted_indices, 0]
    coordinate_scale_m = max(float(np.ptp(vertices, axis=0).max()), 1.0)
    coordinate_tolerance_m = 64.0 * np.finfo(float).eps * coordinate_scale_m

    output = np.empty((len(points), *values.shape[1:]), dtype=float)
    for point_index, point in enumerate(points):
        prefix_count = int(
            np.searchsorted(
                sorted_lower_x, point[0] + coordinate_tolerance_m, side="right"
            )
        )
        candidates = sorted_indices[:prefix_count]
        if candidates.size:
            in_bounds = np.all(
                (point >= lower[candidates] - coordinate_tolerance_m)
                & (point <= upper[candidates] + coordinate_tolerance_m),
                axis=1,
            )
            candidates = candidates[in_bounds]

        for cell_index in candidates:
            origin = element_vertices[cell_index, 0]
            local_coordinates = inverse_edges[cell_index] @ (point - origin)
            weights = np.concatenate(([1.0 - local_coordinates.sum()], local_coordinates))
            if np.all(weights >= -weight_tolerance) and np.all(
                weights <= 1.0 + weight_tolerance
            ):
                output[point_index] = np.tensordot(
                    weights, values[cells[cell_index]], axes=(0, 0)
                )
                break
        else:
            raise ValueError(
                f"target point {point_index} at {tuple(point)} lies outside the source mesh"
            )

    if values.ndim == 1:
        return output.reshape(len(points))
    return output
