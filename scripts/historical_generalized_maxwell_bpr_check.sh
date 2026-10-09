#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STEP_DIR="${ROOT}/pylith/step13_historical_generalized_maxwell_bpr"
OUTPUT_DIR="${STEP_DIR}/output"
ENV_PREFIX="${ROOT}/envs/axial-modeling"
PYTHON="${ENV_PREFIX}/bin/python"

mkdir -p "${STEP_DIR}/mesh" "${OUTPUT_DIR}"
if ! timeout 300 "${PYTHON}" "${ROOT}/meshing/axial_ellipsoid_bpr.py" \
    --output "${STEP_DIR}/mesh/axial_ellipsoid.msh" \
    >"${OUTPUT_DIR}/mesh.log" 2>&1; then
    tail -n 40 "${OUTPUT_DIR}/mesh.log"
    exit 1
fi

export PYTHONPATH="${ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"
if ! timeout 300 "${PYTHON}" "${ROOT}/scripts/generalized_maxwell_ellipsoid_smoke.py" build \
    --mesh "${STEP_DIR}/mesh/axial_ellipsoid.msh" \
    --database "${OUTPUT_DIR}/genmaxwell-material.spatialdb" \
    --temperature-archive "${OUTPUT_DIR}/hydrothermal-temperature.npz" \
    >"${OUTPUT_DIR}/material-build.log" 2>&1; then
    tail -n 50 "${OUTPUT_DIR}/material-build.log"
    exit 1
fi
cat "${OUTPUT_DIR}/material-build.log"

center_daily="${ROOT}/data/processed/axial_historical_bpr/wc81_1997.daily.csv"
if [[ ! -f "${center_daily}" ]]; then
    "${PYTHON}" "${ROOT}/data/process_historical_bpr.py"
fi

timeout 300 "${PYTHON}" "${ROOT}/scripts/historical_generalized_maxwell_bpr_check.py" \
    --mesh "${STEP_DIR}/mesh/axial_ellipsoid.msh" \
    --material-database "${OUTPUT_DIR}/genmaxwell-material.spatialdb" "$@"
