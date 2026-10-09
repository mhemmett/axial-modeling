"""Synthetic checks for postprocessed failure indicators."""

import numpy as np
import pytest

from axialstress.failure import (
    classify_andersonian_regime,
    failure_indicators,
    mohr_coulomb_yield_pa,
    stress_voigt_to_tensor_pa,
)


def test_converts_pylith_voigt_order_to_symmetric_stress_tensor() -> None:
    stress = stress_voigt_to_tensor_pa(np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0]))
    np.testing.assert_array_equal(
        stress,
        np.array([[1.0, 4.0, 6.0], [4.0, 2.0, 5.0], [6.0, 5.0, 3.0]]),
    )


def test_mohr_coulomb_yield_is_positive_above_shear_threshold() -> None:
    stress = np.diag([12.0e6, 0.0, -12.0e6])
    yield_pa = mohr_coulomb_yield_pa(
        stress, cohesion_pa=2.0e6, friction_angle_deg=30.0
    )
    assert float(yield_pa) > 0.0


def test_friction_coefficient_matches_equivalent_friction_angle() -> None:
    stress = np.diag([-20.0e6, -12.0e6, -4.0e6])
    angle_yield = mohr_coulomb_yield_pa(
        stress, cohesion_pa=1.0e6, friction_angle_deg=25.0
    )
    coefficient_yield = mohr_coulomb_yield_pa(
        stress,
        cohesion_pa=1.0e6,
        friction_coefficient=float(np.tan(np.deg2rad(25.0))),
    )
    np.testing.assert_allclose(coefficient_yield, angle_yield, rtol=1.0e-14)


@pytest.mark.parametrize(
    ("friction_angle_deg", "friction_coefficient"),
    [(None, None), (25.0, 0.5), (-1.0, None), (None, -0.5)],
)
def test_mohr_coulomb_requires_one_valid_friction_parameterization(
    friction_angle_deg: float | None, friction_coefficient: float | None
) -> None:
    with pytest.raises(ValueError):
        mohr_coulomb_yield_pa(
            np.zeros((3, 3)),
            cohesion_pa=1.0e6,
            friction_angle_deg=friction_angle_deg,
            friction_coefficient=friction_coefficient,
        )


def test_uniaxial_tension_triggers_tensile_cutoff_only() -> None:
    stress = np.diag([5.0e6, 0.0, 0.0])
    result = failure_indicators(
        stress,
        cohesion_pa=5.0e6,
        friction_angle_deg=30.0,
        tensile_strength_pa=2.0e6,
    )
    assert bool(result["tensile_failure"])
    assert not bool(result["mohr_coulomb_failure"])


def test_pure_shear_crosses_mohr_coulomb_threshold() -> None:
    stress = np.diag([12.0e6, -12.0e6, 0.0])
    result = failure_indicators(
        stress,
        cohesion_pa=2.0e6,
        friction_angle_deg=30.0,
        tensile_strength_pa=20.0e6,
    )
    assert bool(result["mohr_coulomb_failure"])
    assert not bool(result["tensile_failure"])


def test_lithostatic_stress_is_normal_faulting() -> None:
    stress = np.diag([0.0, 0.0, -30.0e6])
    result = failure_indicators(
        stress,
        cohesion_pa=20.0e6,
        friction_angle_deg=30.0,
        tensile_strength_pa=5.0e6,
    )
    assert not bool(result["tensile_failure"])
    assert classify_andersonian_regime(stress).item() == "normal"


def test_horizontal_maximum_vertical_intermediate_is_strike_slip() -> None:
    stress = np.diag([-10.0e6, 0.0, -5.0e6])
    assert classify_andersonian_regime(stress).item() == "strike-slip"
