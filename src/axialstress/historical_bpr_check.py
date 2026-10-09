"""Spatial checks of historical Axial BPR changes against an elastic Mogi source."""

from __future__ import annotations

import datetime as dt

import numpy as np

from axialstress.benchmarks import mogi_surface_displacement_m
from axialstress.bpr_mogi_calibration import local_east_north_offset_m

EVENT_WINDOWS = {
    "1998": {
        "pre_start": dt.date(1998, 1, 20),
        "pre_end": dt.date(1998, 1, 25),
        "post_start": dt.date(1998, 1, 31),
        "post_end": dt.date(1998, 2, 5),
    },
    "2011": {
        "pre_start": dt.date(2011, 4, 1),
        "pre_end": dt.date(2011, 4, 6),
        "post_start": dt.date(2011, 4, 7),
        "post_end": dt.date(2011, 4, 12),
    },
}


def mogi_vertical_response_ratio(
    target_lat_lon_deg: tuple[float, float],
    source_lat_lon_deg: tuple[float, float],
    *,
    source_depth_m: float = 4000.0,
    source_radius_m: float = 700.0,
    youngs_modulus_pa: float = 60.0e9,
    poisson_ratio: float = 0.25,
) -> float:
    """Return target-to-source vertical displacement per unit pressure change."""
    if not np.isfinite(youngs_modulus_pa) or youngs_modulus_pa <= 0.0:
        raise ValueError("Young's modulus must be finite and positive")
    if not np.isfinite(poisson_ratio) or not 0.0 < poisson_ratio < 0.5:
        raise ValueError("Poisson ratio must be in (0, 0.5)")
    x_m, y_m = local_east_north_offset_m(
        target_lat_lon_deg[0],
        target_lat_lon_deg[1],
        origin_latitude_deg=source_lat_lon_deg[0],
        origin_longitude_deg=source_lat_lon_deg[1],
    )
    shear_modulus_pa = youngs_modulus_pa / (2.0 * (1.0 + poisson_ratio))
    bulk_modulus_pa = youngs_modulus_pa / (3.0 * (1.0 - 2.0 * poisson_ratio))
    source_vertical_m = mogi_surface_displacement_m(
        0.0,
        0.0,
        source_depth_m=source_depth_m,
        source_radius_m=source_radius_m,
        pressure_change_pa=1.0,
        bulk_modulus_pa=bulk_modulus_pa,
        shear_modulus_pa=shear_modulus_pa,
    )[2]
    target_vertical_m = mogi_surface_displacement_m(
        x_m,
        y_m,
        source_depth_m=source_depth_m,
        source_radius_m=source_radius_m,
        pressure_change_pa=1.0,
        bulk_modulus_pa=bulk_modulus_pa,
        shear_modulus_pa=shear_modulus_pa,
    )[2]
    return float(target_vertical_m / source_vertical_m)
