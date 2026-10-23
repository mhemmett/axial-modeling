"""Plot a source-output-free analogue of Cabaniss et al. Figure 4."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import reconstruct_center_pressure as center

from axialstress.paper_bpr import file_sha256

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "processed" / "source_value_bpr_failure_2011_2015"
OUTPUT = ROOT / "figures" / "source_value_figure4_pressure_volume"
STYLES = (
    ("constant_maxwell", "Non-TD Maxwell", "#4b9a69", "o"),
    ("thermal_maxwell", "Thermal Maxwell", "#c44d50", "d"),
    ("hydrothermal_maxwell", "Hydrothermal Maxwell", "#d7a43a", "^"),
)


def _read_csv(path: Path) -> list[dict[str, str]]:
    """Read a nonempty generated time series from local storage."""
    with path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise ValueError(f"empty model or BPR series: {path}")
    return rows


def _observed_segments(
    processed_dir: Path, dates: list[datetime]
) -> dict[str, tuple[list[datetime], np.ndarray]]:
    """Keep each Center deployment at its own observed depth datum."""
    observations, _, _ = center._load_observations(processed_dir, dates)
    grouped = defaultdict(list)
    for item in observations:
        grouped[item.deployment].append(item)
    segments = {}
    for slug, records in grouped.items():
        records.sort(key=lambda item: item.time_index)
        first_depth_m = records[0].depth_m
        segments[slug] = (
            [dates[item.time_index] for item in records],
            np.asarray([first_depth_m - item.depth_m for item in records]),
        )
    return segments


def main() -> None:
    """Save pressure and PyLith cavity-volume panels with observed BPR segments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=INPUT)
    parser.add_argument(
        "--processed-dir", type=Path, default=ROOT / "data/processed/paper_center_bpr"
    )
    parser.add_argument("--output-stem", type=Path, default=OUTPUT)
    args = parser.parse_args()
    args.input_dir = args.input_dir.resolve()
    args.processed_dir = args.processed_dir.resolve()
    args.output_stem = args.output_stem.resolve()
    source_summary_path = args.input_dir / "summary.json"
    source = json.loads(source_summary_path.read_text(encoding="utf-8"))
    volume = json.loads((args.input_dir / "volume_summary.json").read_text(encoding="utf-8"))
    if (
        source.get("status") != "conditional_bpr_failure_reconstruction_temporally_unresolved"
        or volume.get("source_summary_sha256") != file_sha256(source_summary_path)
        or volume.get("paper_output_data_used") is not False
    ):
        raise ValueError("volume and BPR reconstructions have different provenance")
    dates = center._grid(7)
    observations = _observed_segments(args.processed_dir, dates)
    event_utc = datetime.fromisoformat(source["eruption_utc"])

    fig, axes = plt.subplots(2, 1, figsize=(7.2, 6.0), sharex=True, layout="constrained")
    observed_axes = [ax.twinx() for ax in axes]
    for ax in axes:
        ax.axvspan(dates[0], event_utc, color="#e9f3f7", zorder=0)
        ax.grid(axis="y", color="0.84", linewidth=0.5)
        ax.spines[["top", "right"]].set_visible(False)
    for ax in observed_axes:
        ax.spines[["top", "left"]].set_visible(False)
        for slug, (sample_dates, uplift_m) in observations.items():
            ax.plot(
                sample_dates,
                uplift_m,
                color="0.38",
                linewidth=0.8,
                marker=".",
                markersize=2.0,
                alpha=0.75,
                label="Observed BPR, separate datums" if slug == center.SOURCE_SLUGS[0] else None,
                zorder=1,
            )
        ax.set_ylabel("Deployment-relative uplift (m)", color="0.35")
        ax.tick_params(axis="y", colors="0.35")

    for case, label, color, marker in STYLES:
        case_summary = source["cases"][case]
        pressure_path = args.input_dir / case_summary["pressure_failure_csv"]
        volume_path = args.input_dir / volume["cases"][case]["volume_history_csv"]
        if volume["cases"][case]["pressure_series_sha256"] != file_sha256(
            pressure_path
        ):
            raise ValueError(f"pressure and volume inputs differ for {case}")
        pressure_rows = _read_csv(pressure_path)
        volume_rows = _read_csv(volume_path)
        if len(pressure_rows) != len(volume_rows):
            raise ValueError(f"pressure and volume lengths differ for {case}")
        case_dates = [datetime.fromisoformat(row["time_utc"]) for row in pressure_rows]
        volume_dates = [datetime.fromisoformat(row["time_utc"]) for row in volume_rows]
        if case_dates != volume_dates:
            raise ValueError(f"pressure and volume dates differ for {case}")
        pressure_mpa = np.asarray(
            [float(row["pressure_change_mpa"]) for row in pressure_rows]
        )
        low_mpa = np.asarray(
            [float(row["pressure_weight_0p1_mpa"]) for row in pressure_rows]
        )
        high_mpa = np.asarray(
            [float(row["pressure_weight_10_mpa"]) for row in pressure_rows]
        )
        cavity_change_km3 = np.asarray(
            [float(row["first_order_volume_change_km3"]) for row in volume_rows]
        )
        axes[0].fill_between(
            case_dates,
            np.minimum(low_mpa, high_mpa),
            np.maximum(low_mpa, high_mpa),
            color=color,
            alpha=0.12,
            linewidth=0,
            zorder=2,
        )
        axes[0].plot(
            case_dates, pressure_mpa, color=color, marker=marker, markersize=2.0,
            markevery=8, linewidth=1.2, label=label, zorder=3,
        )
        axes[1].plot(
            case_dates, cavity_change_km3, color=color, marker=marker, markersize=2.0,
            markevery=8, linewidth=1.2, zorder=3,
        )
        first_failure = next(
            (
                case_dates[index]
                for index, row in enumerate(pressure_rows)
                if row["joint_failure_zero_tensile_strength"] == "True"
            ),
            None,
        )
        if first_failure is not None:
            for ax in axes:
                ax.axvline(first_failure, color=color, linestyle=":", linewidth=1.0)
    for ax in axes:
        ax.axvline(event_utc, color="0.2", linestyle="--", linewidth=1.0)
        ax.plot(
            event_utc,
            1.015,
            marker="*",
            markersize=9,
            color="0.2",
            transform=ax.get_xaxis_transform(),
            clip_on=False,
        )
    axes[0].set_ylabel("Reservoir pressure change (MPa)")
    axes[1].set_ylabel("PyLith cavity-volume increase (km$^3$)")
    axes[1].set_xlabel("Year")
    axes[0].set_title("a  Pressure inferred from Center BPR", loc="left", fontsize=10)
    axes[1].set_title("b  Reservoir expansion calculated from PyLith", loc="left", fontsize=10)
    axes[0].legend(frameon=False, fontsize=8, loc="upper left")
    axes[1].xaxis.set_major_locator(mdates.YearLocator())
    axes[1].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    args.output_stem.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output_stem.with_suffix(".pdf"))
    fig.savefig(args.output_stem.with_suffix(".png"), dpi=200)
    plt.close(fig)
    print(f"wrote {args.output_stem.with_suffix('.pdf')}")


if __name__ == "__main__":
    main()
