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
SECONDS_PER_DAY = 86_400
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
    sampling_interval_s: float = 15.0
    raw_channel_note: str = ""

    @property
    def path(self) -> Path:
        """Return the expected local compressed source file."""
        return RAW_DIR / self.archive / self.filename


EARLIER_NCEI_DEPLOYMENTS = (
    ("wc09_1987", "WC09 1987–1988", "wc09_19870923to19880710.csv.gz", 45.979, -129.9903, 56.25),
    ("wc15_1988", "WC15 1988–1989", "wc15_19880905to19890804.csv.gz", 45.96, -130.02, 56.25),
    ("wc20_1989", "WC20 1989–1990", "wc20_19890907to19900730.csv.gz", 45.9498, -130.0236, 56.25),
    ("wc25_1990", "WC25 1990–1991", "wc25_19900819to19910522.csv.gz", 45.9572, -130.0122, 56.25),
    ("wc32_1991", "WC32 1991–1992", "wc32_19910624to19920604.csv.gz", 45.956, -130.0002, 56.25),
    ("wc51_1993", "WC51 1993–1994", "wc51_19930721to19940917.csv.gz", 45.9314, -129.9856, 15.0),
    ("wc61_1994", "WC61 1994–1995", "wc61_19940806to19950615.csv.gz", 45.9597, -129.9643, 15.0),
    ("wc67_1995", "WC67 1995–1996", "wc67_19950721to19960622.csv.gz", 45.962, -129.967, 15.0),
    ("wc68_1995", "WC68 1995–1996", "wc68_19950721to19960622.csv.gz", 45.9567, -130.0, 15.0),
    ("wc69_1995", "WC69 1995–1996", "wc69_19950617to19960622.csv.gz", 45.9333, -129.9805, 15.0),
)

