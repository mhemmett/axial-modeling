"""Calculate ellipsoid cavity-volume change from saved PyLith displacement."""

from __future__ import annotations

from collections import Counter
from itertools import combinations
from pathlib import Path

import h5py
import numpy as np
from numpy.typing import NDArray
from scipy.spatial import cKDTree

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]


def read_gmsh_cavity_surface(mesh_path: str | Path) -> tuple[FloatArray, IntArray]:
    """Read the closed first-order cavity triangle mesh in meters.

    Parameters
    ----------
    mesh_path : str or pathlib.Path
        Gmsh 4.x mesh with a two-dimensional physical group named ``cavity``.

    Returns
    -------
    tuple of numpy.ndarray
        Cavity vertices in meters and zero-based triangular face indices.

    Notes
    -----
    Cabaniss et al. (2020), supplement Eq. 24 and following text, integrate
    the reservoir boundary to obtain volume change. The original physical
    cavity mesh defines that boundary. PyLith's boundary output can contain
    additional visualization faces, so its topology is not substituted here.
    """
    try:
        import gmsh
    except ImportError as exc:
        raise RuntimeError("Gmsh is required to read the cavity surface") from exc

    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.open(str(mesh_path))
        matching = [
            int(tag)
            for dim, tag in gmsh.model.getPhysicalGroups()
            if dim == 2 and gmsh.model.getPhysicalName(dim, tag) == "cavity"
        ]
        if len(matching) != 1:
            raise ValueError("mesh must have one cavity surface physical group")
        face_tags = []
        for entity in gmsh.model.getEntitiesForPhysicalGroup(2, matching[0]):
            element_types, _, node_tags = gmsh.model.mesh.getElements(2, int(entity))
            for element_type, tags in zip(element_types, node_tags, strict=True):
                if int(element_type) != 2:
                    raise ValueError("cavity surface must use first-order triangles")
                face_tags.extend(np.asarray(tags, dtype=np.int64).reshape(-1, 3))
        if not face_tags:
            raise ValueError("cavity surface has no triangles")
        node_tags, coordinates, _ = gmsh.model.mesh.getNodes()
        coordinate_by_tag = dict(
            zip(
                map(int, node_tags),
                np.asarray(coordinates, dtype=float).reshape(-1, 3),
                strict=True,
            )
        )
        unique_tags, faces = np.unique(np.asarray(face_tags), return_inverse=True)
        vertices = np.asarray([coordinate_by_tag[int(tag)] for tag in unique_tags])
        return vertices, faces.reshape(-1, 3)
    finally:
        gmsh.finalize()


def orient_closed_cavity(vertices_m: FloatArray, faces: IntArray) -> IntArray:
    """Orient a convex, closed cavity surface away from its interior."""
    vertices = np.asarray(vertices_m, dtype=float)
    triangles = np.asarray(faces, dtype=np.int64)
    if vertices.ndim != 2 or vertices.shape[1] != 3:
        raise ValueError("cavity vertices must have shape (n, 3)")
    if triangles.ndim != 2 or triangles.shape[1] != 3:
        raise ValueError("cavity faces must have shape (m, 3)")
    if len(vertices) < 4 or len(triangles) < 4 or not np.all(np.isfinite(vertices)):
        raise ValueError("cavity geometry is empty or non-finite")
    if np.any(triangles < 0) or np.any(triangles >= len(vertices)):
        raise ValueError("cavity faces reference missing vertices")
    if np.any(np.diff(np.sort(triangles, axis=1), axis=1) == 0):
        raise ValueError("cavity triangle contains repeated vertices")
    edges = Counter(
        tuple(sorted((int(a), int(b))))
        for triangle in triangles
        for a, b in combinations(triangle, 2)
    )
    if any(count != 2 for count in edges.values()):
        raise ValueError("cavity surface has an open or non-manifold edge")
    if len({tuple(sorted(map(int, face))) for face in triangles}) != len(triangles):
        raise ValueError("cavity surface has duplicate triangles")
    if len(vertices) - len(edges) + len(triangles) != 2:
        raise ValueError("cavity surface is not one closed ellipsoid")

    oriented = triangles.copy()
    points = vertices[oriented]
    normals = np.cross(points[:, 1] - points[:, 0], points[:, 2] - points[:, 0])
    interior = np.mean(vertices, axis=0)
    radial = np.mean(points, axis=1) - interior
    direction = np.einsum("ij,ij->i", normals, radial)
    if np.any(~np.isfinite(direction)) or np.any(direction == 0):
        raise ValueError("cavity has a degenerate or non-convex triangle")
    swap = direction < 0
    oriented[swap, 1], oriented[swap, 2] = (
        oriented[swap, 2].copy(),
        oriented[swap, 1].copy(),
    )
    return oriented


