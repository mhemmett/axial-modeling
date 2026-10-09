"""Tests for building temperature-dependent PyLith Maxwell databases."""

from pathlib import Path

import numpy as np
import pytest

from axialstress.material_database import (
    write_elastic_database,
    write_temperature_dependent_maxwell_database,
)
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
