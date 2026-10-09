"""Compare subdaily raw BPR depths around the 1998 and 2011 Axial eruptions."""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from axialstress.historical_bpr import (
    DEPLOYMENTS,
    MINIMUM_DAILY_COVERAGE,
    MINIMUM_WINDOW_DAYS,
    PROCESSED_DIR,
    DailyObservation,
    Deployment,
    event_window_change,
    iter_raw_samples,
    process_deployment,
)

ROOT = Path(__file__).resolve().parents[2]
FIGURE_DIR = ROOT / "figures"
EVENT_DATES = (date(1998, 1, 25), date(2011, 4, 6))
EVENT_RADIUS_DAYS = 21
HOURLY_COVERAGE = MINIMUM_DAILY_COVERAGE


@dataclass(frozen=True)
class HourlyObservation:
    """One hourly median from an original, uncorrected raw pressure channel."""

    time_utc: datetime
    raw_channel_median: float
    equivalent_depth_m: float
    relative_uplift_m: float | None
    sample_count: int
    coverage_fraction: float


def _parse_timestamp(stamp: str, archive: str) -> datetime:
    """Parse a source timestamp as UTC without applying a time correction."""
    if archive == "ncei":
        parsed = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        return parsed.astimezone(UTC) if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    return datetime.strptime(stamp, "%m/%d/%Y %H:%M:%S").replace(tzinfo=UTC)


def _event_deployments() -> tuple[Deployment, ...]:
    """Return only original station deployments that span the two events."""
    return tuple(
        deployment for deployment in DEPLOYMENTS if deployment.eruption_date in EVENT_DATES
    )


def hourly_event_observations(
    deployment: Deployment,
    *,
    event_date: date,
    radius_days: int = EVENT_RADIUS_DAYS,
) -> list[HourlyObservation]:
    """Aggregate raw source samples into coverage-screened UTC-hour medians."""
    first_day = event_date - timedelta(days=radius_days)
    final_day = event_date + timedelta(days=radius_days)
    bins: dict[datetime, list[float]] = {}
    for stamp, raw_value in iter_raw_samples(deployment):
        if deployment.archive == "ncei":
            sample_day = date.fromisoformat(stamp[:10])
        else:
            month, day, year = stamp[:10].split("/")
            sample_day = date(int(year), int(month), int(day))
        if sample_day < first_day or sample_day > final_day:
            continue
        timestamp = _parse_timestamp(stamp, deployment.archive)
        hour = timestamp.replace(minute=0, second=0, microsecond=0)
        bins.setdefault(hour, []).append(raw_value)

    expected_samples = 3600.0 / deployment.sampling_interval_s
    observations = []
    for hour, values in sorted(bins.items()):
        coverage = len(values) / expected_samples
        if coverage < HOURLY_COVERAGE:
            continue
        raw_median = statistics.median(values)
        depth_m = raw_median * deployment.depth_factor_m_per_unit
        observations.append(
            HourlyObservation(
                time_utc=hour,
                raw_channel_median=raw_median,
                equivalent_depth_m=depth_m,
                relative_uplift_m=None,
                sample_count=len(values),
                coverage_fraction=coverage,
            )
        )

    pre_depths = [
        row.equivalent_depth_m
        for row in observations
        if -7 <= (row.time_utc.date() - event_date).days <= -1
    ]
    post_depths = [
        row.equivalent_depth_m
        for row in observations
        if 8 <= (row.time_utc.date() - event_date).days <= 14
    ]
    minimum_window_hours = MINIMUM_WINDOW_DAYS * 24
    if len(pre_depths) < minimum_window_hours or len(post_depths) < minimum_window_hours:
        raise ValueError(
            f"{deployment.station} has fewer than {minimum_window_hours} valid "
            "hourly bins in a pre- or post-eruption window"
        )
    baseline_depth = statistics.median(pre_depths)
    return [
        HourlyObservation(
            time_utc=row.time_utc,
            raw_channel_median=row.raw_channel_median,
            equivalent_depth_m=row.equivalent_depth_m,
            relative_uplift_m=baseline_depth - row.equivalent_depth_m,
            sample_count=row.sample_count,
            coverage_fraction=row.coverage_fraction,
        )
        for row in observations
    ]


