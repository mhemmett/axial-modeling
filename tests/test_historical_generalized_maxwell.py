from datetime import date, timedelta

import numpy as np
import pytest

from axialstress.historical_generalized_maxwell import (
    compare_model_history,
    prepare_center_fit_pressure_history,
)


def test_center_fit_history_uses_shared_days_and_starts_at_zero() -> None:
    start = date(1998, 1, 1)
    center = {start + timedelta(days=day): 100.0 - 0.01 * day for day in range(6)}
    south = {start + timedelta(days=day): 200.0 - 0.004 * day for day in range(1, 7)}
    history = prepare_center_fit_pressure_history(
        center,
        south,
        center_compliance_m_per_mpa=0.02,
    )

    assert history.dates_utc[0] == start + timedelta(days=1)
    assert len(history.dates_utc) == 5
    assert history.elapsed_seconds[0] == 0.0
    assert history.elapsed_seconds[-1] == 4 * 86_400.0
    assert history.center_uplift_m[0] == 0.0
    assert history.south_uplift_m[0] == 0.0
    assert history.pressure_change_mpa[0] == 0.0
    assert history.pressure_change_mpa[-1] == pytest.approx(2.0)


def test_history_comparison_interpolates_to_observation_days() -> None:
    start = date(2011, 1, 1)
    dates = [start + timedelta(days=day) for day in range(5)]
    center = {day: 100.0 - 0.01 * index for index, day in enumerate(dates)}
    south = {day: 200.0 - 0.005 * index for index, day in enumerate(dates)}
    history = prepare_center_fit_pressure_history(
        center,
        south,
        center_compliance_m_per_mpa=0.01,
    )
    model_times = np.asarray([0.0, 2.0 * 86_400.0, 4.0 * 86_400.0])
    model_center = np.asarray([0.0, 0.02, 0.04])
    model_south = np.asarray([0.0, 0.01, 0.02])

    rows, summary = compare_model_history(
        history,
        model_times,
        model_center,
        model_south,
    )

    assert len(rows) == 5
    assert rows[1]["center_model_uplift_m"] == pytest.approx(0.01)
    assert rows[3]["south_model_uplift_m"] == pytest.approx(0.015)
    assert summary["center"]["rmse_m"] == pytest.approx(0.0)
    assert summary["south"]["rmse_m"] == pytest.approx(0.0)


def test_history_rejects_invalid_compliance_or_short_overlap() -> None:
    start = date(2011, 1, 1)
    series = {start + timedelta(days=day): float(day) for day in range(5)}
    with pytest.raises(ValueError, match="compliance"):
        prepare_center_fit_pressure_history(
            series,
            series,
            center_compliance_m_per_mpa=0.0,
        )
    with pytest.raises(ValueError, match="five paired"):
        prepare_center_fit_pressure_history(
            {start: 1.0},
            {start: 1.0},
            center_compliance_m_per_mpa=1.0,
        )
