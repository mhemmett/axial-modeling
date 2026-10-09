"""Check the shared 1998 and 2011 raw BPR deployment time series."""

from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.dates as mdates
import matplotlib.pyplot as plt

from axialstress.historical_bpr import DEPLOYMENTS, PROCESSED_DIR
from axialstress.historical_mogi_timeseries import compare_center_to_south_timeseries

EVENT_PAIRS = {
    "1998": (date(1998, 1, 25), "wc81_1997", "wc82a_1997"),
    "2011": (
        date(2011, 4, 6),
        "nemo_2010_2011_center",
        "nemo_2009_2011_south",
    ),
}
DAILY_HEADER = [
    "time_utc",
    "raw_channel_mean",
    "raw_channel_unit",
    "equivalent_depth_m",
    "relative_uplift_m",
    "sample_count",
    "coverage_fraction",
]


def read_valid_daily_depths(path: Path) -> dict[date, float]:
    """Read complete daily raw-channel equivalent depths from one CSV."""
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != DAILY_HEADER:
            raise ValueError(f"unexpected daily BPR schema in {path}")
        depths = {}
        for row_number, row in enumerate(reader, start=2):
            if not row["relative_uplift_m"]:
                continue
            try:
                day = date.fromisoformat(row["time_utc"][:10])
                depth = float(row["equivalent_depth_m"])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"invalid daily BPR row {row_number} in {path}") from exc
            if not math.isfinite(depth):
                raise ValueError(f"nonfinite daily BPR depth at row {row_number} in {path}")
            depths[day] = depth
    return depths


def _write_event(event: str, output_dir: Path) -> dict[str, object]:
    """Write one event's aligned model series and diagnostic summary."""
    eruption_date, center_slug, south_slug = EVENT_PAIRS[event]
    deployments = {deployment.slug: deployment for deployment in DEPLOYMENTS}
    center = deployments[center_slug]
    south = deployments[south_slug]
    center_depth = read_valid_daily_depths(output_dir / f"{center_slug}.daily.csv")
    south_depth = read_valid_daily_depths(output_dir / f"{south_slug}.daily.csv")
    rows, summary = compare_center_to_south_timeseries(
        center_depth,
        south_depth,
        eruption_date=eruption_date,
        center_lat_lon_deg=(center.latitude, center.longitude),
        south_lat_lon_deg=(south.latitude, south.longitude),
    )
    summary.update(
        {
            "center_station": center.station,
            "south_station": south.station,
            "daily_data_source": "original raw NCEI or MGDS BPR channels",
            "center_raw_channel": center.raw_channel,
            "south_raw_channel": south.raw_channel,
            "static_elastic_memory_included": False,
            "publication_observations_used": False,
        }
    )

    csv_path = output_dir / f"historical_mogi_timeseries_{event}.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary_path = output_dir / f"historical_mogi_timeseries_{event}.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"wrote {csv_path} and {summary_path}")
    return summary


def plot_comparisons(output_dir: Path) -> tuple[Path, Path]:
    """Plot raw South observations against daily Center-fit Mogi predictions."""
    figure, axes = plt.subplots(2, 1, figsize=(11.5, 8.0), sharex=False)
    colors = {"observed": "#0072B2", "predicted": "#D55E00"}
    deployments = {deployment.slug: deployment for deployment in DEPLOYMENTS}
    for axis, event in zip(axes, EVENT_PAIRS, strict=True):
        path = output_dir / f"historical_mogi_timeseries_{event}.csv"
        with path.open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        times = [date.fromisoformat(row["time_utc"][:10]) for row in rows]
        observed = [float(row["south_observed_uplift_m"]) for row in rows]
        predicted = [float(row["south_predicted_uplift_m"]) for row in rows]
        eruption_date = EVENT_PAIRS[event][0]
        axis.plot(times, observed, color=colors["observed"], linewidth=0.9, label="South observed")
        axis.plot(
            times,
            predicted,
            color=colors["predicted"],
            linewidth=1.1,
            label="South predicted from daily Center fit",
        )
        axis.axvline(eruption_date, color="#555555", linewidth=0.9, linestyle="--")
        axis.axhline(0.0, color="#555555", linewidth=0.6)
        center_station = deployments[EVENT_PAIRS[event][1]].station
        south_station = deployments[EVENT_PAIRS[event][2]].station
        axis.set_title(
            f"{eruption_date.year}: {center_station} fit; {south_station} held out"
        )
        axis.set_ylabel("Relative elevation (m; up positive)")
        axis.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        axis.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        axis.grid(True, color="#D9D9D9", linewidth=0.55)
        axis.legend(frameon=False, loc="best")
    axes[-1].set_xlabel("Date (UTC)")
    figure.suptitle(
        "Static elastic Mogi time-series check from original raw BPR channels\n"
        "Daily Center calibration; South held out; no tide or drift correction"
    )
    figure.autofmt_xdate()
    figure.tight_layout()
    stem = output_dir / "historical_mogi_timeseries"
    png_path = stem.with_suffix(".png")
    pdf_path = stem.with_suffix(".pdf")
    figure.savefig(png_path, dpi=220)
    figure.savefig(pdf_path)
    plt.close(figure)
    return png_path, pdf_path


def main() -> None:
    """Compare and plot the shared raw BPR intervals for both eruption events."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROCESSED_DIR,
        help="directory containing daily CSVs and receiving local comparison files",
    )
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for event in EVENT_PAIRS:
        _write_event(event, args.output_dir)
    png_path, pdf_path = plot_comparisons(args.output_dir)
    print(f"wrote {png_path} and {pdf_path}")


if __name__ == "__main__":
    main()
