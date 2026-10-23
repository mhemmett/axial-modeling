"""Plot cited Center BPR observations without joining deployment datums."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np

from axialstress.paper_bpr import file_sha256

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "processed" / "paper_center_bpr"
OUTPUT = ROOT / "figures" / "report_figure2_center_bpr"
SUMMARY = ROOT / "data" / "processed" / "report_figure2_center_bpr_summary.json"


def _selected_observations(
    input_dir: Path,
) -> tuple[list[tuple[str, list[datetime], np.ndarray]], dict[str, object]]:
    """Return recorded noon depths, preserving each archived deployment."""
    summary_path = input_dir / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if (
        summary.get("status") != "observations_exported"
        or summary.get("model_outputs_used") is not False
        or summary.get("common_datum_verified") is not False
    ):
        raise ValueError("Center BPR export has unexpected provenance")
    deployments = []
    inputs = {}
    for record in summary["deployments"]:
        path = Path(record["output_file"]).resolve()
        if path.parent != input_dir or file_sha256(path) != record["output_sha256"]:
            raise ValueError(f"Center BPR file does not match its provenance: {path}")
        dates = []
        depths = []
        with path.open(encoding="utf-8", newline="") as stream:
            for row in csv.DictReader(stream):
                instant = datetime.fromisoformat(row["time_utc"])
                if instant.hour == 12 and instant.minute == 0 and instant.second == 0:
                    dates.append(instant)
                    depths.append(float(row["observed_depth_m"]))
        if len(dates) < 2 or not np.all(np.isfinite(depths)):
            raise ValueError(f"too few finite noon observations in {path}")
        if any(right <= left for left, right in zip(dates[:-1], dates[1:], strict=True)):
            raise ValueError(f"Center BPR dates are not increasing in {path}")
        uplift_m = depths[0] - np.asarray(depths)
        deployments.append((record["deployment"], dates, uplift_m))
        inputs[record["deployment"]] = {
            "source_doi": record["source_doi"],
            "source_channel": record["source_channel"],
            "hourly_export_sha256": record["output_sha256"],
            "selected_noon_samples": len(dates),
            "first_selected_time_utc": dates[0].isoformat(),
            "last_selected_time_utc": dates[-1].isoformat(),
        }
    return deployments, {
        "paper_output_data_used": False,
        "model_output_data_used": False,
        "observations_are_deployment_relative": True,
        "input_summary_sha256": file_sha256(summary_path),
        "deployments": inputs,
    }


def _plot_unjoined(
    ax: plt.Axes, dates: list[datetime], uplift_m: np.ndarray, color: str
) -> None:
    """Draw only contiguous observed daily samples from one deployment."""
    start = 0
    for index in range(1, len(dates) + 1):
        if index == len(dates) or dates[index] - dates[index - 1] > timedelta(days=2):
            ax.plot(
                dates[start:index],
                uplift_m[start:index],
                color=color,
                linewidth=0.9,
            )
            start = index


def main() -> None:
    """Save a partial Cabaniss Figure 2 analogue from cited BPR samples."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=INPUT)
    parser.add_argument("--output-stem", type=Path, default=OUTPUT)
    parser.add_argument("--summary", type=Path, default=SUMMARY)
    args = parser.parse_args()
    input_dir = args.input_dir.resolve()
    output_stem = args.output_stem.resolve()
    summary_path = args.summary.resolve()
    deployments, provenance = _selected_observations(input_dir)
    fig, (history, coverage) = plt.subplots(
        2,
        1,
        figsize=(8.0, 5.4),
        sharex=True,
        gridspec_kw={"height_ratios": [3.2, 1.3]},
        layout="constrained",
    )
    first_date = min(item[1][0] for item in deployments)
    last_date = max(item[1][-1] for item in deployments)
    for ax in (history, coverage):
        ax.axvspan(
            datetime(2011, 4, 6, tzinfo=UTC),
            datetime(2015, 4, 24, tzinfo=UTC),
            color="#e9f3f7",
            zorder=0,
        )
        ax.set_xlim(first_date - timedelta(days=100), last_date + timedelta(days=100))
        ax.grid(axis="y", color="0.88", linewidth=0.5)
        ax.spines[["top", "right"]].set_visible(False)
    history.axhline(0.0, color="0.6", linewidth=0.7)
    for index, (_slug, dates, uplift_m) in enumerate(deployments):
        _plot_unjoined(history, dates, uplift_m, "0.2" if index % 2 == 0 else "0.48")
        coverage.scatter(
            dates,
            np.full(len(dates), index),
            marker="|",
            s=11,
            linewidths=0.55,
            color="0.3",
        )
    for event, label in (
        (datetime(2011, 4, 6, tzinfo=UTC), "2011"),
        (datetime(2015, 4, 24, tzinfo=UTC), "2015"),
    ):
        history.axvline(event, color="#a14a39", linestyle="--", linewidth=0.8)
        history.text(
            event,
            0.98,
            label,
            ha="right",
            va="top",
            rotation=90,
            transform=history.get_xaxis_transform(),
            color="#853b2d",
            fontsize=8,
        )
    history.axvspan(
        datetime(1998, 1, 1, tzinfo=UTC),
        datetime(1998, 2, 1, tzinfo=UTC),
        color="#a14a39",
        alpha=0.17,
    )
    history.text(
        datetime(1998, 1, 15, tzinfo=UTC),
        0.98,
        "Jan. 1998",
        ha="left",
        va="top",
        rotation=90,
        transform=history.get_xaxis_transform(),
        color="#853b2d",
        fontsize=8,
    )
    coverage.set_yticks(range(len(deployments)))
    coverage.set_yticklabels(
        [slug.replace("nemo_", "").replace("fox_wc81_", "") for slug, _, _ in deployments],
        fontsize=7,
    )
    coverage.set_ylim(-0.7, len(deployments) - 0.3)
    coverage.invert_yaxis()
    history.set_ylabel("Deployment-relative uplift (m)")
    coverage.set_ylabel("Center deployment")
    coverage.set_xlabel("Year")
    history.set_title("a  Observed Center BPR deformation", loc="left", fontsize=10)
    coverage.set_title("b  Recorded noon samples and datum boundaries", loc="left", fontsize=10)
    coverage.xaxis.set_major_locator(mdates.YearLocator(2))
    coverage.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    output_stem.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_stem.with_suffix(".pdf"))
    fig.savefig(output_stem.with_suffix(".png"), dpi=200)
    plt.close(fig)
    provenance["output_files"] = [
        str(output_stem.with_suffix(suffix)) for suffix in (".pdf", ".png")
    ]
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {output_stem.with_suffix('.pdf')}")


if __name__ == "__main__":
    main()
