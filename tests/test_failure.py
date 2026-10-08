"""Synthetic checks for postprocessed failure indicators."""

import numpy as np

from axialstress.failure import classify_andersonian_regime, failure_indicators


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
