"""Synthetic checks for historical Center-fit ellipsoid comparisons."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from axialstress.historical_ellipsoid_timeseries import (
    compare_center_to_south_ellipsoid_timeseries,
)


def test_recovers_synthetic_daily_ellipsoid_response() -> None:
    start = date(2003, 6, 1)
    center_response = 0.03
    south_response = 0.005
    center_depth = {}
    south_depth = {}
    for day_offset in range(14):
        day = start + timedelta(days=day_offset)
        pressure_mpa = max(day_offset - 6, 0) * 0.5
        center_depth[day] = 1500.0 - pressure_mpa * center_response
        south_depth[day] = 1550.0 - pressure_mpa * south_response

    rows, summary = compare_center_to_south_ellipsoid_timeseries(
        center_depth,
        south_depth,
        center_unit_response_m_per_mpa=center_response,
        south_unit_response_m_per_mpa=south_response,
    )

    assert len(rows) == 14
    assert summary["baseline_paired_day_count"] == 7
    assert summary["baseline_method"] == "first up to seven paired days"
    assert summary["south_rmse_m"] == pytest.approx(0.0, abs=1.0e-12)
    assert summary["south_correlation"] == pytest.approx(1.0)
    assert rows[-1]["center_fit_pressure_change_mpa"] == pytest.approx(3.5)


def test_allows_five_day_overlap_and_reports_actual_baseline_length() -> None:
    start = date(2011, 1, 1)
    days = {start + timedelta(days=offset): 1500.0 for offset in range(5)}

    _, summary = compare_center_to_south_ellipsoid_timeseries(
        days,
        days,
        center_unit_response_m_per_mpa=0.03,
        south_unit_response_m_per_mpa=0.005,
    )

    assert summary["baseline_paired_day_count"] == 5


def test_requires_positive_finite_unit_responses() -> None:
    day = date(2011, 1, 1)
    depths = {day: 1500.0}

    with pytest.raises(ValueError, match="unit responses"):
        compare_center_to_south_ellipsoid_timeseries(
            depths,
            depths,
            center_unit_response_m_per_mpa=0.0,
            south_unit_response_m_per_mpa=0.005,
        )
