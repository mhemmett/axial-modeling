"""Tests for raw historical Axial BPR observations."""

from __future__ import annotations

import csv
import gzip
from dataclasses import replace
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


def test_mgds_reader_uses_only_the_selected_original_channel(tmp_path, monkeypatch):
    """Keep MGDS drift-corrected columns out of original-channel processing."""
    monkeypatch.setattr(historical_bpr, "RAW_DIR", tmp_path)
    deployment = historical_bpr.Deployment(
        slug="nemo_2010_2011_center",
        station="NeMO 2010–2011 Center",
        filename="center.txt.gz",
        archive="mgds",
        raw_channel="RawDep",
        raw_unit="m",
        depth_factor_m_per_unit=1.0,
        latitude=45.95547,
        longitude=-130.00947,
        eruption_date=date(2011, 4, 6),
    )
    deployment.path.parent.mkdir(parents=True)
    with gzip.open(deployment.path, "wt", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(("Date", "RawDep", "DriftCorrRawDep", "SpotlDep"))
        writer.writerow(("09/05/2010 00:00:00", "1500", "1550", "1550"))
        writer.writerow(("09/05/2010 00:00:15", "1501", "1551", "1551"))

    rows = list(historical_bpr._raw_rows(deployment))

    assert rows == [(date(2010, 9, 5), 1500.0), (date(2010, 9, 5), 1501.0)]


def test_fox_archive_reader_uses_raw_depth_and_ignores_derived_columns(
    tmp_path, monkeypatch
):
    """Read only the original depth samples from the Fox MGDS archive."""
    monkeypatch.setattr(historical_bpr, "RAW_DIR", tmp_path)
    deployment = replace(
        historical_bpr.FOX_1997_1998_DEPLOYMENTS[0],
        filename="center.txt.gz",
        archive="mgds",
    )
    deployment.path.parent.mkdir(parents=True)
    with gzip.open(deployment.path, "wt", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(("Date", "Depth", "Temp", "SpotlDetidedDepth", "LPFDetidedDepth"))
        writer.writerow(("10/03/1997 03:00:00", "1507.478", "3.2", "1600", "1700"))
        writer.writerow(("10/03/1997 03:00:15", "1507.476", "3.2", "1600", "1700"))

    rows = list(historical_bpr._raw_rows(deployment))

    assert rows == [
        (date(1997, 10, 3), 1507.478),
        (date(1997, 10, 3), 1507.476),
    ]


def test_legacy_ncei_coverage_uses_56_25_second_sampling_interval(
    tmp_path, monkeypatch
):
    """Measure legacy NCEI daily coverage against its slower source cadence."""
    monkeypatch.setattr(historical_bpr, "RAW_DIR", tmp_path)
    deployment = historical_bpr.Deployment(
        slug="wc09_1987",
        station="WC09 1987–1988",
        filename="wc09.csv.gz",
        archive="ncei",
        raw_channel="seafloor_pressure_abs_raw [dbar]",
        raw_unit="dbar",
        depth_factor_m_per_unit=historical_bpr.METERS_PER_DBAR,
        latitude=45.979,
        longitude=-129.9903,
        eruption_date=None,
        sampling_interval_s=56.25,
    )
    deployment.path.parent.mkdir(parents=True)
    with gzip.open(deployment.path, "wt", encoding="utf-8", newline="") as stream:
        stream.write("// datetime [ISO8601], seafloor_pressure_abs_raw [dbar], temperature [K]\n")
        writer = csv.writer(stream, delimiter="\t")
        for day, pressure in ((date(1987, 9, 23), 1555.0), (date(1987, 9, 24), 1556.0)):
            start = datetime.combine(day, datetime.min.time(), tzinfo=UTC)
            for sample in range(1536):
                stamp = start + timedelta(seconds=sample * 56.25)
                writer.writerow((stamp.isoformat().replace("+00:00", "Z"), pressure, 276.9))

    observations = historical_bpr.process_deployment(deployment)

    assert [row.day for row in observations] == [date(1987, 9, 23), date(1987, 9, 24)]
    assert all(row.sample_count == 1536 for row in observations)
    assert all(row.coverage_fraction == pytest.approx(1.0) for row in observations)


def test_raw_source_comparison_aligns_daily_series_to_shared_baseline():
    """Compare archive copies after removing their independent depth offsets."""
    days = [date(1998, 1, 1) + timedelta(days=offset) for offset in range(5)]
    reference = [
        historical_bpr.DailyObservation(day, 1500.0 + offset, 1500.0 + offset, 0.0, 4320, 4320.0)
        for offset, day in enumerate(days)
    ]
    comparison = [
        historical_bpr.DailyObservation(day, 2500.0 + offset, 2500.0 + offset, 0.0, 4320, 4320.0)
        for offset, day in enumerate(days)
    ]

    result = historical_bpr.compare_raw_deployment_sources(
        reference,
        comparison,
        reference_station="NCEI",
        comparison_station="MGDS",
    )

    assert result["shared_daily_means"] == 5
    assert result["comparison_minus_reference_bias_m"] == pytest.approx(0.0)
    assert result["comparison_minus_reference_rmse_m"] == pytest.approx(0.0)
    assert result["relative_uplift_correlation"] == pytest.approx(1.0)
