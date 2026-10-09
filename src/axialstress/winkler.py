"""Calculate units and scale for a basal Winkler foundation."""

from __future__ import annotations

import math


def area_stiffness_pa_per_m_from_density_contrast(
    density_contrast_kg_m3: float,
    gravity_m_s2: float,
) -> float:
    """Return Galgana area stiffness from density contrast, in Pa/m.

    Parameters
    ----------
    density_contrast_kg_m3 : float
        Asthenosphere minus lithosphere density, in kg/m^3.
    gravity_m_s2 : float
        Local gravitational acceleration, in m/s^2.

    Returns
    -------
    float
        Distributed spring stiffness, in Pa/m.

    Notes
    -----
    Uses ``k_W = delta_rho * g`` as the coefficient between basal
    displacement and restoring traction (Galgana et al., 2011, section 2.2).
    The caller must supply an Axial density contrast; this function does not
    assign Venusian or generic crustal values to Axial Seamount.
    """
    _require_finite_positive("density_contrast_kg_m3", density_contrast_kg_m3)
    _require_finite_positive("gravity_m_s2", gravity_m_s2)
    return density_contrast_kg_m3 * gravity_m_s2


def area_stiffness_pa_per_m_from_supplement(
    density_kg_m3: float,
    model_depth_m: float,
    gravity_m_s2: float,
    reference_displacement_m: float,
) -> float:
    """Convert the supplement's total spring constant to area stiffness.

    Parameters
    ----------
    density_kg_m3 : float
        Density used in the supplement expression, in kg/m^3.
    model_depth_m : float
        Vertical box thickness, in m.
    gravity_m_s2 : float
        Local gravitational acceleration, in m/s^2.
    reference_displacement_m : float
        Reference displacement in the supplement expression, in m.

    Returns
    -------
    float
        Distributed basal stiffness, in Pa/m.

    Notes
    -----
    Dividing ``s = rho * V * g / Zdisp`` by the basal area gives
    ``k = rho * H * g / Zdisp``. This conversion preserves the distinction
    between total stiffness in N/m and area stiffness in Pa/m.
    """
    _require_finite_positive("density_kg_m3", density_kg_m3)
    _require_finite_positive("model_depth_m", model_depth_m)
    _require_finite_positive("gravity_m_s2", gravity_m_s2)
    _require_finite_positive("reference_displacement_m", reference_displacement_m)
    return (
        density_kg_m3
        * model_depth_m
        * gravity_m_s2
        / reference_displacement_m
    )


def dimensionless_foundation_ratio(
    area_stiffness_pa_per_m: float,
    characteristic_length_m: float,
    youngs_modulus_pa: float,
) -> float:
    """Return basal spring stiffness divided by bulk stiffness scale.

    Parameters
    ----------
    area_stiffness_pa_per_m : float
        Distributed spring stiffness, in Pa/m.
    characteristic_length_m : float
        Vertical length scale, in m.
    youngs_modulus_pa : float
        Young's modulus, in Pa.

    Returns
    -------
    float
        Dimensionless ratio ``k * L / E``.
    """
    _require_finite_positive("area_stiffness_pa_per_m", area_stiffness_pa_per_m)
    _require_finite_positive("characteristic_length_m", characteristic_length_m)
    _require_finite_positive("youngs_modulus_pa", youngs_modulus_pa)
    return area_stiffness_pa_per_m * characteristic_length_m / youngs_modulus_pa


def _require_finite_positive(name: str, value: float) -> None:
    """Reject non-finite and non-positive physical inputs."""
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError(f"{name} must be finite and positive")
