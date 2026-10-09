"""Check the unit-load PyLith ellipsoid response over a Maxwell relaxation time."""

from __future__ import annotations

import json
import time
from pathlib import Path

import h5py
import numpy as np

from axialstress.bpr_mogi_calibration import (
    CENTRAL_CALDERA_LAT_LON_DEG,
    EAST_CALDERA_LAT_LON_DEG,
    local_east_north_offset_m,
)
from axialstress.surface_interpolation import interpolate_triangular_surface

ROOT = Path(__file__).resolve().parents[1]
STEP_DIR = ROOT / "pylith" / "step06_maxwell_ellipsoid"
OUTPUT_DIR = ROOT / "data" / "processed"
SURFACE_PATH = STEP_DIR / "output" / "maxwell-surface.h5"
MATERIAL_PATH = STEP_DIR / "output" / "maxwell-material.h5"
SUMMARY_PATH = OUTPUT_DIR / "maxwell_ellipsoid_response.json"
END_TIME_S = 63_115_200.0
SHEAR_MODULUS_PA = 20.0e9
VISCOSITY_PA_S = 1.0e18


def main() -> None:
    """Validate the Maxwell material state and report surface displacement."""
    started = time.perf_counter()
    with h5py.File(SURFACE_PATH, "r") as surface:
        required = ("time", "geometry/vertices", "viz/topology/cells", "vertex_fields/displacement")
        if any(name not in surface for name in required):
            raise SystemExit("PyLith surface output is missing a required dataset")
        times_s = np.asarray(surface["time"], dtype=float).reshape(-1)
        vertices = np.asarray(surface["geometry/vertices"], dtype=float)
        triangles = np.asarray(surface["viz/topology/cells"], dtype=np.int64)
        displacement = np.asarray(surface["vertex_fields/displacement"], dtype=float)
    if displacement.ndim != 3 or displacement.shape[0] != len(times_s):
        raise SystemExit("PyLith surface displacement has an unexpected time-series shape")
    if displacement.shape[1:] != vertices.shape or not np.all(np.isfinite(displacement)):
        raise SystemExit("PyLith surface displacement is malformed or non-finite")
    if not np.isclose(times_s[-1], END_TIME_S, rtol=0.0, atol=1.0e-5):
        raise SystemExit(f"PyLith ended at {times_s[-1]:g} s, expected {END_TIME_S:g} s")
    if np.any(np.diff(times_s) <= 0.0):
        raise SystemExit("PyLith output times must be strictly increasing")

    east_offset, north_offset = local_east_north_offset_m(
        EAST_CALDERA_LAT_LON_DEG[0],
        EAST_CALDERA_LAT_LON_DEG[1],
        origin_latitude_deg=CENTRAL_CALDERA_LAT_LON_DEG[0],
        origin_longitude_deg=CENTRAL_CALDERA_LAT_LON_DEG[1],
    )
    central_uplift = np.asarray(
        [
            interpolate_triangular_surface(vertices, triangles, values, (0.0, 0.0))[2]
            for values in displacement
        ]
    )
    east_uplift = np.asarray(
        [
            interpolate_triangular_surface(
                vertices, triangles, values, (east_offset, north_offset)
            )[2]
            for values in displacement
        ]
    )
    with h5py.File(MATERIAL_PATH, "r") as material:
        if "cell_fields/cauchy_stress" not in material:
            raise SystemExit("PyLith Cauchy stress output is missing")
        if "cell_fields/viscous_strain" not in material:
            raise SystemExit("PyLith viscous strain state output is missing")
        stress = np.asarray(material["cell_fields/cauchy_stress"], dtype=float)
        viscous_strain = np.asarray(material["cell_fields/viscous_strain"], dtype=float)
    if not np.all(np.isfinite(stress)) or np.max(np.abs(stress)) <= 0.0:
        raise SystemExit("PyLith Cauchy stress is non-finite or zero")
    if not np.all(np.isfinite(viscous_strain)) or np.max(np.abs(viscous_strain[-1])) <= 0.0:
        raise SystemExit("PyLith viscous-strain state is non-finite or zero")
    monotonic_tolerance_m = 1.0e-9
    if central_uplift[0] <= 0.0 or central_uplift[-1] <= central_uplift[0]:
        raise SystemExit("constant inflation did not produce positive growing Central uplift")
    if np.any(np.diff(central_uplift) < -monotonic_tolerance_m):
        raise SystemExit("Central uplift is not monotone under constant Maxwell loading")

    maxwell_time_s = VISCOSITY_PA_S / SHEAR_MODULUS_PA
    summary = {
        "model": "uniform one-branch IsotropicLinearMaxwell diagnostic",
        "youngs_modulus_pa": 50.0e9,
        "poisson_ratio": 0.25,
        "density_kg_m3": 2700.0,
        "viscosity_pa_s": VISCOSITY_PA_S,
        "maxwell_time_s": maxwell_time_s,
        "maxwell_time_years": maxwell_time_s / (365.25 * 86400.0),
        "constant_cavity_overpressure_pa": 1.0e6,
        "end_time_s": float(times_s[-1]),
        "output_steps": len(times_s),
        "central_initial_uplift_m": float(central_uplift[0]),
        "central_final_uplift_m": float(central_uplift[-1]),
        "east_initial_uplift_m": float(east_uplift[0]),
        "east_final_uplift_m": float(east_uplift[-1]),
        "peak_abs_cauchy_stress_pa": float(np.max(np.abs(stress))),
        "peak_abs_final_viscous_strain": float(np.max(np.abs(viscous_strain[-1]))),
        "monotone_central_creep": True,
        "postprocessing_seconds": round(time.perf_counter() - started, 2),
        "interpretation": (
            "solver-state smoke test; not the generalized temperature-dependent target model"
        ),
        "observations_used": False,
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"wrote {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