def enclosed_volume_m3(vertices_m: FloatArray, oriented_faces: IntArray) -> float:
    """Return the signed enclosed volume of oriented cavity triangles in m³."""
    vertices = np.asarray(vertices_m, dtype=float)
    triangles = np.asarray(oriented_faces, dtype=np.int64)
    reference = vertices.mean(axis=0)
    corners = vertices[triangles] - reference
    volumes = np.einsum(
        "ij,ij->i",
        corners[:, 0],
        np.cross(corners[:, 1], corners[:, 2]),
    ) / 6.0
    volume = float(np.sum(volumes))
    if not np.isfinite(volume) or volume <= 0:
        raise ValueError("cavity enclosed volume must be finite and positive")
    return volume


def cavity_volume_history(
    vertices_m: FloatArray,
    faces: IntArray,
    displacement_m: FloatArray,
) -> dict[str, FloatArray | float]:
    """Return exact and first-order cavity-volume changes in cubic meters.

    Parameters
    ----------
    vertices_m : numpy.ndarray
        Reference cavity vertex coordinates, shape ``(n, 3)``, in meters.
    faces : numpy.ndarray
        Gmsh cavity surface triangles, shape ``(m, 3)``.
    displacement_m : numpy.ndarray
        PyLith cavity displacement, shape ``(ntime, n, 3)``, in meters.

    Returns
    -------
    dict
        Reference volume, deformed volume, geometric volume change, and
        first-order surface integral, all in cubic meters.

    Notes
    -----
    Geometric change is the enclosed volume of the displaced boundary minus
    reference volume. The first-order result integrates nodal displacement
    against reference-face area vectors. Both come from PyLith fields; neither
    uses a published volume curve as input.
    """
    vertices = np.asarray(vertices_m, dtype=float)
    displacement = np.asarray(displacement_m, dtype=float)
    oriented = orient_closed_cavity(vertices, faces)
    if displacement.ndim != 3 or displacement.shape[1:] != vertices.shape:
        raise ValueError("displacement must have shape (ntime, nvertices, 3)")
    if len(displacement) == 0 or not np.all(np.isfinite(displacement)):
        raise ValueError("displacement must be nonempty and finite")
    reference_volume = enclosed_volume_m3(vertices, oriented)
    corners = vertices[oriented]
    area_vectors = 0.5 * np.cross(
        corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0]
    )
    first_order = np.einsum(
        "tij,ij->t", displacement[:, oriented, :].mean(axis=2), area_vectors
    )
    deformed_volume = np.asarray(
        [enclosed_volume_m3(vertices + state, oriented) for state in displacement]
    )
    return {
        "reference_volume_m3": reference_volume,
        "deformed_volume_m3": deformed_volume,
        "geometric_change_m3": deformed_volume - reference_volume,
        "first_order_change_m3": first_order,
    }


def read_pylith_cavity_volume_history(
    mesh_path: str | Path,
    boundary_hdf5: str | Path,
    *,
    match_tolerance_m: float = 1.0e-6,
) -> tuple[FloatArray, dict[str, FloatArray | float]]:
    """Match Gmsh cavity faces to PyLith displacement and return volume history."""
    vertices, faces = read_gmsh_cavity_surface(mesh_path)
    with h5py.File(boundary_hdf5, "r") as output:
        required = ("time", "geometry/vertices", "vertex_fields/displacement")
        if any(name not in output for name in required):
            raise ValueError("PyLith cavity output is missing time, vertices, or displacement")
        times_s = np.asarray(output["time"], dtype=float).reshape(-1)
        output_vertices = np.asarray(output["geometry/vertices"], dtype=float)
        output_displacement = np.asarray(output["vertex_fields/displacement"], dtype=float)
    if not np.all(np.isfinite(output_vertices)) or not np.all(np.isfinite(times_s)):
        raise ValueError("PyLith cavity times or vertices are non-finite")
    if len(times_s) != len(output_displacement) or np.any(np.diff(times_s) <= 0):
        raise ValueError("PyLith cavity time and displacement arrays disagree")
    distance, index = cKDTree(output_vertices).query(vertices)
    if np.any(distance > match_tolerance_m) or len(np.unique(index)) != len(vertices):
        raise ValueError("Gmsh cavity vertices do not map uniquely to PyLith output")
    history = cavity_volume_history(vertices, faces, output_displacement[:, index, :])
    return times_s, history
