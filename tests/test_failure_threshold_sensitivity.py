"""Synthetic checks for saved-record failure-parameter sweeps."""

import numpy as np
import pytest

from axialstress.failure_threshold_sensitivity import analyze_failure_threshold_grid


def _single_tetrahedron_with_top_and_cavity_faces() -> tuple[np.ndarray, np.ndarray]:
    vertices = np.array(
        [[0.0, 0.0, 0.0], [0.0, 0.0, 1.0], [1.0, 0.0, 1.0], [0.0, 1.0, 1.0]]
    )
    cells = np.array([[0, 1, 2, 3]])
    return vertices, cells


def test_threshold_grid_reports_path_and_tensile_envelope() -> None:
    vertices, cells = _single_tetrahedron_with_top_and_cavity_faces()
    stress_history = np.zeros((2, 1, 6))
    stress_history[1, 0, :3] = [-12.0e6, 0.0, 12.0e6]

    results = analyze_failure_threshold_grid(
        vertices,
        cells,
        stress_history,
        np.array([0.0, 86_400.0]),
        cohesion_pa_values=[1.0e6, 20.0e6],
        friction_angle_deg_values=[25.0],
        pore_pressure_pa_values=[0.0],
    )

    assert results[0]["path_record_count"] == 1
    assert results[0]["first_path_time_s"] == 86_400.0
    assert results[0]["maximum_tensile_strength_with_saved_path_pa"] == pytest.approx(
        12.0e6
    )
    assert results[1]["path_record_count"] == 0
    assert results[1]["maximum_tensile_strength_with_saved_path_pa"] is None


def test_threshold_grid_rejects_ambiguous_or_invalid_parameter_values() -> None:
    vertices, cells = _single_tetrahedron_with_top_and_cavity_faces()
    with pytest.raises(ValueError, match="friction angle"):
        analyze_failure_threshold_grid(
            vertices,
            cells,
            np.zeros((1, 1, 6)),
            np.array([0.0]),
            cohesion_pa_values=[1.0],
            friction_angle_deg_values=[90.0],
            pore_pressure_pa_values=[0.0],
        )
