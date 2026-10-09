#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STEP_DIR="${ROOT}/pylith/step06_maxwell_ellipsoid"
OUTPUT_DIR="${STEP_DIR}/output"
PYLITH_ROOT="${ROOT}/pylith/pylith-5.0.2-linux-x86_64"
PYTHON="${ROOT}/envs/axial-modeling/bin/python"
SUMMARY_JSON="${ROOT}/data/processed/ellipsoid-failure-progression.json"

mkdir -p "${OUTPUT_DIR}"
if ! "${PYTHON}" "${ROOT}/meshing/axial_ellipsoid_bpr.py" \
    --output "${STEP_DIR}/mesh/axial_ellipsoid.msh" >"${OUTPUT_DIR}/mesh.log" 2>&1; then
    tail -n 40 "${OUTPUT_DIR}/mesh.log"
    exit 1
fi

cd "${PYLITH_ROOT}"
source setup.sh
cd "${STEP_DIR}"
if ! timeout 300 pylith step06.cfg >"${OUTPUT_DIR}/pylith.log" 2>&1; then
    tail -n 50 "${OUTPUT_DIR}/pylith.log"
    exit 1
fi

PYTHONPATH="${ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}" "${PYTHON}" \
    -m axialstress.failure_analysis \
    --material-h5 "${OUTPUT_DIR}/maxwell-material.h5" \
    --output "${SUMMARY_JSON}" \
    --cohesion-pa 1000000 \
    --friction-angle-deg 25 \
    --pore-pressure-pa 0 \
    --all-times

"${PYTHON}" - "${SUMMARY_JSON}" <<'PY'
import json
import sys
from pathlib import Path

summary = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
records = summary.get("records", [])
if summary.get("record_count") != 25 or len(records) != 25:
    raise SystemExit("ellipsoid failure history must contain 25 stress records")
times = [record["time_s"] for record in records]
if any(later <= earlier for earlier, later in zip(times, times[1:], strict=False)):
    raise SystemExit("ellipsoid failure history times are not strictly increasing")
if not all(record["cell_count"] == 2761 for record in records):
    raise SystemExit("ellipsoid failure records do not match the configured mesh")
first_path = next(
    (
        record["time_s"]
        for record in records
        if record["cavity_to_surface_shear_path_found"]
    ),
    None,
)
if first_path != summary["first_cavity_to_surface_shear_path_time_s"]:
    raise SystemExit("reported first path time does not match per-record results")
print(
    "Ellipsoid failure progression passed with "
    f"{len(records)} stress records through {times[-1]:g} s."
)
PY
