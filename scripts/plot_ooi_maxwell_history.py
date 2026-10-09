"""Plot the OOI-constrained Maxwell response and failure diagnostics."""

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
from numpy.typing import NDArray

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SUMMARY = ROOT / "data/processed/ooi_maxwell_ellipsoid_summary.json"
DEFAULT_TIMESERIES = ROOT / "data/processed/ooi_maxwell_ellipsoid_timeseries.csv"
DEFAULT_OUTPUT_STEM = ROOT / "figures/ooi_maxwell_failure_history"
SECONDS_PER_YEAR = 365.25 * 24.0 * 3600.0
TIMESERIES_FIELDS = (
    "elapsed_years",
    "time_s",
    "inferred_pressure_change_mpa",
    "central_ooi_monthly_mean_uplift_m",
    "central_pylith_uplift_m",
    "east_ooi_monthly_mean_uplift_m",
    "east_pylith_uplift_m",
)


def _read_timeseries(path: Path) -> dict[str, NDArray[np.float64]]:
    """Read and validate saved OOI observations and Maxwell outputs."""
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != TIMESERIES_FIELDS:
            raise ValueError(f"unexpected OOI Maxwell columns in {path}")
        rows = list(reader)
    if len(rows) < 2:
        raise ValueError("the OOI Maxwell history requires at least two records")
    values: dict[str, NDArray[np.float64]] = {}
    for field in TIMESERIES_FIELDS:
        try:
            column = np.asarray([float(row[field]) for row in rows], dtype=float)
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"invalid {field} values in {path}") from exc
        if not np.all(np.isfinite(column)):
            raise ValueError(f"{field} contains non-finite values in {path}")
        values[field] = column
    if np.any(np.diff(values["time_s"]) <= 0.0):
        raise ValueError("OOI Maxwell output times must increase strictly")
    return values


def _read_failure_records(
    summary_path: Path, times_s: NDArray[np.float64]
) -> tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.bool_]]:
    """Read failure metrics and align them with the saved Maxwell times."""
    with summary_path.open(encoding="utf-8") as stream:
        summary = json.load(stream)
    diagnostic = summary.get("failure_threshold_diagnostic", {})
    records = diagnostic.get("records", [])
    if len(records) != len(times_s):
        raise ValueError("failure diagnostics and Maxwell time-series lengths differ")
    record_times = np.asarray([record["time_s"] for record in records], dtype=float)
    if not np.allclose(record_times, times_s, rtol=0.0, atol=1.0e-7):
        raise ValueError("failure diagnostics do not align with Maxwell output times")
    yield_counts = np.asarray(
        [record["mohr_coulomb_shear_yield_cell_count"] for record in records],
        dtype=float,
    )
    tensile_stress_mpa = np.asarray(
        [record["maximum_cavity_tensile_stress_pa"] for record in records],
        dtype=float,
    ) / 1.0e6
    connected_path = np.asarray(
        [record["cavity_to_surface_shear_path_found"] for record in records],
        dtype=bool,
    )
    if not np.all(np.isfinite(yield_counts)) or not np.all(np.isfinite(tensile_stress_mpa)):
        raise ValueError("failure diagnostics contain non-finite values")
    return yield_counts, tensile_stress_mpa, connected_path


