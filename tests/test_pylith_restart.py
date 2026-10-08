"""Tests for exporting PyLith Maxwell state to spatial databases."""

from pathlib import Path

import h5py
import numpy as np
import pytest

from axialstress.pylith_restart import write_maxwell_restart_databases


def _write_observers(
    solution_path: Path,
    material_path: Path,
    *,
    final_time: float = 1.0,
    vertex_shift: float = 0.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    vertices = np.array(
        [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
    )
    shifted_vertices = vertices.copy()
    shifted_vertices[0, 0] += vertex_shift
    cells = np.array([[0, 1, 2, 3]], dtype=np.int32)
    displacement = np.arange(12, dtype=float).reshape(1, 4, 3) * 1.0e-3
    viscous_strain = np.arange(6, dtype=float).reshape(1, 1, 6) * 1.0e-6
    total_strain = viscous_strain + 2.0e-6

    with h5py.File(solution_path, "w") as solution:
        solution.create_dataset("time", data=[0.0, final_time])
        solution.create_dataset("geometry/vertices", data=vertices)
        solution.create_dataset("vertex_fields/displacement", data=displacement)

    with h5py.File(material_path, "w") as material:
        material.create_dataset("time", data=[0.0, final_time])
        material.create_dataset("geometry/vertices", data=shifted_vertices)
        material.create_dataset("viz/topology/cells", data=cells)
        material.create_dataset("cell_fields/viscous_strain", data=viscous_strain)
        material.create_dataset("cell_fields/cauchy_strain", data=total_strain)

    return vertices, displacement[0], viscous_strain[0]


def test_exports_vertex_displacement_and_cell_state(tmp_path: Path) -> None:
    solution_path = tmp_path / "solution.h5"
    material_path = tmp_path / "material.h5"
    vertices, displacement, state = _write_observers(solution_path, material_path)

    displacement_path, state_path = write_maxwell_restart_databases(
        solution_path, material_path, tmp_path / "db"
    )

    displacement_rows = np.loadtxt(displacement_path, comments="#", skiprows=13)
    state_rows = np.atleast_2d(
        np.loadtxt(state_path, comments="#", skiprows=13)
    )
    np.testing.assert_allclose(displacement_rows[:, :3], vertices)
    np.testing.assert_allclose(displacement_rows[:, 3:], displacement)
    np.testing.assert_allclose(state_rows[0, :3], vertices.mean(axis=0))
    np.testing.assert_allclose(state_rows[0, 3:9], state[0])
    np.testing.assert_allclose(state_rows[0, 9:15], state[0] + 2.0e-6)
    assert "value-names = displacement_x displacement_y displacement_z" in (
        displacement_path.read_text(encoding="utf-8")
    )
    assert "value-names = viscous_strain_xx" in state_path.read_text(encoding="utf-8")


def test_rejects_observer_files_with_different_final_times(tmp_path: Path) -> None:
    solution_path = tmp_path / "solution.h5"
    material_path = tmp_path / "material.h5"
    _write_observers(solution_path, material_path)
    with h5py.File(material_path, "a") as material:
        material["time"][1] = 2.0

    with pytest.raises(ValueError, match="different final times"):
        write_maxwell_restart_databases(solution_path, material_path, tmp_path / "db")


def test_rejects_observer_files_with_different_vertices(tmp_path: Path) -> None:
    solution_path = tmp_path / "solution.h5"
    material_path = tmp_path / "material.h5"
    _write_observers(solution_path, material_path, vertex_shift=0.1)

    with pytest.raises(ValueError, match="different vertices"):
        write_maxwell_restart_databases(solution_path, material_path, tmp_path / "db")
