#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STEP_DIR="${ROOT}/pylith/step02_mogi_benchmark"
OUTPUT_DIR="${STEP_DIR}/output"
mkdir -p "${OUTPUT_DIR}"

run_case() {
    local NAME="$1"
    local HALF_WIDTH_M="$2"
    local BOTTOM_DEPTH_M="$3"
    local LOG_PATH="${OUTPUT_DIR}/mogi-domain-${NAME}.log"

    MOGI_HALF_WIDTH_M="${HALF_WIDTH_M}" \
        MOGI_BOTTOM_DEPTH_M="${BOTTOM_DEPTH_M}" \
        MOGI_LC_FAR_M=12000 \
        MOGI_LC_NEAR_M=20 \
        MOGI_MAX_RELATIVE_ERROR=1.0 \
        bash "${ROOT}/scripts/mogi_benchmark_smoke.sh" >"${LOG_PATH}" 2>&1
    cp "${STEP_DIR}/mesh/mogi.msh" "${OUTPUT_DIR}/mogi-domain-${NAME}.msh"
    cp "${OUTPUT_DIR}/mogi-surface.h5" "${OUTPUT_DIR}/mogi-domain-${NAME}-surface.h5"
    cp "${OUTPUT_DIR}/mogi-material.h5" "${OUTPUT_DIR}/mogi-domain-${NAME}-material.h5"
    tail -n 1 "${LOG_PATH}"
}

run_case baseline 8000 8000
run_case expanded 12000 12000
