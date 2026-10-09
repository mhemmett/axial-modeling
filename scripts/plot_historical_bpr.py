"""Plot raw non-OOI BPR observations around the 1998 and 2011 eruptions."""

from __future__ import annotations

import argparse
import csv
import statistics
from datetime import date, timedelta
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from axialstress.historical_bpr import DEPLOYMENTS, PROCESSED_DIR


def read_daily(path: Path) -> list[dict[str, str]]:
    """Read one daily historical BPR file and validate its output schema."""
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        expected = [
            "time_utc",
            "raw_channel_mean",
            "raw_channel_unit",
            "equivalent_depth_m",
            "relative_uplift_m",
            "sample_count",
            "coverage_fraction",
        ]
        if reader.fieldnames != expected:
            raise ValueError(f"unexpected daily BPR schema in {path}")
        return list(reader)


def _event_series(deployment, output_dir: Path) -> tuple[list[int], list[float]]:
    """Return daily uplift relative to the seven days before an eruption."""
    if deployment.eruption_date is None:
        raise ValueError(f"{deployment.station} has no eruption window")
    rows = read_daily(output_dir / f"{deployment.slug}.daily.csv")
    by_date = {
        date.fromisoformat(row["time_utc"][:10]): row
        for row in rows
        if row["relative_uplift_m"]
    }
    pre_window = [
        float(by_date[deployment.eruption_date + timedelta(days=offset)]["equivalent_depth_m"])
        for offset in range(-7, 0)
        if deployment.eruption_date + timedelta(days=offset) in by_date
    ]
    if len(pre_window) < 5:
        raise ValueError(f"{deployment.station} has too few pre-eruption daily means")
    reference_depth = statistics.median(pre_window)
    offsets = []
    uplift = []
    for day, row in by_date.items():
        offset = (day - deployment.eruption_date).days
        if -21 <= offset <= 21:
            offsets.append(offset)
            uplift.append(reference_depth - float(row["equivalent_depth_m"]))
    ordered = sorted(zip(offsets, uplift, strict=True))
    return [item[0] for item in ordered], [item[1] for item in ordered]


def plot_event_windows(output_dir: Path) -> tuple[Path, Path]:
    """Write event-centered figures from independent raw deployments."""
    output_dir.mkdir(parents=True, exist_ok=True)
    figure, axes = plt.subplots(1, 2, figsize=(11.2, 4.8), constrained_layout=True)
    groups = [
        (date(1998, 1, 25), [DEPLOYMENTS[0]], "January 1998"),
        (date(2011, 4, 6), [DEPLOYMENTS[2], DEPLOYMENTS[3]], "April 2011"),
    ]
    colors = {
        "wc82a_1997": "#0072B2",
        "nemo_2009_2011_south": "#D55E00",
        "nemo_2010_2011_center": "#009E73",
    }
    for axis, (event_date, deployments, title) in zip(axes, groups, strict=True):
        for deployment in deployments:
            offsets, uplift = _event_series(deployment, output_dir)
            axis.plot(
                offsets,
                uplift,
                linewidth=1.15,
                marker=".",
                markersize=2.5,
                color=colors[deployment.slug],
                label=deployment.station,
            )
        axis.axvline(0, color="#555555", linewidth=0.9, linestyle="--")
        axis.axhline(0, color="#555555", linewidth=0.7)
        axis.set_title(title)
        axis.set_xlabel(f"Days from {event_date.isoformat()} eruption date (UTC)")
        axis.set_xlim(-21, 21)
        axis.grid(True, color="#D9D9D9", linewidth=0.55)
        axis.legend(frameon=False, loc="best")
    axes[0].set_ylabel("Relative seafloor elevation (m; up positive)")
    figure.suptitle(
        "Axial eruption intervals from raw non-OOI BPR channels\n"
        "15-second records averaged by UTC day; no tide or drift correction"
    )
    stem = output_dir / "historical_bpr_eruption_windows"
    png_path = stem.with_suffix(".png")
    pdf_path = stem.with_suffix(".pdf")
    figure.savefig(png_path, dpi=220)
    figure.savefig(pdf_path)
    plt.close(figure)
    return png_path, pdf_path


def main() -> None:
    """Plot already processed daily data in the ignored output directory."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROCESSED_DIR,
        help="directory containing daily CSVs and receiving local figures",
    )
    args = parser.parse_args()
    png, pdf = plot_event_windows(args.output_dir)
    print(f"wrote {png} and {pdf}")


if __name__ == "__main__":
    main()
