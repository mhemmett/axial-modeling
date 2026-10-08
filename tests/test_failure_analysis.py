"""Synthetic checks for failure diagnostics across saved stress records."""

import numpy as np
import pytest

from axialstress.failure_analysis import analyze_stress_history


def _single_tetrahedron_with_top_and_cavity_faces() -> tuple[np.ndarray, np.ndarray]:
    vertices = np.array(
        [[0.0, 0.0, 0.0], [0.0, 0.0, 1.0], [1.0, 0.0, 1.0], [0.0, 1.0, 1.0]]
    )
    cells = np.array([[0, 1, 2, 3]])
    return vertices, cells


def test_stress_history_records_first_connected_path_time() -> None:
    vertices, cells = _single_tetrahedron_with_top_and_cavity_faces()
    stress_history = np.zeros((3, 1, 6))
    stress_history[1:, 0, :3] = [-12.0e6, 0.0, 12.0e6]

    result = analyze_stress_history(
        vertices,
        cells,
        stress_history,
        np.array([[[0.0]], [[1.0]], [[2.0]]]),
        cohesion_pa=1.0e6,
        friction_angle_deg=25.0,
        pore_pressure_pa=0.0,
    )

    assert result["record_count"] == 3
    assert result["first_cavity_to_surface_shear_path_time_s"] == 1.0
    assert [record["cavity_to_surface_shear_path_found"] for record in result["records"]] == [
        False,
        True,
        True,
    ]


@pytest.mark.parametrize(
    ("stress_history", "time_s"),
    [
        (np.zeros((2, 1, 6)), np.array([0.0])),
        (np.zeros((2, 1, 6)), np.array([1.0, 0.0])),
        (np.zeros((2, 1, 6)), np.array([0.0, np.nan])),
    ],
)
def test_stress_history_rejects_malformed_times(
    stress_history: np.ndarray, time_s: np.ndarray
) -> None:
    vertices, cells = _single_tetrahedron_with_top_and_cavity_faces()

    with pytest.raises(ValueError):
        analyze_stress_history(
            vertices,
            cells,
            stress_history,
            time_s,
            cohesion_pa=1.0e6,
            friction_angle_deg=25.0,
            pore_pressure_pa=0.0,
        )
