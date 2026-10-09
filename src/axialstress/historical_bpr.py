"""Process raw, non-OOI Axial bottom-pressure recorder observations."""

from __future__ import annotations

import csv
import gzip
import math
import statistics
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw" / "axial_bpr"
PROCESSED_DIR = ROOT / "data" / "processed" / "axial_historical_bpr"
SAMPLES_PER_DAY = 5760
MINIMUM_DAILY_COVERAGE = 0.75
MINIMUM_WINDOW_DAYS = 5
WATER_DENSITY_KG_M3 = 1025.0
GRAVITY_M_S2 = 9.80665
METERS_PER_DBAR = 10_000.0 / (WATER_DENSITY_KG_M3 * GRAVITY_M_S2)
DAILY_HEADER = [
    "time_utc",
    "raw_channel_mean",
    "raw_channel_unit",
    "equivalent_depth_m",
    "relative_uplift_m",
    "sample_count",
    "coverage_fraction",
]


@dataclass(frozen=True)
class Deployment:
    """Identify a raw pressure channel and its archive metadata."""

    slug: str
    station: str
    filename: str
    archive: str
    raw_channel: str
    raw_unit: str
    depth_factor_m_per_unit: float
    latitude: float
    longitude: float
    eruption_date: date | None

    @property
    def path(self) -> Path:
        """Return the expected local compressed source file."""
        return RAW_DIR / self.archive / self.filename


DEPLOYMENTS = (
    Deployment(
        slug="wc81_1997",
        station="WC81 1997 Center",
        filename="wc81_19971003to19980807.csv.gz",
        archive="ncei",
        raw_channel="seafloor_pressure_abs_raw [dbar]",
        raw_unit="dbar",
        depth_factor_m_per_unit=METERS_PER_DBAR,
        latitude=45.957,
        longitude=-130.0006,
        eruption_date=date(1998, 1, 25),
    ),
    Deployment(
        slug="wc82a_1997",
        station="WC82A 1997",
        filename="wc82a_19971003to19981003.csv.gz",
        archive="ncei",
        raw_channel="seafloor_pressure_abs_raw [dbar]",
        raw_unit="dbar",
        depth_factor_m_per_unit=METERS_PER_DBAR,
        latitude=45.9306,
        longitude=-129.9832,
        eruption_date=date(1998, 1, 25),
    ),
    Deployment(
        slug="wc82b_1998",
        station="WC82B 1998",
        filename="wc82b_19980924to19990505.csv.gz",
        archive="ncei",
        raw_channel="seafloor_pressure_abs_raw [dbar]",
        raw_unit="dbar",
        depth_factor_m_per_unit=METERS_PER_DBAR,
        latitude=45.9306,
        longitude=-129.9832,
        eruption_date=None,
    ),
    Deployment(
        slug="nemo_2009_2011_south",
        station="NeMO 2009–2011 South",
        filename="nemo2009-2011-BPR-south-15sec-detided-lpf.txt.gz",
        archive="mgds/source_archive/MGDS_Download/JdF:Axial_Deformation",
        raw_channel="Depth",
        raw_unit="m",
        depth_factor_m_per_unit=1.0,
        latitude=45.93412,
        longitude=-129.99988,
        eruption_date=date(2011, 4, 6),
    ),
    Deployment(
        slug="nemo_2010_2011_center",
        station="NeMO 2010–2011 Center",
        filename="nemo2010-2011-BPR-center-15sec-driftcorr-detided-lpf.txt.gz",
        archive="mgds/source_archive/MGDS_Download/JdF:Axial_Deformation",
        raw_channel="RawDep",
        raw_unit="m",
        depth_factor_m_per_unit=1.0,
        latitude=45.95547,
        longitude=-130.00947,
        eruption_date=date(2011, 4, 6),
    ),
)


@dataclass(frozen=True)
class DailyObservation:
    """One UTC-day mean from an uncorrected BPR channel."""

    day: date
    raw_channel_mean: float
    equivalent_depth_m: float
    relative_uplift_m: float | None
    sample_count: int

    @property
    def coverage_fraction(self) -> float:
        """Return the fraction of expected 15-second samples in this UTC day."""
        return self.sample_count / SAMPLES_PER_DAY


def _day_from_timestamp(stamp: str, archive: str) -> date:
    """Read the calendar day from an archive timestamp, interpreted as UTC."""
    if archive == "ncei":
        return date.fromisoformat(stamp[:10])
    month, day, year = stamp[:10].split("/")
    return date(int(year), int(month), int(day))


