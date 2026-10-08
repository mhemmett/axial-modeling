"""Plot independent OOI Central and Eastern Caldera relative-uplift series."""

from __future__ import annotations

import argparse
from datetime import UTC
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np

from axialstress.bpr_observations import (
    BprSeries,
    latest_processed_bpr_path,
    read_processed_bpr_series,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_STEM = ROOT / "figures" / "ooi_bpr_relative_uplift"


def _label(series: BprSeries) -> str:
    finite_values = series.uplift_m[np.isfinite(series.uplift_m)]
    if finite_values.size == 0:
        raise ValueError(f"{series.site} BPR series has no finite uplift values")
    codes = ", ".join(sorted(set(series.quality_codes)))
    return (
        f"{series.site.title()} Caldera ({series.times_utc[0]:%Y-%m}–"
        f"{series.times_utc[-1]:%Y-%m}; QC {codes})"
    )


def plot_series(
    central: BprSeries,
    east: BprSeries,
    output_stem: Path,
) -> tuple[Path, Path]:
    """Write PNG and PDF plots of the two independently referenced series."""
    output_stem.parent.mkdir(parents=True, exist_ok=True)
    figure, axis = plt.subplots(figsize=(10.5, 5.6), constrained_layout=True)
    axis.plot(
        central.times_utc,
        central.uplift_m,
        color="#0072B2",
        linewidth=0.8,
        alpha=0.78,
        label=_label(central),
    )
    axis.plot(
        east.times_utc,
        east.uplift_m,
        color="#D55E00",
        linewidth=0.8,
        alpha=0.78,
        label=_label(east),
    )
    axis.axhline(0.0, color="#555555", linewidth=0.8, linestyle="--", zorder=0)
    axis.set_title("Independent OOI bottom-pressure observations")
    axis.set_xlabel(
        "Date (UTC)\nEach site is referenced to its first available sample. "
        "QC codes are retained; code 2 is not evaluated."
    )
    axis.set_ylabel("Relative seafloor uplift (m)")
    axis.grid(True, color="#D9D9D9", linewidth=0.55)
    axis.xaxis.set_major_locator(mdates.YearLocator(2, tz=UTC))
    axis.xaxis.set_major_formatter(mdates.DateFormatter("%Y", tz=UTC))
    axis.legend(frameon=False, loc="upper left")
    png_path = output_stem.with_suffix(".png")
    pdf_path = output_stem.with_suffix(".pdf")
    figure.savefig(png_path, dpi=220)
    figure.savefig(pdf_path)
    plt.close(figure)
    return png_path, pdf_path


def main() -> None:
    """Plot the latest processed series or explicitly selected inputs."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--central", type=Path, help="processed Central Caldera CSV")
    parser.add_argument("--east", type=Path, help="processed Eastern Caldera CSV")
    parser.add_argument(
        "--output-stem",
        type=Path,
        default=DEFAULT_OUTPUT_STEM,
        help="output path without extension (default: figures/ooi_bpr_relative_uplift)",
    )
    args = parser.parse_args()
    central_path = args.central or latest_processed_bpr_path("central")
    east_path = args.east or latest_processed_bpr_path("east")
    central = read_processed_bpr_series("central", central_path)
    east = read_processed_bpr_series("east", east_path)
    png_path, pdf_path = plot_series(central, east, args.output_stem)
    for series, path in ((central, central_path), (east, east_path)):
        finite = series.uplift_m[np.isfinite(series.uplift_m)]
        print(
            f"{series.site}: {len(finite)} finite of {len(series.uplift_m)} records, "
            f"{series.times_utc[0].date()} to {series.times_utc[-1].date()}, "
            f"last relative uplift {finite[-1]:.6g} m, source {path}"
        )
    print(f"wrote {png_path} and {pdf_path}")


if __name__ == "__main__":
    main()
