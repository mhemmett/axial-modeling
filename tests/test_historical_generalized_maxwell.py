from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pytest
from scripts.historical_generalized_maxwell_bpr_check import (
    INITIAL_DT_S,
    SECONDS_PER_YEAR,
    _write_pressure_history,
)

from axialstress.historical_generalized_maxwell import (
    compare_model_history,
    prepare_center_fit_pressure_history,
    prepare_contiguous_center_pressure_forcing,
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


def test_contiguous_pressure_forcing_carries_terminal_pressure_across_gap() -> None:
    start = date(2011, 1, 1)
    first = {
        start + timedelta(days=day): depth
        for day, depth in enumerate((100.0, 99.98, 100.02))
    }
    second_start = start + timedelta(days=7)
    second = {
        second_start + timedelta(days=day): depth
        for day, depth in enumerate((200.0, 199.98, 200.0))
    }

    history = prepare_contiguous_center_pressure_forcing(
        first,
        second,
        center_compliance_m_per_mpa=0.02,
    )

    assert history.transition_gap_days == 5
    assert history.dates_utc[0] == start
    assert history.dates_utc[-1] == second_start + timedelta(days=2)
    assert history.pressure_change_mpa.tolist() == pytest.approx(
        [0.0, 1.0, -1.0, -1.0, 0.0, -1.0]
    )
    assert history.elapsed_seconds.tolist() == pytest.approx(
        [0.0, 86_400.0, 172_800.0, 604_800.0, 691_200.0, 777_600.0]
    )


def test_contiguous_pressure_forcing_rejects_overlap_and_long_gaps() -> None:
    start = date(2011, 1, 1)
    first = {start + timedelta(days=day): 100.0 for day in range(3)}
    overlapping = {start + timedelta(days=2 + day): 200.0 for day in range(3)}
    distant = {start + timedelta(days=11 + day): 200.0 for day in range(3)}

    with pytest.raises(ValueError, match="nonoverlapping"):
        prepare_contiguous_center_pressure_forcing(
            first,
            overlapping,
            center_compliance_m_per_mpa=0.02,
        )
    with pytest.raises(ValueError, match="maximum constant-pressure gap"):
        prepare_contiguous_center_pressure_forcing(
            first,
            distant,
            center_compliance_m_per_mpa=0.02,
        )


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


def test_pressure_history_extends_final_value_for_solver_endpoint(
    tmp_path: Path,
) -> None:
    path = tmp_path / "pressure.timedb"
    elapsed_seconds = np.asarray([0.0, 86_400.0, 172_800.0])
    pressure_mpa = np.asarray([0.0, 1.0, 2.0])

    _write_pressure_history(path, elapsed_seconds, pressure_mpa)

    contents = path.read_text(encoding="utf-8").splitlines()
    assert any(line.strip() == "num-points = 4" for line in contents)
    samples = contents[contents.index("}") + 1 :]
    assert len(samples) == 4
    assert float(samples[-1].split()[0]) == pytest.approx(
        (elapsed_seconds[-1] + INITIAL_DT_S) / SECONDS_PER_YEAR
    )
    assert float(samples[-1].split()[1]) == pytest.approx(pressure_mpa[-1])
