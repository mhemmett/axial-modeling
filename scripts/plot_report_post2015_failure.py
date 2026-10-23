"""Plot observed post-2015 uplift and PyLith cavity stress histories."""

from __future__ import annotations

import csv
import json
from datetime import date, timedelta
from pathlib import Path

import h5py
import matplotlib

matplotlib.use("Agg")

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np

from axialstress.failure import stress_voigt_to_tensor_pa
from axialstress.failure_analysis import analyze_stress_history
from axialstress.paper_bpr import file_sha256
from axialstress.surface_interpolation import interpolate_triangular_surface
from axialstress.topology import box_cavity_boundary_cells

ROOT = Path(__file__).resolve().parents[1]
OBS = ROOT / "data/processed/ooi_center_daily"
MAXWELL = ROOT / "data/processed/source_value_ooi_failure_2015_present"
TECTONIC = ROOT / "data/processed/source_value_tectonic_post_2015"
BASIS = ROOT / "data/processed/refined_elastic_basis_400m"
ELASTIC_SCREEN = ROOT / "data/processed/method_refined_failure_400m/summary.json"
OUTPUT = ROOT / "figures/report_post2015_failure"
SUMMARY = ROOT / "data/processed/report_post2015_failure_summary.json"
CASES = (
    ("constant_maxwell", "Uniform Maxwell", "#4d8261"),
    ("thermal_maxwell", "Thermal Maxwell", "#b14b40"),
    ("hydrothermal_maxwell", "Hydrothermal Maxwell", "#c69d3b"),
    ("tectonic_hydrothermal", "Hydrothermal + spreading", "#75558b"),
)


def _elastic_history(observed: list[dict]) -> tuple[np.ndarray, dict]:
    """Compute elastic cavity principal stress from observed OOI uplift."""
    screen = json.loads(ELASTIC_SCREEN.read_text(encoding="utf-8"))
    reference_path = BASIS / "fixed-base-equilibrium-material.h5"
    loaded_path = BASIS / "fixed-base-material.h5"
    surface_path = BASIS / "fixed-base-surface.h5"
    if (
        screen.get("paper_output_data_used") is not False
        or screen["equilibrium_material_sha256"] != file_sha256(reference_path)
        or screen["one_mpa_material_sha256"] != file_sha256(loaded_path)
        or screen["fixed_base_surface_sha256"] != file_sha256(surface_path)
    ):
        raise ValueError("elastic PyLith basis differs from screened stress")
    with h5py.File(surface_path, "r") as surface:
        surf_vertices = np.asarray(surface["geometry/vertices"], dtype=float)
        triangles = np.asarray(surface["viz/topology/cells"], dtype=np.int64)
        displacement = np.asarray(surface["vertex_fields/displacement"][-1], dtype=float)
    compliance = float(
        interpolate_triangular_surface(surf_vertices, triangles, displacement, (0.0, 0.0))[2]
    )
    if compliance <= 0.0:
        raise ValueError("nonpositive elastic compliance at OOI MJ03F")
    uplift = np.asarray([float(row["uplift_from_2015_baseline_m"]) for row in observed])
    pressure = uplift / compliance
    with h5py.File(reference_path, "r") as material:
        vertices = np.asarray(material["geometry/vertices"], dtype=float)
        cells = np.asarray(material["viz/topology/cells"], dtype=np.int64)
        reference = np.asarray(material["cell_fields/cauchy_stress"][-1], dtype=float)
    with h5py.File(loaded_path, "r") as material:
        if not np.array_equal(vertices, material["geometry/vertices"][:]) or not np.array_equal(
            cells, material["viz/topology/cells"][:]
        ):
            raise ValueError("elastic PyLith meshes differ")
        loaded = np.asarray(material["cell_fields/cauchy_stress"][-1], dtype=float)
    cavity = box_cavity_boundary_cells(vertices, cells)["cavity"]
    principal = np.empty(len(pressure))
    for start in range(0, len(pressure), 128):
        stop = min(len(pressure), start + 128)
        stress = (
            reference[cavity][None]
            + pressure[start:stop, None, None] * (loaded[cavity] - reference[cavity])[None]
        )
        principal[start:stop] = np.linalg.eigvalsh(stress_voigt_to_tensor_pa(stress))[:, :, -1].max(
            axis=1
        )
    bracket = screen["pressure_scan"]["0"]
    lower = float(bracket["refined_last_without_joint_pressure_mpa"])
    upper = float(bracket["refined_first_joint_pressure_mpa"])
    if upper <= lower:
        raise ValueError("elastic joint-failure pressure bracket is invalid")
    lower_index = next((i for i, value in enumerate(pressure) if value > lower), None)
    upper_index = next((i for i, value in enumerate(pressure) if value >= upper), None)
    if upper_index is not None:
        stress = reference + pressure[upper_index] * (loaded - reference)
        check = analyze_stress_history(
            vertices,
            cells,
            stress[None],
            np.asarray([0.0]),
            cohesion_pa=1.0e6,
            friction_angle_deg=25.0,
            pore_pressure_pa=0.0,
        )["records"][0]
        if not (
            check["maximum_cavity_principal_stress_pa"] > 0.0
            and check["cavity_to_surface_shear_path_found"]
        ):
            raise ValueError("first post-2015 elastic candidate does not meet joint screen")
    return principal, {
        "static_compliance_m_per_mpa": compliance,
        "pressure_scan_bracket_mpa": [lower, upper],
        "first_above_scan_lower_utc": observed[lower_index]["time_utc"]
        if lower_index is not None
        else None,
        "first_confirmed_joint_utc": observed[upper_index]["time_utc"]
        if upper_index is not None
        else None,
        "first_confirmed_joint_pressure_mpa": float(pressure[upper_index])
        if upper_index is not None
        else None,
        "last_inferred_pressure_mpa": float(pressure[-1]),
        "maximum_cavity_principal_stress_pa": float(principal.max()),
        "elastic_failure_summary_sha256": file_sha256(ELASTIC_SCREEN),
        "reference_sha256": file_sha256(reference_path),
        "loaded_sha256": file_sha256(loaded_path),
        "surface_sha256": file_sha256(surface_path),
    }


