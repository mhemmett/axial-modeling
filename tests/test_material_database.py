"""Tests for building temperature-dependent PyLith Maxwell databases."""

from pathlib import Path

import numpy as np
import pytest

from axialstress.material_database import (
    write_maxwell_database_from_thermal_archive,
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
