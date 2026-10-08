"""Synthetic tests for the OOI BPR retrieval and uplift conversion."""

import csv
import datetime as dt
import gzip

import numpy as np
import pytest
from data.fetch_bpr import erddap_url
from data.process_bpr import process_file, relative_uplift


def test_erddap_url_requests_daily_depth_and_qc_for_inclusive_dates() -> None:
    url = erddap_url(
        "ooi-rs03ccal-mj03f-05-botpta301",
        start=dt.date(2015, 1, 1),
        end=dt.date(2015, 1, 31),
    )
    assert "botsflu_daydepth" in url
    assert "botsflu_daydepth_qc_agg" in url
    assert "2015-01-01T00:00:00Z" in url
    assert "2015-01-31T23:59:59Z" in url
    assert "botsflu_daydepth%21%3DNaN" in url


def test_relative_uplift_uses_up_positive_signed_depth() -> None:
    uplift = relative_uplift([-1510.0, -1509.8, -1510.2])
    np.testing.assert_allclose(uplift, [0.0, 0.2, -0.2])


def test_relative_uplift_rejects_all_missing_depths() -> None:
    with pytest.raises(ValueError, match="no finite values"):
        relative_uplift([np.nan, np.inf])


def test_process_file_preserves_daily_qc_flags(tmp_path) -> None:
    source = tmp_path / "input.csv.gz"
    with gzip.open(source, "wt", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(
            [
                "time (UTC)",
                "botsflu_daydepth (m)",
                "botsflu_daydepth_qc_agg",
            ]
        )
        writer.writerow(["2016-01-01T00:00:00Z", "-1510.0", "2"])
        writer.writerow(["2016-01-02T00:00:00Z", "-1509.8", "3"])

    output = tmp_path / "relative.csv"
    assert process_file(source, output) == 2
    with output.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    assert rows[0]["relative_uplift_m"] == "0"
    assert float(rows[1]["relative_uplift_m"]) == pytest.approx(0.2)
    assert [row["ooi_qc_aggregate"] for row in rows] == ["2", "3"]
