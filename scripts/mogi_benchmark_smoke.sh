#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STEP_DIR="${ROOT}/pylith/step02_mogi_benchmark"
OUTPUT_DIR="${STEP_DIR}/output"
PYLITH_ROOT="${ROOT}/pylith/pylith-5.0.2-linux-x86_64"
PYTHON="${ROOT}/envs/axial-modeling/bin/python"

mkdir -p "${OUTPUT_DIR}"
if ! PYTHONPATH="${ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}" "${PYTHON}" - "${STEP_DIR}" \
    >"${OUTPUT_DIR}/mesh.log" 2>&1 <<'PY'
from pathlib import Path
import os
import sys

from meshing.mogi_sphere import build_mesh

step_dir = Path(sys.argv[1])
tetrahedra = build_mesh(
    step_dir / "mesh" / "mogi.msh",
    half_width_m=float(os.environ.get("MOGI_HALF_WIDTH_M", "8000")),
    bottom_depth_m=float(os.environ.get("MOGI_BOTTOM_DEPTH_M", "8000")),
    lc_far_m=float(os.environ.get("MOGI_LC_FAR_M", "12000")),
    lc_near_m=float(os.environ.get("MOGI_LC_NEAR_M", "20")),
)
if tetrahedra > 3500:
    raise SystemExit(f"mesh has {tetrahedra} tetrahedra; limit is 3500")
print(f"Benchmark mesh contains {tetrahedra} linear tetrahedra.")
PY
then
    tail -n 40 "${OUTPUT_DIR}/mesh.log"
    exit 1
fi

cd "${PYLITH_ROOT}"
source setup.sh
cd "${STEP_DIR}"
if ! timeout 300 pylith --nodes=8 step02.cfg >"${OUTPUT_DIR}/pylith.log" 2>&1; then
    tail -n 50 "${OUTPUT_DIR}/pylith.log"
    exit 1
fi

PYTHONPATH="${ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}" "${PYTHON}" - \
    "${OUTPUT_DIR}/mogi-surface.h5" "${OUTPUT_DIR}/mogi-material.h5" <<'PY'
from pathlib import Path
import sys

import h5py
import numpy as np
import os

from axialstress.benchmarks import (
    interpolate_surface_triangles,
    mogi_surface_displacement_m,
)

surface_path = Path(sys.argv[1])
material_path = Path(sys.argv[2])
bulk_modulus_pa = 80.0e9 / 3.0
shear_modulus_pa = 16.0e9
pressure_change_pa = 10.0e6

with h5py.File(surface_path, "r") as surface:
    coordinates = np.asarray(surface["geometry/vertices"], dtype=float)
    triangles = np.asarray(surface["viz/topology/cells"], dtype=np.int64)
    displacement = np.asarray(surface["vertex_fields/displacement"][-1], dtype=float)
    final_time = float(np.asarray(surface["time"]).reshape(-1)[-1])

with h5py.File(material_path, "r") as material:
    stress = np.asarray(material["cell_fields/cauchy_stress"][-1], dtype=float)

if not np.isclose(final_time, 1.0, rtol=0.0, atol=1.0e-12):
    raise SystemExit(f"PyLith ended at {final_time:g} s, expected 1 s")
if displacement.shape != coordinates.shape or not np.all(np.isfinite(displacement)):
    raise SystemExit("surface displacement is missing, malformed, or non-finite")
if not np.all(np.isfinite(stress)) or np.max(np.abs(stress)) <= 0.0:
    raise SystemExit("PyLith stress response is missing, non-finite, or zero")

axis = np.linspace(-6_000.0, 6_000.0, 41)
grid_x, grid_y = np.meshgrid(axis, axis)
query_points = np.column_stack((grid_x.reshape(-1), grid_y.reshape(-1)))
sampled_displacement = interpolate_surface_triangles(
    coordinates, triangles, displacement, query_points
)
reference = mogi_surface_displacement_m(
    query_points[:, 0],
    query_points[:, 1],
    source_depth_m=2000.0,
    source_radius_m=200.0,
    pressure_change_pa=pressure_change_pa,
    bulk_modulus_pa=bulk_modulus_pa,
    shear_modulus_pa=shear_modulus_pa,
)
center = int(np.argmin(np.hypot(query_points[:, 0], query_points[:, 1])))
center_relative_error = abs(sampled_displacement[center, 2] - reference[center, 2]) / abs(
    reference[center, 2]
)
field_relative_error = float(
    np.linalg.norm(sampled_displacement - reference) / np.linalg.norm(reference)
)
peak_uplift_m = float(np.max(sampled_displacement[:, 2]))
maximum_relative_error = float(os.environ.get("MOGI_MAX_RELATIVE_ERROR", "0.5"))
if peak_uplift_m <= 0.0:
    raise SystemExit(f"inflation produced non-positive peak uplift {peak_uplift_m:g} m")
if not np.isfinite(maximum_relative_error) or maximum_relative_error <= 0.0:
    raise SystemExit("MOGI_MAX_RELATIVE_ERROR must be finite and positive")
if center_relative_error > maximum_relative_error or field_relative_error > maximum_relative_error:
    raise SystemExit(
        f"PyLith/Mogi mismatch exceeds {maximum_relative_error:.0%}: "
        f"center={center_relative_error:.3%}, field L2={field_relative_error:.3%}"
    )

print(
    "PyLith Mogi benchmark passed at t = 1 s; "
    f"peak uplift = {peak_uplift_m:.6g} m, "
    f"interpolated-axis center error = {center_relative_error:.3%}, "
    f"fixed-grid vector L2 error = {field_relative_error:.3%}."
)
PY
