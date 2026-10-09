"""Tests for subdaily checks from original historical BPR channels."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime, timedelta

import pytest

from axialstress import historical_bpr_subdaily_events


def test_hourly_event_series_uses_original_samples_and_coverage_threshold(
    monkeypatch,
):
    """Retain hourly raw medians and use a station-specific pre-event baseline."""
    event_date = date(1998, 1, 25)
    deployment = replace(
        historical_bpr_subdaily_events.DEPLOYMENTS[10],
        archive="ncei",
        depth_factor_m_per_unit=1.0,
        sampling_interval_s=900.0,
    )
    source_rows = []
    missing_hour = datetime(1998, 1, 22, 0, tzinfo=UTC)
    for day_offset in range(-21, 22):
        sample_day = event_date + timedelta(days=day_offset)
        depth = 97.0 if day_offset >= 8 else 100.0
        for hour in range(24):
            hour_start = datetime.combine(sample_day, datetime.min.time(), tzinfo=UTC)
            hour_start += timedelta(hours=hour)
            count = 2 if hour_start == missing_hour else 3
            for sample in range(count):
                stamp = hour_start + timedelta(minutes=sample * 15)
                source_rows.append((stamp.isoformat().replace("+00:00", "Z"), depth))

    monkeypatch.setattr(
        historical_bpr_subdaily_events,
        "iter_raw_samples",
        lambda _deployment: iter(source_rows),
    )

    observations = historical_bpr_subdaily_events.hourly_event_observations(
        deployment,
        event_date=event_date,
    )

    assert len(observations) == 43 * 24 - 1
    assert observations[0].coverage_fraction == pytest.approx(0.75)
    assert observations[0].relative_uplift_m == pytest.approx(0.0)
    post_event = [row for row in observations if (row.time_utc.date() - event_date).days == 8]
    assert len(post_event) == 24
    assert all(row.relative_uplift_m == pytest.approx(3.0) for row in post_event)


def test_mgds_timestamp_is_interpreted_as_utc():
    """Parse the original MGDS timestamp format without clock adjustment."""
    stamp = historical_bpr_subdaily_events._parse_timestamp(
        "04/06/2011 12:15:30",
        "mgds",
    )

    assert stamp == datetime(2011, 4, 6, 12, 15, 30, tzinfo=UTC)
