#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
project_python="${project_root}/envs/axial-modeling/bin/python"
export PYTHONPATH="${project_root}/src:${project_root}/scripts"

for near_size_m in 400 250 150; do
    case "${near_size_m}" in
        400) max_tetrahedra=20000 ;;
        250) max_tetrahedra=30000 ;;
        150) max_tetrahedra=60000 ;;
    esac
    basis_dir="${project_root}/data/processed/refined_elastic_basis_${near_size_m}m"
    fit_dir="${project_root}/data/processed/method_refined_fit_${near_size_m}m"
    failure_dir="${project_root}/data/processed/method_refined_failure_${near_size_m}m"
    "${project_python}" "${project_root}/scripts/refined_elastic_basis.py" \
        --lc-near-m "${near_size_m}" \
        --max-tetrahedra "${max_tetrahedra}" \
        --output-dir "${basis_dir}" --overwrite
    "${project_python}" "${project_root}/scripts/reconstruct_center_pressure.py" \
        --surface "${basis_dir}/fixed-base-surface.h5" \
        --output-dir "${fit_dir}" --overwrite
    "${project_python}" "${project_root}/scripts/screen_bpr_failure.py" \
        --fit-dir "${fit_dir}" --step-output "${basis_dir}" \
        --basis-summary "${basis_dir}/basis_summary.json" \
        --output-dir "${failure_dir}" --overwrite
done

"${project_python}" "${project_root}/scripts/summarize_method_mesh_refinement.py"