def _hourly_event_summary(
    deployment: Deployment,
    observations: list[HourlyObservation],
    event_date: date,
    daily: list[DailyObservation],
) -> dict[str, object]:
    """Summarize a raw hourly event change and compare daily averaging."""
    pre = [
        row.equivalent_depth_m
        for row in observations
        if -7 <= (row.time_utc.date() - event_date).days <= -1
    ]
    post = [
        row.equivalent_depth_m
        for row in observations
        if 8 <= (row.time_utc.date() - event_date).days <= 14
    ]
    hourly_change = statistics.median(pre) - statistics.median(post)
    daily_change = event_window_change(daily, event_date, deployment.station)
    return {
        "station": deployment.station,
        "source_archive": deployment.archive,
        "source_file": deployment.filename,
        "raw_channel": deployment.raw_channel,
        "raw_unit": deployment.raw_unit,
        "sample_interval_s": deployment.sampling_interval_s,
        "event_date_utc": event_date.isoformat(),
        "event_window_days": [-EVENT_RADIUS_DAYS, EVENT_RADIUS_DAYS],
        "pre_window_days": [-7, -1],
        "post_window_days": [8, 14],
        "valid_hourly_bins": len(observations),
        "pre_valid_hours": len(pre),
        "post_valid_hours": len(post),
        "hourly_median_post_minus_pre_uplift_m": hourly_change,
        "daily_mean_post_minus_pre_uplift_m": daily_change["post_minus_pre_relative_uplift_m"],
        "hourly_minus_daily_change_m": (
            hourly_change - daily_change["post_minus_pre_relative_uplift_m"]
        ),
    }