def main() -> None:
    """Save the observed uplift and first conditional PyLith failure dates."""
    obs_summary_path = OBS / "summary.json"
    obs_summary = json.loads(obs_summary_path.read_text(encoding="utf-8"))
    obs_series_path = OBS / "center_relative_uplift.csv"
    if (
        obs_summary.get("paper_model_output_used") is not False
        or file_sha256(obs_series_path) != obs_summary["series_sha256"]
    ):
        raise ValueError("post-2015 OOI observational provenance changed")
    with obs_series_path.open(encoding="utf-8", newline="") as stream:
        observed = list(csv.DictReader(stream))
    obs_dates = [date.fromisoformat(row["time_utc"]) for row in observed]
    uplift = np.asarray([float(row["uplift_from_2015_baseline_m"]) for row in observed])
    elastic_stress, elastic_record = _elastic_history(observed)
    figure, (top, bottom) = plt.subplots(
        2,
        1,
        figsize=(8.2, 5.5),
        sharex=True,
        layout="constrained",
        gridspec_kw={"height_ratios": [1.1, 1.8]},
    )
    segment_start = 0
    for index in range(1, len(obs_dates) + 1):
        if index < len(obs_dates) and obs_dates[index] - obs_dates[index - 1] == timedelta(days=1):
            continue
        top.plot(
            obs_dates[segment_start:index], uplift[segment_start:index], color="0.2", linewidth=0.85
        )
        segment_start = index
    top.set_ylabel("Center uplift (m)")
    top.set_title("a  Observed OOI Central Caldera daily depth", loc="left", fontsize=10)
    bottom.plot(obs_dates, elastic_stress / 1.0e6, color="#315f9c", linewidth=1.0, label="Elastic")
    model_records = {}
    for case, label, color in CASES:
        summary_path = (
            TECTONIC / "summary.json"
            if case == "tectonic_hydrothermal"
            else MAXWELL / case / "summary.json"
        )
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        series_path = (
            TECTONIC / "pressure_failure.csv"
            if case == "tectonic_hydrothermal"
            else MAXWELL / case / "pressure_failure.csv"
        )
        fit_provenance_matches = (
            summary["fit_summary_sha256"]
            == file_sha256(MAXWELL / "hydrothermal_maxwell/summary.json")
            if case == "tectonic_hydrothermal"
            else summary["observation_summary_sha256"] == file_sha256(obs_summary_path)
        )
        if (
            summary.get("paper_output_data_used") is not False
            or summary["series_sha256"] != file_sha256(series_path)
            or not fit_provenance_matches
        ):
            raise ValueError(f"post-2015 {case} provenance changed")
        with series_path.open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        dates = [date.fromisoformat(row["time_utc"][:10]) for row in rows]
        stress = np.asarray(
            [float(row["maximum_cavity_principal_stress_pa"]) / 1.0e6 for row in rows]
        )
        bottom.plot(dates, stress, color=color, linewidth=1.0, label=label)
        first = summary["first_sampled_joint_failure_utc"]
        if first:
            bottom.axvline(date.fromisoformat(first), color=color, linestyle="--", linewidth=0.8)
        model_records[case] = {
            "first_sampled_joint_failure_utc": first,
            "maximum_cavity_principal_stress_pa": float(stress.max() * 1.0e6),
            "summary_sha256": file_sha256(summary_path),
            "series_sha256": file_sha256(series_path),
        }
    bottom.axhline(0.0, color="0.3", linewidth=0.7, linestyle=":")
    for gap in obs_summary["gaps"]:
        if gap["missing_days"] >= 30:
            for ax in (top, bottom):
                ax.axvspan(
                    date.fromisoformat(gap["first_missing_day"]),
                    date.fromisoformat(gap["last_missing_day"]),
                    color="0.85",
                    alpha=0.5,
                    zorder=0,
                )
    first_elastic = elastic_record["first_confirmed_joint_utc"]
    if first_elastic:
        first_date = date.fromisoformat(first_elastic)
        bottom.axvline(first_date, color="#315f9c", linestyle="--", linewidth=0.85)
        bottom.annotate(
            "elastic first joint screen",
            xy=(first_date, 0.0),
            xytext=(12, 15),
            textcoords="offset points",
            fontsize=7,
            arrowprops={"arrowstyle": "-", "color": "#315f9c"},
        )
    bottom.set_ylabel("Maximum cavity principal stress (MPa)")
    bottom.set_title("b  PyLith stress from BPR-fitted loading", loc="left", fontsize=10)
    bottom.legend(frameon=False, fontsize=8, ncol=2)
    bottom.xaxis.set_major_locator(mdates.YearLocator(2))
    bottom.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    bottom.set_xlabel("Year")
    for ax in (top, bottom):
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", color="0.88", linewidth=0.5)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(OUTPUT.with_suffix(".pdf"))
    figure.savefig(OUTPUT.with_suffix(".png"), dpi=200)
    plt.close(figure)
    record = {
        "method": "OOI observed uplift and PyLith BPR-constrained cavity stress",
        "status": "conditional_post_2015_failure_history",
        "paper_output_data_used": False,
        "observation_summary_sha256": file_sha256(obs_summary_path),
        "last_observed_utc": obs_summary["last_observed_date_utc"],
        "observed_daily_depth_count": len(observed),
        "elastic": elastic_record,
        "maxwell_cases": model_records,
        "interpretation": (
            "Crossings are retrospective BPR-constrained screens, not prospective "
            "eruption forecasts."
        ),
    }
    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUTPUT.with_suffix('.pdf')}")


if __name__ == "__main__":
    main()
