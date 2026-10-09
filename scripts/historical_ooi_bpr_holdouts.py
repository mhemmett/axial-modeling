"""Check raw 2017–18 MGDS BPRs against an OOI Central ellipsoid fit."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import date, datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np

from axialstress.bpr_mogi_calibration import (
    CENTRAL_CALDERA_LAT_LON_DEG,
    local_east_north_offset_m,
)
from axialstress.bpr_observations import (
    latest_processed_bpr_path,
    read_processed_bpr_series,
)
from axialstress.ellipsoid_bpr_calibration import read_ellipsoid_unit_response
from axialstress.historical_bpr import DEPLOYMENTS, PROCESSED_DIR

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SURFACE = (
    ROOT / "pylith" / "step05_ellipsoid_elastic" / "output" / "ellipsoid-surface.h5"
)
DEFAULT_OUTPUT_DIR = PROCESSED_DIR / "ooi_2017_2018_raw_bpr_holdouts"
DEFAULT_FIGURE_STEM = ROOT / "figures" / "ooi_2017_2018_raw_bpr_holdouts"
HOLDOUT_SLUGS = (
    "minibpr_2017_2018_ax303",
    "minibpr_2017_2018_ax105",
    "minibpr_2017_2018_ax302",
    "minibpr_2017_2018_ax307",
    "nemo_2017_2018_north",
    "nemo_2017_2018_west",
)
AX105_ANOMALY_START = date(2017, 11, 25)
AX105_ANOMALY_END = date(2017, 12, 11)


def read_daily_depths(path: Path) -> dict[date, float]:
    """Read finite UTC daily depths from one original MGDS channel."""
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        expected = {
            "time_utc",
            "equivalent_depth_m",
            "relative_uplift_m",
        }
        if reader.fieldnames is None or not expected.issubset(reader.fieldnames):
            raise ValueError(f"unexpected daily BPR schema in {path}")
        depths = {}
        for row_number, row in enumerate(reader, start=2):
            if not row["relative_uplift_m"]:
                continue
            try:
                day = date.fromisoformat(row["time_utc"][:10])
                depth_m = float(row["equivalent_depth_m"])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"invalid daily BPR row {row_number} in {path}") from exc
            if not np.isfinite(depth_m):
                raise ValueError(f"nonfinite daily BPR depth at row {row_number} in {path}")
            depths[day] = depth_m
    return depths


def metrics(observed_m: np.ndarray, predicted_m: np.ndarray) -> dict[str, float | None]:
    """Summarize static model residuals in meters and unitless correlation."""
    residual_m = predicted_m - observed_m
    correlation = (
        float(np.corrcoef(observed_m, predicted_m)[0, 1])
        if np.std(observed_m) > 0.0 and np.std(predicted_m) > 0.0
        else None
    )
    return {
        "rmse_m": float(np.sqrt(np.mean(residual_m**2))),
        "bias_m": float(np.mean(residual_m)),
        "correlation": correlation,
    }


def run(
    *,
    surface_hdf5: Path,
    output_dir: Path,
    figure_stem: Path,
) -> dict[str, object]:
    """Fit static pressure to OOI Central and compare raw MGDS holdouts."""
    if not surface_hdf5.is_file():
        raise FileNotFoundError(surface_hdf5)
    if not (PROCESSED_DIR / "summary.json").is_file():
        raise FileNotFoundError(
            f"missing historical raw daily data under {PROCESSED_DIR}; "
            "run make historical-bpr-daily"
        )

    ooi_path = latest_processed_bpr_path("central")
    central = read_processed_bpr_series("central", ooi_path)
    central_by_day = {
        timestamp.date(): float(uplift)
        for timestamp, uplift in zip(central.times_utc, central.uplift_m, strict=True)
        if np.isfinite(uplift)
    }
    central_qc = {
        timestamp.date(): quality
        for timestamp, quality in zip(
            central.times_utc, central.quality_codes, strict=True
        )
    }
    central_response, _ = read_ellipsoid_unit_response(
        surface_hdf5,
        central_xy_m=(0.0, 0.0),
        east_xy_m=(0.0, 0.0),
    )
    central_compliance = float(central_response[2])
    if not np.isfinite(central_compliance) or central_compliance <= 0.0:
        raise ValueError("Central unit response must be finite and positive")

    deployments = {deployment.slug: deployment for deployment in DEPLOYMENTS}
    output_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, object]] = []
    rows: list[dict[str, object]] = []
    figure, axes = plt.subplots(3, 2, figsize=(12.0, 9.0), sharex=True)
    axes = np.asarray(axes).ravel()
    colors = {"observed": "#0072B2", "predicted": "#D55E00"}

    for axis, slug in zip(axes, HOLDOUT_SLUGS, strict=True):
        deployment = deployments[slug]
        station_depths = read_daily_depths(
            PROCESSED_DIR / f"{slug}.daily.csv"
        )
        paired_days = sorted(station_depths.keys() & central_by_day.keys())
        if len(paired_days) < 5:
            raise ValueError(f"OOI overlap for {slug} has fewer than five days")
        baseline_day = paired_days[0]
        observed_m = np.asarray(
            [station_depths[baseline_day] - station_depths[day] for day in paired_days],
            dtype=float,
        )
        central_uplift_m = np.asarray(
            [central_by_day[day] - central_by_day[baseline_day] for day in paired_days],
            dtype=float,
        )
        east_m, north_m = local_east_north_offset_m(
            deployment.latitude,
            deployment.longitude,
            origin_latitude_deg=CENTRAL_CALDERA_LAT_LON_DEG[0],
            origin_longitude_deg=CENTRAL_CALDERA_LAT_LON_DEG[1],
        )
        _, station_response = read_ellipsoid_unit_response(
            surface_hdf5,
            central_xy_m=(0.0, 0.0),
            east_xy_m=(east_m, north_m),
        )
        station_compliance = float(station_response[2])
        predicted_m = central_uplift_m * station_compliance / central_compliance

        metric_mask = np.ones(len(paired_days), dtype=bool)
        exclusions: list[dict[str, str]] = []
        if slug == "minibpr_2017_2018_ax105":
            metric_mask = np.asarray(
                [
                    not AX105_ANOMALY_START <= day <= AX105_ANOMALY_END
                    for day in paired_days
                ],
                dtype=bool,
            )
            exclusions.append(
                {
                    "start_utc": AX105_ANOMALY_START.isoformat(),
                    "end_utc": AX105_ANOMALY_END.isoformat(),
                    "reason": "MGDS reports repeated raw-depth offsets and unrealistic changes.",
                }
            )
        if int(np.sum(metric_mask)) < 5:
            raise ValueError(f"fewer than five primary metric days remain for {slug}")

        all_metrics = metrics(observed_m, predicted_m)
        primary_metrics = metrics(observed_m[metric_mask], predicted_m[metric_mask])
        station_record = {
            "station_slug": slug,
            "station": deployment.station,
            "source_file": str(deployment.path),
            "raw_channel": deployment.raw_channel,
            "raw_channel_note": deployment.raw_channel_note,
            "sampling_interval_s": deployment.sampling_interval_s,
            "latitude": deployment.latitude,
            "longitude": deployment.longitude,
            "paired_daily_sample_count": len(paired_days),
            "primary_metric_sample_count": int(np.sum(metric_mask)),
            "overlap_start_utc": paired_days[0].isoformat(),
            "overlap_end_utc": paired_days[-1].isoformat(),
            "baseline_utc": baseline_day.isoformat(),
            "central_compliance_m_per_mpa": central_compliance,
            "station_compliance_m_per_mpa": station_compliance,
            "all_record_metrics": all_metrics,
            "primary_metrics": primary_metrics,
            "excluded_metric_intervals": exclusions,
        }
        records.append(station_record)

        for day, center_value, observed, predicted, metric_day in zip(
            paired_days,
            central_uplift_m,
            observed_m,
            predicted_m,
            metric_mask,
            strict=True,
        ):
            rows.append(
                {
                    "station_slug": slug,
                    "time_utc": f"{day.isoformat()}T00:00:00Z",
                    "ooi_central_relative_uplift_m": center_value,
                    "ooi_central_qc_aggregate": central_qc[day],
                    "station_observed_uplift_m": observed,
                    "station_static_ellipsoid_prediction_m": predicted,
                    "residual_m": predicted - observed,
                    "included_in_primary_metrics": metric_day,
                }
            )

        dates = [datetime.combine(day, datetime.min.time()) for day in paired_days]
        axis.plot(
            dates,
            observed_m,
            color=colors["observed"],
            linewidth=0.8,
            label="Raw BPR observed",
        )
        axis.plot(
            dates,
            predicted_m,
            color=colors["predicted"],
            linewidth=0.9,
            linestyle="--",
            label="Static ellipsoid from OOI Central",
        )
        if slug == "minibpr_2017_2018_ax105":
            axis.axvspan(
                datetime.combine(AX105_ANOMALY_START, datetime.min.time()),
                datetime.combine(AX105_ANOMALY_END, datetime.min.time()),
                color="#999999",
                alpha=0.2,
                label="MGDS-reported offset interval",
            )
        axis.axhline(0.0, color="#555555", linewidth=0.6)
        axis.set_title(deployment.station)
        axis.set_ylabel("Relative elevation (m; up positive)")
        axis.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        axis.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        axis.grid(True, color="#D9D9D9", linewidth=0.55)
        axis.legend(frameon=False, fontsize=7, loc="best")

    figure.suptitle(
        "2017–18 raw BPR holdouts against an OOI Central static ellipsoid fit\n"
        "Original channels; no tide or drift corrections; OOI QC retained"
    )
    figure.autofmt_xdate()
    figure.tight_layout()
    figure_stem.parent.mkdir(parents=True, exist_ok=True)
    png_path = figure_stem.with_suffix(".png")
    pdf_path = figure_stem.with_suffix(".pdf")
    figure.savefig(png_path, dpi=220)
    figure.savefig(pdf_path)
    plt.close(figure)

    timeseries_path = output_dir / "timeseries.csv"
    with timeseries_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary: dict[str, object] = {
        "method": "static elastic PyLith ellipsoid response calibrated to OOI Central daily uplift",
        "observation_provenance": "OOI Central and original MGDS raw BPR channels",
        "paper_publication_data_used": False,
        "ooi_central_source_file": str(ooi_path),
        "ooi_central_quality_codes_retained": sorted(set(central.quality_codes)),
        "ooi_qc_filter_applied": False,
        "ooi_baseline": "first common daily sample for each station overlap",
        "holdout_records": records,
        "daily_coverage_threshold": 0.75,
        "tide_ocean_and_instrument_drift_corrections_applied": False,
        "material_assumptions": {
            "youngs_modulus_pa": 50.0e9,
            "poisson_ratio": 0.25,
            "reservoir_dimensions_km": [6.0, 3.0, 1.0],
            "reservoir_center_depth_km": 1.6,
            "compliance_mesh_converged": False,
        },
        "interpretation": (
            "The six raw deployments add spatial checks in the OOI era. "
            "Residuals also include tides, ocean variability, and uncorrected "
            "instrument drift; static pressure and compliance remain provisional."
        ),
        "timeseries_csv": str(timeseries_path),
        "figure_png": str(png_path),
        "figure_pdf": str(pdf_path),
    }
    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"wrote {summary_path}, {timeseries_path}, {png_path}, and {pdf_path}")
    return summary


def main() -> None:
    """Parse paths and run the bounded 2017–18 raw-station check."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--surface-hdf5", type=Path, default=DEFAULT_SURFACE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--figure-stem", type=Path, default=DEFAULT_FIGURE_STEM)
    args = parser.parse_args()
    run(
        surface_hdf5=args.surface_hdf5,
        output_dir=args.output_dir,
        figure_stem=args.figure_stem,
    )


if __name__ == "__main__":
    main()
