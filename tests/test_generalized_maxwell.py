"""Tests for generalized Maxwell constitutive verification formulas."""

import numpy as np
import pytest

from axialstress.generalized_maxwell import (
    generalized_maxwell_relaxation_times_s,
    reconstruct_generalized_maxwell_stress_pa,
)


def test_relaxation_times_match_pylith_fractional_shear_definition() -> None:
    relaxation_times_s = generalized_maxwell_relaxation_times_s(
        50.0e9,
        0.25,
        np.array([1.0e18, 5.0e17, 2.0e18]),
        np.array([0.25, 0.25, 0.25]),
    )

    np.testing.assert_allclose(relaxation_times_s, [2.0e8, 1.0e8, 4.0e8])


def test_reconstructs_volumetric_and_deviatoric_stress() -> None:
    youngs_modulus_pa = 40.0e9
    poisson_ratio = 0.25
    fractions = np.array([0.2, 0.3, 0.1])
    strain = np.array([3.0e-4, -1.0e-4, 2.0e-4, 4.0e-5, -2.0e-5, 1.0e-5])
    branch_state = np.array(
        [
            [0.1e-4, -0.2e-4, 0.1e-4, 0.3e-4, 0.0, -0.1e-4],
            [-0.1e-4, 0.2e-4, -0.1e-4, -0.2e-4, 0.1e-4, 0.05e-4],
            [0.3e-4, 0.0, -0.3e-4, 0.1e-4, -0.2e-4, 0.0],
        ]
    )

    shear_modulus_pa = youngs_modulus_pa / (2.0 * (1.0 + poisson_ratio))
    bulk_modulus_pa = youngs_modulus_pa / (3.0 * (1.0 - 2.0 * poisson_ratio))
    strain_trace = 4.0e-4
    deviatoric_strain = np.array(
        [
            3.0e-4 - strain_trace / 3.0,
            -1.0e-4 - strain_trace / 3.0,
            2.0e-4 - strain_trace / 3.0,
            4.0e-5,
            -2.0e-5,
            1.0e-5,
        ]
    )
    equilibrium_fraction = 1.0 - fractions.sum()
    expected_stress_pa = 2.0 * shear_modulus_pa * (
        equilibrium_fraction * deviatoric_strain
        + fractions[0] * branch_state[0]
        + fractions[1] * branch_state[1]
        + fractions[2] * branch_state[2]
    )
    expected_stress_pa[:3] += bulk_modulus_pa * strain_trace

    actual_stress_pa = reconstruct_generalized_maxwell_stress_pa(
        strain,
        branch_state,
        youngs_modulus_pa,
        poisson_ratio,
        fractions,
    )

    np.testing.assert_allclose(actual_stress_pa, expected_stress_pa, rtol=1.0e-14)


def test_rejects_mismatched_branch_state_shape() -> None:
    with pytest.raises(ValueError, match="viscous strain must have shape"):
        reconstruct_generalized_maxwell_stress_pa(
            np.zeros(6),
            np.zeros((2, 6)),
            40.0e9,
            0.25,
            np.array([0.2, 0.3, 0.1]),
        )


def test_rejects_branch_fractions_above_one_for_relaxation_times() -> None:
    with pytest.raises(ValueError, match="sum to at most one"):
        generalized_maxwell_relaxation_times_s(
            40.0e9,
            0.25,
            np.array([1.0e18, 5.0e17, 2.0e18]),
            np.array([0.5, 0.5, 0.1]),
        )
