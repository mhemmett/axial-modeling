"""Check exact stress-cell alignment across PyLith MPI partitions."""

import numpy as np
import pytest

from axialstress.mesh_alignment import match_tetrahedral_cells


def _two_tetrahedra() -> tuple[np.ndarray, np.ndarray]:
    vertices = np.asarray(
        [(0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1), (0, 0, -1)],
        dtype=float,
    )
    cells = np.asarray([(0, 1, 2, 3), (0, 1, 2, 4)], dtype=np.int64)
    return vertices, cells


def test_reorders_fields_across_vertex_and_cell_permutations() -> None:
    vertices, cells = _two_tetrahedra()
    vertex_order = np.asarray([3, 0, 4, 2, 1])
    inverse_order = np.argsort(vertex_order)
    target_vertices = vertices[vertex_order]
    target_cells = inverse_order[cells[[1, 0]][:, [3, 2, 1, 0]]]

    indices = match_tetrahedral_cells(vertices, cells, target_vertices, target_cells)

    assert indices.tolist() == [1, 0]
    assert np.asarray([10.0, 20.0])[indices].tolist() == [20.0, 10.0]


def test_rejects_changed_tetrahedron_geometry() -> None:
    vertices, cells = _two_tetrahedra()
    changed_cells = cells.copy()
    changed_cells[1] = (0, 1, 3, 4)

    with pytest.raises(ValueError, match="different tetrahedra"):
        match_tetrahedral_cells(vertices, cells, vertices, changed_cells)
