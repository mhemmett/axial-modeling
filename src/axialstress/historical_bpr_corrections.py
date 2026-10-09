"""Read independently processed tide- and drift-corrected Axial BPR channels."""

from __future__ import annotations

import csv
import gzip
import math
from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from axialstress.historical_bpr import (
    CORRECTED_DAILY_HEADER,
    DEPLOYMENTS,
    FOX_1997_1998_DEPLOYMENTS,
    MINIMUM_DAILY_COVERAGE,
    SECONDS_PER_DAY,
    Deployment,
    _day_from_timestamp,
)

PROCESSED_CORRECTED_DIR = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "processed"
    / "axial_historical_bpr"
    / "corrected"
)

TIDE_AND_DRIFT_CHANNELS = ("DriftCorrSpotlDep", "DriftCorrDetidedDep")
TIDE_ONLY_CHANNELS = (
    "SpotlDetidedDepth",
    "SpotlDep",
    "DetideDep",
    "ThomsonDetidedDepth",
    "DetidedDepth(m)",
    "DetidedDepth",
)


class NoCorrectedChannelError(ValueError):
    """Raised when an archive file has no recognized corrected observation channel."""


@dataclass(frozen=True)
class CorrectedDailyObservation:
    """One UTC-day mean from a corrected BPR observation channel."""

    day: date
    corrected_source_channel: str
    correction_components: str
    channel_mean: float
    equivalent_depth_m: float
    relative_uplift_m: float | None
    sample_count: int
    expected_samples_per_day: float

    @property
    def coverage_fraction(self) -> float:
        """Return valid samples divided by the expected deployment cadence."""
        return self.sample_count / self.expected_samples_per_day


def _select_corrected_channels(header: list[str]) -> tuple[str, str] | None:
    """Select combined tide/drift output or a tide-only field from MGDS."""
    for channel in TIDE_AND_DRIFT_CHANNELS:
        if channel in header:
            return channel, "predicted tide and MPR-based drift"

    tide_channel = next((name for name in TIDE_ONLY_CHANNELS if name in header), None)
    if tide_channel is None:
        return None
    return tide_channel, "predicted tide; no MPR drift estimate in this file"


def iter_corrected_samples(
    deployment: Deployment,
) -> Iterator[tuple[date, str, str, float]]:
    """Yield corrected source observations as UTC day, channel, method, and value."""
    if deployment.archive == "ncei":
        raise NoCorrectedChannelError(
            f"{deployment.station} is available only as an original NCEI channel"
        )
    if not deployment.path.is_file():
        raise FileNotFoundError(deployment.path)

    with gzip.open(deployment.path, "rt", encoding="utf-8", newline="") as stream:
        reader = csv.reader(stream)
        try:
            header = [field.strip() for field in next(reader)]
        except StopIteration as exc:
            raise ValueError(f"MGDS file has no header: {deployment.path}") from exc
        if not header or header[0] not in {"Date", "DateTime"}:
            raise ValueError(f"unexpected MGDS header in {deployment.path}: {header}")

        channels = _select_corrected_channels(header)
        if channels is None:
            raise NoCorrectedChannelError(
                f"{deployment.station} has no supported corrected observation field"
            )
        channel, components = channels
        channel_index = header.index(channel)

        for row_number, row in enumerate(reader, start=2):
            if not row or len(row) <= channel_index:
                continue
            try:
                stamp = row[0].strip()
                value = float(row[channel_index])
            except (IndexError, ValueError) as exc:
                raise ValueError(
                    f"invalid corrected BPR row {row_number} in {deployment.path}"
                ) from exc
            if math.isfinite(value):
                yield _day_from_timestamp(stamp, deployment.archive), channel, components, value


def process_corrected_deployment(
    deployment: Deployment,
) -> tuple[str, str, list[CorrectedDailyObservation]]:
    """Aggregate tide-corrected MGDS samples and available MPR drift corrections."""
    totals: dict[date, float] = defaultdict(float)
    counts: dict[date, int] = defaultdict(int)
    source_channel = None
    correction_components = None
    for day, channel, components, value in iter_corrected_samples(deployment):
        source_channel = channel
        correction_components = components
        totals[day] += value
        counts[day] += 1

    if not counts or source_channel is None or correction_components is None:
        raise ValueError(f"no corrected samples found for {deployment.station}")

    expected_samples = SECONDS_PER_DAY / deployment.sampling_interval_s
    valid_days = {
        day
        for day, count in counts.items()
        if count >= expected_samples * MINIMUM_DAILY_COVERAGE
    }
    if not valid_days:
        raise ValueError(f"no corrected days meet coverage for {deployment.station}")
    first_depth_m = (
        totals[min(valid_days)] / counts[min(valid_days)]
    ) * deployment.depth_factor_m_per_unit

    observations = []
    for day in sorted(counts):
        mean_value = totals[day] / counts[day]
        depth_m = mean_value * deployment.depth_factor_m_per_unit
        covered = day in valid_days
        observations.append(
            CorrectedDailyObservation(
                day=day,
                corrected_source_channel=source_channel,
                correction_components=correction_components,
                channel_mean=mean_value,
                equivalent_depth_m=depth_m,
                relative_uplift_m=(first_depth_m - depth_m if covered else None),
                sample_count=counts[day],
                expected_samples_per_day=expected_samples,
            )
        )
    return source_channel, correction_components, observations


def write_corrected_daily_csv(
    deployment: Deployment, path: Path
) -> tuple[str, str, list[CorrectedDailyObservation]]:
    """Write corrected daily means while retaining their archive provenance."""
    channel, components, observations = process_corrected_deployment(deployment)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(CORRECTED_DAILY_HEADER)
        for row in observations:
            writer.writerow(
                [
                    f"{row.day.isoformat()}T00:00:00Z",
                    row.corrected_source_channel,
                    row.correction_components,
                    f"{row.channel_mean:.12g}",
                    deployment.raw_unit,
                    f"{row.equivalent_depth_m:.12g}",
                    "" if row.relative_uplift_m is None else f"{row.relative_uplift_m:.12g}",
                    row.sample_count,
                    f"{row.expected_samples_per_day:.8g}",
                    f"{row.coverage_fraction:.8f}",
                ]
            )
    return channel, components, observations


CORRECTED_ERUPTION_DEPLOYMENTS = (
    *FOX_1997_1998_DEPLOYMENTS,
    next(item for item in DEPLOYMENTS if item.slug == "nemo_2010_2011_center"),
    next(item for item in DEPLOYMENTS if item.slug == "nemo_2009_2011_south"),
)
