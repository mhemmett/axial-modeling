"""Compare raw historical BPR deployment series with a static Mogi response."""

from __future__ import annotations

import math
import statistics
from collections.abc import Mapping
from datetime import date, timedelta

from axialstress.benchmarks import mogi_surface_displacement_m
from axialstress.bpr_mogi_calibration import local_east_north_offset_m
from axialstress.historical_bpr import MINIMUM_WINDOW_DAYS

DEPTH_REFERENCE_OFFSETS_DAYS = range(-7, 0)


def mogi_vertical_response_per_pa(
    east_offset_m: float,
    north_offset_m: float,
    *,
    youngs_modulus_pa: float = 60.0e9,
    poisson_ratio: float = 0.25,
    source_radius_m: float = 700.0,
    source_depth_m: float = 4000.0,
) -> float:
    """Return vertical displacement per unit pressure at one surface point.

    Parameters
    ----------
    east_offset_m, north_offset_m : float
        Horizontal surface offsets from the source axis, in meters.
    youngs_modulus_pa : float
        Assumed homogeneous elastic Young's modulus, in pascals.
    poisson_ratio : float
        Assumed elastic Poisson ratio.
    source_radius_m, source_depth_m : float
        Spherical source radius and positive-down center depth, in meters.

    Returns
    -------
    float
        Vertical uplift per pascal of pressure change, in meters per pascal.
    """
    values = (
        east_offset_m,
        north_offset_m,
        youngs_modulus_pa,
        poisson_ratio,
        source_radius_m,
        source_depth_m,
    )
    if not all(math.isfinite(value) for value in values):
        raise ValueError("Mogi geometry and elastic properties must be finite")
    if youngs_modulus_pa <= 0.0 or source_radius_m <= 0.0 or source_depth_m <= 0.0:
        raise ValueError("Mogi elastic properties and source geometry must be positive")
    if not 0.0 < poisson_ratio < 0.5:
        raise ValueError("Poisson ratio must be in (0, 0.5)")

    shear_modulus_pa = youngs_modulus_pa / (2.0 * (1.0 + poisson_ratio))
    bulk_modulus_pa = youngs_modulus_pa / (3.0 * (1.0 - 2.0 * poisson_ratio))
    return float(
        mogi_surface_displacement_m(
            east_offset_m,
            north_offset_m,
            source_depth_m=source_depth_m,
            source_radius_m=source_radius_m,
            pressure_change_pa=1.0,
            bulk_modulus_pa=bulk_modulus_pa,
            shear_modulus_pa=shear_modulus_pa,
        )[2]
    )


