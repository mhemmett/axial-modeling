"""Compare the written Winkler stiffness scales for the project domain."""

from __future__ import annotations

import argparse

from axialstress.winkler import (
    area_stiffness_pa_per_m_from_density_contrast,
    area_stiffness_pa_per_m_from_supplement,
    dimensionless_foundation_ratio,
)


def _format_ratio_range(
    stiffness_pa_per_m: float,
    depth_m: float,
    youngs_modulus_max_pa: float,
    youngs_modulus_min_pa: float,
) -> str:
    """Format the stiffness-to-elastic scale across the modulus limits."""
    ratios = (
        dimensionless_foundation_ratio(
            stiffness_pa_per_m,
            depth_m,
            youngs_modulus_max_pa,
        ),
        dimensionless_foundation_ratio(
            stiffness_pa_per_m,
            depth_m,
            youngs_modulus_min_pa,
        ),
    )
    return f"{ratios[0]:.6g} to {ratios[1]:.6g}"


def main() -> None:
    """Print the supplement scale and an optional Galgana density sweep point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--density-kg-m3",
        type=float,
        default=2_800.0,
        help="assumed supplement density in kg/m^3 (default: current PyLith value)",
    )
    parser.add_argument(
        "--density-contrast-kg-m3",
        type=float,
        help="Axial asthenosphere-minus-lithosphere density contrast in kg/m^3",
    )
    parser.add_argument("--gravity-m-s2", type=float, default=9.81)
    parser.add_argument("--depth-m", type=float, default=10_000.0)
    parser.add_argument("--base-area-m2", type=float, default=2.5e9)
    parser.add_argument("--reference-displacement-m", type=float, default=1.0e-10)
    parser.add_argument("--minimum-youngs-modulus-pa", type=float, default=20.0e9)
    parser.add_argument("--maximum-youngs-modulus-pa", type=float, default=50.0e9)
    args = parser.parse_args()

    stiffness = area_stiffness_pa_per_m_from_supplement(
        args.density_kg_m3,
        args.depth_m,
        args.gravity_m_s2,
        args.reference_displacement_m,
    )
    total_stiffness = stiffness * args.base_area_m2
    print("Supplement Eq. 23 converted to distributed basal stiffness")
    print(f"  assumed density: {args.density_kg_m3:.6g} kg/m^3")
    print(f"  model depth: {args.depth_m / 1_000.0:.6g} km")
    print(f"  base area: {args.base_area_m2:.6g} m^2")
    print(f"  reference displacement: {args.reference_displacement_m:.6g} m")
    print(f"  total spring constant: {total_stiffness:.6g} N/m")
    print(f"  distributed stiffness: {stiffness:.6g} Pa/m")
    ratio_range = _format_ratio_range(
        stiffness,
        args.depth_m,
        args.maximum_youngs_modulus_pa,
        args.minimum_youngs_modulus_pa,
    )
    print(f"  k/(E/H): {ratio_range}")
    print(f"  displacement under 1 MPa traction: {1.0e6 / stiffness:.6g} m")

    if args.density_contrast_kg_m3 is not None:
        galgana_stiffness = area_stiffness_pa_per_m_from_density_contrast(
            args.density_contrast_kg_m3,
            args.gravity_m_s2,
        )
        print("Galgana et al. density-contrast formulation")
        print(f"  supplied density contrast: {args.density_contrast_kg_m3:.6g} kg/m^3")
        print(f"  distributed stiffness: {galgana_stiffness:.6g} Pa/m")
        ratio_range = _format_ratio_range(
            galgana_stiffness,
            args.depth_m,
            args.maximum_youngs_modulus_pa,
            args.minimum_youngs_modulus_pa,
        )
        print(f"  k/(E/H): {ratio_range}")


if __name__ == "__main__":
    main()
