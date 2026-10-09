"""Tests for raw historical Axial BPR observations."""

from __future__ import annotations

import csv
import gzip
from datetime import UTC, date, datetime, timedelta

import pytest

from axialstress import historical_bpr


def test_ncei_pressure_is_aggregated_and_converted_to_relative_elevation(
    tmp_path, monkeypatch
):
    """Convert daily NCEI dbar means to relative elevation in meters."""
    monkeypatch.setattr(historical_bpr, "RAW_DIR", tmp_path)
    deployment = historical_bpr.Deployment(
        slug="nemo_2000_center",
        station="NeMO 2000 Center",
        filename="nemo_20000706to20010801.csv.gz",
        archive="ncei",
        raw_channel="seafloor_pressure_abs_raw [dbar]",
        raw_unit="dbar",
        depth_factor_m_per_unit=historical_bpr.METERS_PER_DBAR,
        latitude=45.95522,
        longitude=-130.01017,
        eruption_date=None,
    )
    deployment.path.parent.mkdir(parents=True)
    with gzip.open(deployment.path, "wt", encoding="utf-8", newline="") as stream:
        stream.write("// datetime [ISO8601], seafloor_pressure_abs_raw [dbar], temperature [K]\n")
        writer = csv.writer(stream, delimiter="\t")
        for day, pressure in ((date(2000, 7, 6), 1558.0), (date(2000, 7, 7), 1559.0)):
            start = datetime.combine(day, datetime.min.time(), tzinfo=UTC)
            for sample in range(4320):
                stamp = start + timedelta(seconds=sample * 15)
                writer.writerow((stamp.isoformat().replace("+00:00", "Z"), pressure, 276.9))

    observations = historical_bpr.process_deployment(deployment)

    assert [row.day for row in observations] == [date(2000, 7, 6), date(2000, 7, 7)]
    assert observations[0].relative_uplift_m == pytest.approx(0.0)
    assert observations[1].relative_uplift_m == pytest.approx(
        -historical_bpr.METERS_PER_DBAR
    )
    assert all(row.sample_count == 4320 for row in observations)
