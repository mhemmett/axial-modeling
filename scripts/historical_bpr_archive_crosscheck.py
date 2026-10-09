"""Compare original MGDS Fox raw-depth channels with archived NCEI pressure."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from axialstress.historical_bpr import (
    DEPLOYMENTS,
    FOX_1997_1998_DEPLOYMENTS,
    PROCESSED_DIR,
    RAW_DIR,
    compare_raw_deployment_sources,
    event_window_change,
    process_deployment,
)


def sha256_file(path: Path) -> str:
    """Return the SHA-256 checksum of one local archive."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    """Write raw-source comparisons for the 1998 Center and South BPRs."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=PROCESSED_DIR / "mgds_fox_1998_source_comparison.json",
        help="ignored JSON output path",
    )
    args = parser.parse_args()

    ncei_by_slug = {deployment.slug: deployment for deployment in DEPLOYMENTS}
    fox_by_slug = {deployment.slug: deployment for deployment in FOX_1997_1998_DEPLOYMENTS}
    fox_rows = {
        slug: process_deployment(deployment)
        for slug, deployment in fox_by_slug.items()
    }
    ncei_center = process_deployment(ncei_by_slug["wc81_1997"])
    ncei_south = process_deployment(ncei_by_slug["wc82a_1997"])
    ncei_south_followup = process_deployment(ncei_by_slug["wc82b_1998"])

    source_comparisons = [
        compare_raw_deployment_sources(
            ncei_center,
            fox_rows["fox_wc81_1997_center"],
            reference_station="NCEI WC81/VSM1 Center raw pressure",
            comparison_station="MGDS Fox WC81/VSM1 original Depth",
        ),
        compare_raw_deployment_sources(
            ncei_south,
            fox_rows["fox_wc82_1997_south"],
            reference_station="NCEI WC82A/VSM2 South raw pressure",
            comparison_station="MGDS Fox WC82/VSM2 original Depth",
        ),
        compare_raw_deployment_sources(
            ncei_south_followup,
            fox_rows["fox_wc82_1997_south"],
            reference_station="NCEI WC82B/VSM2 South raw pressure",
            comparison_station="MGDS Fox WC82/VSM2 original Depth",
        ),
    ]
    event_changes = [
        event_window_change(
            fox_rows[deployment.slug],
            deployment.eruption_date,
            deployment.station,
        )
        for deployment in FOX_1997_1998_DEPLOYMENTS
        if deployment.eruption_date is not None
    ]
    archive = RAW_DIR / "mgds" / "ieda_322344_1997_1998_bpr_records.tar"
    payload = {
        "processed_utc": datetime.now(UTC).isoformat(),
        "source": {
            "dataset": "MGDS IEDA/322344 (Fox 1997–1998 BPR records)",
            "doi": "10.1594/IEDA/322344",
            "archive": str(archive),
            "archive_sha256": sha256_file(archive),
            "selected_channel": "Depth",
            "selected_channel_description": (
                "original 15-second pressure samples converted from psi to meters"
            ),
            "excluded_channels": ["SpotlDetidedDepth", "LPFDetidedDepth"],
            "license": "CC BY-NC-SA 3.0",
        },
        "method": (
            "Daily raw values are converted to relative uplift from the first "
            "shared valid UTC day before source differences are calculated."
        ),
        "source_comparisons": source_comparisons,
        "event_window_changes": event_changes,
        "interpretation": (
            "The MGDS files archive the same WC81/VSM1 and WC82/VSM2 physical "
            "instruments as the NCEI files; they add an archive-source check, "
            "not additional station coverage."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote raw-source comparison to {args.output}")
    for result in source_comparisons:
        print(
            f"{result['comparison_station']} vs {result['reference_station']}: "
            f"{result['shared_daily_means']} paired days, "
            f"RMSE={result['comparison_minus_reference_rmse_m']:.4f} m, "
            f"r={result['relative_uplift_correlation']:.6f}"
        )


if __name__ == "__main__":
    main()
