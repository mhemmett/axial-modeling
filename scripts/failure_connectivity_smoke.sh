#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR="${ROOT}/pylith/step02_mogi_benchmark/output"
PYTHON="${ROOT}/envs/axial-modeling/bin/python"
MATERIAL_H5="${OUTPUT_DIR}/mogi-material.h5"
SUMMARY_JSON="${OUTPUT_DIR}/failure-analysis.json"

if [[ ! -f "${MATERIAL_H5}" ]]; then
    echo "Missing synthetic Mogi material output: ${MATERIAL_H5}" >&2
    echo "Run make mogi-benchmark first." >&2
    exit 1
fi

PYTHONPATH="${ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}" "${PYTHON}" \
    -m axialstress.failure_analysis \
    --material-h5 "${MATERIAL_H5}" \
    --output "${SUMMARY_JSON}" \
    --cohesion-pa 1000000 \
    --friction-angle-deg 25 \
    --pore-pressure-pa 0

PYTHONPATH="${ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}" "${PYTHON}" - "${SUMMARY_JSON}" <<'PY'
import json
import sys
from pathlib import Path

summary = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
required = {
    "cell_count",
    "cavity_adjacent_cell_count",
    "top_surface_adjacent_cell_count",
    "mohr_coulomb_shear_yield_cell_count",
    "cavity_to_surface_shear_path_found",
    "maximum_cavity_tensile_stress_pa",
    "final_time_s",
}
missing = required.difference(summary)
if missing:
    raise SystemExit(f"failure summary is missing fields: {sorted(missing)}")
if summary["cell_count"] <= 0 or summary["cavity_adjacent_cell_count"] <= 0:
    raise SystemExit("failure summary has no mesh or cavity boundary cells")
if summary["top_surface_adjacent_cell_count"] <= 0:
    raise SystemExit("failure summary has no top-surface boundary cells")
print("Synthetic failure-threshold and connectivity analysis passed.")
PY
