"""Synthetic checks for analytical elastic benchmark solutions."""

import numpy as np
import pytest

from axialstress.benchmarks import mogi_surface_displacement_m


def test_mogi_displacement_has_radial_symmetry_and_positive_uplift() -> None:
    displacement = mogi_surface_displacement_m(
        np.array([-1000.0, 0.0, 1000.0]),
        np.zeros(3),
        source_depth_m=2000.0,
        source_radius_m=500.0,
        pressure_change_pa=2.0e6,
        bulk_modulus_pa=25.0e9,
        shear_modulus_pa=16.0e9,
    )

    assert displacement[0, 0] == pytest.approx(-displacement[2, 0])
    assert displacement[0, 2] == pytest.approx(displacement[2, 2])
    assert displacement[1, 0] == pytest.approx(0.0)
    assert displacement[1, 1] == pytest.approx(0.0)
    expected_center_uplift = (
        2.0e6
        * 500.0**3
        / 2000.0**2
        * (3.0 * 25.0e9 + 4.0 * 16.0e9)
        / (2.0 * 16.0e9 * (3.0 * 25.0e9 + 16.0e9))
    )
    assert displacement[1, 2] == pytest.approx(expected_center_uplift)


def test_mogi_displacement_scales_linearly_with_pressure() -> None:
    base = mogi_surface_displacement_m(
        300.0,
        400.0,
        source_depth_m=2500.0,
        source_radius_m=600.0,
        pressure_change_pa=1.0e6,
        bulk_modulus_pa=30.0e9,
        shear_modulus_pa=18.0e9,
    )
    doubled = mogi_surface_displacement_m(
        300.0,
        400.0,
        source_depth_m=2500.0,
        source_radius_m=600.0,
        pressure_change_pa=2.0e6,
        bulk_modulus_pa=30.0e9,
        shear_modulus_pa=18.0e9,
    )

    np.testing.assert_allclose(doubled, 2.0 * base)


def test_mogi_rejects_invalid_source_or_elastic_parameters() -> None:
    with pytest.raises(ValueError, match="source depth and radius"):
        mogi_surface_displacement_m(
            0.0,
            0.0,
            source_depth_m=0.0,
            source_radius_m=500.0,
            pressure_change_pa=1.0e6,
            bulk_modulus_pa=25.0e9,
            shear_modulus_pa=16.0e9,
        )