DEPLOYMENTS = tuple(
    Deployment(
        slug=slug,
        station=station,
        filename=filename,
        archive="ncei",
        raw_channel="seafloor_pressure_abs_raw [dbar]",
        raw_unit="dbar",
        depth_factor_m_per_unit=METERS_PER_DBAR,
        latitude=latitude,
        longitude=longitude,
        eruption_date=None,
        sampling_interval_s=sampling_interval_s,
    )
    for slug, station, filename, latitude, longitude, sampling_interval_s
    in EARLIER_NCEI_DEPLOYMENTS
) + (
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
        slug="nemo_2000_center",
        station="NeMO 2000 Center",
        filename="nemo_20000706to20010801.csv.gz",
        archive="ncei",
        raw_channel="seafloor_pressure_abs_raw [dbar]",
        raw_unit="dbar",
        depth_factor_m_per_unit=METERS_PER_DBAR,
        latitude=45.95522,
        longitude=-130.01017,
        eruption_date=None,
    ),
    Deployment(
        slug="nemo_2001_center",
        station="NeMO 2001 Center",
        filename="nemo_20010701to20020719.csv.gz",
        archive="ncei",
        raw_channel="seafloor_pressure_abs_raw [dbar]",
        raw_unit="dbar",
        depth_factor_m_per_unit=METERS_PER_DBAR,
        latitude=45.95522,
        longitude=-130.01017,
        eruption_date=None,
    ),
    Deployment(
        slug="nemo_2002_2004_center",
        station="NeMO 2002–2004 Center",
        filename="nemo2002-2004-BPR-center-15sec-driftcorr-detided-lpf.txt.gz",
        archive="mgds/source_archive_2002_2004/MGDS_Download/JdF:Axial_Deformation",
        raw_channel="DriftCorrRawDep",
        raw_unit="m",
        depth_factor_m_per_unit=1.0,
        latitude=45.95252,
        longitude=-130.01017,
        eruption_date=None,
        raw_channel_note=(
            "MGDS states the deployment drift correction is zero, so this "
            "raw-depth field is unchanged from the instrument record."
        ),
    ),
    Deployment(
        slug="nemo_2003_2005_center",
        station="NeMO 2003–2005 Center",
        filename="nemo2003-2005-BPR-center-15sec-detided-lpf.txt.gz",
        archive="mgds/source_archive/MGDS_Download/JdF:Axial_Deformation",
        raw_channel="Depth",
        raw_unit="m",
        depth_factor_m_per_unit=1.0,
        latitude=45.9552,
        longitude=-130.0102,
        eruption_date=None,
    ),
    Deployment(
        slug="nemo_2003_2005_south",
        station="NeMO 2003–2005 South",
        filename="nemo2003-2005-BPR-south-15sec-detided-lpf.txt.gz",
        archive="mgds/source_archive/MGDS_Download/JdF:Axial_Deformation",
        raw_channel="Depth",
        raw_unit="m",
        depth_factor_m_per_unit=1.0,
        latitude=45.9333,
        longitude=-130.0,
        eruption_date=None,
    ),
    Deployment(
        slug="nemo_2004_2007_center",
        station="NeMO 2004–2007 Center",
        filename="nemo2004-2007-BPR-center-15sec-driftcorr-detided-lpf.txt.gz",
        archive="mgds/source_archive/MGDS_Download/JdF:Axial_Deformation",
        raw_channel="RawDep",
        raw_unit="m",
        depth_factor_m_per_unit=1.0,
        latitude=45.9517,
        longitude=-130.0083,
        eruption_date=None,
    ),
    Deployment(
        slug="nemo_2005_2007_south1",
        station="NeMO 2005–2007 South 1",
        filename="nemo2005-2007-BPR-south1-15sec-detided-lpf.txt.gz",
        archive="mgds/source_archive/MGDS_Download/JdF:Axial_Deformation",
        raw_channel="Depth",
        raw_unit="m",
        depth_factor_m_per_unit=1.0,
        latitude=45.9427,
        longitude=-130.0,
        eruption_date=None,
    ),
    Deployment(
        slug="nemo_2005_2009_south2",
        station="NeMO 2005–2009 South 2",
        filename="nemo2005-2009-BPR-south2-15sec-detided-lpf.txt.gz",
        archive="mgds/source_archive/MGDS_Download/JdF:Axial_Deformation",
        raw_channel="Depth",
        raw_unit="m",
        depth_factor_m_per_unit=1.0,
        latitude=45.9333,
        longitude=-130.0,
        eruption_date=None,
    ),
    Deployment(
        slug="nemo_2007_2009_south1",
        station="NeMO 2007–2009 South 1",
        filename="nemo2007-2009-BPR-south1-15sec-detided-lpf.txt.gz",
        archive="mgds/source_archive/MGDS_Download/JdF:Axial_Deformation",
        raw_channel="Depth",
        raw_unit="m",
        depth_factor_m_per_unit=1.0,
        latitude=45.9419,
        longitude=-130.0003,
        eruption_date=None,
    ),
    Deployment(
        slug="nemo_2007_2010_center",
        station="NeMO 2007–2010 Center",
        filename="nemo2007-2010-BPR-center-15sec-driftcorr-detided-lpf.txt.gz",
        archive="mgds/source_archive/MGDS_Download/JdF:Axial_Deformation",
        raw_channel="RawDep",
        raw_unit="m",
        depth_factor_m_per_unit=1.0,
        latitude=45.9553,
        longitude=-130.0101,
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
    Deployment(
        slug="nemo_2011_2013_center",
        station="NeMO 2011–2013 Center",
        filename="nemo2011-2013-BPR-center-15sec-driftcorr-detided-lpf.txt.gz",
        archive="mgds/source_archive/MGDS_Download/JdF:Axial_Deformation",
        raw_channel="RawDep",
        raw_unit="m",
        depth_factor_m_per_unit=1.0,
        latitude=45.9555,
        longitude=-130.0095,
        eruption_date=None,
    ),
    Deployment(
        slug="nemo_2011_2013_south",
        station="NeMO 2011–2013 South",
        filename="nemo2011-2013-BPR-south-15sec-detided-lpf.txt.gz",
        archive="mgds/source_archive/MGDS_Download/JdF:Axial_Deformation",
        raw_channel="Depth",
        raw_unit="m",
        depth_factor_m_per_unit=1.0,
        latitude=45.9341,
        longitude=-129.9999,
        eruption_date=None,
    ),
    Deployment(
        slug="nemo_2013_2015_center",
        station="NeMO 2013–2015 Center",
        filename="nemo2013-2015-BPR-Center-15sec-driftcorr-detided-lpf.txt.gz",
        archive="mgds/source_archive/MGDS_Download/JdF:Axial_Deformation",
        raw_channel="RawDep",
        raw_unit="m",
        depth_factor_m_per_unit=1.0,
        latitude=45.9568,
        longitude=-130.0106,
        eruption_date=None,
    ),
    Deployment(
        slug="nemo_2013_2015_south1",
        station="NeMO 2013–2015 South 1",
        filename="nemo2013-2015-BPR-South-1-15sec-driftcorr-detided-lpf.txt.gz",
        archive="mgds/source_archive/MGDS_Download/JdF:Axial_Deformation",
        raw_channel="RawDep",
        raw_unit="m",
        depth_factor_m_per_unit=1.0,
        latitude=45.9318,
        longitude=-129.9988,
        eruption_date=None,
    ),
    Deployment(
        slug="nemo_2013_2015_south2",
        station="NeMO 2013–2015 South 2",
        filename="nemo2013-2015-BPR-South-2-15sec-driftcorr-detided-lpf.txt.gz",
        archive="mgds/source_archive/MGDS_Download/JdF:Axial_Deformation",
        raw_channel="RawDep",
        raw_unit="m",
        depth_factor_m_per_unit=1.0,
        latitude=45.9160,
        longitude=-129.9935,
        eruption_date=None,
    ),
    Deployment(
        slug="nemo_2015_2017_center",
        station="NeMO 2015–2017 Center",
        filename="nemo2015-2017-BPR-center-15sec-driftcorr-detided-lpf.txt.gz",
        archive="mgds/source_archive/MGDS_Download/JdF:Axial_Deformation",
        raw_channel="RawDep",
        raw_unit="m",
        depth_factor_m_per_unit=1.0,
        latitude=45.9568,
        longitude=-130.0106,
        eruption_date=None,
    ),
    Deployment(
        slug="nemo_2015_2017_south2",
        station="NeMO 2015–2017 South 2",
        filename="nemo2015-2017-BPR-south2-15sec-driftcorr-detided-lpf.txt.gz",
        archive="mgds/source_archive/MGDS_Download/JdF:Axial_Deformation",
        raw_channel="RawDep",
        raw_unit="m",
        depth_factor_m_per_unit=1.0,
        latitude=45.9160,
        longitude=-129.9935,
        eruption_date=None,
    ),
    Deployment(
        slug="nemo_2017_2018_center",
        station="NeMO 2017–2018 Center",
        filename="nemo2017-2018-BPR-center-15sec-driftcorr-detided-lpf.txt.gz",
        archive="mgds/source_archive_2017_2022/MGDS_Download/JdF:Axial_Deformation",
        raw_channel="RawDep",
        raw_unit="m",
        depth_factor_m_per_unit=1.0,
        latitude=45.95745,
        longitude=-130.01097,
        eruption_date=None,
    ),
    Deployment(
        slug="nemo_2017_2018_south2",
        station="NeMO 2017–2018 South 2",
        filename="nemo2017-2018-BPR-south2-15sec-driftcorr-detided-lpf.txt.gz",
        archive="mgds/source_archive_2017_2022/MGDS_Download/JdF:Axial_Deformation",
        raw_channel="RawDep",
        raw_unit="m",
        depth_factor_m_per_unit=1.0,
        latitude=45.91597,
        longitude=-129.99365,
        eruption_date=None,
    ),
    Deployment(
        slug="nemo_2018_2020_center",
        station="NeMO 2018–2020 Center",
        filename="nemo2018-2020-BPR-center-15sec-driftcorr-detided.txt.gz",
        archive="mgds/source_archive_2017_2022/MGDS_Download/JdF:Axial_Deformation",
        raw_channel="RawDep",
        raw_unit="m",
        depth_factor_m_per_unit=1.0,
        latitude=45.953625,
        longitude=-130.012297,
        eruption_date=None,
    ),
    Deployment(
        slug="nemo_2018_2020_south2",
        station="NeMO 2018–2020 South 2",
        filename="nemo2018-2020-BPR-south2-15sec-driftcorr-detided.txt.gz",
        archive="mgds/source_archive_2017_2022/MGDS_Download/JdF:Axial_Deformation",
        raw_channel="RawDep",
        raw_unit="m",
        depth_factor_m_per_unit=1.0,
        latitude=45.970624,
        longitude=-130.009368,
        eruption_date=None,
    ),
    Deployment(
        slug="minibpr_2020_2022_south1",
        station="Mini-BPR AX-308 South 1 2020–2022",
        filename="miniBPR_2020_01_cd_detided_AX308.txt.gz",
        archive="mgds/source_archive_2017_2022/MGDS_Download/JdF:Axial_Deformation",
        raw_channel="RawDepth(m)",
        raw_unit="m",
        depth_factor_m_per_unit=1.0,
        latitude=45.9316,
        longitude=-129.9988,
        eruption_date=None,
        sampling_interval_s=100.0,
    ),
    Deployment(
        slug="minibpr_2020_2022_center",
        station="Mini-BPR AX-101 Caldera Center 2020–2022",
        filename="miniBPR_2020_02_cd_detided_AX101.txt.gz",
        archive="mgds/source_archive_2017_2022/MGDS_Download/JdF:Axial_Deformation",
        raw_channel="RawDepth(m)",
        raw_unit="m",
        depth_factor_m_per_unit=1.0,
        latitude=45.9552,
        longitude=-130.0099,
        eruption_date=None,
        sampling_interval_s=100.0,
    ),
)

