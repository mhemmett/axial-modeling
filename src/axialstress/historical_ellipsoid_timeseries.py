"""Compare raw historical BPR overlaps with a static PyLith ellipsoid response."""

from __future__ import annotations

import math
import statistics
from collections.abc import Mapping
from datetime import date

from axialstress.historical_bpr import MINIMUM_WINDOW_DAYS

BASELINE_DAYS = 7


def compare_center_to_south_ellipsoid_timeseries(
    center_depth_m: Mapping[date, float],
    south_depth_m: Mapping[date, float],
    *,
    center_unit_response_m_per_mpa: float,
    south_unit_response_m_per_mpa: float,
) -> tuple[list[dict[str, str | float]], dict[str, str | float | int | None]]:
    """Fit daily Center uplift and predict held-out South uplift.

    Parameters
    ----------
    center_depth_m, south_depth_m : Mapping[datetime.date, float]
        Valid daily equivalent depths from original raw channels, in meters.
    center_unit_response_m_per_mpa, south_unit_response_m_per_mpa : float
        Vertical PyLith displacement for a 1 MPa reservoir pressure increment,
        in meters per megapascal.

    Returns
    -------
    rows : list of dict
        Aligned daily observations, Center-fit pressure, South prediction, and
        South residual.
    summary : dict
        Shared baseline, overlap, pressure range, and held-out South metrics.

    Notes
    -----
    Each day is an independent static elastic fit. The calculation does not
    remove tides or drift and does not include viscoelastic memory.
    """
    if not center_depth_m or not south_depth_m:
        raise ValueError("both historical BPR series must contain valid daily means")
    if not all(
        math.isfinite(value)
        for value in (*center_depth_m.values(), *south_depth_m.values())
    ):
        raise ValueError("historical BPR depths must be finite")
    if (
        not math.isfinite(center_unit_response_m_per_mpa)
        or center_unit_response_m_per_mpa <= 0.0
        or not math.isfinite(south_unit_response_m_per_mpa)
        or south_unit_response_m_per_mpa <= 0.0
    ):
        raise ValueError("Center and South unit responses must be finite and positive")

    common_days = sorted(center_depth_m.keys() & south_depth_m.keys())
    if len(common_days) < MINIMUM_WINDOW_DAYS:
        raise ValueError("fewer than five paired daily means occur in the deployment overlap")
    baseline_days = common_days[:BASELINE_DAYS]
    center_reference_m = statistics.median(center_depth_m[day] for day in baseline_days)
    south_reference_m = statistics.median(south_depth_m[day] for day in baseline_days)

    rows: list[dict[str, str | float]] = []
    for day in common_days:
        center_uplift_m = center_reference_m - center_depth_m[day]
        south_uplift_m = south_reference_m - south_depth_m[day]
        pressure_change_mpa = center_uplift_m / center_unit_response_m_per_mpa
        south_prediction_m = pressure_change_mpa * south_unit_response_m_per_mpa
        rows.append(
            {
                "time_utc": f"{day.isoformat()}T00:00:00Z",
                "center_observed_uplift_m": center_uplift_m,
                "center_fit_pressure_change_mpa": pressure_change_mpa,
                "south_observed_uplift_m": south_uplift_m,
                "south_predicted_uplift_m": south_prediction_m,
                "south_residual_m": south_uplift_m - south_prediction_m,
            }
        )

    observed = [float(row["south_observed_uplift_m"]) for row in rows]
    predicted = [float(row["south_predicted_uplift_m"]) for row in rows]
    residuals = [float(row["south_residual_m"]) for row in rows]
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
    pressures = [float(row["center_fit_pressure_change_mpa"]) for row in rows]
    summary: dict[str, str | float | int | None] = {
        "method": "daily static PyLith ellipsoid fit at Center with South held out",
        "overlap_start_utc": common_days[0].isoformat(),
        "overlap_end_utc": common_days[-1].isoformat(),
        "paired_daily_sample_count": len(rows),
        "baseline_start_utc": baseline_days[0].isoformat(),
        "baseline_end_utc": baseline_days[-1].isoformat(),
        "baseline_paired_day_count": len(baseline_days),
        "baseline_method": "first up to seven paired days",
        "center_unit_response_m_per_mpa": center_unit_response_m_per_mpa,
        "south_unit_response_m_per_mpa": south_unit_response_m_per_mpa,
        "center_fit_pressure_min_mpa": min(pressures),
        "center_fit_pressure_max_mpa": max(pressures),
        "south_rmse_m": math.sqrt(statistics.fmean(residual**2 for residual in residuals)),
        "south_bias_m": statistics.fmean(residuals),
        "south_correlation": correlation,
        "center_is_calibration_site": True,
        "south_is_held_out_site": True,
        "static_elastic_memory_included": False,
        "tide_or_drift_correction_applied": False,
    }
    return rows, summary
