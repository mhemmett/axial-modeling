"""Constitutive checks for PyLith's generalized Maxwell material."""

from __future__ import annotations

import math

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]
BRANCH_COUNT = 3
TENSOR_COMPONENT_COUNT = 6


def generalized_maxwell_relaxation_times_s(
    youngs_modulus_pa: float,
    poisson_ratio: float,
    viscosity_pa_s_by_branch: FloatArray,
    shear_modulus_ratio_by_branch: FloatArray,
) -> FloatArray:
    """Return the three branch relaxation times in seconds.

    Parameters
    ----------
    youngs_modulus_pa : float
        Total elastic Young's modulus in pascals.
    poisson_ratio : float
        Isotropic Poisson ratio in the stable range ``(-1, 0.5)``.
    viscosity_pa_s_by_branch : array_like
        Positive Maxwell branch viscosities in pascal-seconds, shape ``(3,)``
        or ``(3, ncells)``.
    shear_modulus_ratio_by_branch : array_like
        Positive branch fractions, with the same shape as the viscosities.
        Their sum may not exceed one in any cell.

    Returns
    -------
    numpy.ndarray
        Branch relaxation times, in seconds, with the input branch layout.

    Notes
    -----
    Uses PyLith 5.0.2 Eq. 90, ``tau_i = eta_i / (mu_total * mu_i)``.
    See https://pylith.readthedocs.io/en/v5.0.2/user/governingeqns/elasticity/bulk-rheologies/linear-genmaxwell.html.
    """
    viscosities = np.asarray(viscosity_pa_s_by_branch, dtype=float)
    fractions = np.asarray(shear_modulus_ratio_by_branch, dtype=float)
    if viscosities.ndim not in (1, 2) or viscosities.shape[0] != BRANCH_COUNT:
        raise ValueError("branch viscosities must have shape (3,) or (3, ncells)")
    if fractions.shape != viscosities.shape:
        raise ValueError("branch fractions must have the same shape as viscosities")
    if not math.isfinite(youngs_modulus_pa) or youngs_modulus_pa <= 0.0:
        raise ValueError("Young's modulus must be finite and positive")
    if not math.isfinite(poisson_ratio) or not -1.0 < poisson_ratio < 0.5:
        raise ValueError("Poisson ratio must be in the stable range (-1, 0.5)")
    if not np.all(np.isfinite(viscosities)) or np.any(viscosities <= 0.0):
        raise ValueError("branch viscosities must be finite and positive")
    if not np.all(np.isfinite(fractions)) or np.any(fractions <= 0.0):
        raise ValueError("branch fractions must be finite and positive")
    if np.any(np.sum(fractions, axis=0) > 1.0):
        raise ValueError("branch fractions must sum to at most one in every cell")

    shear_modulus_pa = youngs_modulus_pa / (2.0 * (1.0 + poisson_ratio))
    return viscosities / (shear_modulus_pa * fractions)


def reconstruct_generalized_maxwell_stress_pa(
    strain: FloatArray,
    viscous_strain_by_branch: FloatArray,
    youngs_modulus_pa: float,
    poisson_ratio: float,
    shear_modulus_ratio_by_branch: FloatArray,
) -> FloatArray:
    """Reconstruct Cauchy stress in pascals from strain and branch states.

    Parameters
    ----------
    strain : array_like
        Total strain components ordered ``xx, yy, zz, xy, yz, xz``. The last
        dimension must have length six.
    viscous_strain_by_branch : array_like
        PyLith branch memory variables with shape ``(*strain.shape[:-1], 3, 6)``.
    youngs_modulus_pa : float
        Total elastic Young's modulus in pascals.
    poisson_ratio : float
        Isotropic Poisson ratio in the stable range ``(-1, 0.5)``.
    shear_modulus_ratio_by_branch : array_like
        Positive shear modulus fractions for the three branches, either shape
        ``(3,)`` or cellwise shape ``(*strain.shape[-2:-1], 3)``. For a history
        array, cellwise fractions are broadcast across the time dimension.

    Returns
    -------
    numpy.ndarray
        Cauchy stress components in pascals, in the same tensor layout as
        ``strain``.

    Notes
    -----
    Uses PyLith 5.0.2 Eq. 88: the volumetric response is elastic, while the
    deviatoric response combines the equilibrium spring and branch states.
    See https://pylith.readthedocs.io/en/v5.0.2/user/governingeqns/elasticity/bulk-rheologies/linear-genmaxwell.html.
    """
    values = np.asarray(strain, dtype=float)
    branch_state = np.asarray(viscous_strain_by_branch, dtype=float)
    fractions = np.asarray(shear_modulus_ratio_by_branch, dtype=float)
    if values.ndim == 0 or values.shape[-1] != TENSOR_COMPONENT_COUNT:
        raise ValueError("strain must have six tensor components on its last axis")
    expected_state_shape = (*values.shape[:-1], BRANCH_COUNT, TENSOR_COMPONENT_COUNT)
    if branch_state.shape != expected_state_shape:
        raise ValueError(f"viscous strain must have shape {expected_state_shape}")
    if not np.all(np.isfinite(values)) or not np.all(np.isfinite(branch_state)):
        raise ValueError("strain and viscous strain must be finite")
    if fractions.shape == (BRANCH_COUNT,):
        broadcast_fractions = np.broadcast_to(
            fractions, (*values.shape[:-1], BRANCH_COUNT)
        )
    elif fractions.shape == (*values.shape[:-1], BRANCH_COUNT):
        broadcast_fractions = fractions
    elif values.ndim >= 2 and fractions.shape == (
        *values.shape[1:-1],
        BRANCH_COUNT,
    ):
        broadcast_fractions = np.broadcast_to(
            fractions, (*values.shape[:-1], BRANCH_COUNT)
        )
    else:
        raise ValueError("branch fractions must be global or match the cell dimensions")
    if not np.all(np.isfinite(broadcast_fractions)) or np.any(
        broadcast_fractions <= 0.0
    ):
        raise ValueError("branch fractions must be finite and positive")
    if np.any(np.sum(broadcast_fractions, axis=-1) > 1.0):
        raise ValueError("branch fractions must sum to at most one in every cell")
    if not math.isfinite(youngs_modulus_pa) or youngs_modulus_pa <= 0.0:
        raise ValueError("Young's modulus must be finite and positive")
    if not math.isfinite(poisson_ratio) or not -1.0 < poisson_ratio < 0.5:
        raise ValueError("Poisson ratio must be in the stable range (-1, 0.5)")

    shear_modulus_pa = youngs_modulus_pa / (2.0 * (1.0 + poisson_ratio))
    bulk_modulus_pa = youngs_modulus_pa / (3.0 * (1.0 - 2.0 * poisson_ratio))
    strain_trace = np.sum(values[..., :3], axis=-1)
    deviatoric_strain = values.copy()
    deviatoric_strain[..., :3] -= strain_trace[..., np.newaxis] / 3.0
    equilibrium_fraction = 1.0 - np.sum(broadcast_fractions, axis=-1)
    deviatoric_stress_pa = 2.0 * shear_modulus_pa * (
        equilibrium_fraction[..., np.newaxis] * deviatoric_strain
        + np.einsum("...b,...bj->...j", broadcast_fractions, branch_state)
    )
    stress_pa = deviatoric_stress_pa.copy()
    stress_pa[..., :3] += bulk_modulus_pa * strain_trace[..., np.newaxis]
    return stress_pa
