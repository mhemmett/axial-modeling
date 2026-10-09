"""Synthetic checks for tetrahedral failure connectivity."""

import numpy as np

from axialstress.topology import TetrahedralFaceGraph, find_connected_failure_path


def test_finds_face_connected_failed_cell_path() -> None:
    cells = np.array([[0, 1, 2, 3], [1, 2, 3, 4], [2, 3, 4, 5]])

    path = find_connected_failure_path(
        cells,
        np.array([True, True, True]),
        np.array([0]),
        np.array([2]),
    )

    np.testing.assert_array_equal(path, [0, 1, 2])


def test_failure_gap_breaks_boundary_path() -> None:
    cells = np.array([[0, 1, 2, 3], [1, 2, 3, 4], [2, 3, 4, 5]])

    path = find_connected_failure_path(
        cells,
        np.array([True, False, True]),
        np.array([0]),
        np.array([2]),
    )

    assert path.size == 0


def test_cached_face_graph_matches_path_search() -> None:
    cells = np.array([[0, 1, 2, 3], [1, 2, 3, 4], [2, 3, 4, 5]])
    failed = np.array([True, True, True])
    source = np.array([0])
    target = np.array([2])
    graph = TetrahedralFaceGraph(cells)

    np.testing.assert_array_equal(
        graph.find_connected_failure_path(failed, source, target),
        find_connected_failure_path(cells, failed, source, target),
    )
