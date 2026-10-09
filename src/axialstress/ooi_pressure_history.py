"""Prepare monthly pressure changes from the independent OOI calibration."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]
SECONDS_PER_YEAR = 365.25 * 24.0 * 3600.0
CALIBRATION_HEADER = (
    "time_utc",
    "central_relative_uplift_m",
    "central_elastic_fit_m",
    "east_relative_uplift_m",
    "east_elastic_prediction_m",
    "east_residual_m",
    "inferred_pressure_change_mpa",
    "central_ooi_qc_aggregate",
    "east_ooi_qc_aggregate",
)


@dataclass(frozen=True)
class OoiPressureHistory:
    """Monthly OOI uplift and elastic pressure history in chronological order."""

    times_utc: tuple[datetime, ...]
    elapsed_years: FloatArray
    pressure_change_mpa: FloatArray
    central_uplift_m: FloatArray
    east_uplift_m: FloatArray
    monthly_record_counts: tuple[int, ...]
    central_qc_codes: tuple[str, ...]
    east_qc_codes: tuple[str, ...]


def read_monthly_ooi_pressure_history(path: str | Path) -> OoiPressureHistory:
    """Read and monthly-average OOI uplift and its static elastic pressure fit.

    Parameters
    ----------
    path : str or pathlib.Path
        Calibration CSV produced by `ellipsoid_bpr_check.py` from independent
        OOI Central and Eastern BPR records.

    Returns
    -------
    OoiPressureHistory
        A zero-baseline initial sample followed by calendar-month means.

    Notes
    -----
    The OOI aggregate quality flags are retained as metadata; no flag-based
    filtering is applied. Month-end timestamps keep the pressure history
    within the measured date range and reduce the daily input to a bounded
    solver cadence.
    """
    records: list[tuple[datetime, float, float, float, str, str]] = []
    with Path(path).open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != CALIBRATION_HEADER:
            raise ValueError(f"unexpected ellipsoid calibration columns in {path}")
        for row_number, row in enumerate(reader, start=2):
            try:
                time = datetime.fromisoformat(row["time_utc"].replace("Z", "+00:00"))
                central = float(row["central_relative_uplift_m"])
                east = float(row["east_relative_uplift_m"])
                pressure = float(row["inferred_pressure_change_mpa"])
            except (AttributeError, TypeError, ValueError) as exc:
                raise ValueError(f"invalid calibration row {row_number} in {path}") from exc
            if time.tzinfo is None or time.utcoffset() != UTC.utcoffset(time):
                raise ValueError(f"calibration timestamps must be UTC in {path}")
            if not np.all(np.isfinite((central, east, pressure))):
                continue
            records.append(
                (
                    time.astimezone(UTC),
                    central,
                    east,
                    pressure,
                    row["central_ooi_qc_aggregate"],
                    row["east_ooi_qc_aggregate"],
                )
            )

    if len(records) < 2:
        raise ValueError("at least two finite common OOI calibration records are required")
    if any(
        later[0] <= earlier[0]
        for earlier, later in zip(records, records[1:], strict=False)
    ):
        raise ValueError("calibration timestamps must be strictly increasing")
    start_time = records[0][0]
    initial = records[0]
    if not np.allclose(initial[1:4], 0.0, rtol=0.0, atol=1.0e-10):
        raise ValueError("calibration series must begin at a zero relative-uplift baseline")

    grouped: dict[tuple[int, int], list[tuple[float, float, float, str, str]]] = {}
    for time, central, east, pressure, central_qc, east_qc in records:
        grouped.setdefault((time.year, time.month), []).append(
            (central, east, pressure, central_qc, east_qc)
        )

    times_utc = [start_time]
    central_values = [0.0]
    east_values = [0.0]
    pressure_values = [0.0]
    record_counts = [1]
    for (year, month), monthly in sorted(grouped.items()):
        if month == 12:
            month_end = datetime(year + 1, 1, 1, tzinfo=UTC)
        else:
            month_end = datetime(year, month + 1, 1, tzinfo=UTC)
        month_end -= timedelta(days=1)
        if month_end <= start_time:
            continue
        times_utc.append(month_end)
        central_values.append(float(np.mean([row[0] for row in monthly])))
        east_values.append(float(np.mean([row[1] for row in monthly])))
        pressure_values.append(float(np.mean([row[2] for row in monthly])))
        record_counts.append(len(monthly))

    if len(times_utc) < 3:
        raise ValueError("the OOI calibration must span at least two complete months")
    elapsed_years = np.asarray(
        [(time - start_time).total_seconds() / SECONDS_PER_YEAR for time in times_utc],
        dtype=float,
    )
    if np.any(np.diff(elapsed_years) <= 0.0):
        raise ValueError("monthly pressure-history times must be strictly increasing")

    return OoiPressureHistory(
        times_utc=tuple(times_utc),
        elapsed_years=elapsed_years,
        pressure_change_mpa=np.asarray(pressure_values, dtype=float),
        central_uplift_m=np.asarray(central_values, dtype=float),
        east_uplift_m=np.asarray(east_values, dtype=float),
        monthly_record_counts=tuple(record_counts),
        central_qc_codes=tuple(sorted({row[4] for row in records})),
        east_qc_codes=tuple(sorted({row[5] for row in records})),
    )


def write_normalized_time_history(path: str | Path, history: OoiPressureHistory) -> None:
    """Write pressure changes as a SpatialData normalized-amplitude history."""
    if (
        len(history.elapsed_years) != len(history.pressure_change_mpa)
        or len(history.elapsed_years) < 2
        or not np.all(np.isfinite(history.elapsed_years))
        or not np.all(np.isfinite(history.pressure_change_mpa))
        or np.any(np.diff(history.elapsed_years) <= 0.0)
    ):
        raise ValueError("pressure history requires finite, increasing matched arrays")
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as stream:
        stream.write("#TIME HISTORY ascii\n")
        stream.write("TimeHistory {\n")
        stream.write(f"  num-points = {len(history.elapsed_years)}\n")
        stream.write("  time-units = year\n")
        stream.write("}\n")
        for time_year, pressure_mpa in zip(
            history.elapsed_years, history.pressure_change_mpa, strict=True
        ):
            stream.write(f"{time_year:.12g} {pressure_mpa:.12g}\n")
