#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STEP_DIR="${ROOT}/pylith/step01_maxwell_restart"
OUTPUT_DIR="${STEP_DIR}/output"
LOG_DIR="${OUTPUT_DIR}"
PYLITH_ROOT="${ROOT}/pylith/pylith-5.0.2-linux-x86_64"
PYTHON="${ROOT}/envs/axial-modeling/bin/python"

mkdir -p "${OUTPUT_DIR}"
python "${ROOT}/meshing/axial_box_ellipsoid.py" \
    --output "${STEP_DIR}/mesh/axial_box.msh"

cd "${PYLITH_ROOT}"
source setup.sh
cd "${STEP_DIR}"

run_pylith() {
    local config="$1"
    local log_path="${LOG_DIR}/${config%.cfg}.log"
    if ! timeout 300 pylith "${config}" >"${log_path}" 2>&1; then
        tail -n 50 "${log_path}"
        return 1
    fi
}

run_pylith step01_single.cfg
run_pylith step01_split.cfg
"${PYTHON}" "${ROOT}/src/axialstress/pylith_restart.py" \
    "${OUTPUT_DIR}/first-domain.h5" \
    "${OUTPUT_DIR}/first-material.h5" \
    --output-dir "${OUTPUT_DIR}" \
    --prefix restart
run_pylith step01_restart.cfg

"${PYTHON}" - "${OUTPUT_DIR}" <<'PY'
from pathlib import Path
import sys

import h5py
import numpy as np

output = Path(sys.argv[1])
fields = (
    ("single-domain.h5", "restart-domain.h5", "vertex_fields/displacement"),
    ("single-material.h5", "restart-material.h5", "cell_fields/cauchy_stress"),
    ("single-material.h5", "restart-material.h5", "cell_fields/cauchy_strain"),
    ("single-material.h5", "restart-material.h5", "cell_fields/viscous_strain"),
)
tolerance = 5.0e-7

for single_name, restart_name, field in fields:
    with h5py.File(output / single_name, "r") as single, h5py.File(
        output / restart_name, "r"
    ) as restarted:
        single_time = float(np.asarray(single["time"]).reshape(-1)[-1])
        restart_time = float(np.asarray(restarted["time"]).reshape(-1)[-1])
        if not np.isclose(single_time, 2.0, rtol=0.0, atol=1.0e-12):
            raise SystemExit(f"continuous run ended at {single_time:g} s")
        if not np.isclose(restart_time, 2.0, rtol=0.0, atol=1.0e-12):
            raise SystemExit(f"restarted run ended at {restart_time:g} s")
        expected = np.asarray(single[field][-1], dtype=float)
        actual = np.asarray(restarted[field][-1], dtype=float)
        if expected.shape != actual.shape:
            raise SystemExit(f"{field} shapes differ: {expected.shape} != {actual.shape}")
        scale = max(float(np.max(np.abs(expected))), np.finfo(float).tiny)
        relative_error = float(np.max(np.abs(actual - expected)) / scale)
        if not np.isfinite(relative_error) or relative_error > tolerance:
            raise SystemExit(
                f"{field} relative error {relative_error:.3e} exceeds {tolerance:.1e}"
            )
        print(f"{field}: relative error {relative_error:.3e}")

print("Maxwell same-mesh restart check passed at t = 2 s.")
PY
