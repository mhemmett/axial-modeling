"""Compare written hydrothermal temperatures across bounded ellipsoid meshes."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

from axialstress.tetrahedral_interpolation import interpolate_tetrahedral_field
from axialstress.thermal_model import solve_written_thermal_model

ROOT = Path(__file__).resolve().parents[1]
STEP_DIR = ROOT / "pylith" / "step03_steady_thermal"
MESH_DIR = STEP_DIR / "mesh" / "thermal_sensitivity"
OUTPUT_DIR = ROOT / "data" / "processed"
SUMMARY_PATH = OUTPUT_DIR / "thermal_mesh_sensitivity.json"
FIGURE_STEM = ROOT / "figures" / "thermal_mesh_sensitivity"
LC_FAR_M = 10_000.0
LC_NEAR_M = (1_200.0, 1_150.0, 1_100.0)
MAX_TETRAHEDRA = 3_500


def _probe_points_m() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return a vertical profile and a plane of common rock-domain probes."""
    profile_depth_m = np.linspace(100.0, 9_500.0, 24)
    profile_points = np.column_stack(
        (
            np.full_like(profile_depth_m, 5_000.0),
            np.zeros_like(profile_depth_m),
            -profile_depth_m,
        )
    )
    plane_x_m, plane_y_m = np.meshgrid(
        np.linspace(-12_000.0, 12_000.0, 9),
        np.linspace(-12_000.0, 12_000.0, 9),
        indexing="xy",
    )
    plane_points = np.column_stack(
        (plane_x_m.ravel(), plane_y_m.ravel(), np.full(plane_x_m.size, -2_500.0))
    )
    return profile_points, plane_points, np.vstack((profile_points, plane_points))


def _summarize_pair(
    coarse_name: str,
    fine_name: str,
    coarse_values_c: np.ndarray,
    fine_values_c: np.ndarray,
    probe_points_m: np.ndarray,
) -> dict[str, object]:
    """Return finite-probe differences between two non-nested meshes."""
    difference_c = fine_values_c - coarse_values_c
    absolute_difference_c = np.abs(difference_c)
    maximum_index = int(np.argmax(absolute_difference_c))
    return {
        "coarse_case": coarse_name,
        "fine_case": fine_name,
        "probe_count": int(len(difference_c)),
        "probe_rmse_c": float(np.sqrt(np.mean(difference_c**2))),
        "probe_median_absolute_change_c": float(np.median(absolute_difference_c)),
        "probe_95th_percentile_absolute_change_c": float(
            np.quantile(absolute_difference_c, 0.95)
        ),
        "probe_maximum_absolute_change_c": float(np.max(absolute_difference_c)),
        "probe_maximum_change_location_m": probe_points_m[maximum_index].tolist(),
        "interpretation": (
            "Finite common-probe changes only; independently generated meshes "
            "are not nested and this is not a fieldwise convergence norm."
        ),
    }


