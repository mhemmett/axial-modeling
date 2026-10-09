#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STEP_DIR="${ROOT}/pylith/step00_elastic_cavity"
OUTPUT_DIR="${STEP_DIR}/output"
LOG="${OUTPUT_DIR}/step00.log"

mkdir -p "${OUTPUT_DIR}"
python "${ROOT}/meshing/axial_box_ellipsoid.py" \
    --output "${STEP_DIR}/mesh/axial_box.msh"

PYLITH_ROOT="${ROOT}/pylith/pylith-5.0.2-linux-x86_64"
cd "${PYLITH_ROOT}"
# PyLith's setup script expects the current directory to be its distribution root.
source setup.sh
cd "${STEP_DIR}"

start_seconds="$(date +%s)"
if ! timeout 300 pylith --nodes=8 step00.cfg >"${LOG}" 2>&1; then
    tail -n 40 "${LOG}"
    exit 1
fi
elapsed_seconds="$(( $(date +%s) - start_seconds ))"

surface_file="${OUTPUT_DIR}/step00_elastic-surface.h5"
material_file="${OUTPUT_DIR}/step00_elastic-material.h5"
test -s "${surface_file}"
test -s "${material_file}"

python - "${surface_file}" "${material_file}" "${elapsed_seconds}" <<'PY'
from pathlib import Path
import sys

import h5py
import numpy as np

surface_path = Path(sys.argv[1])
material_path = Path(sys.argv[2])
runtime_seconds = int(sys.argv[3])

with h5py.File(surface_path, "r") as surface:
    displacement = np.asarray(surface["vertex_fields/displacement"])
    if displacement.ndim == 3:
        displacement = displacement[-1]
    uplift = float(np.max(displacement[:, 2]))

with h5py.File(material_path, "r") as material:
    if "cell_fields/cauchy_stress" not in material:
        raise SystemExit("Cauchy stress is missing from the material HDF5 output")

if not 0.01 <= uplift <= 10.0:
    raise SystemExit(f"peak surface uplift {uplift:g} m is outside [0.01, 10] m")

print(f"Smoke test passed in {runtime_seconds} s; peak uplift = {uplift:.6g} m")
PY
