"""Derive cavity-volume histories from fitted PyLith displacement fields."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path

import numpy as np

from axialstress.cavity_volume import read_pylith_cavity_volume_history
from axialstress.paper_bpr import file_sha256

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "processed" / "source_value_bpr_failure_2011_2015"
MESH = ROOT / "data" / "processed" / "refined_elastic_basis_400m" / "axial_ellipsoid.msh"


def main() -> None:
    """Write mesh-integrated cavity-volume changes for each fitted case."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=INPUT)
    parser.add_argument("--mesh", type=Path, default=MESH)
    args = parser.parse_args()
    args.input_dir = args.input_dir.resolve()
    args.mesh = args.mesh.resolve()
    source_summary_path = args.input_dir / "summary.json"
    source = json.loads(source_summary_path.read_text(encoding="utf-8"))
    if source.get("status") != "conditional_bpr_failure_reconstruction_temporally_unresolved":
        raise ValueError("source-value BPR summary has an unexpected status")
    if source["mesh_sha256"] != file_sha256(args.mesh):
        raise ValueError("cavity-volume mesh differs from the BPR reconstruction")
    start_utc = datetime.fromisoformat(source["cycle_start_utc"])
    results = {}
    for case, case_summary in source["cases"].items():
        pressure_series_path = args.input_dir / case_summary["pressure_failure_csv"]
        with pressure_series_path.open(encoding="utf-8", newline="") as stream:
            pressure_rows = list(csv.DictReader(stream))
        domain_path = (
            args.input_dir / "runs" / case / "bpr_pressure" / "output" / "maxwell-domain.h5"
        )
        times_s, volume = read_pylith_cavity_volume_history(args.mesh, domain_path)
        expected_times_s = np.asarray(
            [
                (datetime.fromisoformat(row["time_utc"]) - start_utc).total_seconds()
                for row in pressure_rows
            ]
        )
        if times_s.shape != expected_times_s.shape or not np.allclose(
            times_s, expected_times_s, rtol=0.0, atol=0.01
        ):
            raise ValueError(f"{case} volume and pressure times do not match")
        geometric = np.asarray(volume["geometric_change_m3"], dtype=float)
        first_order = np.asarray(volume["first_order_change_m3"], dtype=float)
        output_path = args.input_dir / f"{case}_volume_history.csv"
        with output_path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(
                (
                    "time_utc",
                    "pressure_change_mpa",
                    "first_order_volume_change_km3",
                    "geometric_volume_change_km3",
                )
            )
            for row, linear_m3, geometric_m3 in zip(
                pressure_rows, first_order, geometric, strict=True
            ):
                writer.writerow(
                    (
                        row["time_utc"],
                        row["pressure_change_mpa"],
                        linear_m3 / 1.0e9,
                        geometric_m3 / 1.0e9,
                    )
                )
        results[case] = {
            "reference_cavity_volume_km3": float(volume["reference_volume_m3"]) / 1.0e9,
            "final_first_order_volume_change_km3": float(first_order[-1]) / 1.0e9,
            "final_geometric_volume_change_km3": float(geometric[-1]) / 1.0e9,
            "final_geometric_to_first_order_difference_percent": float(
                100.0 * (geometric[-1] - first_order[-1]) / first_order[-1]
            ),
            "domain_output_sha256": file_sha256(domain_path),
            "pressure_series_sha256": file_sha256(pressure_series_path),
            "volume_history_csv": output_path.name,
        }
        print(
            f"{case}: final first-order cavity-volume change "
            f"{first_order[-1] / 1.0e9:.5f} km3",
            flush=True,
        )
    summary = {
        "method": "integrate generated PyLith cavity displacement over Gmsh cavity faces",
        "status": "conditional_cavity_volume_history",
        "paper_output_data_used": False,
        "source_summary_sha256": file_sha256(source_summary_path),
        "mesh_sha256": file_sha256(args.mesh),
        "cases": results,
    }
    (args.input_dir / "volume_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
