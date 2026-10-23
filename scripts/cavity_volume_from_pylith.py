"""Write cavity-volume change calculated from PyLith boundary displacement."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from axialstress.cavity_volume import read_pylith_cavity_volume_history
from axialstress.paper_bpr import file_sha256


def main() -> None:
    """Write model-derived volume in cubic meters with mesh provenance."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mesh", type=Path, required=True)
    parser.add_argument("--cavity-output", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    args = parser.parse_args()
    times, history = read_pylith_cavity_volume_history(args.mesh, args.cavity_output)
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.output_csv.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow([
            "time_s", "cavity_volume_m3", "geometric_volume_change_m3",
            "first_order_volume_change_m3",
        ])
        writer.writerows(zip(
            times,
            history["deformed_volume_m3"],
            history["geometric_change_m3"],
            history["first_order_change_m3"],
            strict=True,
        ))
    metadata = {
        "method": "closed Gmsh cavity faces with PyLith displacement mapped by vertex position",
        "mesh": str(args.mesh),
        "mesh_sha256": file_sha256(args.mesh),
        "cavity_output": str(args.cavity_output),
        "cavity_output_sha256": file_sha256(args.cavity_output),
        "reference_volume_m3": history["reference_volume_m3"],
        "times": len(times),
        "paper_volume_curve_used": False,
        "paper_equivalence_established": False,
    }
    args.output_csv.with_suffix(".json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Wrote {len(times)} model volume records to {args.output_csv}")


if __name__ == "__main__":
    main()
