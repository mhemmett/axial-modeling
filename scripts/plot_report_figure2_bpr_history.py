"""Plot cited Center BPR observations with documented display-only splices."""

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
BOUNDARY_NOON_SAMPLES = 2
OVERLAP_MATCH_DAYS = 30
GAP_EDGE_DAYS = 7
PRE_1998_START = datetime(1998, 1, 18, 12, tzinfo=UTC)
PRE_1998_END = datetime(1998, 1, 24, 12, tzinfo=UTC)
PRE_2011_START = datetime(2011, 3, 30, 12, tzinfo=UTC)
PRE_2011_END = datetime(2011, 4, 5, 12, tzinfo=UTC)


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
        if len(dates) < 2 * BOUNDARY_NOON_SAMPLES + GAP_EDGE_DAYS or not np.all(
            np.isfinite(depths)
        ):
            raise ValueError(f"too few finite noon observations in {path}")
        if any(right <= left for left, right in zip(dates[:-1], dates[1:], strict=True)):
            raise ValueError(f"Center BPR dates are not increasing in {path}")
        dates = dates[BOUNDARY_NOON_SAMPLES:-BOUNDARY_NOON_SAMPLES]
        depths = depths[BOUNDARY_NOON_SAMPLES:-BOUNDARY_NOON_SAMPLES]
        uplift_m = depths[0] - np.asarray(depths)
        deployments.append((record["deployment"], dates, uplift_m))
        inputs[record["deployment"]] = {
            "source_doi": record["source_doi"],
            "source_channel": record["source_channel"],
            "hourly_export_sha256": record["output_sha256"],
            "selected_noon_samples": len(dates),
            "boundary_noon_samples_removed_per_end": BOUNDARY_NOON_SAMPLES,
            "first_selected_time_utc": dates[0].isoformat(),
            "last_selected_time_utc": dates[-1].isoformat(),
        }
    return deployments, {
        "paper_output_data_used": False,
        "model_output_data_used": False,
        "source_observations_have_separate_datums": True,
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


def _splice_deployments(
    deployments: list[tuple[str, list[datetime], np.ndarray]],
    inputs: dict[str, dict[str, object]],
    *,
    gap_1998_2000_uplift_m: float = 0.0,
) -> tuple[list[tuple[str, list[datetime], np.ndarray]], list[dict[str, object]]]:
    """Align overlaps and apply a stated 1998–2000 gap uplift assumption."""
    if not np.isfinite(gap_1998_2000_uplift_m):
        raise ValueError("1998–2000 gap uplift must be finite")
    aligned = []
    transitions = []
    for slug, dates, local_uplift_m in deployments:
        if not aligned:
            aligned.append((slug, dates, local_uplift_m))
            continue
        prior_slug, prior_dates, prior_uplift_m = aligned[-1]
        if dates[0] <= prior_dates[0]:
            raise ValueError("Center deployments are not ordered by start date")
        prior_by_date = dict(zip(prior_dates, prior_uplift_m, strict=True))
        current_by_date = dict(zip(dates, local_uplift_m, strict=True))
        common_dates = sorted(prior_by_date.keys() & current_by_date.keys())
        if common_dates:
            if len(common_dates) < OVERLAP_MATCH_DAYS:
                raise ValueError("too few paired noon observations for an overlap splice")
            prior_corrected = inputs[prior_slug]["source_channel"] == "DriftCorrLPFDep"
            current_corrected = inputs[slug]["source_channel"] == "DriftCorrLPFDep"
            if prior_corrected and not current_corrected:
                handoff = prior_dates[-1]
                match_dates = common_dates[-OVERLAP_MATCH_DAYS:]
            elif current_corrected and not prior_corrected:
                handoff = dates[0]
                match_dates = common_dates[:OVERLAP_MATCH_DAYS]
            else:
                handoff = common_dates[len(common_dates) // 2]
                nearest = sorted(common_dates, key=lambda day: abs(day - handoff))[
                    :OVERLAP_MATCH_DAYS
                ]
                match_dates = sorted(nearest)
            differences_m = np.asarray(
                [prior_by_date[day] - current_by_date[day] for day in match_dates]
            )
            offset_m = float(np.median(differences_m))
            residual_m = differences_m - offset_m
            if handoff == dates[0]:
                keep_prior = [day < handoff for day in prior_dates]
                keep_current = [day >= handoff for day in dates]
            else:
                keep_prior = [day <= handoff for day in prior_dates]
                keep_current = [day > handoff for day in dates]
            aligned[-1] = (
                prior_slug,
                [day for day, keep in zip(prior_dates, keep_prior, strict=True) if keep],
                prior_uplift_m[keep_prior],
            )
            current_dates = [day for day, keep in zip(dates, keep_current, strict=True) if keep]
            current_uplift_m = local_uplift_m[keep_current] + offset_m
            transition = {
                "prior_deployment": prior_slug,
                "deployment": slug,
                "method": "median paired noon uplift around overlap handoff",
                "handoff_utc": handoff.isoformat(),
                "paired_days": len(match_dates),
                "paired_start_utc": match_dates[0].isoformat(),
                "paired_end_utc": match_dates[-1].isoformat(),
                "paired_residual_median_absolute_deviation_m": float(
                    np.median(np.abs(residual_m))
                ),
                "offset_m": offset_m,
            }
        else:
            gap_days = (dates[0] - prior_dates[-1]).total_seconds() / 86400.0
            if gap_days <= 0.0:
                raise ValueError("Center deployments overlap without paired noon samples")
            prior_window_m = float(np.median(prior_uplift_m[-GAP_EDGE_DAYS:]))
            current_window_m = float(np.median(local_uplift_m[:GAP_EDGE_DAYS]))
            gap_uplift_m = (
                gap_1998_2000_uplift_m
                if prior_slug == "fox_wc81_1997_center"
                and slug == "nemo_2000_2002_center_processed" else 0.0
            )
            offset_m = prior_window_m - current_window_m + gap_uplift_m
            current_dates = dates
            current_uplift_m = local_uplift_m + offset_m
            transition = {
                "prior_deployment": prior_slug,
                "deployment": slug,
                "method": "align medians of seven recorded noon values at each gap edge",
                "gap_days": gap_days,
                "gap_net_deformation_assumption_m": gap_uplift_m,
                "prior_window_median_uplift_m": prior_window_m,
                "current_window_median_uplift_m": current_window_m,
                "offset_m": offset_m,
            }
        if not aligned[-1][1] or not current_dates:
            raise ValueError("a Center BPR handoff removed an entire deployment")
        aligned.append((slug, current_dates, current_uplift_m))
        transitions.append(transition)
    return aligned, transitions


def _pre_event_median(
    aligned: list[tuple[str, list[datetime], np.ndarray]],
    start: datetime,
    end: datetime,
) -> float:
    """Return the median of seven recorded pre-eruption noon uplift samples."""
    values = [
        float(value)
        for _slug, dates, uplift in aligned
        for date, value in zip(dates, uplift, strict=True)
        if start <= date <= end
    ]
    if len(values) != 7:
        raise ValueError("pre-eruption level requires seven recorded noon samples")
    return float(np.median(values))


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
    zero_gap, _ = _splice_deployments(deployments, provenance["deployments"])
    pre_1998_m = _pre_event_median(zero_gap, PRE_1998_START, PRE_1998_END)
    pre_2011_zero_gap_m = _pre_event_median(
        zero_gap, PRE_2011_START, PRE_2011_END
    )
    gap_uplift_m = pre_1998_m - pre_2011_zero_gap_m
    aligned, transitions = _splice_deployments(
        deployments, provenance["deployments"],
        gap_1998_2000_uplift_m=gap_uplift_m,
    )
    if not np.isclose(
        _pre_event_median(aligned, PRE_2011_START, PRE_2011_END), pre_1998_m,
        rtol=0.0, atol=1.0e-9,
    ):
        raise ValueError("equal pre-eruption level assumption was not applied")
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
    history.axhline(pre_1998_m, color="#8f6c46", linestyle=":", linewidth=0.8)
    for index, (_slug, dates, uplift_m) in enumerate(aligned):
        _plot_unjoined(history, dates, uplift_m, "0.2" if index % 2 == 0 else "0.48")
    for index, (_slug, dates, _uplift_m) in enumerate(deployments):
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
    history.set_ylabel("Spliced relative uplift (m)")
    coverage.set_ylabel("Center deployment")
    coverage.set_xlabel("Year")
    history.set_title(
        "a  Observed Center BPR segments; equal-level gap scenario",
        loc="left", fontsize=10,
    )
    coverage.set_title(
        "b  Recorded noon samples and deployment boundaries", loc="left", fontsize=10
    )
    coverage.xaxis.set_major_locator(mdates.YearLocator(2))
    coverage.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    output_stem.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_stem.with_suffix(".pdf"))
    fig.savefig(output_stem.with_suffix(".png"), dpi=200)
    plt.close(fig)
    provenance["output_files"] = [
        str(
            output_stem.with_suffix(suffix).relative_to(ROOT)
            if output_stem.with_suffix(suffix).is_relative_to(ROOT)
            else output_stem.with_suffix(suffix)
        )
        for suffix in (".pdf", ".png")
    ]
    provenance["display_only_splice"] = False
    provenance["gap_assumption_used_for_historical_pressure_fit"] = True
    provenance["absolute_vertical_datum_verified"] = False
    provenance["equal_pre_1998_2011_level_assumption"] = {
        "source": "Chadwick et al. (2012) time-predictable scenario",
        "source_url": "https://www.nature.com/articles/ngeo1464",
        "not_directly_observed_due_to_1998_2000_gap": True,
        "pre_1998_window_utc": [PRE_1998_START.isoformat(), PRE_1998_END.isoformat()],
        "pre_2011_window_utc": [PRE_2011_START.isoformat(), PRE_2011_END.isoformat()],
        "pre_1998_median_relative_uplift_m": pre_1998_m,
        "pre_2011_zero_gap_median_relative_uplift_m": pre_2011_zero_gap_m,
        "required_1998_2000_gap_uplift_m": gap_uplift_m,
    }
    provenance["splice_transitions"] = transitions
    provenance["plotted_segments"] = {
        slug: {
            "first_plotted_noon_utc": dates[0].isoformat(),
            "last_plotted_noon_utc": dates[-1].isoformat(),
            "plotted_noon_samples": len(dates),
        }
        for slug, dates, _uplift_m in aligned
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {output_stem.with_suffix('.pdf')}")


if __name__ == "__main__":
    main()