def compare_center_to_south_timeseries(
    center_depth_m: Mapping[date, float],
    south_depth_m: Mapping[date, float],
    *,
    eruption_date: date | None = None,
    center_lat_lon_deg: tuple[float, float],
    south_lat_lon_deg: tuple[float, float],
    youngs_modulus_pa: float = 60.0e9,
    poisson_ratio: float = 0.25,
    source_radius_m: float = 700.0,
    source_depth_m: float = 4000.0,
) -> tuple[list[dict[str, str | float]], dict[str, str | float | int | None]]:
    """Fit daily Center uplift and predict held-out South uplift over overlap.

    Parameters
    ----------
    center_depth_m, south_depth_m : Mapping[date, float]
        Valid daily mean equivalent depths from original raw channels, in
        meters. Dates without sufficient raw sample coverage must be omitted.
    eruption_date : date or None
        Optional event date. When supplied, both station baselines use the
        shared daily samples from seven through one day before the event. When
        omitted, the first seven paired daily samples set the shared baseline.
    center_lat_lon_deg, south_lat_lon_deg : tuple of float
        Station coordinates in WGS84 degrees. The Center station sets the
        source-axis origin.
    youngs_modulus_pa, poisson_ratio : float
        Assumed homogeneous elastic properties.
    source_radius_m, source_depth_m : float
        Assumed spherical source geometry, in meters.

    Returns
    -------
    rows : list of dict
        Daily aligned Center observations, South observations and predictions,
        residuals, and Center-fit pressure changes.
    summary : dict
        Overlap, shared baseline, source assumptions, and South holdout scores.

    Notes
    -----
    Each day is an independent static elastic fit. This calculation has no
    viscoelastic memory, tide removal, ocean correction, or instrument-drift
    correction; it is a time-span cross-check, not a deformation hindcast.
    """
    if not center_depth_m or not south_depth_m:
        raise ValueError("both historical BPR series must contain valid daily means")
    depth_values = (*center_depth_m.values(), *south_depth_m.values())
    if not all(math.isfinite(value) for value in depth_values):
        raise ValueError("historical BPR depths must be finite")

    common_days = sorted(center_depth_m.keys() & south_depth_m.keys())
    if not common_days:
        raise ValueError("the historical BPR series have no overlapping valid days")
    if eruption_date is None:
        baseline_days = common_days[: len(DEPTH_REFERENCE_OFFSETS_DAYS)]
    else:
        baseline_days = [
            eruption_date + timedelta(days=offset)
            for offset in DEPTH_REFERENCE_OFFSETS_DAYS
            if eruption_date + timedelta(days=offset) in center_depth_m
            and eruption_date + timedelta(days=offset) in south_depth_m
        ]
    if len(baseline_days) < MINIMUM_WINDOW_DAYS:
        baseline_description = (
            "shared pre-event baseline"
            if eruption_date is not None
            else "first shared baseline window"
        )
        raise ValueError(f"fewer than five paired daily means occur in the {baseline_description}")

    center_reference_depth_m = statistics.median(
        center_depth_m[day] for day in baseline_days
    )
    south_reference_depth_m = statistics.median(
        south_depth_m[day] for day in baseline_days
    )
    east_offset_m, north_offset_m = local_east_north_offset_m(
        south_lat_lon_deg[0],
        south_lat_lon_deg[1],
        origin_latitude_deg=center_lat_lon_deg[0],
        origin_longitude_deg=center_lat_lon_deg[1],
    )
    center_unit_response_m_per_pa = mogi_vertical_response_per_pa(
        0.0,
        0.0,
        youngs_modulus_pa=youngs_modulus_pa,
        poisson_ratio=poisson_ratio,
        source_radius_m=source_radius_m,
        source_depth_m=source_depth_m,
    )
    south_unit_response_m_per_pa = mogi_vertical_response_per_pa(
        east_offset_m,
        north_offset_m,
        youngs_modulus_pa=youngs_modulus_pa,
        poisson_ratio=poisson_ratio,
        source_radius_m=source_radius_m,
        source_depth_m=source_depth_m,
    )

    rows: list[dict[str, str | float]] = []
    for day in common_days:
        center_uplift_m = center_reference_depth_m - center_depth_m[day]
        south_uplift_m = south_reference_depth_m - south_depth_m[day]
        pressure_change_pa = center_uplift_m / center_unit_response_m_per_pa
        south_prediction_m = pressure_change_pa * south_unit_response_m_per_pa
        rows.append(
            {
                "time_utc": f"{day.isoformat()}T00:00:00Z",
                "center_observed_uplift_m": center_uplift_m,
                "south_observed_uplift_m": south_uplift_m,
                "south_predicted_uplift_m": south_prediction_m,
                "south_residual_m": south_uplift_m - south_prediction_m,
                "center_fit_pressure_change_pa": pressure_change_pa,
            }
        )

    observed = [float(row["south_observed_uplift_m"]) for row in rows]
    predicted = [float(row["south_predicted_uplift_m"]) for row in rows]
    residuals = [float(row["south_residual_m"]) for row in rows]
    rmse_m = math.sqrt(statistics.fmean(residual**2 for residual in residuals))
    bias_m = statistics.fmean(residuals)
    observed_mean = statistics.fmean(observed)
    predicted_mean = statistics.fmean(predicted)
    covariance = statistics.fmean(
        (obs - observed_mean) * (pred - predicted_mean)
        for obs, pred in zip(observed, predicted, strict=True)
    )
    observed_variance = statistics.pvariance(observed)
    predicted_variance = statistics.pvariance(predicted)
    correlation = (
        covariance / math.sqrt(observed_variance * predicted_variance)
        if observed_variance > 0.0 and predicted_variance > 0.0
        else None
    )
    pressures = [float(row["center_fit_pressure_change_pa"]) for row in rows]
    summary: dict[str, str | float | int | None] = {
        "method": "daily static elastic Mogi fit at Center with South held out",
        "eruption_date_utc": (
            None if eruption_date is None else eruption_date.isoformat()
        ),
        "overlap_start_utc": common_days[0].isoformat(),
        "overlap_end_utc": common_days[-1].isoformat(),
        "paired_daily_sample_count": len(rows),
        "baseline_start_utc": baseline_days[0].isoformat(),
        "baseline_end_utc": baseline_days[-1].isoformat(),
        "baseline_paired_day_count": len(baseline_days),
        "baseline_method": (
            "first seven paired days"
            if eruption_date is None
            else "seven days before eruption"
        ),
        "south_rmse_m": rmse_m,
        "south_bias_m": bias_m,
        "south_correlation": correlation,
        "center_fit_pressure_min_pa": min(pressures),
        "center_fit_pressure_max_pa": max(pressures),
        "south_offset_east_m": east_offset_m,
        "south_offset_north_m": north_offset_m,
        "youngs_modulus_pa": youngs_modulus_pa,
        "poisson_ratio_assumed": poisson_ratio,
        "source_radius_m": source_radius_m,
        "source_depth_m": source_depth_m,
        "center_is_calibration_site": True,
        "south_is_held_out_site": True,
        "tide_or_drift_correction_applied": False,
    }
    return rows, summary
