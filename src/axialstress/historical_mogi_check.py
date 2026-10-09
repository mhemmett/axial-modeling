"""Compare raw 2011 BPR event changes with a calibrated elastic Mogi source."""

from __future__ import annotations

import math

from axialstress.benchmarks import mogi_surface_displacement_m
from axialstress.bpr_mogi_calibration import local_east_north_offset_m


def compare_center_to_south_event(
    center_uplift_m: float,
    south_uplift_m: float,
    *,
    center_lat_lon_deg: tuple[float, float],
    south_lat_lon_deg: tuple[float, float],
    youngs_modulus_pa: float = 60.0e9,
    poisson_ratio: float = 0.25,
    source_radius_m: float = 700.0,
    source_depth_m: float = 4000.0,
) -> dict[str, float | str | bool]:
    """Fit a point-source pressure at Center and predict South event uplift.

    Parameters
    ----------
    center_uplift_m, south_uplift_m : float
        Relative vertical displacement over the stated event windows, in
        meters, with uplift positive.
    center_lat_lon_deg, south_lat_lon_deg : tuple of float
        BPR station coordinates in WGS84 degrees.
    youngs_modulus_pa : float
        Assumed elastic Young's modulus, in pascals.
    poisson_ratio : float
        Assumed Poisson ratio.
    source_radius_m, source_depth_m : float
        Spherical source radius and positive-down center depth, in meters.

    Returns
    -------
    dict
        Inferred pressure, South prediction, residual, and stated assumptions.

    Notes
    -----
    Uses the repository's homogeneous elastic Mogi benchmark. South is a
    held-out spatial check; this is not the ellipsoidal Maxwell model.
    """
    parameters = (
        center_uplift_m,
        south_uplift_m,
        youngs_modulus_pa,
        poisson_ratio,
        source_radius_m,
        source_depth_m,
    )
    if not all(math.isfinite(value) for value in parameters):
        raise ValueError("Mogi event inputs must be finite")
    if youngs_modulus_pa <= 0.0 or source_radius_m <= 0.0 or source_depth_m <= 0.0:
        raise ValueError("Mogi elastic properties and source geometry must be positive")
    if not 0.0 < poisson_ratio < 0.5:
        raise ValueError("Poisson ratio must be in (0, 0.5)")

    shear_modulus_pa = youngs_modulus_pa / (2.0 * (1.0 + poisson_ratio))
    bulk_modulus_pa = youngs_modulus_pa / (3.0 * (1.0 - 2.0 * poisson_ratio))
    east_offset_m, north_offset_m = local_east_north_offset_m(
        south_lat_lon_deg[0],
        south_lat_lon_deg[1],
        origin_latitude_deg=center_lat_lon_deg[0],
        origin_longitude_deg=center_lat_lon_deg[1],
    )
    unit_center_m_per_pa = float(
        mogi_surface_displacement_m(
            0.0,
            0.0,
            source_depth_m=source_depth_m,
            source_radius_m=source_radius_m,
            pressure_change_pa=1.0,
            bulk_modulus_pa=bulk_modulus_pa,
            shear_modulus_pa=shear_modulus_pa,
        )[2]
    )
    pressure_change_pa = center_uplift_m / unit_center_m_per_pa
    south_prediction_m = float(
        mogi_surface_displacement_m(
            east_offset_m,
            north_offset_m,
            source_depth_m=source_depth_m,
            source_radius_m=source_radius_m,
            pressure_change_pa=pressure_change_pa,
            bulk_modulus_pa=bulk_modulus_pa,
            shear_modulus_pa=shear_modulus_pa,
        )[2]
    )
    return {
        "method": "elastic Mogi pressure fit at Center with South held out",
        "center_observed_relative_uplift_m": center_uplift_m,
        "south_observed_relative_uplift_m": south_uplift_m,
        "south_predicted_relative_uplift_m": south_prediction_m,
        "south_residual_m": south_uplift_m - south_prediction_m,
        "inferred_pressure_change_pa": pressure_change_pa,
        "south_offset_east_m": east_offset_m,
        "south_offset_north_m": north_offset_m,
        "south_horizontal_distance_m": math.hypot(east_offset_m, north_offset_m),
        "youngs_modulus_pa": youngs_modulus_pa,
        "poisson_ratio_assumed": poisson_ratio,
        "source_radius_m": source_radius_m,
        "source_depth_m": source_depth_m,
        "center_is_calibration_site": True,
        "south_is_held_out_site": True,
        "publication_observations_used": False,
    }
