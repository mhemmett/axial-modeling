"""Export processed Center BPR observations without joining deployment datums."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from axialstress.paper_bpr import (
    CANDIDATE_PROCESSED_CENTER_SOURCES,
    export_hourly_observations,
)

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    """Write hourly source samples and a provenance record for the paper cycles."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir", type=Path, default=ROOT / "data/processed/paper_center_bpr"
    )
    args = parser.parse_args()
    missing = [str(source.deployment.path) for source in CANDIDATE_PROCESSED_CENTER_SOURCES
               if not source.deployment.path.is_file()]
    if missing:
        raise SystemExit("Missing cited BPR archive files:\n" + "\n".join(missing))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = args.output_dir / "summary.json"
    summary_path.write_text('{"status": "incomplete"}\n', encoding="utf-8")
    records = []
    for source in CANDIDATE_PROCESSED_CENTER_SOURCES:
        output = args.output_dir / f"{source.deployment.slug}.hourly.csv"
        record = export_hourly_observations(source, output)
        records.append(record)
        print(f"{source.deployment.slug}: {record['samples']} hourly observations", flush=True)
    summary = {
        "status": "observations_exported",
        "processed_utc": datetime.now(UTC).isoformat(),
        "method": "copy source low-pass depth values at existing on-hour timestamps",
        "model_outputs_used": False,
        "paper_channel_selection_verified": False,
        "common_datum_verified": False,
        "ready_for_cycle_calibration": False,
        "deployments": records,
        "remaining_inputs": [
            "processed Center observations for 2000–2002 from the cited archive",
            "documented offsets tying successive deployments to one uplift datum",
            "confirmation of the channel and temporal sampling used by Cabaniss",
            "loading and viscoelastic initialization across observation gaps and eruptions",
        ],
    }
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {summary_path}; deployment datums remain unresolved.")


if __name__ == "__main__":
    main()
