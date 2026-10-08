"""Cell adjacency and boundary topology for tetrahedral meshes."""

from __future__ import annotations

from collections import deque
from itertools import combinations

import numpy as np
from numpy.typing import NDArray

IntArray = NDArray[np.int64]
BoolArray = NDArray[np.bool_]
BOUNDARY_NAMES = ("top", "bottom", "x_neg", "x_pos", "y_neg", "y_pos", "cavity")


def box_cavity_boundary_cells(
    vertices_m: NDArray[np.float64],
    tetrahedra: IntArray,
    *,
    tolerance_m: float = 1.0e-7,
) -> dict[str, IntArray]:
    """Find cells adjacent to each box face and the interior cavity boundary.

    Parameters
    ----------
    vertices_m : array_like
        Tetrahedral mesh coordinates in meters, with shape (nvertices, 3).
    tetrahedra : array_like
        Zero-based tetrahedron indices with shape (ncells, 4).
    tolerance_m : float, optional
        Coordinate tolerance for identifying the six planar box boundaries.

    Returns
    -------
    dict[str, numpy.ndarray]
        Cell indices adjacent to top, bottom, four side faces, and all other
        boundary faces (the cavity).

    Raises
    ------
    ValueError
        If the mesh is malformed or contains a non-manifold triangular face.
    """
    vertices = np.asarray(vertices_m, dtype=float)
    cells = np.asarray(tetrahedra, dtype=np.int64)
    if vertices.ndim != 2 or vertices.shape[1] != 3 or len(vertices) < 4:
        raise ValueError("vertices_m must have shape (n, 3) with at least four points")
    if not np.all(np.isfinite(vertices)):
        raise ValueError("vertices_m must contain only finite coordinates")
    if cells.ndim != 2 or cells.shape[1] != 4 or len(cells) == 0:
        raise ValueError("tetrahedra must have shape (m, 4) with at least one cell")
    if np.any(cells < 0) or np.any(cells >= len(vertices)):
        raise ValueError("tetrahedra contain invalid vertex indices")
    if not np.isfinite(tolerance_m) or tolerance_m <= 0.0:
        raise ValueError("tolerance_m must be finite and positive")

    bounds_min = np.min(vertices, axis=0)
    bounds_max = np.max(vertices, axis=0)
    owners: dict[tuple[int, int, int], list[int]] = {}
    for cell_index, cell in enumerate(cells):
        for face_vertices in combinations(map(int, cell), 3):
            face = tuple(sorted(face_vertices))
            owners.setdefault(face, []).append(cell_index)

    boundary_cells: dict[str, set[int]] = {name: set() for name in BOUNDARY_NAMES}
    for face, adjacent_cells in owners.items():
        if len(adjacent_cells) > 2:
            raise ValueError(f"non-manifold face {face} belongs to multiple cells")
        if len(adjacent_cells) != 1:
            continue
        coordinates = vertices[np.asarray(face)]
        if np.all(np.abs(coordinates[:, 2] - bounds_max[2]) <= tolerance_m):
            name = "top"
        elif np.all(np.abs(coordinates[:, 2] - bounds_min[2]) <= tolerance_m):
            name = "bottom"
        elif np.all(np.abs(coordinates[:, 0] - bounds_min[0]) <= tolerance_m):
            name = "x_neg"
        elif np.all(np.abs(coordinates[:, 0] - bounds_max[0]) <= tolerance_m):
            name = "x_pos"
        elif np.all(np.abs(coordinates[:, 1] - bounds_min[1]) <= tolerance_m):
            name = "y_neg"
        elif np.all(np.abs(coordinates[:, 1] - bounds_max[1]) <= tolerance_m):
            name = "y_pos"
        else:
            name = "cavity"
        boundary_cells[name].add(adjacent_cells[0])
    return {
        name: np.asarray(sorted(indices), dtype=np.int64)
        for name, indices in boundary_cells.items()
    }


def find_connected_failure_path(
    tetrahedra: IntArray,
    failed_cells: BoolArray,
    source_cells: IntArray,
    target_cells: IntArray,
) -> IntArray:
    """Find a face-connected failure path between source and target cells.

    Parameters
    ----------
    tetrahedra : array_like
        Zero-based tetrahedron indices with shape (ncells, 4).
    failed_cells : array_like
        Boolean failure indicator for every cell.
    source_cells, target_cells : array_like
        Cell indices adjacent to the two boundaries of interest.

    Returns
    -------
    numpy.ndarray
        Cell indices along the shortest face-connected failed path, or an
        empty array when no path connects the boundary sets.
    """
    cells = np.asarray(tetrahedra, dtype=np.int64)
    failed = np.asarray(failed_cells, dtype=bool)
    sources = np.asarray(source_cells, dtype=np.int64)
    targets = np.asarray(target_cells, dtype=np.int64)
    if cells.ndim != 2 or cells.shape[1] != 4 or len(cells) == 0:
        raise ValueError("tetrahedra must have shape (m, 4) with at least one cell")
    if failed.shape != (len(cells),):
        raise ValueError("failed_cells must have one boolean value per tetrahedron")
    if sources.ndim != 1 or targets.ndim != 1:
        raise ValueError("source_cells and target_cells must be one-dimensional")
    for name, indices in (("source_cells", sources), ("target_cells", targets)):
        if np.any(indices < 0) or np.any(indices >= len(cells)):
            raise ValueError(f"{name} contain invalid cell indices")

    face_owners: dict[tuple[int, int, int], list[int]] = {}
    for cell_index, cell in enumerate(cells):
        for face_vertices in combinations(map(int, cell), 3):
            face = tuple(sorted(face_vertices))
            face_owners.setdefault(face, []).append(cell_index)

    neighbors = [set() for _ in range(len(cells))]
    for face, adjacent_cells in face_owners.items():
        if len(adjacent_cells) > 2:
            raise ValueError(f"non-manifold face {face} belongs to multiple cells")
        if len(adjacent_cells) == 2:
            left, right = adjacent_cells
            neighbors[left].add(right)
            neighbors[right].add(left)

    target_set = set(map(int, targets))
    queue = deque()
    parent: dict[int, int | None] = {}
    for source in sorted(set(map(int, sources))):
        if failed[source]:
            queue.append(source)
            parent[source] = None

    while queue:
        current = queue.popleft()
        if current in target_set:
            path = [current]
            while parent[path[-1]] is not None:
                path.append(parent[path[-1]])
            return np.asarray(path[::-1], dtype=np.int64)
        for neighbor in sorted(neighbors[current]):
            if failed[neighbor] and neighbor not in parent:
                parent[neighbor] = current
                queue.append(neighbor)
    return np.empty(0, dtype=np.int64)
