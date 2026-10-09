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
    assert result["first_cavity_to_surface_shear_path_interpolated_time_s"] == pytest.approx(
        0.0755256, abs=5.0e-3
    )
    bracket = result["interpolated_path_bracket"]
    assert bracket["lower_record_index"] == 0
    assert bracket["upper_record_index"] == 1
    assert bracket["last_no_path_time_s"] < bracket["time_s"]
    assert bracket["time_s"] < bracket["first_path_time_s"]
    assert bracket["first_path_time_s"] - bracket["last_no_path_time_s"] <= 0.01
    assert [record["cavity_to_surface_shear_path_found"] for record in result["records"]] == [
        False,
        True,
        True,
    ]


def test_stress_history_without_a_path_has_no_interpolated_onset() -> None:
    vertices, cells = _single_tetrahedron_with_top_and_cavity_faces()
    result = analyze_stress_history(
        vertices,
        cells,
        np.zeros((2, 1, 6)),
        np.array([0.0, 2.0]),
        cohesion_pa=1.0e6,
        friction_angle_deg=25.0,
        pore_pressure_pa=0.0,
    )

    assert result["first_cavity_to_surface_shear_path_time_s"] is None
    assert result["first_cavity_to_surface_shear_path_interpolated_time_s"] is None
    assert result["interpolated_path_bracket"] is None
    assert result["maximum_tensile_strength_with_a_saved_connected_path_pa"] is None


def test_stress_history_reports_joint_threshold_without_assuming_tensile_strength() -> None:
    vertices, cells = _single_tetrahedron_with_top_and_cavity_faces()
    stress_history = np.zeros((2, 1, 6))
    stress_history[1, 0, :3] = [-12.0e6, 0.0, 12.0e6]

    result = analyze_stress_history(
        vertices,
        cells,
        stress_history,
        np.array([0.0, 1.0]),
        cohesion_pa=1.0e6,
        friction_angle_deg=25.0,
        pore_pressure_pa=0.0,
    )

    assert result["assumed_tensile_strength_pa"] is None
    assert result["first_joint_eruption_criterion_record_time_s"] is None
    assert result["maximum_tensile_strength_with_a_saved_connected_path_pa"] == pytest.approx(
        12.0e6
    )
    assert result["records"][1]["reservoir_tensile_failure"] is None
    assert result["records"][1]["joint_eruption_criterion_met"] is None


@pytest.mark.parametrize(
    ("tensile_strength_pa", "expected_joint_state", "expected_time_s"),
    [(5.0e6, True, 1.0), (15.0e6, False, None)],
)
def test_stress_history_checks_joint_tensile_and_connected_path_condition(
    tensile_strength_pa: float,
    expected_joint_state: bool,
    expected_time_s: float | None,
) -> None:
    vertices, cells = _single_tetrahedron_with_top_and_cavity_faces()
    stress_history = np.zeros((2, 1, 6))
    stress_history[1, 0, :3] = [-12.0e6, 0.0, 12.0e6]

    result = analyze_stress_history(
        vertices,
        cells,
        stress_history,
        np.array([0.0, 1.0]),
        cohesion_pa=1.0e6,
        friction_angle_deg=25.0,
        pore_pressure_pa=0.0,
        tensile_strength_pa=tensile_strength_pa,
    )

    assert result["assumed_tensile_strength_pa"] == tensile_strength_pa
    assert result["first_joint_eruption_criterion_record_time_s"] == expected_time_s
    assert result["records"][0]["joint_eruption_criterion_met"] is False
    assert result["records"][1]["joint_eruption_criterion_met"] is expected_joint_state


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
