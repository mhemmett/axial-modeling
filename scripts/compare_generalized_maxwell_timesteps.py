"""Compare final synthetic Maxwell fields from two time-step sizes."""

from __future__ import annotations

import argparse
from pathlib import Path

import h5py
import numpy as np


def compare_outputs(coarse_path: Path, fine_path: Path) -> None:
    """Report final-field changes from coarse to refined time stepping."""
    fields = (
        "cell_fields/cauchy_stress",
        "cell_fields/viscous_strain",
        "vertex_fields/displacement",
    )
    with h5py.File(coarse_path, "r") as coarse, h5py.File(fine_path, "r") as fine:
        coarse_time = np.asarray(coarse["time"], dtype=float).reshape(-1)
        fine_time = np.asarray(fine["time"], dtype=float).reshape(-1)
        if not np.isclose(coarse_time[-1], fine_time[-1], rtol=0.0, atol=1.0e-6):
            raise SystemExit("coarse and fine runs do not end at the same time")
        if not np.array_equal(coarse["geometry/vertices"], fine["geometry/vertices"]):
            raise SystemExit("coarse and fine runs use different meshes")
        if not np.array_equal(coarse["viz/topology/cells"], fine["viz/topology/cells"]):
            raise SystemExit("coarse and fine runs use different cell topology")

        print(
            f"Compared final fields at t={fine_time[-1]:.0f} s; "
            f"saved records: coarse={len(coarse_time)}, fine={len(fine_time)}."
        )
        for field in fields:
            coarse_values = np.asarray(coarse[field][-1], dtype=float)
            fine_values = np.asarray(fine[field][-1], dtype=float)
            if coarse_values.shape != fine_values.shape:
                raise SystemExit(f"{field} differs in shape between runs")
            denominator = float(np.linalg.norm(fine_values))
            if denominator == 0.0:
                raise SystemExit(f"{field} is zero in the refined run")
            relative_change = float(np.linalg.norm(coarse_values - fine_values) / denominator)
            maximum_absolute_change = float(np.max(np.abs(coarse_values - fine_values)))
            print(
                f"{field}: relative L2 change={relative_change:.6g}; "
                f"maximum absolute change={maximum_absolute_change:.6g}."
            )


def main() -> None:
    """Compare final fields from coarse and fine output files."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coarse", type=Path, required=True)
    parser.add_argument("--fine", type=Path, required=True)
    args = parser.parse_args()
    compare_outputs(args.coarse, args.fine)


if __name__ == "__main__":
    main()
