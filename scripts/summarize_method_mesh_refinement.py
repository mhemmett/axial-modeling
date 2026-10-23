"""Summarize BPR pressure and failure onset across refined PyLith meshes."""

from __future__ import annotations

import json
from pathlib import Path

from axialstress.paper_bpr import file_sha256

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data/processed"
LEVELS_M = (400, 250, 150)


def main() -> None:
    """Write a checksum-verified mesh comparison from local model outputs."""
    cases = []
    for near_size_m in LEVELS_M:
        basis_dir = PROCESSED / f"refined_elastic_basis_{near_size_m}m"
        fit_dir = PROCESSED / f"method_refined_fit_{near_size_m}m"
        failure_dir = PROCESSED / f"method_refined_failure_{near_size_m}m"
        basis_path = basis_dir / "basis_summary.json"
        fit_path = fit_dir / "summary.json"
        failure_path = failure_dir / "summary.json"
        basis = json.loads(basis_path.read_text(encoding="utf-8"))
        fit = json.loads(fit_path.read_text(encoding="utf-8"))
        failure = json.loads(failure_path.read_text(encoding="utf-8"))
        if (
            basis["mesh_lc_near_m"] != near_size_m
            or basis["mesh_sha256"] != file_sha256(basis_dir / "axial_ellipsoid.msh")
            or failure["basis_summary_sha256"] != file_sha256(basis_path)
            or failure["fit_summary_sha256"] != file_sha256(fit_path)
            or failure["fixed_base_surface_sha256"]
            != file_sha256(basis_dir / "fixed-base-surface.h5")
            or fit["static_surface_sha256"]
            != file_sha256(basis_dir / "fixed-base-surface.h5")
        ):
            raise ValueError(f"source or model checksum changed for {near_size_m} m")
        case = {
            "near_cavity_size_m": near_size_m,
            "tetrahedra": basis["mesh_tetrahedra"],
            "relative_cavity_volume_difference": basis[
                "relative_cavity_volume_difference"
            ],
            "center_2013_2015_compliance_m_per_mpa": fit[
                "site_compliance_m_per_mpa"
            ]["nemo_2013_2015_center"],
            "nominal_last_preeruption_pressure_mpa": failure["bpr_histories"]["1.0"][
                "last_preeruption_pressure_mpa"
            ],
            "first_connected_path_pressure_mpa": failure[
                "interpolated_shear_path_pressure_mpa"
            ],
            "joint_failure_bracket_mpa_for_zero_tensile_strength": [
                failure["pressure_scan"]["0"]["refined_last_without_joint_pressure_mpa"],
                failure["pressure_scan"]["0"]["refined_first_joint_pressure_mpa"],
            ],
            "joint_pressure_step_mpa": failure["refined_pressure_scan_step_mpa"],
            "first_joint_path_cell_count": failure["pressure_scan"]["0"][
                "refined_joint_path_cell_count"
            ],
            "first_joint_time_utc": failure["bpr_histories"]["1.0"][
                "strength_cases"
            ]["0"]["first_joint_time_utc"],
            "basis_summary_sha256": file_sha256(basis_path),
            "fit_summary_sha256": file_sha256(fit_path),
            "failure_summary_sha256": file_sha256(failure_path),
        }
        cases.append(case)
    summary = {
        "method": "elastic fixed-base PyLith mesh refinement with the same BPR inversion",
        "paper_output_data_used": False,
        "models": cases,
        "mechanical_convergence_established": False,
        "convergence_limit": (
            "The connected-path pressure and pressure-fit compliance still "
            "change from 250 m to 150 m."
        ),
    }
    output = PROCESSED / "method_mesh_refinement.json"
    output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    for case in cases:
        lower_mpa, upper_mpa = case["joint_failure_bracket_mpa_for_zero_tensile_strength"]
        print(
            f"{case['near_cavity_size_m']:3d} m: "
            f"{case['tetrahedra']:5d} tets, "
            f"preeruption {case['nominal_last_preeruption_pressure_mpa']:.2f} MPa, "
            f"path onset {case['first_connected_path_pressure_mpa']:.2f} MPa, "
            f"joint bracket {lower_mpa:.2f}–{upper_mpa:.2f} MPa"
        )
    print(f"wrote {output}")


if __name__ == "__main__":
    main()
