"""Calibrate the PyLith ellipsoid response with authorized OOI BPR data."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import UTC
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import h5py
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np

from axialstress.bpr_observations import (
    latest_processed_bpr_path,
    read_processed_bpr_series,
)
from axialstress.ellipsoid_bpr_calibration import (
    calibrate_ellipsoid_to_bpr,
    read_ellipsoid_unit_response,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STEP_DIR = ROOT / "pylith" / "step05_ellipsoid_elastic"
DEFAULT_OUTPUT_DIR = ROOT / "data" / "processed"
DEFAULT_FIGURE_STEM = ROOT / "figures" / "ooi_ellipsoid_elastic_calibration"


def _write_series_csv(path: Path, result) -> None:
    """Write aligned observations, elastic predictions, pressure, and OOI flags."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(
            [
                "time_utc",
                "central_relative_uplift_m",
                "central_elastic_fit_m",
                "east_relative_uplift_m",
                "east_elastic_prediction_m",
                "east_residual_m",
                "inferred_pressure_change_mpa",
                "central_ooi_qc_aggregate",
                "east_ooi_qc_aggregate",
            ]
        )
        for index, time in enumerate(result.times_utc):
            writer.writerow(
                [
                    time.isoformat().replace("+00:00", "Z"),
                    f"{result.central_uplift_m[index]:.12g}",
                    f"{result.central_prediction_m[index]:.12g}",
                    f"{result.east_uplift_m[index]:.12g}",
                    f"{result.east_prediction_m[index]:.12g}",
                    f"{result.east_residual_m[index]:.12g}",
                    f"{result.pressure_change_mpa[index]:.12g}",
                    result.central_quality_codes[index],
                    result.east_quality_codes[index],
                ]
            )


def _plot_result(result, path_stem: Path) -> tuple[Path, Path]:
    """Plot calibration, held-out uplift, and inferred elastic pressure."""
    path_stem.parent.mkdir(parents=True, exist_ok=True)
    figure, axes = plt.subplots(
        3, 1, figsize=(10.5, 8.6), sharex=True, constrained_layout=True
    )
    times = result.times_utc
    axes[0].plot(
        times,
        result.central_uplift_m,
        color="#0072B2",
        linewidth=0.9,
        label="Central observed",
    )
    axes[0].plot(
        times,
        result.central_prediction_m,
        color="#000000",
        linewidth=0.6,
        linestyle="--",
        label="Central elastic fit",
    )
    axes[0].set_ylabel("Central Δu (m)")
    axes[0].legend(frameon=False, loc="upper left")

    axes[1].plot(
        times,
        result.east_uplift_m,
        color="#D55E00",
        linewidth=0.9,
        label="Eastern observed",
    )
    axes[1].plot(
        times,
        result.east_prediction_m,
        color="#009E73",
        linewidth=0.9,
        label="Eastern prediction from Central fit",
    )
    axes[1].set_ylabel("Eastern Δu (m)")
    axes[1].legend(frameon=False, loc="upper left")

    axes[2].plot(times, result.pressure_change_mpa, color="#CC79A7", linewidth=0.9)
    axes[2].set_ylabel("Inferred ΔP (MPa)")
    axes[2].set_xlabel(
        "Date (UTC)\nStatic PyLith elastic ellipsoid; E = 50 GPa, ν = 0.25 assumed; "
        "1 MPa unit load. OOI QC flags retained."
    )
    for axis in axes:
        axis.grid(True, color="#D9D9D9", linewidth=0.55)
        axis.xaxis.set_major_locator(mdates.YearLocator(2, tz=UTC))
        axis.xaxis.set_major_formatter(mdates.DateFormatter("%Y", tz=UTC))
    figure.suptitle("Independent OOI BPR check of the elastic ellipsoid response")
    png_path = path_stem.with_suffix(".png")
    pdf_path = path_stem.with_suffix(".pdf")
    figure.savefig(png_path, dpi=220)
    figure.savefig(pdf_path)
    plt.close(figure)
    return png_path, pdf_path


def _validate_material_output(path: Path) -> None:
    """Confirm PyLith wrote a finite, nonzero Cauchy-stress field."""
    with h5py.File(path, "r") as material:
        if "cell_fields/cauchy_stress" not in material:
            raise ValueError(f"PyLith Cauchy stress is missing from {path}")
        stress = np.asarray(material["cell_fields/cauchy_stress"], dtype=float)
    if not np.all(np.isfinite(stress)) or np.max(np.abs(stress)) <= 0.0:
        raise ValueError(f"PyLith Cauchy stress is non-finite or zero in {path}")


def main() -> None:
    """Run the unit-response calibration against Central and Eastern OOI BPRs."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--central", type=Path)
    parser.add_argument("--east", type=Path)
    parser.add_argument(
        "--surface-hdf5", type=Path, default=DEFAULT_STEP_DIR / "output" / "ellipsoid-surface.h5"
    )
    parser.add_argument(
        "--material-hdf5", type=Path, default=DEFAULT_STEP_DIR / "output" / "ellipsoid-material.h5"
    )
    parser.add_argument(
        "--csv-output",
        type=Path,
        default=DEFAULT_OUTPUT_DIR / "ooi_ellipsoid_elastic_calibration.csv",
    )
    parser.add_argument(
        "--summary-output",
        type=Path,
        default=DEFAULT_OUTPUT_DIR / "ooi_ellipsoid_elastic_calibration_summary.json",
    )
    parser.add_argument("--figure-stem", type=Path, default=DEFAULT_FIGURE_STEM)
    args = parser.parse_args()

    central_path = args.central or latest_processed_bpr_path("central")
    east_path = args.east or latest_processed_bpr_path("east")
    central_bpr = read_processed_bpr_series("central", central_path)
    east_bpr = read_processed_bpr_series("east", east_path)
    _validate_material_output(args.material_hdf5)
    central_response, east_response = read_ellipsoid_unit_response(args.surface_hdf5)
    if not np.all(np.isfinite([central_response[2], east_response[2]])):
        raise SystemExit("PyLith unit response contains a non-finite vertical displacement")

    result = calibrate_ellipsoid_to_bpr(
        central_bpr,
        east_bpr,
        central_unit_response_m=float(central_response[2]),
        east_unit_response_m=float(east_response[2]),
    )
    _write_series_csv(args.csv_output, result)
    args.summary_output.parent.mkdir(parents=True, exist_ok=True)
    args.summary_output.write_text(
        json.dumps(result.summary(), indent=2) + "\n", encoding="utf-8"
    )
    png_path, pdf_path = _plot_result(result, args.figure_stem)
    print(json.dumps(result.summary(), indent=2))
    print(f"wrote {args.csv_output}, {args.summary_output}, {png_path}, and {pdf_path}")


if __name__ == "__main__":
    main()
