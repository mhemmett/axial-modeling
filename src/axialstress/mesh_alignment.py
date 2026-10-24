"""Match PyLith tetrahedral cells across MPI partitions by exact geometry."""

from __future__ import annotations

import numpy as np


def match_tetrahedral_cells(
    source_vertices: np.ndarray,
    source_cells: np.ndarray,
    target_vertices: np.ndarray,
    target_cells: np.ndarray,
) -> np.ndarray:
    """Return source cell indices in target-cell order for one identical mesh.

    Parameters
    ----------
    source_vertices, target_vertices : ndarray
        Vertex coordinates in meters, shaped ``(n, 3)``.
    source_cells, target_cells : ndarray
        Tetrahedral connectivity, shaped ``(m, 4)``.

    Returns
    -------
    ndarray
        Indices into source cell fields, one for each target cell.

    Notes
    -----
    PyLith may reorder global vertices and cells when the MPI rank count
    changes. Exact coordinates and unordered tetrahedral vertex sets must
    match; this function does not interpolate between different meshes.
    """
    source_vertices = np.asarray(source_vertices)
    target_vertices = np.asarray(target_vertices)
    source_cells = np.asarray(source_cells)
    target_cells = np.asarray(target_cells)
    if (
        source_vertices.ndim != 2
        or source_vertices.shape[1] != 3
        or source_vertices.shape != target_vertices.shape
        or source_cells.ndim != 2
        or source_cells.shape[1] != 4
        or source_cells.shape != target_cells.shape
        or not np.isfinite(source_vertices).all()
        or not np.isfinite(target_vertices).all()
    ):
        raise ValueError("PyLith tetrahedral mesh shapes or coordinates differ")
    if np.array_equal(source_vertices, target_vertices) and np.array_equal(
        source_cells, target_cells
    ):
        return np.arange(len(source_cells), dtype=np.int64)

    coordinate_to_source = {
        tuple(coordinate): index for index, coordinate in enumerate(source_vertices)
    }
    if len(coordinate_to_source) != len(source_vertices):
        raise ValueError("source mesh has duplicate vertex coordinates")
    try:
        target_to_source = np.asarray(
            [coordinate_to_source[tuple(coordinate)] for coordinate in target_vertices],
            dtype=np.int64,
        )
    except KeyError as error:
        raise ValueError("PyLith meshes have different vertex coordinates") from error
    if len(np.unique(target_to_source)) != len(source_vertices):
        raise ValueError("target mesh has duplicate vertex coordinates")
    if (
        np.any(source_cells < 0)
        or np.any(target_cells < 0)
        or np.any(source_cells >= len(source_vertices))
        or np.any(target_cells >= len(target_vertices))
    ):
        raise ValueError("PyLith cell connectivity references an invalid vertex")

    source_keys = np.sort(source_cells, axis=1)
    key_to_source = {tuple(key): index for index, key in enumerate(source_keys)}
    if len(key_to_source) != len(source_cells):
        raise ValueError("source mesh has duplicate tetrahedra")
    target_keys = np.sort(target_to_source[target_cells], axis=1)
    try:
        indices = np.asarray(
            [key_to_source[tuple(key)] for key in target_keys], dtype=np.int64
        )
    except KeyError as error:
        raise ValueError("PyLith meshes have different tetrahedra") from error
    if len(np.unique(indices)) != len(source_cells):
        raise ValueError("target mesh has duplicate tetrahedra")
    return indices
