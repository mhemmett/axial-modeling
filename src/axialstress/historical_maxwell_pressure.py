"""Prepare raw historical BPR pairs for Maxwell-kernel pressure inversion."""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]
DAILY_HEADER = (
    "time_utc",
    "raw_channel_mean",
    "raw_channel_unit",
    "equivalent_depth_m",
    "relative_uplift_m",
    "sample_count",
    "coverage_fraction",
)
CORRECTED_DAILY_HEADER = (
    "time_utc",
    "corrected_source_channel",
    "correction_components",
    "corrected_channel_mean",
    "channel_unit",
    "equivalent_depth_m",
    "relative_uplift_m",
    "sample_count",
    "expected_samples_per_day",
    "coverage_fraction",
)
SECONDS_PER_DAY = 86_400.0
SECONDS_PER_YEAR = 365.25 * SECONDS_PER_DAY
MINIMUM_DAILY_COVERAGE = 0.75


@dataclass(frozen=True)
class HistoricalMaxwellHistory:
    """Aligned, uniformly sampled historical BPR uplift observations."""

    times_utc: tuple[datetime, ...]
    elapsed_years: FloatArray
    pressure_change_mpa: FloatArray
    center_uplift_m: FloatArray
    south_uplift_m: FloatArray
    center_station: str
    south_station: str
    center_lat_lon_deg: tuple[float, float]
    south_lat_lon_deg: tuple[float, float]
    paired_daily_samples: int
    maximum_observation_gap_days: int

    @property
    def time_step_s(self) -> float:
        """Return the common, uniform time step in seconds."""
        return float(np.diff(self.elapsed_years)[0] * SECONDS_PER_YEAR)


def read_raw_daily_depths(
    path: str | Path, *, expected_unit: str
) -> dict[date, float]:
    """Read covered daily depths from a raw or corrected BPR channel."""
    daily_depths: dict[date, float] = {}
    with Path(path).open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        fieldnames = tuple(reader.fieldnames or ())
        if fieldnames == DAILY_HEADER:
            unit_column = "raw_channel_unit"
        elif fieldnames == CORRECTED_DAILY_HEADER:
            unit_column = "channel_unit"
        else:
            raise ValueError(f"unexpected BPR daily columns in {path}")
        for row_number, row in enumerate(reader, start=2):
            try:
                timestamp = datetime.fromisoformat(row["time_utc"].replace("Z", "+00:00"))
                unit = row[unit_column]
                depth_m = float(row["equivalent_depth_m"])
                coverage = float(row["coverage_fraction"])
                has_valid_uplift = bool(row["relative_uplift_m"].strip())
            except (AttributeError, KeyError, TypeError, ValueError) as exc:
                raise ValueError(f"invalid raw BPR daily row {row_number} in {path}") from exc
            if timestamp.tzinfo is None or timestamp.utcoffset() != UTC.utcoffset(timestamp):
                raise ValueError(f"raw BPR daily timestamps must be UTC in {path}")
            if any((timestamp.hour, timestamp.minute, timestamp.second, timestamp.microsecond)):
                raise ValueError(f"raw BPR daily timestamps must be at midnight in {path}")
            if unit != expected_unit:
                raise ValueError(
                    f"expected BPR channel in {expected_unit}, found {unit!r} in {path}"
                )
            if not math.isfinite(depth_m) or not math.isfinite(coverage):
                raise ValueError(f"non-finite raw BPR daily values in {path}")
            if coverage < MINIMUM_DAILY_COVERAGE or not has_valid_uplift:
                continue
            day = timestamp.date()
            if day in daily_depths:
                raise ValueError(f"duplicate raw BPR daily date {day} in {path}")
            daily_depths[day] = depth_m
    if not daily_depths:
        raise ValueError(f"no covered raw BPR daily means in {path}")
    return daily_depths


def prepare_historical_maxwell_history(
    center_depth_m: dict[date, float],
    south_depth_m: dict[date, float],
    *,
    center_station: str,
    south_station: str,
    center_lat_lon_deg: tuple[float, float],
    south_lat_lon_deg: tuple[float, float],
    target_interval_days: float = 7.0,
) -> HistoricalMaxwellHistory:
    """Align raw BPR deployments and interpolate them to a uniform weekly grid."""
    if not center_depth_m or not south_depth_m:
        raise ValueError("Center and South raw BPR series must not be empty")
    if not math.isfinite(target_interval_days) or target_interval_days <= 0.0:
        raise ValueError("target interval must be finite and positive")
    if not all(
        math.isfinite(value)
        for value in (*center_depth_m.values(), *south_depth_m.values())
    ):
        raise ValueError("raw BPR daily depth values must be finite")

    paired_days = tuple(sorted(center_depth_m.keys() & south_depth_m.keys()))
    if len(paired_days) < 5:
        raise ValueError("at least five paired raw BPR days are required")
    start_day = paired_days[0]
    duration_s = (paired_days[-1] - start_day).days * SECONDS_PER_DAY
    if duration_s <= 0.0:
        raise ValueError("paired raw BPR observations must span a positive interval")
    interval_count = max(
        5, int(round(duration_s / (target_interval_days * SECONDS_PER_DAY)))
    )
    time_step_s = duration_s / interval_count
    elapsed_seconds = np.linspace(0.0, duration_s, interval_count + 1, dtype=float)
    elapsed_years = elapsed_seconds / SECONDS_PER_YEAR
    dates_elapsed_s = np.asarray(
        [(day - start_day).days * SECONDS_PER_DAY for day in paired_days], dtype=float
    )
    center_reference_m = center_depth_m[start_day]
    south_reference_m = south_depth_m[start_day]
    center_paired_uplift_m = np.asarray(
        [center_reference_m - center_depth_m[day] for day in paired_days], dtype=float
    )
    south_paired_uplift_m = np.asarray(
        [south_reference_m - south_depth_m[day] for day in paired_days], dtype=float
    )
    grid_center_uplift_m = np.interp(
        elapsed_seconds, dates_elapsed_s, center_paired_uplift_m
    )
    grid_south_uplift_m = np.interp(
        elapsed_seconds, dates_elapsed_s, south_paired_uplift_m
    )
    times_utc = tuple(
        datetime.combine(start_day, datetime.min.time(), tzinfo=UTC)
        + timedelta(seconds=float(seconds))
        for seconds in elapsed_seconds
    )
    max_gap_days = max(
        (later - earlier).days
        for earlier, later in zip(paired_days, paired_days[1:], strict=False)
    )
    if not np.allclose(np.diff(elapsed_seconds), time_step_s, rtol=0.0, atol=1.0e-6):
        raise RuntimeError("historical Maxwell inversion grid is not uniform")

    return HistoricalMaxwellHistory(
        times_utc=times_utc,
        elapsed_years=elapsed_years,
        pressure_change_mpa=np.zeros(interval_count + 1, dtype=float),
        center_uplift_m=grid_center_uplift_m,
        south_uplift_m=grid_south_uplift_m,
        center_station=center_station,
        south_station=south_station,
        center_lat_lon_deg=center_lat_lon_deg,
        south_lat_lon_deg=south_lat_lon_deg,
        paired_daily_samples=len(paired_days),
        maximum_observation_gap_days=max_gap_days,
    )