def main() -> None:
    """Generate three bounded meshes and compare hydrothermal temperatures."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from meshing.axial_ellipsoid_bpr import build_mesh

    MESH_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    profile_points_m, plane_points_m, probe_points_m = _probe_points_m()
    cases: list[dict[str, object]] = []
    probe_values_by_case: list[np.ndarray] = []
    profile_values_by_case: list[np.ndarray] = []

    for index, lc_near_m in enumerate(LC_NEAR_M, start=1):
        name = f"mesh_{index}"
        mesh_path = MESH_DIR / f"{name}.msh"
        archive_path = STEP_DIR / "output" / f"{name}_hydrothermal.npz"
        tetrahedron_count = build_mesh(
            mesh_path,
            lc_far=LC_FAR_M,
            lc_near=lc_near_m,
            max_tetrahedra=MAX_TETRAHEDRA,
        )
        if not 0 < tetrahedron_count <= MAX_TETRAHEDRA:
            raise RuntimeError(
                f"{name} has {tetrahedron_count} tetrahedra; expected 1–"
                f"{MAX_TETRAHEDRA}"
            )
        statistics = solve_written_thermal_model(
            mesh_path, archive_path, hydrothermal=True
        )
        with np.load(archive_path, allow_pickle=False) as archive:
            vertices_m = np.asarray(archive["vertices_m"], dtype=float)
            tetrahedra = np.asarray(archive["tetrahedra"], dtype=np.int64)
            temperature_c = np.asarray(archive["temperature_c"], dtype=float)
            probe_values_c = interpolate_tetrahedral_field(
                vertices_m, tetrahedra, temperature_c, probe_points_m
            )
            profile_values_c = interpolate_tetrahedral_field(
                vertices_m, tetrahedra, temperature_c, profile_points_m
            )
        if len(tetrahedra) != tetrahedron_count:
            raise RuntimeError(f"{name} archive tetrahedron count changed after solve")

        probe_values_by_case.append(probe_values_c)
        profile_values_by_case.append(profile_values_c)
        cases.append(
            {
                "name": name,
                "lc_near_m": lc_near_m,
                "lc_far_m": LC_FAR_M,
                "tetrahedron_count": tetrahedron_count,
                "picard_iterations": statistics[0],
                "relative_picard_change": statistics[1],
                "temperature_range_c": [statistics[2], statistics[3]],
                "maximum_free_residual_w": statistics[4],
                "relative_energy_imbalance": statistics[5],
                "net_boundary_heat_rate_w": statistics[6],
                "vertical_profile_temperature_c": profile_values_c.tolist(),
            }
        )

    pairwise = [
        _summarize_pair(
            cases[index]["name"],
            cases[index + 1]["name"],
            probe_values_by_case[index],
            probe_values_by_case[index + 1],
            probe_points_m,
        )
        for index in range(len(cases) - 1)
    ]
    summary = {
        "method": "steady written Eq. 14 with hydrothermal Eq. 22 conductivity",
        "boundary_assumption": (
            "30 degrees C per km on all external faces; 1200 degrees C on the cavity"
        ),
        "mesh_limits": {
            "lc_far_m": LC_FAR_M,
            "lc_near_m": list(LC_NEAR_M),
            "maximum_tetrahedra": MAX_TETRAHEDRA,
        },
        "probe_definition": (
            "24 points on a vertical x=5 km profile and 81 points on a z=-2.5 km "
            "plane; all points lie in the host-rock domain"
        ),
        "cases": cases,
        "pairwise_changes": pairwise,
        "limitations": [
            "The independently generated tetrahedral meshes are not nested.",
            "Probe differences are not a fieldwise norm or proof of convergence.",
            "Lateral and basal temperatures extend the assumed background geotherm.",
            "The hydrothermal conductivity law remains a written-model diagnostic.",
        ],
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    _plot_sensitivity(profile_values_by_case, profile_points_m, pairwise)
    print(json.dumps(summary, indent=2))
    print(f"wrote {SUMMARY_PATH}, {FIGURE_STEM}.png, and {FIGURE_STEM}.pdf")


def _plot_sensitivity(
    profile_values_by_case: list[np.ndarray],
    profile_points_m: np.ndarray,
    pairwise: list[dict[str, object]],
) -> None:
    """Plot the common vertical profiles and finite-probe differences."""
    FIGURE_STEM.parent.mkdir(parents=True, exist_ok=True)
    depth_km = -profile_points_m[:, 2] / 1_000.0
    figure, (profile_axis, difference_axis) = plt.subplots(
        1, 2, figsize=(10.5, 4.6), constrained_layout=True
    )
    for index, values_c in enumerate(profile_values_by_case):
        profile_axis.plot(
            values_c,
            depth_km,
            marker="o",
            markersize=2.6,
            linewidth=1.4,
            label=f"near size {LC_NEAR_M[index]:g} m",
        )
    profile_axis.set_title("Temperature on the x = 5 km profile")
    profile_axis.set_xlabel("Temperature (°C)")
    profile_axis.set_ylabel("Depth below surface (km)")
    profile_axis.invert_yaxis()
    profile_axis.grid(True, color="#D9D9D9", linewidth=0.55)
    profile_axis.legend(frameon=False)

    pair_locations = np.arange(1, len(pairwise) + 1)
    pair_labels = [
        f"{LC_NEAR_M[index]:g} to {LC_NEAR_M[index + 1]:g} m"
        for index in range(len(pairwise))
    ]
    metrics = (
        ("probe_rmse_c", "Probe RMSE"),
        ("probe_95th_percentile_absolute_change_c", "95th percentile"),
        ("probe_maximum_absolute_change_c", "Maximum change"),
    )
    for key, label in metrics:
        difference_axis.plot(
            pair_locations,
            [comparison[key] for comparison in pairwise],
            marker="o",
            linewidth=1.4,
            label=label,
        )
    difference_axis.set_xticks(pair_locations, pair_labels)
    difference_axis.set_yscale("log")
    difference_axis.set_title("Temperature change at shared probes")
    difference_axis.set_xlabel("Adjacent mesh pair")
    difference_axis.set_ylabel("Absolute change (°C)")
    difference_axis.grid(True, color="#D9D9D9", linewidth=0.55)
    difference_axis.legend(frameon=False, fontsize=8)
    figure.suptitle("Hydrothermal temperature mesh sensitivity")
    figure.savefig(FIGURE_STEM.with_suffix(".png"), dpi=220)
    figure.savefig(FIGURE_STEM.with_suffix(".pdf"))
    plt.close(figure)


if __name__ == "__main__":
    main()