def _write_hourly_csv(
    path: Path,
    deployment: Deployment,
    observations: list[HourlyObservation],
) -> None:
    """Write one auditable hourly series from the selected original channel."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(
            (
                "time_utc",
                "raw_channel_median",
                "raw_channel_unit",
                "equivalent_depth_m",
                "relative_uplift_m",
                "sample_count",
                "coverage_fraction",
            )
        )
        for row in observations:
            writer.writerow(
                (
                    row.time_utc.isoformat().replace("+00:00", "Z"),
                    f"{row.raw_channel_median:.12g}",
                    deployment.raw_unit,
                    f"{row.equivalent_depth_m:.12g}",
                    f"{row.relative_uplift_m:.12g}",
                    row.sample_count,
                    f"{row.coverage_fraction:.8f}",
                )
            )


def _daily_event_series(
    deployment: Deployment,
    event_date: date,
    daily: list[DailyObservation],
) -> tuple[list[float], list[float]]:
    """Return daily means with the same pre-event depth baseline."""
    by_day = {row.day: row for row in daily if row.relative_uplift_m is not None}
    baseline = statistics.median(
        by_day[event_date + timedelta(days=offset)].equivalent_depth_m
        for offset in range(-7, 0)
        if event_date + timedelta(days=offset) in by_day
    )
    offsets = []
    uplift = []
    for day, row in sorted(by_day.items()):
        offset = (day - event_date).total_seconds() / 86_400.0
        if -EVENT_RADIUS_DAYS <= offset <= EVENT_RADIUS_DAYS:
            offsets.append(offset + 0.5)
            uplift.append(baseline - row.equivalent_depth_m)
    return offsets, uplift


def _plot_event_data(
    grouped: dict[
        date,
        list[tuple[Deployment, list[HourlyObservation], list[DailyObservation]]],
    ],
    figure_dir: Path,
) -> tuple[Path, Path]:
    """Plot hourly medians and daily means without smoothing raw channels."""
    figure_dir.mkdir(parents=True, exist_ok=True)
    figure, axes = plt.subplots(1, 2, figsize=(12.2, 5.1), constrained_layout=True)
    colors = {
        "wc81_1997": "#0072B2",
        "wc82a_1997": "#D55E00",
        "nemo_2010_2011_center": "#0072B2",
        "nemo_2009_2011_south": "#D55E00",
    }
    for axis, event_date in zip(axes, EVENT_DATES, strict=True):
        for deployment, observations, daily in grouped[event_date]:
            offsets = [
                (row.time_utc - datetime.combine(event_date, time(), tzinfo=UTC)).total_seconds()
                / 86_400.0
                for row in observations
            ]
            uplift = [row.relative_uplift_m for row in observations]
            color = colors[deployment.slug]
            axis.plot(
                offsets,
                uplift,
                color=color,
                linewidth=0.75,
                alpha=0.82,
                label=f"{deployment.station}, hourly median",
            )
            daily_offsets, daily_uplift = _daily_event_series(deployment, event_date, daily)
            axis.scatter(
                daily_offsets,
                daily_uplift,
                color=color,
                marker="o",
                s=14,
                edgecolor="white",
                linewidth=0.35,
                label=f"{deployment.station}, daily mean",
                zorder=4,
            )
        axis.axvline(0.0, color="#444444", linewidth=0.9, linestyle="--")
        axis.axhline(0.0, color="#777777", linewidth=0.6)
        axis.set_xlim(-EVENT_RADIUS_DAYS, EVENT_RADIUS_DAYS + 0.25)
        axis.set_title(f"{event_date:%B %Y}")
        axis.set_xlabel(f"Days from {event_date.isoformat()} (UTC)")
        axis.grid(True, color="#D9D9D9", linewidth=0.5)
        axis.legend(frameon=False, fontsize=7, loc="best")
    axes[0].set_ylabel("Relative seafloor elevation (m; up positive)")
    figure.suptitle(
        "Eruption-window checks from original raw off-OOI BPR channels\n"
        "Hourly medians retain subdaily pressure variability; daily means shown for comparison"
    )
    stem = figure_dir / "historical_bpr_subdaily_eruption_windows"
    png = stem.with_suffix(".png")
    pdf = stem.with_suffix(".pdf")
    figure.savefig(png, dpi=220)
    figure.savefig(pdf)
    plt.close(figure)
    return png, pdf


def analyze_event_windows(
    output_dir: Path = PROCESSED_DIR / "subdaily_event_windows",
    figure_dir: Path = FIGURE_DIR,
) -> dict[str, object]:
    """Write subdaily raw event series, diagnostics, and comparison plots."""
    output_dir.mkdir(parents=True, exist_ok=True)
    grouped: dict[
        date,
        list[tuple[Deployment, list[HourlyObservation], list[DailyObservation]]],
    ] = {event_date: [] for event_date in EVENT_DATES}
    station_summaries = []
    for deployment in _event_deployments():
        event_date = deployment.eruption_date
        if event_date is None:
            continue
        observations = hourly_event_observations(deployment, event_date=event_date)
        daily = process_deployment(deployment)
        grouped[event_date].append((deployment, observations, daily))
        csv_path = output_dir / f"{deployment.slug}.hourly.csv"
        _write_hourly_csv(csv_path, deployment, observations)
        summary = _hourly_event_summary(deployment, observations, event_date, daily)
        summary["hourly_csv"] = str(csv_path)
        station_summaries.append(summary)
        print(
            f"{deployment.station}: {len(observations)} hourly bins; "
            f"hourly event change {summary['hourly_median_post_minus_pre_uplift_m']:.3f} m; "
            f"daily mean {summary['daily_mean_post_minus_pre_uplift_m']:.3f} m"
        )

    png, pdf = _plot_event_data(grouped, figure_dir)
    summary = {
        "processing": {
            "source_boundary": (
                "Only original NCEI raw pressure and MGDS RawDep/Depth channels; "
                "no detiding, filtering, drift correction, or paper-associated data."
            ),
            "binning": "UTC-hour median of original raw samples",
            "minimum_hourly_coverage_fraction": HOURLY_COVERAGE,
            "event_plot_window_days": [-EVENT_RADIUS_DAYS, EVENT_RADIUS_DAYS],
            "pre_event_baseline_days": [-7, -1],
            "post_event_comparison_days": [8, 14],
            "uplift_sign": "positive upward; decrease in pressure-derived depth",
        },
        "station_summaries": station_summaries,
        "figures": {"png": str(png), "pdf": str(pdf)},
    }
    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {summary_path}, {png}, and {pdf}")
    return summary


def main() -> None:
    """Run bounded hourly aggregation for the two earlier eruption windows."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROCESSED_DIR / "subdaily_event_windows",
        help="directory for ignored hourly series and JSON summary",
    )
    parser.add_argument(
        "--figure-dir",
        type=Path,
        default=FIGURE_DIR,
        help="directory for tracked comparison figures",
    )
    args = parser.parse_args()
    analyze_event_windows(args.output_dir, args.figure_dir)


if __name__ == "__main__":
    main()
