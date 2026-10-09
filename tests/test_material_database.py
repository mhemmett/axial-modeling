"""Tests for building temperature-dependent PyLith Maxwell databases."""

from pathlib import Path

import numpy as np
import pytest

from axialstress.material_database import (
    write_elastic_database,
    write_maxwell_database_from_thermal_archive,
    write_temperature_dependent_maxwell_database,
)
from axialstress.tetrahedral_interpolation import interpolate_tetrahedral_field
from axialstress.thermal import temperature_dependent_viscosity_pa_s


def test_writes_centroid_properties_and_zero_initial_state(tmp_path: Path) -> None:
    vertices = np.array(
        [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
    )
    temperature = np.array([0.0, 10.0, 20.0, 30.0])
    destination = write_temperature_dependent_maxwell_database(
        tmp_path / "material.spatialdb",
        vertices,
        np.array([[0, 1, 2, 3]]),
        temperature,
        40.0e9,
        density_kg_m3=2800.0,
        poisson_ratio=0.25,
    )

    rows = np.atleast_2d(np.loadtxt(destination, comments="#", skiprows=13))
    centroid_temperature = float(np.mean(temperature))
    shear_modulus = 40.0e9 / (2.0 * 1.25)
    bulk_modulus = 40.0e9 / (3.0 * 0.5)
    expected_vs = np.sqrt(shear_modulus / 2800.0) / 1000.0
    expected_vp = np.sqrt((bulk_modulus + 4.0 * shear_modulus / 3.0) / 2800.0) / 1000.0

    np.testing.assert_allclose(rows[0, :3], vertices.mean(axis=0))
    np.testing.assert_allclose(rows[0, 3:6], [2800.0, expected_vs, expected_vp])
    assert rows[0, 6] == pytest.approx(
        temperature_dependent_viscosity_pa_s(centroid_temperature)
    )
    np.testing.assert_array_equal(rows[0, 7:], np.zeros(12))
    assert "value-names = density vs vp viscosity" in destination.read_text(encoding="utf-8")


def test_rejects_unstable_poisson_ratio(tmp_path: Path) -> None:
    vertices = np.array(
        [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
    )

    with pytest.raises(ValueError, match="Poisson ratio"):
        write_temperature_dependent_maxwell_database(
            tmp_path / "material.spatialdb",
            vertices,
            np.array([[0, 1, 2, 3]]),
            np.zeros(4),
            40.0e9,
            density_kg_m3=2800.0,
            poisson_ratio=0.5,
        )


def test_writes_cellwise_youngs_modulus_values(tmp_path: Path) -> None:
    vertices = np.array(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
            [1.0, 1.0, 1.0],
        ]
    )
    cells = np.array([[0, 1, 2, 3], [1, 2, 3, 4]])
    path = write_temperature_dependent_maxwell_database(
        tmp_path / "variable-material.spatialdb",
        vertices,
        cells,
        np.array([0.0, 0.0, 0.0, 0.0, 1200.0]),
        np.array([25.0e9, 75.0e9]),
        density_kg_m3=2800.0,
        poisson_ratio=0.25,
    )

    rows = np.atleast_2d(np.loadtxt(path, comments="#", skiprows=13))
    assert rows.shape == (2, 19)
    elastic_path = write_elastic_database(
        tmp_path / "matching-elastic.spatialdb",
        vertices,
        cells,
        np.array([25.0e9, 75.0e9]),
        density_kg_m3=2800.0,
        poisson_ratio=0.25,
    )
    elastic_rows = np.atleast_2d(np.loadtxt(elastic_path, comments="#", skiprows=13))
    expected_vs = np.sqrt(np.array([25.0e9, 75.0e9]) / 2.5 / 2800.0) / 1000.0
    np.testing.assert_allclose(rows[:, 4], expected_vs)
    np.testing.assert_allclose(rows[:, 3:6], elastic_rows[:, 3:6])


def test_writes_cell_centered_elastic_properties(tmp_path: Path) -> None:
    vertices = np.array(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
            [1.0, 1.0, 1.0],
        ]
    )
    cells = np.array([[0, 1, 2, 3], [1, 2, 3, 4]])
    path = write_elastic_database(
        tmp_path / "elastic.spatialdb",
        vertices,
        cells,
        np.array([25.0e9, 50.0e9]),
        density_kg_m3=2800.0,
        poisson_ratio=0.25,
    )

    rows = np.atleast_2d(np.loadtxt(path, comments="#", skiprows=13))
    assert rows.shape == (2, 6)
    np.testing.assert_allclose(rows[:, :3], vertices[cells].mean(axis=1))
    np.testing.assert_allclose(rows[:, 3], 2800.0)
    expected_vs = np.sqrt(np.array([25.0e9, 50.0e9]) / 2.5 / 2800.0) / 1000.0
    expected_vp = np.sqrt(
        np.array([25.0e9, 50.0e9]) / 0.5
        * (1.5 / 2.5)
        / 2800.0
    ) / 1000.0
    np.testing.assert_allclose(rows[:, 4], expected_vs)
    np.testing.assert_allclose(rows[:, 5], expected_vp)


