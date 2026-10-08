#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR="${ROOT}/pylith/step02_mogi_benchmark/output"
PYTHON="${ROOT}/envs/axial-modeling/bin/python"
MATERIAL_H5="${OUTPUT_DIR}/mogi-material.h5"
SUMMARY_JSON="${OUTPUT_DIR}/failure-progression-analysis.json"

PYTHONPATH="${ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}" "${PYTHON}" \
    -m axialstress.failure_analysis \
    --material-h5 "${MATERIAL_H5}" \
    --output "${SUMMARY_JSON}" \
    --cohesion-pa 1000000 \
    --friction-angle-deg 25 \
    --pore-pressure-pa 0 \
    --all-times

PYTHONPATH="${ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}" "${PYTHON}" - "${SUMMARY_JSON}" <<'PY'
import json
import sys
from pathlib import Path

summary = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
records = summary.get("records", [])
if summary.get("record_count") != len(records) or not records:
    raise SystemExit("failure history has a missing or inconsistent record count")
times = [record["time_s"] for record in records]
if any(later <= earlier for earlier, later in zip(times, times[1:], strict=False)):
    raise SystemExit("failure history times are not strictly increasing")
first_path = next(
    (record["time_s"] for record in records if record["cavity_to_surface_shear_path_found"]),
    None,
)
if first_path != summary["first_cavity_to_surface_shear_path_time_s"]:
    raise SystemExit("reported first path time does not match the per-record results")
print(f"Synthetic failure history passed with {len(records)} output record(s).")
PY