FOX_1997_1998_DEPLOYMENTS = (
    Deployment(
        slug="fox_wc81_1997_center",
        station="Fox archive WC81/VSM1 1997 Center",
        filename="nemo1997-1998-BPR-center-15sec-spotl-lpf.txt.gz",
        archive="mgds/source_archive_322344/MGDS_Download/JdF:Axial_Deformation",
        raw_channel="Depth",
        raw_unit="m",
        depth_factor_m_per_unit=1.0,
        latitude=45.9567,
        longitude=-130.0,
        eruption_date=date(1998, 1, 25),
    ),
    Deployment(
        slug="fox_wc82_1997_south",
        station="Fox archive WC82/VSM2 1997 South",
        filename="nemo1997-1998-BPR-south-15sec-spotl-lpf.txt.gz",
        archive="mgds/source_archive_322344/MGDS_Download/JdF:Axial_Deformation",
        raw_channel="Depth",
        raw_unit="m",
        depth_factor_m_per_unit=1.0,
        latitude=45.9302,
        longitude=-129.984,
        eruption_date=date(1998, 1, 25),
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
    expected_samples_per_day: float

    @property
    def coverage_fraction(self) -> float:
        """Return the fraction of expected 15-second samples in this UTC day."""
        return self.sample_count / self.expected_samples_per_day


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
            "run data/fetch_historical_bpr.py --download --ncei-only for NCEI, "
            "or accept the MGDS research-use terms for MGDS records"
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
            if (
                not header
                or header[0] not in {"Date", "DateTime"}
                or deployment.raw_channel not in header
            ):
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

    expected_samples_per_day = SECONDS_PER_DAY / deployment.sampling_interval_s
    daily_raw = {
        day: totals[day] / counts[day]
        for day in totals
        if counts[day] >= expected_samples_per_day * MINIMUM_DAILY_COVERAGE
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
                expected_samples_per_day=expected_samples_per_day,
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


def compare_raw_deployment_sources(
    reference: list[DailyObservation],
    comparison: list[DailyObservation],
    *,
    reference_station: str,
    comparison_station: str,
) -> dict[str, object]:
    """Compare raw deployment series after aligning their first shared day."""
    reference_by_day = {
        row.day: row for row in reference if row.relative_uplift_m is not None
    }
    comparison_by_day = {
        row.day: row for row in comparison if row.relative_uplift_m is not None
    }
    shared_days = sorted(reference_by_day.keys() & comparison_by_day.keys())
    if len(shared_days) < MINIMUM_WINDOW_DAYS:
        raise ValueError("raw BPR sources have too few shared complete daily means")

    first_day = shared_days[0]
    reference_origin = reference_by_day[first_day].equivalent_depth_m
    comparison_origin = comparison_by_day[first_day].equivalent_depth_m
    reference_uplift = [
        reference_origin - reference_by_day[day].equivalent_depth_m
        for day in shared_days
    ]
    comparison_uplift = [
        comparison_origin - comparison_by_day[day].equivalent_depth_m
        for day in shared_days
    ]
    differences = [
        second - first
        for first, second in zip(reference_uplift, comparison_uplift, strict=True)
    ]
    rmse_m = math.sqrt(math.fsum(value * value for value in differences) / len(differences))
    bias_m = math.fsum(differences) / len(differences)
    try:
        correlation = statistics.correlation(reference_uplift, comparison_uplift)
    except statistics.StatisticsError:
        correlation = None
    return {
        "reference_station": reference_station,
        "comparison_station": comparison_station,
        "shared_start_utc": shared_days[0].isoformat(),
        "shared_end_utc": shared_days[-1].isoformat(),
        "shared_daily_means": len(shared_days),
        "comparison_minus_reference_bias_m": bias_m,
        "comparison_minus_reference_rmse_m": rmse_m,
        "relative_uplift_correlation": correlation,
    }