def test_builds_material_database_from_thermal_archive(tmp_path: Path) -> None:
    vertices = np.array(
        [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
    )
    cells = np.array([[0, 1, 2, 3]])
    temperatures = np.array([0.0, 10.0, 20.0, 30.0])
    archive_path = tmp_path / "thermal.npz"
    np.savez_compressed(
        archive_path,
        vertices_m=vertices,
        tetrahedra=cells,
        temperature_c=temperatures,
    )

    database_path = write_maxwell_database_from_thermal_archive(
        archive_path,
        tmp_path / "material.spatialdb",
        35.0e9,
        density_kg_m3=2800.0,
        poisson_ratio=0.25,
    )

    rows = np.atleast_2d(np.loadtxt(database_path, comments="#", skiprows=13))
    assert rows.shape == (1, 19)
    assert rows[0, 6] == pytest.approx(
        temperature_dependent_viscosity_pa_s(float(temperatures.mean()))
    )


def test_interpolates_affine_scalar_and_vector_fields_across_tetrahedra() -> None:
    vertices = np.array(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
            [1.0, 1.0, 1.0],
        ]
    )
    tetrahedra = np.array([[0, 1, 2, 3], [1, 2, 3, 4]])
    scalar = 4.0 + 2.0 * vertices[:, 0] - vertices[:, 1] + 3.0 * vertices[:, 2]
    vector = np.column_stack((scalar, -2.0 * scalar))
    points = np.array([[0.1, 0.2, 0.1], [0.7, 0.8, 0.7]])

    result_scalar = interpolate_tetrahedral_field(
        vertices, tetrahedra, scalar, points
    )
    result_vector = interpolate_tetrahedral_field(
        vertices, tetrahedra, vector, points
    )
    expected = 4.0 + 2.0 * points[:, 0] - points[:, 1] + 3.0 * points[:, 2]

    np.testing.assert_allclose(result_scalar, expected, atol=1.0e-14)
    np.testing.assert_allclose(result_vector, np.column_stack((expected, -2.0 * expected)))


def test_interpolation_rejects_points_outside_source_mesh() -> None:
    vertices = np.array(
        [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
    )
    with pytest.raises(ValueError, match="outside the source mesh"):
        interpolate_tetrahedral_field(
            vertices,
            np.array([[0, 1, 2, 3]]),
            np.zeros(4),
            np.array([[2.0, 2.0, 2.0]]),
        )


def test_maps_thermal_archive_to_different_mechanics_mesh(tmp_path: Path) -> None:
    thermal_vertices = np.array(
        [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
    )
    thermal_cells = np.array([[0, 1, 2, 3]])
    thermal_temperature = (
        300.0
        + 10.0 * thermal_vertices[:, 0]
        + 20.0 * thermal_vertices[:, 1]
        + 30.0 * thermal_vertices[:, 2]
    )
    mechanics_vertices = np.array(
        [
            [0.1, 0.1, 0.1],
            [0.4, 0.1, 0.1],
            [0.1, 0.4, 0.1],
            [0.1, 0.1, 0.4],
        ]
    )
    mechanics_cells = np.array([[0, 1, 2, 3]])
    thermal_archive = tmp_path / "coarse-thermal.npz"
    np.savez_compressed(
        thermal_archive,
        vertices_m=thermal_vertices,
        tetrahedra=thermal_cells,
        temperature_c=thermal_temperature,
    )

    database_path = write_maxwell_database_from_thermal_archive(
        thermal_archive,
        tmp_path / "mapped-material.spatialdb",
        35.0e9,
        density_kg_m3=2800.0,
        poisson_ratio=0.25,
        mechanics_vertices_m=mechanics_vertices,
        mechanics_tetrahedra=mechanics_cells,
    )

    rows = np.atleast_2d(np.loadtxt(database_path, comments="#", skiprows=13))
    expected_temperature = 300.0 + 10.0 * 0.175 + 20.0 * 0.175 + 30.0 * 0.175
    assert rows.shape == (1, 19)
    np.testing.assert_allclose(rows[0, :3], mechanics_vertices.mean(axis=0))
    assert rows[0, 6] == pytest.approx(
        temperature_dependent_viscosity_pa_s(expected_temperature)
    )