def plot_history(
    summary_path: Path,
    timeseries_path: Path,
    output_stem: Path,
) -> tuple[Path, Path]:
    """Write a diagnostic plot from saved OOI and PyLith outputs."""
    values = _read_timeseries(timeseries_path)
    yield_counts, tensile_stress_mpa, connected_path = _read_failure_records(
        summary_path, values["time_s"]
    )
    with summary_path.open(encoding="utf-8") as stream:
        summary = json.load(stream)
    start_time = datetime.fromisoformat(summary["input_record_start_utc"])
    if start_time.tzinfo is None:
        raise ValueError("the OOI observation start time must include a timezone")
    start_time = start_time.astimezone(UTC)
    dates = [
        start_time + timedelta(seconds=float(years) * SECONDS_PER_YEAR)
        for years in values["elapsed_years"]
    ]

    figure, axes = plt.subplots(
        3, 1, figsize=(11.0, 9.0), sharex=True, constrained_layout=True
    )
    uplift_axis, pressure_axis, failure_axis = axes
    uplift_axis.plot(
        dates,
        values["central_ooi_monthly_mean_uplift_m"],
        color="#0072B2",
        linewidth=1.1,
        label="Central OOI",
    )
    uplift_axis.plot(
        dates,
        values["central_pylith_uplift_m"],
        color="#0072B2",
        linewidth=1.5,
        linestyle="--",
        label="Central PyLith",
    )
    uplift_axis.plot(
        dates,
        values["east_ooi_monthly_mean_uplift_m"],
        color="#D55E00",
        linewidth=1.1,
        label="Eastern OOI",
    )
    uplift_axis.plot(
        dates,
        values["east_pylith_uplift_m"],
        color="#D55E00",
        linewidth=1.5,
        linestyle="--",
        label="Eastern PyLith",
    )
    uplift_axis.set_ylabel("Relative uplift (m)")
    uplift_axis.legend(frameon=False, ncol=2, loc="upper left")
    uplift_axis.grid(True, color="#D9D9D9", linewidth=0.55)

    pressure_axis.plot(
        dates,
        values["inferred_pressure_change_mpa"],
        color="#009E73",
        linewidth=1.2,
    )
    pressure_axis.axhline(0.0, color="#555555", linewidth=0.8, linestyle=":")
    pressure_axis.set_ylabel("Inferred pressure change (MPa)")
    pressure_axis.grid(True, color="#D9D9D9", linewidth=0.55)

    failure_axis.plot(
        dates,
        yield_counts,
        color="#CC79A7",
        linewidth=1.2,
        label="Mohr–Coulomb yield cells",
    )
    failure_axis.scatter(
        np.asarray(dates, dtype=object)[connected_path],
        yield_counts[connected_path],
        color="#D55E00",
        s=13,
        zorder=3,
        label="Cavity-to-surface shear path",
    )
    failure_axis.set_ylabel("Yielding cells")
    failure_axis.set_xlabel("Date (UTC)")
    failure_axis.grid(True, color="#D9D9D9", linewidth=0.55)
    tensile_axis = failure_axis.twinx()
    tensile_axis.plot(
        dates,
        tensile_stress_mpa,
        color="#0072B2",
        linewidth=1.0,
        alpha=0.8,
        label="Maximum cavity tensile stress",
    )
    tensile_axis.set_ylabel("Maximum tensile stress (MPa)")
    handles, labels = failure_axis.get_legend_handles_labels()
    extra_handles, extra_labels = tensile_axis.get_legend_handles_labels()
    failure_axis.legend(
        handles + extra_handles,
        labels + extra_labels,
        frameon=False,
        ncol=2,
        loc="upper left",
    )

    axes[-1].xaxis.set_major_locator(mdates.YearLocator(2, tz=UTC))
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%Y", tz=UTC))
    figure.suptitle(
        summary.get("plot_title", "OOI-constrained one-branch Maxwell diagnostic")
    )
    plot_note = summary.get(
        "plot_note",
        "OOI QC 2 (NOT_EVALUATED) retained. Pressure uses static elastic Central compliance. "
        "Failure uses C = 1 MPa, 25° directly, zero pore pressure, and no tensile cutoff. "
        "The 2,761-tetrahedron compliance is not mesh-converged.",
    )
    figure.text(
        0.01,
        -0.015,
        plot_note,
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
    """Plot saved OOI Maxwell output with explicit diagnostic assumptions."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--timeseries", type=Path, default=DEFAULT_TIMESERIES)
    parser.add_argument(
        "--output-stem",
        type=Path,
        default=DEFAULT_OUTPUT_STEM,
        help="output path without extension",
    )
    args = parser.parse_args()
    png_path, pdf_path = plot_history(args.summary, args.timeseries, args.output_stem)
    print(f"wrote {png_path} and {pdf_path}")


if __name__ == "__main__":
    main()
