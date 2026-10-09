"""Plot fixed-base and diagnostic Winkler surface compliance."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SUMMARY = ROOT / "data" / "processed" / "winkler_foundation_check.json"
DEFAULT_OUTPUT_STEM = ROOT / "figures" / "winkler_foundation_check"


def plot_foundation_check(summary_path: Path, output_stem: Path) -> tuple[Path, Path]:
    """Plot central and eastern vertical compliance for a static unit load."""
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if summary.get("converged") is not True:
        raise ValueError("Winkler summary must record a converged outer iteration")

    stiffness_pa_per_m = float(summary["area_stiffness_pa_per_m"])
    station_names = ("Central", "Eastern")
    fixed_base = np.asarray(
        [
            summary["fixed_base_central_vertical_compliance_m_per_mpa"],
            summary["fixed_base_east_vertical_compliance_m_per_mpa"],
        ],
        dtype=float,
    )
    winkler = np.asarray(
        [
            summary["central_vertical_compliance_m_per_mpa"],
            summary["east_vertical_compliance_m_per_mpa"],
        ],
        dtype=float,
    )
    if (
        not math.isfinite(stiffness_pa_per_m)
        or stiffness_pa_per_m <= 0.0
        or not np.all(np.isfinite(fixed_base))
        or not np.all(np.isfinite(winkler))
        or np.any(fixed_base <= 0.0)
        or np.any(winkler <= 0.0)
    ):
        raise ValueError("Winkler summary contains invalid compliance values")

    compliance_mm_per_mpa = np.vstack((fixed_base, winkler)) * 1_000.0
    fractional_change_pct = (winkler / fixed_base - 1.0) * 100.0
    positions = np.arange(len(station_names), dtype=float)
    width = 0.34
    colors = ("#4477AA", "#CC6677")

    figure, axis = plt.subplots(figsize=(7.2, 4.4), constrained_layout=True)
    fixed_bars = axis.bar(
        positions - width / 2,
        compliance_mm_per_mpa[0],
        width,
        color=colors[0],
        label="Fixed base",
    )
    winkler_bars = axis.bar(
        positions + width / 2,
        compliance_mm_per_mpa[1],
        width,
        color=colors[1],
        label="Iterated Winkler",
    )
    axis.bar_label(fixed_bars, fmt="%.2f", padding=3, fontsize=8)
    axis.bar_label(
        winkler_bars,
        labels=[f"{value:.2f}\n{change:+.1f}%" for value, change in zip(
            compliance_mm_per_mpa[1], fractional_change_pct, strict=True
        )],
        padding=3,
        fontsize=8,
    )
    axis.set_xticks(positions, station_names)
    axis.set_ylabel("Vertical compliance (mm/MPa)")
    axis.set_title("Fixed-base and diagnostic Winkler response")
    axis.text(
        0.5,
        0.96,
        f"Area stiffness = {stiffness_pa_per_m:.3g} Pa/m; 1 MPa cavity load",
        transform=axis.transAxes,
        ha="center",
        va="bottom",
        fontsize=8,
    )
    axis.grid(axis="y", color="#999999", alpha=0.25, linewidth=0.6)
    axis.set_axisbelow(True)
    axis.legend(frameon=False, loc="upper left")
    axis.set_ylim(0.0, float(np.max(compliance_mm_per_mpa) * 1.3))

    output_stem.parent.mkdir(parents=True, exist_ok=True)
    png_path = output_stem.with_suffix(".png")
    pdf_path = output_stem.with_suffix(".pdf")
    figure.savefig(png_path, dpi=220, bbox_inches="tight")
    figure.savefig(pdf_path, bbox_inches="tight")
    plt.close(figure)
    return png_path, pdf_path


def main() -> None:
    """Read a converged check summary and write PNG and PDF figures."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--output-stem", type=Path, default=DEFAULT_OUTPUT_STEM)
    args = parser.parse_args()
    png_path, pdf_path = plot_foundation_check(args.summary, args.output_stem)
    print(f"wrote {png_path} and {pdf_path}")


if __name__ == "__main__":
    main()
