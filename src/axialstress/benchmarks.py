"""Analytical elastic references used to verify numerical mechanics."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]


def interpolate_surface_triangles(
    vertices_m: FloatArray,
    triangles: NDArray[np.int64],
    vertex_values: FloatArray,
    query_points_m: FloatArray,
    *,
    barycentric_tolerance: float = 1.0e-10,
) -> FloatArray:
    """Interpolate a vertex field to fixed points on a horizontal triangle mesh.

    Parameters
    ----------
    vertices_m : array_like
        Surface coordinates with shape (nvertices, 3), in meters.
    triangles : array_like
        Zero-based triangle indices with shape (ntriangles, 3).
    vertex_values : array_like
        Scalar or vector values at mesh vertices, with first dimension
        nvertices.
    query_points_m : array_like
        Horizontal coordinates with shape (nqueries, 2), in meters.
    barycentric_tolerance : float, optional
        Dimensionless tolerance for points on triangle edges.

    Returns
    -------
    numpy.ndarray
        Linearly interpolated values, with first dimension nqueries.

    Raises
    ------
    ValueError
        If the mesh or field is malformed, a triangle is degenerate, or a
        query point lies outside the surface mesh.
    """
    vertices = np.asarray(vertices_m, dtype=float)
    cells = np.asarray(triangles, dtype=np.int64)
    values = np.asarray(vertex_values, dtype=float)
    queries = np.asarray(query_points_m, dtype=float)
    if vertices.ndim != 2 or vertices.shape[1] != 3 or len(vertices) < 3:
        raise ValueError("vertices_m must have shape (n, 3) with at least three points")
    if not np.all(np.isfinite(vertices)) or not np.allclose(
        vertices[:, 2], vertices[0, 2], rtol=0.0, atol=1.0e-8
    ):
        raise ValueError("surface vertices must be finite and horizontal")
    if cells.ndim != 2 or cells.shape[1] != 3 or len(cells) == 0:
        raise ValueError("triangles must have shape (m, 3) with at least one triangle")
    if np.any(cells < 0) or np.any(cells >= len(vertices)):
        raise ValueError("triangles contain invalid vertex indices")
    if values.ndim < 1 or values.shape[0] != len(vertices) or not np.all(np.isfinite(values)):
        raise ValueError("vertex_values must be finite and have one row per vertex")
    if queries.ndim != 2 or queries.shape[1] != 2 or not np.all(np.isfinite(queries)):
        raise ValueError("query_points_m must have finite shape (n, 2)")
    if not np.isfinite(barycentric_tolerance) or barycentric_tolerance < 0.0:
        raise ValueError("barycentric_tolerance must be finite and nonnegative")

    triangles_xy = vertices[cells, :2]
    edge_1 = triangles_xy[:, 1] - triangles_xy[:, 0]
    edge_2 = triangles_xy[:, 2] - triangles_xy[:, 0]
    denominators = edge_1[:, 0] * edge_2[:, 1] - edge_1[:, 1] * edge_2[:, 0]
    if np.any(np.abs(denominators) <= np.finfo(float).tiny):
        raise ValueError("surface mesh contains a degenerate triangle")

    result = np.full((len(queries), *values.shape[1:]), np.nan, dtype=float)
    unassigned = np.ones(len(queries), dtype=bool)
    for triangle_index, triangle in enumerate(triangles_xy):
        point_delta = queries - triangle[0]
        edge1 = triangle[1] - triangle[0]
        edge2 = triangle[2] - triangle[0]
        denominator = denominators[triangle_index]
        weight_1 = (
            point_delta[:, 0] * edge2[1] - point_delta[:, 1] * edge2[0]
        ) / denominator
        weight_2 = (
            edge1[0] * point_delta[:, 1] - edge1[1] * point_delta[:, 0]
        ) / denominator
        weight_0 = 1.0 - weight_1 - weight_2
        tolerance = barycentric_tolerance
        inside = (
            unassigned
            & (weight_0 >= -tolerance)
            & (weight_1 >= -tolerance)
            & (weight_2 >= -tolerance)
            & (weight_0 <= 1.0 + tolerance)
            & (weight_1 <= 1.0 + tolerance)
            & (weight_2 <= 1.0 + tolerance)
        )
        if not np.any(inside):
            continue
        result[inside] = (
            weight_0[inside].reshape((-1,) + (1,) * (values.ndim - 1))
            * values[cells[triangle_index, 0]]
            + weight_1[inside].reshape((-1,) + (1,) * (values.ndim - 1))
            * values[cells[triangle_index, 1]]
            + weight_2[inside].reshape((-1,) + (1,) * (values.ndim - 1))
            * values[cells[triangle_index, 2]]
        )
        unassigned[inside] = False
    if np.any(unassigned):
        raise ValueError(f"{np.count_nonzero(unassigned)} query point(s) lie outside the mesh")
    return result


def mogi_surface_displacement_m(
    x_m: FloatArray | float,
    y_m: FloatArray | float,
    *,
    source_depth_m: float,
    source_radius_m: float,
    pressure_change_pa: FloatArray | float,
    bulk_modulus_pa: float,
    shear_modulus_pa: float,
) -> FloatArray:
    """Calculate the elastic half-space displacement above a spherical source.

    Parameters
    ----------
    x_m, y_m : array_like or float
        Surface coordinates relative to the source axis, in meters.
    source_depth_m : float
        Positive-down depth to the source center, in meters.
    source_radius_m : float
        Spherical source radius, in meters.
    pressure_change_pa : array_like or float
        Pressure change in pascals; positive values represent inflation.
    bulk_modulus_pa : float
        Host-rock bulk modulus in pascals.
    shear_modulus_pa : float
        Host-rock shear modulus in pascals.

    Returns
    -------
    numpy.ndarray
        Displacement components ``(u_x, u_y, u_z)`` in meters, with the last
        axis containing the three Cartesian components.

    Notes
    -----
    This is the homogeneous elastic spherical-source reference in Eqs. 1–2 of
    ``docs/model_specification.md``. It is an analytical benchmark and does
    not account for a finite mesh, ellipsoidal reservoir, layering, or
    viscoelastic response.
    """
    x, y, pressure = np.broadcast_arrays(
        np.asarray(x_m, dtype=float),
        np.asarray(y_m, dtype=float),
        np.asarray(pressure_change_pa, dtype=float),
    )
    if not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)):
        raise ValueError("surface coordinates must be finite")
    if not np.all(np.isfinite(pressure)):
        raise ValueError("pressure change must be finite")
    source_parameters = (source_depth_m, source_radius_m)
    if not np.all(np.isfinite(source_parameters)) or np.any(
        np.asarray(source_parameters) <= 0.0
    ):
        raise ValueError("source depth and radius must be finite and positive")
    elastic_parameters = (bulk_modulus_pa, shear_modulus_pa)
    if not np.all(np.isfinite(elastic_parameters)) or np.any(
        np.asarray(elastic_parameters) <= 0.0
    ):
        raise ValueError("bulk and shear moduli must be finite and positive")

    distance = np.hypot(np.hypot(x, y), source_depth_m)
    compliance = (3.0 * bulk_modulus_pa + 4.0 * shear_modulus_pa) / (
        2.0 * shear_modulus_pa * (3.0 * bulk_modulus_pa + shear_modulus_pa)
    )
    with np.errstate(over="raise", invalid="raise", divide="raise"):
        amplitude = pressure * source_radius_m**3 * compliance / distance**3
        displacement = np.stack(
        (amplitude * x, amplitude * y, amplitude * source_depth_m), axis=-1
        )
    if not np.all(np.isfinite(displacement)):
        raise ValueError("parameters produce non-finite displacement")
    return displacement
