"""Synthetic checks for the extracted thermal equations."""

import numpy as np
import pytest

from axialstress.thermal import (
    evaluate_eq16_youngs_modulus_pa,
    hydrothermal_conductivity_w_mk,
    solve_steady_1d_temperature,
    temperature_dependent_viscosity_pa_s,
)


def test_printed_eq16_is_increasing_with_temperature() -> None:
    modulus = evaluate_eq16_youngs_modulus_pa(np.array([0.0, 1200.0, 1.0e6]))
    expected_cold = 25.0e9 + 50.0e9 / (1.0 + 5.0 * np.exp(12.0))
    assert modulus[0] == pytest.approx(expected_cold)
    assert modulus[0] < modulus[1] < modulus[2]
    assert modulus[2] == pytest.approx(75.0e9, rel=1.0e-8)


def test_arrhenius_viscosity_uses_absolute_temperature() -> None:
    viscosity = temperature_dependent_viscosity_pa_s(np.array([0.0, 1200.0]))
    expected_hot = 1.0e9 * np.exp(1.2e5 / (8.3114 * (1200.0 + 273.15)))
    assert viscosity[0] > viscosity[1]
    assert viscosity[1] == pytest.approx(expected_hot)


def test_hydrothermal_conductivity_is_enhanced_in_the_shallow_cold_limit() -> None:
    conductivity = hydrothermal_conductivity_w_mk(
        np.array([0.0, 1200.0]), np.array([0.0, 12000.0])
    )
    expected_shallow = 3.0 * (1.0 + 7.0 * np.exp(1.5))
    assert conductivity[0] == pytest.approx(expected_shallow)
    assert 3.0 < conductivity[1] < conductivity[0]


def test_hydrothermal_conductivity_reaches_nusselt_value_at_both_cutoffs() -> None:
    conductivity = hydrothermal_conductivity_w_mk(600.0, 6000.0)
    assert conductivity == pytest.approx(24.0)


def test_constant_conductivity_solution_matches_manufactured_profile() -> None:
    depth = np.linspace(0.0, 1000.0, 21)
    conductivity = 3.0
    heat_production = 2.0e-3
    temperature = solve_steady_1d_temperature(
        depth,
        surface_temperature_c=0.0,
        bottom_temperature_c=30.0,
        conductivity=lambda temp, z: np.full_like(z, conductivity),
        heat_production_w_m3=heat_production,
    )
    expected = 30.0 * depth / depth[-1] + heat_production / (2.0 * conductivity) * depth * (
        depth[-1] - depth
    )
    np.testing.assert_allclose(temperature, expected, rtol=1.0e-8, atol=1.0e-8)


def test_variable_conductivity_solution_matches_manufactured_profile() -> None:
    depth = np.linspace(0.0, 1000.0, 41)
    bottom_temperature = 30.0
    temperature = solve_steady_1d_temperature(
        depth,
        surface_temperature_c=0.0,
        bottom_temperature_c=bottom_temperature,
        conductivity=lambda temp, z: 3.0 * (1.0 + z / depth[-1]),
    )
    expected = bottom_temperature * np.log1p(depth / depth[-1]) / np.log(2.0)
    np.testing.assert_allclose(temperature, expected, rtol=1.0e-7, atol=1.0e-8)


def test_steady_solver_accepts_temperature_dependent_conductivity() -> None:
    depth = np.linspace(0.0, 6000.0, 31)
    temperature = solve_steady_1d_temperature(
        depth,
        surface_temperature_c=0.0,
        bottom_temperature_c=300.0,
        conductivity=hydrothermal_conductivity_w_mk,
    )
    assert temperature[0] == pytest.approx(0.0)
    assert temperature[-1] == pytest.approx(300.0)
    assert np.all(np.diff(temperature) > 0)


def test_arrhenius_viscosity_rejects_temperature_below_absolute_zero() -> None:
    with pytest.raises(ValueError, match="absolute zero"):
        temperature_dependent_viscosity_pa_s(-274.0)