def _raw_rows(deployment: Deployment):
    """Yield UTC day and one validated raw channel value per source row."""
    if not deployment.path.exists():
        raise FileNotFoundError(
            f"missing {deployment.station} source at {deployment.path}; "
            "run data/fetch_historical_bpr.py --download --accept-mgds-terms"
        )

    with gzip.open(deployment.path, "rt", encoding="utf-8", newline="") as stream:
        if deployment.archive == "ncei":
            for line in stream:
                if line.startswith("// datetime"):
                    header = [
                        field.strip() for field in next(csv.reader([line[3:]]))
                    ]
                    break
                if line.startswith("//"):
                    continue
            else:
                raise ValueError(f"NCEI file has no header: {deployment.path}")
            expected = [
                "datetime [ISO8601]",
                "seafloor_pressure_abs_raw [dbar]",
                "temperature [K]",
            ]
            if header != expected:
                raise ValueError(f"unexpected NCEI header in {deployment.path}: {header}")
            reader = csv.reader(stream, delimiter="\t")
            channel_index = header.index(deployment.raw_channel)
        else:
            reader = csv.reader(stream)
            try:
                header = next(reader)
            except StopIteration as exc:
                raise ValueError(f"MGDS file has no header: {deployment.path}") from exc
            if not header or header[0] != "Date" or deployment.raw_channel not in header:
                raise ValueError(
                    f"raw channel {deployment.raw_channel!r} missing "
                    f"in {deployment.path}"
                )
            channel_index = header.index(deployment.raw_channel)

        for row_number, row in enumerate(reader, start=2):
            if not row or len(row) <= channel_index:
                continue
            try:
                day = _day_from_timestamp(row[0], deployment.archive)
                raw_value = float(row[channel_index])
            except (ValueError, IndexError) as exc:
                raise ValueError(
                    f"invalid raw BPR row {row_number} in {deployment.path}"
                ) from exc
            if math.isfinite(raw_value):
                yield day, raw_value


def process_deployment(deployment: Deployment) -> list[DailyObservation]:
    """Aggregate raw pressure samples into daily means and relative uplift."""
    totals: dict[date, float] = {}
    counts: dict[date, int] = {}
    for day, value in _raw_rows(deployment):
        totals[day] = totals.get(day, 0.0) + value
        counts[day] = counts.get(day, 0) + 1

    daily_raw = {
        day: totals[day] / counts[day]
        for day in totals
        if counts[day] >= SAMPLES_PER_DAY * MINIMUM_DAILY_COVERAGE
    }
    if not daily_raw:
        raise ValueError(f"no days meet the coverage threshold for {deployment.station}")

    first_reference_depth = daily_raw[min(daily_raw)] * deployment.depth_factor_m_per_unit
    observations = []
    for day in sorted(counts):
        raw_mean = totals[day] / counts[day]
        depth_mean = raw_mean * deployment.depth_factor_m_per_unit
        meets_coverage = day in daily_raw
        observations.append(
            DailyObservation(
                day=day,
                raw_channel_mean=raw_mean,
                equivalent_depth_m=depth_mean,
                relative_uplift_m=(
                    first_reference_depth - depth_mean if meets_coverage else None
                ),
                sample_count=counts[day],
            )
        )
    return observations


def write_daily_csv(deployment: Deployment, path: Path) -> list[DailyObservation]:
    """Write a daily CSV using only the specified raw channel."""
    observations = process_deployment(deployment)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(DAILY_HEADER)
        for row in observations:
            writer.writerow(
                [
                    f"{row.day.isoformat()}T00:00:00Z",
                    f"{row.raw_channel_mean:.12g}",
                    deployment.raw_unit,
                    f"{row.equivalent_depth_m:.12g}",
                    "" if row.relative_uplift_m is None else f"{row.relative_uplift_m:.12g}",
                    row.sample_count,
                    f"{row.coverage_fraction:.8f}",
                ]
            )
    return observations


def event_window_change(
    observations: list[DailyObservation],
    eruption_date: date,
    station: str,
) -> dict[str, object]:
    """Compare raw daily depths before and after an eruption date."""
    by_day = {row.day: row for row in observations}
    pre = [
        by_day[eruption_date + timedelta(days=offset)].equivalent_depth_m
        for offset in range(-7, 0)
        if eruption_date + timedelta(days=offset) in by_day
        and by_day[eruption_date + timedelta(days=offset)].relative_uplift_m is not None
    ]
    post = [
        by_day[eruption_date + timedelta(days=offset)].equivalent_depth_m
        for offset in range(8, 15)
        if eruption_date + timedelta(days=offset) in by_day
        and by_day[eruption_date + timedelta(days=offset)].relative_uplift_m is not None
    ]
    if len(pre) < MINIMUM_WINDOW_DAYS or len(post) < MINIMUM_WINDOW_DAYS:
        raise ValueError(
            f"{station} has fewer than {MINIMUM_WINDOW_DAYS} complete days "
            "in a pre- or post-eruption window"
        )
    pre_depth = statistics.median(pre)
    post_depth = statistics.median(post)
    return {
        "station": station,
        "eruption_date_utc": eruption_date.isoformat(),
        "pre_window_utc": [
            (eruption_date - timedelta(days=7)).isoformat(),
            (eruption_date - timedelta(days=1)).isoformat(),
        ],
        "post_window_utc": [
            (eruption_date + timedelta(days=8)).isoformat(),
            (eruption_date + timedelta(days=14)).isoformat(),
        ],
        "pre_valid_days": len(pre),
        "post_valid_days": len(post),
        "pre_median_depth_m": pre_depth,
        "post_median_depth_m": post_depth,
        "post_minus_pre_relative_uplift_m": pre_depth - post_depth,
    }
