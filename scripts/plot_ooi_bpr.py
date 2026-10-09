"""Plot independent OOI Central and Eastern Caldera relative-uplift series."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"
DEFAULT_OUTPUT_STEM = ROOT / "figures" / "ooi_bpr_relative_uplift"
EXPECTED_HEADER = [
    "time_utc",
    "signed_depth_m",
    "relative_uplift_m",
    "ooi_qc_aggregate",
]


@dataclass(frozen=True)
class BprSeries:
    """One processed daily OOI bottom-pressure series."""

    site: str
    times_utc: tuple[datetime, ...]
    uplift_m: np.ndarray
    quality_codes: tuple[str, ...]


def _latest_processed_file(site: str) -> Path:
    matches = sorted(PROCESSED_DIR.glob(f"{site}_*.relative-uplift.csv"))
    if not matches:
        raise FileNotFoundError(
            f"no processed {site} BPR series found under {PROCESSED_DIR}; "
            "fetch and process the authorized OOI records first"
        )
    return matches[-1]


def read_processed_series(site: str, path: Path) -> BprSeries:
    """Read a processed OOI series and validate its time and value columns."""
    times: list[datetime] = []
    uplift: list[float] = []
    quality_codes: list[str] = []
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != EXPECTED_HEADER:
            raise ValueError(f"unexpected processed BPR header in {path}")
        for row_number, row in enumerate(reader, start=2):
            try:
                time = datetime.fromisoformat(row["time_utc"].replace("Z", "+00:00"))
                value = float(row["relative_uplift_m"])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"invalid BPR row {row_number} in {path}") from exc
            if time.tzinfo is None or time.utcoffset() != UTC.utcoffset(time):
                raise ValueError(f"BPR timestamps must be UTC in {path}")
            if np.isinf(value):
                raise ValueError(f"BPR uplift must not be infinite in {path}")
            times.append(time)
            uplift.append(value)
            quality_codes.append(row["ooi_qc_aggregate"])

    if not times:
        raise ValueError(f"processed BPR series has no rows: {path}")
    if any(later <= earlier for earlier, later in zip(times, times[1:], strict=False)):
        raise ValueError(f"BPR timestamps must be strictly increasing in {path}")
    return BprSeries(site, tuple(times), np.asarray(uplift), tuple(quality_codes))


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
    central_path = args.central or _latest_processed_file("central")
    east_path = args.east or _latest_processed_file("east")
    central = read_processed_series("central", central_path)
    east = read_processed_series("east", east_path)
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
