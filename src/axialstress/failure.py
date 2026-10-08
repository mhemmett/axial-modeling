"""Evaluate tensile and Mohr–Coulomb criteria from Cauchy stress tensors.

Stress tensors use PyLith's tensile-positive sign convention and are expressed
in pascals. The failure criteria are postprocessing proxies, not constitutive
updates to the displacement solution.
"""

from __future__ import annotations

import numpy as np


def failure_indicators(
    stress_pa: np.ndarray,
    *,
    cohesion_pa: float,
    friction_angle_deg: float,
    tensile_strength_pa: float,
    pore_pressure_pa: float = 0.0,
) -> dict[str, np.ndarray]:
    """Return tensile and Mohr–Coulomb indicators for symmetric stress tensors.

    Parameters
    ----------
    stress_pa : numpy.ndarray
        Cauchy stress tensors with shape ``(..., 3, 3)``; tension is positive.
    cohesion_pa : float
        Mohr–Coulomb cohesion, in pascals.
    friction_angle_deg : float
        Internal friction angle, in degrees.
    tensile_strength_pa : float
        Tensile failure threshold, in pascals.
    pore_pressure_pa : float, optional
        Isotropic pore pressure, in pascals; default is zero.

    Returns
    -------
    dict[str, numpy.ndarray]
        Boolean ``tensile_failure`` and ``mohr_coulomb_failure`` arrays, plus
        principal stresses and the Mohr–Coulomb yield function in pascals.

    Notes
    -----
    The Mohr–Coulomb proxy uses the maximum and minimum effective compressive
    principal stresses. A tensile cutoff prevents open tensile states from
    being labeled as frictional shear failure.
    """
    stress = np.asarray(stress_pa, dtype=float)
    if stress.shape[-2:] != (3, 3):
        raise ValueError("stress_pa must end in a 3 x 3 tensor")
    if not np.allclose(stress, np.swapaxes(stress, -1, -2), rtol=1e-8, atol=1e-8):
        raise ValueError("stress tensors must be symmetric")
    if cohesion_pa < 0 or tensile_strength_pa < 0 or pore_pressure_pa < 0:
        raise ValueError("strength and pore pressure values must be nonnegative")
    if not 0.0 <= friction_angle_deg < 90.0:
        raise ValueError("friction_angle_deg must be in [0, 90)")

    effective_compression = -stress - pore_pressure_pa * np.eye(3)
    principal_compression = np.linalg.eigvalsh(effective_compression)
    sigma3 = principal_compression[..., 0]
    sigma1 = principal_compression[..., 2]
    tensile_principal = np.linalg.eigvalsh(stress)[..., 2]
    friction = np.deg2rad(friction_angle_deg)
    yield_pa = (
        sigma1
        - sigma3
        - (sigma1 + sigma3) * np.sin(friction)
        - 2.0 * cohesion_pa * np.cos(friction)
    )
    tensile_cutoff = sigma3 >= -tensile_strength_pa
    return {
        "tensile_failure": tensile_principal >= tensile_strength_pa,
        "mohr_coulomb_failure": (yield_pa >= 0.0) & tensile_cutoff,
        "principal_compression_pa": principal_compression,
        "mohr_coulomb_yield_pa": yield_pa,
    }


def classify_andersonian_regime(
    stress_pa: np.ndarray,
    *,
    vertical_axis: int = 2,
    tolerance_deg: float = 15.0,
) -> np.ndarray:
    """Classify stress tensors as normal, strike-slip, reverse, or oblique.

    Parameters
    ----------
    stress_pa : numpy.ndarray
        Cauchy stress tensors with shape ``(..., 3, 3)``; tension is positive.
    vertical_axis : int, optional
        Tensor axis corresponding to vertical, defaulting to ``z``.
    tolerance_deg : float, optional
        Maximum angle between vertical and a principal axis, in degrees.

    Returns
    -------
    numpy.ndarray
        Regime labels with the batch shape of ``stress_pa``.
    """
    stress = np.asarray(stress_pa, dtype=float)
    if stress.shape[-2:] != (3, 3):
        raise ValueError("stress_pa must end in a 3 x 3 tensor")
    if vertical_axis not in (0, 1, 2):
        raise ValueError("vertical_axis must be 0, 1, or 2")
    if not 0.0 <= tolerance_deg < 90.0:
        raise ValueError("tolerance_deg must be in [0, 90)")

    flat = (-stress).reshape((-1, 3, 3))
    labels: list[str] = []
    cosine_limit = np.cos(np.deg2rad(tolerance_deg))
    for tensor in flat:
        _, eigenvectors = np.linalg.eigh(tensor)
        vertical_alignment = np.abs(eigenvectors[vertical_axis, :])
        principal_index = int(np.argmax(vertical_alignment))
        if vertical_alignment[principal_index] < cosine_limit:
            labels.append("oblique")
        elif principal_index == 2:
            labels.append("normal")
        elif principal_index == 0:
            labels.append("reverse")
        else:
            labels.append("strike-slip")
    return np.asarray(labels, dtype=object).reshape(stress.shape[:-2])
