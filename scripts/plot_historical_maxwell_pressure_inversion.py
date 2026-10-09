"""Plot Maxwell-kernel pressure inversions of raw 1998 and 2011 BPR records."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import UTC, datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = (
    ROOT / "data" / "processed" / "axial_historical_bpr" / "maxwell_pressure_inversion"
)
DEFAULT_OUTPUT_STEM = ROOT / "figures" / "historical_maxwell_pressure_inversion"
FIELDS = (
    "time_utc",
    "elapsed_days",
    "inferred_pressure_change_mpa",
    "center_observed_uplift_m",
    "center_pylith_uplift_m",
    "south_observed_uplift_m",
    "south_pylith_uplift_m",
)


def _read_event(data_dir: Path, event: str) -> tuple[dict[str, object], dict[str, np.ndarray]]:
    """Read one saved historical inversion summary and time series."""
    summary_path = data_dir / f"{event}_summary.json"
    timeseries_path = data_dir / f"{event}_timeseries.csv"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    with timeseries_path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != FIELDS:
            raise ValueError(f"unexpected historical inversion columns in {timeseries_path}")
        rows = list(reader)
    if len(rows) < 2:
        raise ValueError(f"historical {event} inversion requires at least two records")
    dates = [datetime.fromisoformat(row["time_utc"]) for row in rows]
    if any(stamp.tzinfo is None or stamp.utcoffset() != UTC.utcoffset(stamp) for stamp in dates):
        raise ValueError(f"historical {event} times must be UTC")
    values = {
        field: np.asarray([float(row[field]) for row in rows], dtype=float)
        for field in FIELDS[1:]
    }
    if any(not np.all(np.isfinite(column)) for column in values.values()):
        raise ValueError(f"historical {event} inversion contains non-finite values")
    if np.any(np.diff(values["elapsed_days"]) <= 0.0):
        raise ValueError(f"historical {event} inversion times must increase")
    values["dates"] = np.asarray(dates, dtype=object)
    return summary, values


def plot_inversions(data_dir: Path, output_stem: Path) -> tuple[Path, Path]:
    """Write event-window uplift and inferred-pressure comparisons."""
    events = [(event, *_read_event(data_dir, event)) for event in ("1998", "2011")]
    figure, axes = plt.subplots(2, 2, figsize=(11.0, 7.4), constrained_layout=True)
    for row, (event, summary, values) in enumerate(events):
        uplift_axis, pressure_axis = axes[row]
        dates = values["dates"]
        eruption_time = datetime.fromisoformat(summary["eruption_date_utc"]).replace(
            tzinfo=UTC
        )
        uplift_axis.plot(
            dates,
            values["center_observed_uplift_m"],
            color="#0072B2",
            linewidth=1.0,
            label=f"{summary['source_records']['center']['station']} raw",
        )
        uplift_axis.plot(
            dates,
            values["center_pylith_uplift_m"],
            color="#0072B2",
            linewidth=1.4,
            linestyle="--",
            label="Central PyLith fit",
        )
        uplift_axis.plot(
            dates,
            values["south_observed_uplift_m"],
            color="#D55E00",
            linewidth=1.0,
            label=f"{summary['source_records']['south']['station']} raw",
        )
        uplift_axis.plot(
            dates,
            values["south_pylith_uplift_m"],
            color="#D55E00",
            linewidth=1.4,
            linestyle="--",
            label="South PyLith holdout",
        )
        uplift_axis.axvline(
            eruption_time,
            color="#555555",
            linewidth=0.8,
            linestyle=":",
        )
        uplift_axis.set_ylabel("Relative uplift (m)")
        uplift_axis.set_title(
            f"{event} eruption: Center RMSE "
            f"{summary['center_forward_metrics']['rmse_m']:.3f} m; South RMSE "
            f"{summary['south_holdout_metrics']['rmse_m']:.3f} m"
        )
        uplift_axis.legend(frameon=False, ncol=2, fontsize=8)
        uplift_axis.grid(True, color="#D9D9D9", linewidth=0.55)

        pressure_axis.plot(
            dates,
            values["inferred_pressure_change_mpa"],
            color="#009E73",
            linewidth=1.2,
        )
        pressure_axis.axhline(0.0, color="#555555", linewidth=0.8, linestyle=":")
        pressure_axis.axvline(
            eruption_time,
            color="#555555",
            linewidth=0.8,
            linestyle=":",
        )
        pressure_axis.set_ylabel("Inferred pressure change (MPa)")
        pressure_axis.grid(True, color="#D9D9D9", linewidth=0.55)

        for axis in (uplift_axis, pressure_axis):
            axis.xaxis.set_major_locator(mdates.MonthLocator(interval=2, tz=UTC))
            axis.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y", tz=UTC))
        if row == 1:
            uplift_axis.set_xlabel("Date (UTC); vertical dotted line marks the eruption")
            pressure_axis.set_xlabel("Date (UTC)")

    figure.suptitle("Raw Axial BPR Maxwell-Kernel Pressure Inversions")
    figure.text(
        0.01,
        -0.01,
        "Only original NCEI and MGDS pressure channels are used. Weekly interpolation, "
        "single-branch rheology, GCV smoothing, and the coarse nonconverged mesh are assumptions. "
        "Raw daily means retain tides, ocean variability, and instrument drift.",
        ha="left",
        va="top",
        fontsize=8,
    )
    output_stem.parent.mkdir(parents=True, exist_ok=True)
    png_path = output_stem.with_suffix(".png")
    pdf_path = output_stem.with_suffix(".pdf")
    figure.savefig(png_path, dpi=220, bbox_inches="tight")
    figure.savefig(pdf_path, bbox_inches="tight")
    plt.close(figure)
    return png_path, pdf_path


def main() -> None:
    """Plot saved raw historical BPR pressure-inversion results."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--output-stem", type=Path, default=DEFAULT_OUTPUT_STEM)
    arguments = parser.parse_args()
    png_path, pdf_path = plot_inversions(arguments.data_dir, arguments.output_stem)
    print(f"wrote {png_path} and {pdf_path}")


if __name__ == "__main__":
    main()
