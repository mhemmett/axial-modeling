"""Checks for monthly OOI pressure histories passed to PyLith."""

from datetime import UTC, datetime

import numpy as np
import pytest

from axialstress.ooi_pressure_history import (
    SECONDS_PER_YEAR,
    read_monthly_ooi_pressure_history,
    write_normalized_time_history,
)


def test_monthly_history_preserves_qc_and_writes_pressure_amplitudes(tmp_path) -> None:
    calibration = tmp_path / "calibration.csv"
    calibration.write_text(
        "time_utc,central_relative_uplift_m,central_elastic_fit_m,"
        "east_relative_uplift_m,east_elastic_prediction_m,east_residual_m,"
        "inferred_pressure_change_mpa,central_ooi_qc_aggregate,east_ooi_qc_aggregate\n"
        "2020-01-01T00:00:00Z,0,0,0,0,0,0,2,2\n"
        "2020-01-16T00:00:00Z,1,1,0.5,0.5,0,2,2,2\n"
        "2020-02-01T00:00:00Z,2,2,1,1,0,4,3,2\n"
        "2020-02-15T00:00:00Z,4,4,2,2,0,8,3,2\n",
        encoding="utf-8",
    )

    history = read_monthly_ooi_pressure_history(calibration)

    assert history.times_utc == (
        datetime(2020, 1, 1, tzinfo=UTC),
        datetime(2020, 1, 31, tzinfo=UTC),
        datetime(2020, 2, 29, tzinfo=UTC),
    )
    np.testing.assert_allclose(history.pressure_change_mpa, [0.0, 1.0, 6.0])
    np.testing.assert_allclose(history.central_uplift_m, [0.0, 0.5, 3.0])
    np.testing.assert_allclose(history.east_uplift_m, [0.0, 0.25, 1.5])
    assert history.monthly_record_counts == (1, 2, 2)
    assert history.central_qc_codes == ("2", "3")
    assert history.east_qc_codes == ("2",)
    assert history.elapsed_years[-1] == pytest.approx(59.0 * 86400.0 / SECONDS_PER_YEAR)

    time_history_path = tmp_path / "pressure.timedb"
    write_normalized_time_history(time_history_path, history)
    content = time_history_path.read_text(encoding="utf-8")
    assert "num-points = 3" in content
    assert "time-units = year" in content
    assert content.splitlines()[-1].endswith(" 6")
