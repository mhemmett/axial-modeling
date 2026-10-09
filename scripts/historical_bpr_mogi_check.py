"""Compare raw historical BPR event changes with a Mogi spatial response."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import math
import statistics
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np

from axialstress.historical_bpr_check import EVENT_WINDOWS, mogi_vertical_response_ratio

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_DIR = ROOT / "data" / "processed" / "historical_bpr"
DEFAULT_SUMMARY = DEFAULT_INPUT_DIR / "mogi_check_summary.json"
DEFAULT_SERIES = DEFAULT_INPUT_DIR / "mogi_check_series.csv"
DEFAULT_FIGURE_STEM = DEFAULT_INPUT_DIR / "historical_bpr_mogi_check"


def read_daily_file(path: Path) -> dict[dt.date, float]:
    """Read daily raw-depth medians from an ignored local CSV file."""
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        required = {"time_utc", "daily_median_raw_depth_m"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError(f"unexpected daily BPR columns in {path}")
        rows = {
            dt.date.fromisoformat(row["time_utc"]): float(
                row["daily_median_raw_depth_m"]
            )
            for row in reader
        }
    if not rows or not all(math.isfinite(value) for value in rows.values()):
        raise ValueError(f"daily BPR depths are empty or non-finite in {path}")
    return rows


def _event_series(
    event: str,
    input_dir: Path,
    source_records: list[dict[str, object]],
) -> dict[str, object]:
    """Fit the Mogi center response and evaluate the south BPR time series."""
    center_path = input_dir / f"{event}_center_daily_raw_depth.csv"
    south_path = input_dir / f"{event}_south_daily_raw_depth.csv"
    center_depth = read_daily_file(center_path)
    south_depth = read_daily_file(south_path)
    windows = EVENT_WINDOWS[event]
    dates = sorted(
        day
        for day in center_depth.keys() & south_depth.keys()
        if windows["pre_start"] <= day < windows["post_end"]
    )
    if not dates:
        raise ValueError(f"no common daily center/south records for {event}")
    pre_dates = [day for day in dates if windows["pre_start"] <= day < windows["pre_end"]]
    if len(pre_dates) < 3:
        raise ValueError(f"fewer than three common pre-event days for {event}")
    center_baseline = statistics.median(center_depth[day] for day in pre_dates)
    south_baseline = statistics.median(south_depth[day] for day in pre_dates)
    center_uplift = np.asarray([center_baseline - center_depth[day] for day in dates])
    south_uplift = np.asarray([south_baseline - south_depth[day] for day in dates])

    center_record = next(
        item for item in source_records if item["event"] == event and item["site"] == "center"
    )
    south_record = next(
        item for item in source_records if item["event"] == event and item["site"] == "south"
    )
    ratio = mogi_vertical_response_ratio(
        (float(south_record["latitude_deg"]), float(south_record["longitude_deg"])),
        (float(center_record["latitude_deg"]), float(center_record["longitude_deg"])),
    )
    south_prediction = ratio * center_uplift
    residual = south_uplift - south_prediction
    denominator = float(np.linalg.norm(south_uplift))
    correlation = (
        float(np.corrcoef(south_uplift, south_prediction)[0, 1])
        if np.std(south_uplift) > 0.0 and np.std(south_prediction) > 0.0
        else None
    )
    return {
        "event": event,
        "dates_utc": dates,
        "center_observed_uplift_m": center_uplift,
        "south_observed_uplift_m": south_uplift,
        "south_predicted_uplift_m": south_prediction,
        "south_residual_m": residual,
        "center_coordinates_lat_lon_deg": [
            center_record["latitude_deg"],
            center_record["longitude_deg"],
        ],
        "south_coordinates_lat_lon_deg": [
            south_record["latitude_deg"],
            south_record["longitude_deg"],
        ],
        "mogi_south_to_center_vertical_ratio": ratio,
        "center_pre_event_baseline_depth_m": center_baseline,
        "south_pre_event_baseline_depth_m": south_baseline,
        "common_record_count": len(dates),
        "south_rmse_m": float(np.sqrt(np.mean(residual**2))),
        "south_relative_l2_error": (
            float(np.linalg.norm(residual) / denominator) if denominator > 0.0 else None
        ),
        "south_correlation": correlation,
        "event_change_observed_center_m": float(center_uplift[-1]),
        "event_change_observed_south_m": float(south_uplift[-1]),
        "event_change_predicted_south_m": float(south_prediction[-1]),
        "assumptions": {
            "source_axis": "center BPR location",
            "source_depth_m": 4000.0,
            "source_radius_m": 700.0,
            "youngs_modulus_pa": 60.0e9,
            "poisson_ratio": 0.25,
            "measurement": "UTC daily median of uncorrected raw depth; no tide or drift correction",
        },
    }


def write_outputs(results: list[dict[str, object]], summary_path: Path, series_path: Path) -> None:
    """Write scalar model-check metrics and aligned event-window series."""
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    series_path.parent.mkdir(parents=True, exist_ok=True)
    summary = {
        "method": "homogeneous elastic Mogi spatial response fit at center BPR",
        "source_data": "MGDS archive raw-depth columns only; no paper-produced series used",
        "created_utc": dt.datetime.now(dt.UTC).isoformat(),
        "events": [
            {key: value for key, value in result.items() if key not in {
                "dates_utc", "center_observed_uplift_m", "south_observed_uplift_m",
                "south_predicted_uplift_m", "south_residual_m",
            }}
            for result in results
        ],
    }
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    with series_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(
            [
                "event",
                "time_utc",
                "center_observed_uplift_m",
                "south_observed_uplift_m",
                "south_mogi_prediction_m",
                "south_residual_m",
            ]
        )
        for result in results:
            for index, day in enumerate(result["dates_utc"]):
                writer.writerow(
                    [
                        result["event"],
                        day.isoformat(),
                        f"{result['center_observed_uplift_m'][index]:.12g}",
                        f"{result['south_observed_uplift_m'][index]:.12g}",
                        f"{result['south_predicted_uplift_m'][index]:.12g}",
                        f"{result['south_residual_m'][index]:.12g}",
                    ]
                )


def plot_results(results: list[dict[str, object]], path_stem: Path) -> tuple[Path, Path]:
    """Plot observed center/south changes and held-out Mogi predictions."""
    path_stem.parent.mkdir(parents=True, exist_ok=True)
    figure, axes = plt.subplots(2, 1, figsize=(10, 8.0), sharex=False)
    for axis, result in zip(axes, results, strict=True):
        dates = result["dates_utc"]
        axis.plot(
            dates,
            result["center_observed_uplift_m"],
            label="Center observed",
            color="#0072B2",
        )
        axis.plot(
            dates,
            result["south_observed_uplift_m"],
            label="South observed",
            color="#D55E00",
        )
        axis.plot(
            dates,
            result["south_predicted_uplift_m"],
            label="South Mogi prediction from center",
            color="#009E73",
            linestyle="--",
        )
        axis.set_title(f"{result['event']} eruption window")
        axis.set_ylabel("Relative vertical change (m; up positive)")
        axis.grid(True, color="#D9D9D9", linewidth=0.55)
        axis.legend(frameon=False, loc="best")
        axis.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    axes[-1].set_xlabel("Date (UTC)")
    figure.suptitle("Historical Axial BPR Spatial Check Against an Elastic Mogi Source")
    figure.text(
        0.5,
        0.015,
        "Daily median raw depth; no tide or drift correction. Mogi source at center BPR: "
        "depth 4 km, radius 0.7 km, E = 60 GPa, ν = 0.25. "
        "Data: MGDS 10.1594/IEDA/322344 and 10.1594/IEDA/322282.",
        ha="center",
        va="bottom",
        fontsize=8,
        wrap=True,
    )
    figure.tight_layout(rect=(0.0, 0.07, 1.0, 0.95))
    png_path = path_stem.with_suffix(".png")
    pdf_path = path_stem.with_suffix(".pdf")
    figure.savefig(png_path, dpi=220)
    figure.savefig(pdf_path)
    plt.close(figure)
    return png_path, pdf_path


def main() -> None:
    """Fit the central BPR event history and check the south BPR response."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--series", type=Path, default=DEFAULT_SERIES)
    parser.add_argument("--figure-stem", type=Path, default=DEFAULT_FIGURE_STEM)
    args = parser.parse_args()
    processing_manifest = args.input_dir / "processing_manifest.json"
    if not processing_manifest.is_file():
        raise SystemExit(
            f"missing {processing_manifest}; run data/process_historical_bpr.py first"
        )
    source_records = json.loads(processing_manifest.read_text(encoding="utf-8"))["records"]
    results = [
        _event_series(event, args.input_dir, source_records) for event in ("1998", "2011")
    ]
    write_outputs(results, args.summary, args.series)
    png_path, pdf_path = plot_results(results, args.figure_stem)
    for result in results:
        print(
            f"{result['event']}: Mogi south/center ratio="
            f"{result['mogi_south_to_center_vertical_ratio']:.4f}; "
            f"south RMSE={result['south_rmse_m']:.3f} m; "
            f"relative L2={result['south_relative_l2_error']:.3f}; "
            f"correlation={result['south_correlation']:.3f}"
        )
    print(f"wrote {args.summary}, {args.series}, {png_path}, and {pdf_path}")


if __name__ == "__main__":
    main()
