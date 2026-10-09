"""Calibrate an elastic Mogi benchmark to one OOI BPR and test a second."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import numpy as np
from numpy.typing import NDArray

from axialstress.benchmarks import mogi_surface_displacement_m
from axialstress.bpr_observations import BprSeries

FloatArray = NDArray[np.float64]
EARTH_RADIUS_M = 6_371_008.8
CENTRAL_CALDERA_LAT_LON_DEG = (45.954850, -130.008772)
EAST_CALDERA_LAT_LON_DEG = (45.939888, -129.974113)


@dataclass(frozen=True)
class MogiBprCalibration:
    """Aligned observations, inferred pressure, and eastern-site prediction."""

    times_utc: tuple[datetime, ...]
    central_uplift_m: FloatArray
    central_prediction_m: FloatArray
    east_uplift_m: FloatArray
    east_prediction_m: FloatArray
    pressure_change_pa: FloatArray
    east_residual_m: FloatArray
    central_quality_codes: tuple[str, ...]
    east_quality_codes: tuple[str, ...]
    east_offset_east_m: float
    east_offset_north_m: float
    youngs_modulus_pa: float
    poisson_ratio: float
    source_radius_m: float
    source_depth_m: float

    def summary(self) -> dict[str, object]:
        """Return scalar metrics and model assumptions for run records."""
        rmse_m = float(np.sqrt(np.mean(self.east_residual_m**2)))
        observed_norm = float(np.linalg.norm(self.east_uplift_m))
        relative_l2_error = (
            float(np.linalg.norm(self.east_residual_m) / observed_norm)
            if observed_norm > 0.0
            else None
        )
        correlation = (
            float(np.corrcoef(self.east_uplift_m, self.east_prediction_m)[0, 1])
            if np.std(self.east_uplift_m) > 0.0
            and np.std(self.east_prediction_m) > 0.0
            else None
        )
        return {
            "method": "instantaneous elastic Mogi source calibrated at Central BPR",
            "record_count": len(self.times_utc),
            "start_time_utc": self.times_utc[0].isoformat(),
            "end_time_utc": self.times_utc[-1].isoformat(),
            "central_quality_codes": sorted(set(self.central_quality_codes)),
            "east_quality_codes": sorted(set(self.east_quality_codes)),
            "youngs_modulus_pa": self.youngs_modulus_pa,
            "poisson_ratio": self.poisson_ratio,
            "poisson_ratio_status": "assumed; not specified in the written benchmark",
            "source_radius_m": self.source_radius_m,
            "source_depth_m": self.source_depth_m,
            "source_axis_location_assumption": "Central Caldera BPR coordinates",
            "east_offset_east_m": self.east_offset_east_m,
            "east_offset_north_m": self.east_offset_north_m,
            "pressure_change_min_pa": float(np.min(self.pressure_change_pa)),
            "pressure_change_max_pa": float(np.max(self.pressure_change_pa)),
            "east_rmse_m": rmse_m,
            "east_relative_l2_error": relative_l2_error,
            "east_correlation": correlation,
            "central_fit_is_calibration": True,
            "east_site_is_held_out_check": True,
            "qc_filter_applied": False,
        }


def local_east_north_offset_m(
    latitude_deg: float,
    longitude_deg: float,
    *,
    origin_latitude_deg: float,
    origin_longitude_deg: float,
) -> tuple[float, float]:
    """Project a nearby WGS84 position into local east/north distances.

    The equirectangular projection is suitable for the few-kilometer BPR
    separation used here; it is not intended for regional-scale mapping.
    """
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


def calibrate_mogi_to_bpr(
    central: BprSeries,
    east: BprSeries,
    *,
    youngs_modulus_pa: float = 60.0e9,
    poisson_ratio: float = 0.25,
    source_radius_m: float = 700.0,
    source_depth_m: float = 4000.0,
    central_lat_lon_deg: tuple[float, float] = CENTRAL_CALDERA_LAT_LON_DEG,
    east_lat_lon_deg: tuple[float, float] = EAST_CALDERA_LAT_LON_DEG,
) -> MogiBprCalibration:
    """Infer pressure from Central BPR uplift and predict at Eastern BPR.

    Each station series is re-referenced to the first common finite sample.
    The instantaneous elastic model is fitted to Central Caldera and evaluated
    independently at Eastern Caldera. OOI quality flags are retained; they are
    not used to filter samples.
    """
    if central.site.lower() != "central" or east.site.lower() not in ("east", "eastern"):
        raise ValueError("central and east inputs must identify the two OOI BPR sites")
    if (
        not np.isfinite(youngs_modulus_pa)
        or youngs_modulus_pa <= 0.0
        or not np.isfinite(poisson_ratio)
        or not 0.0 < poisson_ratio < 0.5
    ):
        raise ValueError("elastic properties require E > 0 and Poisson ratio in (0, 0.5)")

    central_by_time = {
        time: (float(uplift), quality)
        for time, uplift, quality in zip(
            central.times_utc, central.uplift_m, central.quality_codes, strict=True
        )
    }
    east_by_time = {
        time: (float(uplift), quality)
        for time, uplift, quality in zip(
            east.times_utc, east.uplift_m, east.quality_codes, strict=True
        )
    }
    common_times = sorted(central_by_time.keys() & east_by_time.keys())
    valid_times = [
        time
        for time in common_times
        if np.isfinite(central_by_time[time][0]) and np.isfinite(east_by_time[time][0])
    ]
    if not valid_times:
        raise ValueError("BPR series have no common finite daily observations")

    central_values = np.asarray([central_by_time[time][0] for time in valid_times])
    east_values = np.asarray([east_by_time[time][0] for time in valid_times])
    central_uplift = central_values - central_values[0]
    east_uplift = east_values - east_values[0]
    central_qc = tuple(central_by_time[time][1] for time in valid_times)
    east_qc = tuple(east_by_time[time][1] for time in valid_times)

    shear_modulus_pa = youngs_modulus_pa / (2.0 * (1.0 + poisson_ratio))
    bulk_modulus_pa = youngs_modulus_pa / (3.0 * (1.0 - 2.0 * poisson_ratio))
    central_latitude, central_longitude = central_lat_lon_deg
    east_latitude, east_longitude = east_lat_lon_deg
    east_offset_m, north_offset_m = local_east_north_offset_m(
        east_latitude,
        east_longitude,
        origin_latitude_deg=central_latitude,
        origin_longitude_deg=central_longitude,
    )

    unit_central_displacement = mogi_surface_displacement_m(
        0.0,
        0.0,
        source_depth_m=source_depth_m,
        source_radius_m=source_radius_m,
        pressure_change_pa=1.0,
        bulk_modulus_pa=bulk_modulus_pa,
        shear_modulus_pa=shear_modulus_pa,
    )[2]
    pressure_change = central_uplift / unit_central_displacement
    central_prediction = mogi_surface_displacement_m(
        0.0,
        0.0,
        source_depth_m=source_depth_m,
        source_radius_m=source_radius_m,
        pressure_change_pa=pressure_change,
        bulk_modulus_pa=bulk_modulus_pa,
        shear_modulus_pa=shear_modulus_pa,
    )[..., 2]
    east_prediction = mogi_surface_displacement_m(
        east_offset_m,
        north_offset_m,
        source_depth_m=source_depth_m,
        source_radius_m=source_radius_m,
        pressure_change_pa=pressure_change,
        bulk_modulus_pa=bulk_modulus_pa,
        shear_modulus_pa=shear_modulus_pa,
    )[..., 2]
    return MogiBprCalibration(
        times_utc=tuple(valid_times),
        central_uplift_m=central_uplift,
        central_prediction_m=central_prediction,
        east_uplift_m=east_uplift,
        east_prediction_m=east_prediction,
        pressure_change_pa=pressure_change,
        east_residual_m=east_uplift - east_prediction,
        central_quality_codes=central_qc,
        east_quality_codes=east_qc,
        east_offset_east_m=east_offset_m,
        east_offset_north_m=north_offset_m,
        youngs_modulus_pa=youngs_modulus_pa,
        poisson_ratio=poisson_ratio,
        source_radius_m=source_radius_m,
        source_depth_m=source_depth_m,
    )
