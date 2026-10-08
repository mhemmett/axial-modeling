"""Interpolate PyLith displacement fields on triangular surfaces."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]


def interpolate_triangular_surface(
    vertices_m: FloatArray,
    triangles: IntArray,
    values: FloatArray,
    point_xy_m: tuple[float, float],
    *,
    tolerance: float = 1.0e-10,
) -> FloatArray:
    """Evaluate a piecewise-linear field at a point on a triangulated surface.

    Parameters
    ----------
    vertices_m : numpy.ndarray, shape (n, 3)
        Surface vertex coordinates in meters.
    triangles : numpy.ndarray, shape (m, 3)
        Zero-based indices of triangular cells.
    values : numpy.ndarray, shape (n, k)
        One or more vertex fields to interpolate.
    point_xy_m : tuple of float
        Target east and north coordinates in meters.
    tolerance : float, optional
        Barycentric-coordinate tolerance used to include triangle edges.

    Returns
    -------
    numpy.ndarray
        Interpolated field values at the requested horizontal coordinate.

    Raises
    ------
    ValueError
        If array shapes or connectivity are invalid, or the point is outside
        the supplied surface triangulation.
    """
    vertices = np.asarray(vertices_m, dtype=float)
    cells = np.asarray(triangles, dtype=np.int64)
    field = np.asarray(values, dtype=float)
    point = np.asarray(point_xy_m, dtype=float)
    if vertices.ndim != 2 or vertices.shape[1] != 3:
        raise ValueError("vertices must have shape (n, 3)")
    if cells.ndim != 2 or cells.shape[1] != 3 or not len(cells):
        raise ValueError("triangles must have nonempty shape (m, 3)")
    if field.ndim == 1:
        field = field[:, None]
    if field.ndim != 2 or field.shape[0] != len(vertices):
        raise ValueError("values must have one row per vertex")
    if cells.min() < 0 or cells.max() >= len(vertices):
        raise ValueError("triangle connectivity references an invalid vertex")
    if point.shape != (2,) or not np.all(np.isfinite(point)):
        raise ValueError("point_xy_m must contain two finite coordinates")
    if not np.all(np.isfinite(vertices)) or not np.all(np.isfinite(field)):
        raise ValueError("surface coordinates and values must be finite")
    if tolerance <= 0.0:
        raise ValueError("tolerance must be positive")

    triangles_xy = vertices[cells, :2]
    low = np.min(triangles_xy, axis=1) - tolerance
    high = np.max(triangles_xy, axis=1) + tolerance
    candidates = np.flatnonzero(np.all((point >= low) & (point <= high), axis=1))
    for triangle_index in candidates:
        xy = triangles_xy[triangle_index]
        edge_matrix = np.column_stack((xy[1] - xy[0], xy[2] - xy[0]))
        determinant = float(np.linalg.det(edge_matrix))
        if abs(determinant) <= np.finfo(float).eps:
            continue
        uv = np.linalg.solve(edge_matrix, point - xy[0])
        weights = np.array([1.0 - uv.sum(), uv[0], uv[1]])
        if np.all(weights >= -tolerance) and np.all(weights <= 1.0 + tolerance):
            return weights @ field[cells[triangle_index]]
    raise ValueError(f"point {tuple(point)} lies outside the supplied surface triangulation")
