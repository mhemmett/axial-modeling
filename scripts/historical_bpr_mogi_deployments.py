"""Check long raw BPR deployment overlaps with a static Mogi response."""

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

DEPLOYMENT_PAIRS = {
    "1995_1996": ("wc68_1995", "wc69_1995"),
    "2003_2005": ("nemo_2003_2005_center", "nemo_2003_2005_south"),
    "2007_2009": ("nemo_2007_2010_center", "nemo_2005_2009_south2"),
    "2011_2013": ("nemo_2011_2013_center", "nemo_2011_2013_south"),
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


def write_comparison(
    name: str,
    center_slug: str,
    south_slug: str,
    deployments: dict,
    output_dir: Path,
) -> dict[str, object]:
    """Write one first-seven-days-baseline deployment comparison."""
    center = deployments[center_slug]
    south = deployments[south_slug]
    center_depth = read_valid_daily_depths(output_dir / f"{center_slug}.daily.csv")
    south_depth = read_valid_daily_depths(output_dir / f"{south_slug}.daily.csv")
    rows, summary = compare_center_to_south_timeseries(
        center_depth,
        south_depth,
        center_lat_lon_deg=(center.latitude, center.longitude),
        south_lat_lon_deg=(south.latitude, south.longitude),
    )
    summary.update(
        {
            "comparison": name,
            "center_station": center.station,
            "south_station": south.station,
            "daily_data_source": "original raw NCEI or MGDS BPR channels",
            "center_raw_channel": center.raw_channel,
            "south_raw_channel": south.raw_channel,
            "static_elastic_memory_included": False,
            "publication_observations_used": False,
        }
    )
    csv_path = output_dir / f"historical_mogi_deployments_{name}.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    json_path = output_dir / f"historical_mogi_deployments_{name}.json"
    json_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"wrote {csv_path} and {json_path}")
    return summary


def plot_comparisons(output_dir: Path, deployments: dict) -> tuple[Path, Path]:
    """Plot original South channels and static Center-fit Mogi predictions."""
    figure, axes = plt.subplots(
        len(DEPLOYMENT_PAIRS),
        1,
        figsize=(11.5, 3.3 * len(DEPLOYMENT_PAIRS)),
        constrained_layout=True,
    )
    colors = {"observed": "#0072B2", "predicted": "#D55E00"}
    for axis, (name, (center_slug, south_slug)) in zip(
        axes, DEPLOYMENT_PAIRS.items(), strict=True
    ):
        path = output_dir / f"historical_mogi_deployments_{name}.csv"
        with path.open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        times = [date.fromisoformat(row["time_utc"][:10]) for row in rows]
        observed = [float(row["south_observed_uplift_m"]) for row in rows]
        predicted = [float(row["south_predicted_uplift_m"]) for row in rows]
        axis.plot(times, observed, color=colors["observed"], linewidth=0.75, label="South observed")
        axis.plot(
            times,
            predicted,
            color=colors["predicted"],
            linewidth=0.95,
            label="South predicted from daily Center fit",
        )
        center = deployments[center_slug]
        south = deployments[south_slug]
        axis.set_title(f"{name.replace('_', '–')}: {center.station}; {south.station}")
        axis.set_ylabel("Relative elevation (m; up positive)")
        axis.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
        axis.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        axis.grid(True, color="#D9D9D9", linewidth=0.55)
        axis.legend(frameon=False, loc="best")
    axes[-1].set_xlabel("Date (UTC)")
    figure.suptitle(
        "Static elastic Mogi checks across raw non-OOI BPR deployments\n"
        "Each interval uses its first seven paired days as baseline; no tide or drift correction"
    )
    figure.autofmt_xdate()
    stem = output_dir / "historical_mogi_deployment_checks"
    png_path = stem.with_suffix(".png")
    pdf_path = stem.with_suffix(".pdf")
    figure.savefig(png_path, dpi=220)
    figure.savefig(pdf_path)
    plt.close(figure)
    return png_path, pdf_path


def main() -> None:
    """Check overlapping pre-eruption and post-eruption raw deployments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROCESSED_DIR,
        help="directory with ignored daily series and receiving comparison outputs",
    )
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    deployments = {deployment.slug: deployment for deployment in DEPLOYMENTS}
    for name, (center_slug, south_slug) in DEPLOYMENT_PAIRS.items():
        write_comparison(name, center_slug, south_slug, deployments, args.output_dir)
    png_path, pdf_path = plot_comparisons(args.output_dir, deployments)
    print(f"wrote {png_path} and {pdf_path}")


if __name__ == "__main__":
    main()
