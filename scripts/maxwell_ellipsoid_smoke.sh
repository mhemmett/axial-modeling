#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STEP_DIR="${ROOT}/pylith/step06_maxwell_ellipsoid"
OUTPUT_DIR="${STEP_DIR}/output"
PYLITH_ROOT="${ROOT}/pylith/pylith-5.0.2-linux-x86_64"
PYTHON="${ROOT}/envs/axial-modeling/bin/python"

mkdir -p "${OUTPUT_DIR}"
if ! "${PYTHON}" "${ROOT}/meshing/axial_ellipsoid_bpr.py" \
    --output "${STEP_DIR}/mesh/axial_ellipsoid.msh" >"${OUTPUT_DIR}/mesh.log" 2>&1; then
    tail -n 40 "${OUTPUT_DIR}/mesh.log"
    exit 1
fi

cd "${PYLITH_ROOT}"
source setup.sh
cd "${STEP_DIR}"
if ! timeout 300 pylith --nodes=8 step06.cfg >"${OUTPUT_DIR}/pylith.log" 2>&1; then
    tail -n 50 "${OUTPUT_DIR}/pylith.log"
    exit 1
fi

PYTHONPATH="${ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}" \
    "${PYTHON}" "${ROOT}/scripts/maxwell_ellipsoid_check.py"
