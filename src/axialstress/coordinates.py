"""Local coordinate helpers for Axial model sampling."""

from __future__ import annotations

import numpy as np

EARTH_RADIUS_M = 6_371_008.8
CENTRAL_CALDERA_LAT_LON_DEG = (45.954850, -130.008772)
EAST_CALDERA_LAT_LON_DEG = (45.939888, -129.974113)


def local_east_north_offset_m(
    latitude_deg: float,
    longitude_deg: float,
    *,
    origin_latitude_deg: float,
    origin_longitude_deg: float,
) -> tuple[float, float]:
    """Project a nearby WGS84 position into local east/north distances."""
    coordinates = (
        latitude_deg,
        longitude_deg,
        origin_latitude_deg,
        origin_longitude_deg,
    )
    if not np.all(np.isfinite(coordinates)):
        raise ValueError("station coordinates must be finite")
    if not -90.0 <= latitude_deg <= 90.0 or not -90.0 <= origin_latitude_deg <= 90.0:
        raise ValueError("latitude must be in [-90, 90] degrees")
    if not -180.0 <= longitude_deg <= 180.0 or not -180.0 <= origin_longitude_deg <= 180.0:
        raise ValueError("longitude must be in [-180, 180] degrees")

    reference_latitude_rad = np.deg2rad(origin_latitude_deg)
    east_m = (
        EARTH_RADIUS_M
        * np.cos(reference_latitude_rad)
        * np.deg2rad(longitude_deg - origin_longitude_deg)
    )
    north_m = EARTH_RADIUS_M * np.deg2rad(latitude_deg - origin_latitude_deg)
    return float(east_m), float(north_m)
