"""Prepare provisional pressure forcing and compare historical Maxwell output."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]
SECONDS_PER_DAY = 86_400.0
SECONDS_PER_YEAR = 365.25 * SECONDS_PER_DAY


@dataclass(frozen=True)
class HistoricalPressureHistory:
    """Aligned raw observations and center-fit pressure for one event window."""

    dates_utc: tuple[date, ...]
    elapsed_seconds: FloatArray
    center_uplift_m: FloatArray
    south_uplift_m: FloatArray
    pressure_change_mpa: FloatArray


@dataclass(frozen=True)
class HistoricalPressureForcing:
    """A center-fit pressure history spanning multiple BPR deployments."""

    dates_utc: tuple[date, ...]
    elapsed_seconds: FloatArray
    pressure_change_mpa: FloatArray
    transition_gap_days: int


def prepare_contiguous_center_pressure_forcing(
    first_center_depth_m: Mapping[date, float],
    second_center_depth_m: Mapping[date, float],
    *,
    center_compliance_m_per_mpa: float,
    maximum_transition_gap_days: int = 7,
) -> HistoricalPressureForcing:
    """Stitch same-site BPR segments while holding pressure constant across a short gap.

    Each instrument segment has an independent pressure-depth reference. The
    second segment's first value is placed at the final pressure of the first
    segment; missing transition days therefore receive a constant-pressure
    continuation when PyLith interpolates the time history.
    """
    if not first_center_depth_m or not second_center_depth_m:
        raise ValueError("both center deployments must contain daily depths")
    if (
        not math.isfinite(center_compliance_m_per_mpa)
        or center_compliance_m_per_mpa <= 0.0
    ):
        raise ValueError("Center compliance must be finite and positive")
    if maximum_transition_gap_days < 1:
        raise ValueError("maximum transition gap must be at least one day")
    if not all(
        math.isfinite(value)
        for value in (*first_center_depth_m.values(), *second_center_depth_m.values())
    ):
        raise ValueError("daily BPR depths must be finite")

    first_dates = tuple(sorted(first_center_depth_m))
    second_dates = tuple(sorted(second_center_depth_m))
    if first_dates[-1] >= second_dates[0]:
        raise ValueError("center deployments must be nonoverlapping and ordered")
    transition_gap_days = (second_dates[0] - first_dates[-1]).days
    if transition_gap_days > maximum_transition_gap_days:
        raise ValueError(
            "center deployment transition exceeds the maximum constant-pressure gap"
        )

    first_reference_m = float(first_center_depth_m[first_dates[0]])
    first_pressure_mpa = np.asarray(
        [
            (first_reference_m - first_center_depth_m[day])
            / center_compliance_m_per_mpa
            for day in first_dates
        ],
        dtype=float,
    )
    second_reference_m = float(second_center_depth_m[second_dates[0]])
    second_pressure_mpa = first_pressure_mpa[-1] + np.asarray(
        [
            (second_reference_m - second_center_depth_m[day])
            / center_compliance_m_per_mpa
            for day in second_dates
        ],
        dtype=float,
    )
    dates = (*first_dates, *second_dates)
    pressure_change_mpa = np.concatenate(
        (first_pressure_mpa, second_pressure_mpa)
    )
    elapsed_seconds = np.asarray(
        [(day - first_dates[0]).days * SECONDS_PER_DAY for day in dates],
        dtype=float,
    )
    if (
        not np.all(np.isfinite(elapsed_seconds))
        or not np.all(np.isfinite(pressure_change_mpa))
        or np.any(np.diff(elapsed_seconds) <= 0.0)
    ):
        raise ValueError("stitched pressure history must be finite and increasing")
    return HistoricalPressureForcing(
        dates_utc=dates,
        elapsed_seconds=elapsed_seconds,
        pressure_change_mpa=pressure_change_mpa,
        transition_gap_days=transition_gap_days,
    )


def prepare_center_fit_pressure_history(
    center_depth_m: Mapping[date, float],
    south_depth_m: Mapping[date, float],
    *,
    center_compliance_m_per_mpa: float,
) -> HistoricalPressureHistory:
    """Infer a daily pressure history from raw Center depth and static compliance.

    The first shared valid daily measurement defines zero displacement and
    zero pressure at the start of the PyLith run. The inverse uses the static
    elastic Center compliance, so it is an imposed diagnostic history rather
    than a viscoelastic calibration.
    """
    if not center_depth_m or not south_depth_m:
        raise ValueError("Center and South series must contain daily depths")
    if (
        not math.isfinite(center_compliance_m_per_mpa)
        or center_compliance_m_per_mpa <= 0.0
    ):
        raise ValueError("Center compliance must be finite and positive")
    depths = (*center_depth_m.values(), *south_depth_m.values())
    if not all(math.isfinite(value) for value in depths):
        raise ValueError("daily BPR depths must be finite")

    dates = tuple(sorted(center_depth_m.keys() & south_depth_m.keys()))
    if len(dates) < 5:
        raise ValueError("at least five paired daily means are required")
    first_date = dates[0]
    center_reference_m = float(center_depth_m[first_date])
    south_reference_m = float(south_depth_m[first_date])
    center_uplift_m = np.asarray(
        [center_reference_m - center_depth_m[day] for day in dates], dtype=float
    )
    south_uplift_m = np.asarray(
        [south_reference_m - south_depth_m[day] for day in dates], dtype=float
    )
    elapsed_seconds = np.asarray(
        [(day - first_date).days * SECONDS_PER_DAY for day in dates], dtype=float
    )
    pressure_change_mpa = center_uplift_m / center_compliance_m_per_mpa
    if (
        not np.all(np.isfinite(elapsed_seconds))
        or not np.all(np.isfinite(center_uplift_m))
        or not np.all(np.isfinite(south_uplift_m))
        or not np.all(np.isfinite(pressure_change_mpa))
        or np.any(np.diff(elapsed_seconds) <= 0.0)
    ):
        raise ValueError("paired historical pressure history is not finite and increasing")

    return HistoricalPressureHistory(
        dates_utc=dates,
        elapsed_seconds=elapsed_seconds,
        center_uplift_m=center_uplift_m,
        south_uplift_m=south_uplift_m,
        pressure_change_mpa=pressure_change_mpa,
    )


def compare_model_history(
    history: HistoricalPressureHistory,
    model_times_seconds: FloatArray,
    model_center_uplift_m: FloatArray,
    model_south_uplift_m: FloatArray,
) -> tuple[list[dict[str, str | float]], dict[str, object]]:
    """Interpolate model output to paired raw days and summarize residuals."""
    model_times = np.asarray(model_times_seconds, dtype=float)
    model_center = np.asarray(model_center_uplift_m, dtype=float)
    model_south = np.asarray(model_south_uplift_m, dtype=float)
    expected_shape = model_times.shape
    if (
        model_times.ndim != 1
        or len(model_times) < 2
        or model_center.shape != expected_shape
        or model_south.shape != expected_shape
        or not np.all(np.isfinite(model_times))
        or not np.all(np.isfinite(model_center))
        or not np.all(np.isfinite(model_south))
        or np.any(np.diff(model_times) <= 0.0)
    ):
        raise ValueError("model histories must be finite, matched, and increasing")
    if history.elapsed_seconds[0] < model_times[0] or history.elapsed_seconds[-1] > model_times[-1]:
        raise ValueError("model output must cover every paired BPR day")

    center_prediction = np.interp(history.elapsed_seconds, model_times, model_center)
    south_prediction = np.interp(history.elapsed_seconds, model_times, model_south)
    center_residual = center_prediction - history.center_uplift_m
    south_residual = south_prediction - history.south_uplift_m
    rows = [
        {
            "time_utc": f"{day.isoformat()}T00:00:00Z",
            "pressure_change_mpa": float(pressure),
            "center_observed_uplift_m": float(center_observed),
            "center_model_uplift_m": float(center_model_value),
            "center_residual_m": float(center_error),
            "south_observed_uplift_m": float(south_observed),
            "south_model_uplift_m": float(south_model_value),
            "south_residual_m": float(south_error),
        }
        for day, pressure, center_observed, center_model_value, center_error,
        south_observed, south_model_value, south_error in zip(
            history.dates_utc,
            history.pressure_change_mpa,
            history.center_uplift_m,
            center_prediction,
            center_residual,
            history.south_uplift_m,
            south_prediction,
            south_residual,
            strict=True,
        )
    ]

    def metrics(
        residual: FloatArray, observed: FloatArray, predicted: FloatArray
    ) -> dict[str, float | None]:
        correlation = (
            float(np.corrcoef(observed, predicted)[0, 1])
            if np.std(observed) > 0.0 and np.std(predicted) > 0.0
            else None
        )
        return {
            "rmse_m": float(np.sqrt(np.mean(residual**2))),
            "bias_m": float(np.mean(residual)),
            "correlation": correlation,
        }

    summary = {
        "paired_daily_sample_count": len(history.dates_utc),
        "overlap_start_utc": history.dates_utc[0].isoformat(),
        "overlap_end_utc": history.dates_utc[-1].isoformat(),
        "pressure_change_range_mpa": [
            float(np.min(history.pressure_change_mpa)),
            float(np.max(history.pressure_change_mpa)),
        ],
        "center": metrics(center_residual, history.center_uplift_m, center_prediction),
        "south": metrics(south_residual, history.south_uplift_m, south_prediction),
    }
    return rows, summary
