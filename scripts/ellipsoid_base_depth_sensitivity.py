"""Measure fixed-base depth sensitivity of PyLith ellipsoid compliance."""

from __future__ import annotations

import json
import time
from pathlib import Path

from ellipsoid_mesh_sensitivity import _run_mesh_variant

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = ROOT / "data" / "processed" / "ellipsoid_base_depth_sensitivity.json"
DOMAIN_DEPTHS_M = (20_000.0, 30_000.0, 40_000.0)


def main() -> None:
    """Run bounded fixed-base depth variants and save response changes."""
    started = time.perf_counter()
    variants = [
        _run_mesh_variant(
            f"base-{int(depth_m / 1000)}km",
            lc_near=1_200.0,
            lc_far=10_000.0,
            local_refinement_size=None,
            station_refinement_size=300.0,
            domain_depth_m=depth_m,
            embed_station_points=True,
        )
        for depth_m in DOMAIN_DEPTHS_M
    ]
    baseline = variants[0]
    for variant in variants:
        for station in ("central", "east"):
            key = f"{station}_compliance_m_per_mpa"
            baseline_value = float(baseline[key])
            variant[f"{station}_change_from_20km_percent"] = (
                100.0 * (float(variant[key]) - baseline_value) / baseline_value
            )

    result = {
        "method": (
            "static unit-pressure ellipsoid compliance with the PyLith fixed base "
            "moved deeper while the cavity, BPR locations, and size settings are held fixed"
        ),
        "variants": variants,
        "baseline_depth_m": DOMAIN_DEPTHS_M[0],
        "maximum_tetrahedra": 3_500,
        "mesh_variants_are_nested": False,
        "limitation": (
            "independently generated tetrahedral meshes confound fixed-base-depth "
            "and discretization changes; the sequence tests sensitivity but not "
            "Winkler equivalence or convergence"
        ),
        "runtime_seconds": time.perf_counter() - started,
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
