"""Plot elastic and Maxwell PyLith failure indicators on reservoir sections."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import h5py
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import source_value_maxwell_cases as maxwell
from matplotlib.collections import PolyCollection
from matplotlib.patches import Patch

from axialstress.failure import mohr_coulomb_yield_pa, stress_voigt_to_tensor_pa
from axialstress.failure_analysis import analyze_stress_history
from axialstress.paper_bpr import file_sha256

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "processed" / "source_value_bpr_failure_2011_2015"
REFERENCE = (
    ROOT
    / "data"
    / "processed"
    / "refined_elastic_basis_400m"
    / "fixed-base-equilibrium-material.h5"
)
ELASTIC_FAILURE = ROOT / "data" / "processed" / "method_refined_failure_400m"
ELASTIC_FIT = ROOT / "data" / "processed" / "method_refined_fit_400m"
ELASTIC_BASIS = ROOT / "data" / "processed" / "refined_elastic_basis_400m"
OUTPUT = ROOT / "figures" / "report_figure5_failure"
SUMMARY = ROOT / "data" / "processed" / "report_figure5_failure_summary.json"
CASES = (
    ("elastic", "Elastic: first joint screen, 7 Nov 2012"),
    ("constant_maxwell", "Uniform Maxwell"),
    ("thermal_maxwell", "Thermal Maxwell"),
    ("hydrothermal_maxwell", "Hydrothermal Maxwell"),
)
EDGES = ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3))


def _slice_polygons(
    vertices_m: np.ndarray, cells: np.ndarray, plane_offset_m: float = 0.0
) -> tuple[list[np.ndarray], np.ndarray]:
    """Intersect tetrahedra with the vertical N30W reservoir-axis plane."""
    major = np.asarray((-0.5, np.sqrt(3.0) / 2.0, 0.0))
    normal = np.asarray((np.sqrt(3.0) / 2.0, 0.5, 0.0))
    tetrahedra = vertices_m[cells]
    along_m = tetrahedra @ major
    across_m = tetrahedra @ normal - plane_offset_m
    depth_m = -tetrahedra[:, :, 2]
    polygons = []
    indices = []
    for cell_index in range(len(cells)):
        signed_m = across_m[cell_index]
        if np.min(signed_m) > 0.0 or np.max(signed_m) < 0.0:
            continue
        points = []
        for left, right in EDGES:
            first, second = signed_m[left], signed_m[right]
            if first * second > 0.0:
                continue
            if np.isclose(first, second, atol=1.0e-10):
                if np.isclose(first, 0.0, atol=1.0e-10):
                    points.extend(
                        (
                            (along_m[cell_index, left], depth_m[cell_index, left]),
                            (along_m[cell_index, right], depth_m[cell_index, right]),
                        )
                    )
                continue
            fraction = -first / (second - first)
            if 0.0 <= fraction <= 1.0:
                points.append(
                    (
                        along_m[cell_index, left]
                        + fraction * (along_m[cell_index, right] - along_m[cell_index, left]),
                        depth_m[cell_index, left]
                        + fraction * (depth_m[cell_index, right] - depth_m[cell_index, left]),
                    )
                )
        unique = np.unique(np.round(np.asarray(points, dtype=float), 6), axis=0)
        if len(unique) < 3:
            continue
        center = unique.mean(axis=0)
        angle = np.arctan2(unique[:, 1] - center[1], unique[:, 0] - center[0])
        polygon = unique[np.argsort(angle)] / 1000.0
        area_km2 = 0.5 * abs(
            np.dot(polygon[:, 0], np.roll(polygon[:, 1], -1))
            - np.dot(polygon[:, 1], np.roll(polygon[:, 0], -1))
        )
        if area_km2 > 1.0e-10:
            polygons.append(polygon)
            indices.append(cell_index)
    if not polygons:
        raise ValueError("reservoir-axis plane did not intersect the PyLith mesh")
    return polygons, np.asarray(indices, dtype=np.int64)


def _stress_state(
    input_dir: Path,
    reference_path: Path,
    case: str,
    expected_sha256: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, str]:
    """Return the last fitted Cauchy stress plus same-mesh reference stress."""
    path = input_dir / "runs" / case / "bpr_pressure" / "output" / "maxwell-material.h5"
    if file_sha256(path) != expected_sha256:
        raise ValueError(f"fitted PyLith stress output changed for {case}")
    with h5py.File(path, "r") as material:
        vertices = np.asarray(material["geometry/vertices"], dtype=float)
        cells = np.asarray(material["viz/topology/cells"], dtype=np.int64)
        increment = np.asarray(material["cell_fields/cauchy_stress"][-1], dtype=float)
    reference = maxwell._reference_stress(reference_path, vertices, cells)
    return vertices, cells, increment + reference, file_sha256(path)


def _outline_cavity(ax: plt.Axes, plane_offset_m: float = 0.0) -> None:
    """Draw the source-specified ideal ellipsoid on the model section."""
    half_length_km = 3.0 * np.sqrt(1.0 - (plane_offset_m / 1500.0) ** 2)
    along_km = np.linspace(-half_length_km, half_length_km, 300)
    radius = np.sqrt(
        np.maximum(0.0, 1.0 - (along_km / 3.0) ** 2 - (plane_offset_m / 1500.0) ** 2)
    )
    top = 1.6 - 0.5 * radius
    bottom = 1.6 + 0.5 * radius
    ax.fill_between(along_km, top, bottom, color="white", zorder=8)
    ax.plot(along_km, top, color="0.2", linewidth=0.75, zorder=9)
    ax.plot(along_km, bottom, color="0.2", linewidth=0.75, zorder=9)


def _elastic_stress_state() -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, object]]:
    """Rebuild the nominal elastic first-joint state from hashed PyLith fields."""
    failure_path = ELASTIC_FAILURE / "summary.json"
    failure = json.loads(failure_path.read_text(encoding="utf-8"))
    fit_path = ELASTIC_FIT / "summary.json"
    fit = json.loads(fit_path.read_text(encoding="utf-8"))
    basis_path = ELASTIC_BASIS / "basis_summary.json"
    basis = json.loads(basis_path.read_text(encoding="utf-8"))
    if (
        failure.get("paper_output_data_used") is not False
        or fit.get("paper_output_data_used") is not False
        or basis.get("paper_output_data_used") is not False
        or failure["fit_summary_sha256"] != file_sha256(fit_path)
        or failure["basis_summary_sha256"] != file_sha256(basis_path)
    ):
        raise ValueError("elastic fit and stress provenance do not agree")
    reference_path = ELASTIC_BASIS / "fixed-base-equilibrium-material.h5"
    loaded_path = ELASTIC_BASIS / "fixed-base-material.h5"
    if (
        failure["equilibrium_material_sha256"] != file_sha256(reference_path)
        or failure["one_mpa_material_sha256"] != file_sha256(loaded_path)
    ):
        raise ValueError("elastic PyLith fields differ from the failure screen")
    with h5py.File(reference_path, "r") as material:
        vertices = np.asarray(material["geometry/vertices"], dtype=float)
        cells = np.asarray(material["viz/topology/cells"], dtype=np.int64)
        reference = np.asarray(material["cell_fields/cauchy_stress"][-1], dtype=float)
    with h5py.File(loaded_path, "r") as material:
        if not np.array_equal(vertices, material["geometry/vertices"][:]) or not np.array_equal(
            cells, material["viz/topology/cells"][:]
        ):
            raise ValueError("elastic reference and pressure meshes differ")
        loaded = np.asarray(material["cell_fields/cauchy_stress"][-1], dtype=float)
    first = failure["bpr_histories"]["1.0"]["strength_cases"]["0"]
    with (ELASTIC_FIT / fit["pressure_history_csv"]).open(
        encoding="utf-8", newline=""
    ) as stream:
        rows = [
            row
            for row in csv.DictReader(stream)
            if row["time_utc"] == first["first_joint_time_utc"]
        ]
    if len(rows) != 1:
        raise ValueError("elastic first-joint date is missing from the fitted pressure history")
    pressure_mpa = float(rows[0]["pressure_change_mpa"])
    if not np.isclose(pressure_mpa, first["first_joint_fitted_pressure_mpa"], atol=1.0e-9):
        raise ValueError("elastic first-joint pressure differs from the screened history")
    stress = reference + pressure_mpa * (loaded - reference)
    analysis = analyze_stress_history(
        vertices,
        cells,
        stress[None, :, :],
        np.asarray([0.0]),
        cohesion_pa=1.0e6,
        friction_angle_deg=25.0,
        pore_pressure_pa=0.0,
    )["records"][0]
    if not analysis["cavity_to_surface_shear_path_found"] or not (
        analysis["maximum_cavity_principal_stress_pa"] > 0.0
    ):
        raise ValueError("elastic first-joint stress state no longer meets both screens")
    return vertices, cells, stress, {
        "failure_summary_sha256": file_sha256(failure_path),
        "fit_summary_sha256": file_sha256(fit_path),
        "pressure_history_sha256": file_sha256(ELASTIC_FIT / fit["pressure_history_csv"]),
        "reference_sha256": file_sha256(reference_path),
        "loaded_sha256": file_sha256(loaded_path),
        "first_joint_time_utc": first["first_joint_time_utc"],
        "first_joint_pressure_mpa": pressure_mpa,
        "cavity_principal_stress_pa": analysis["maximum_cavity_principal_stress_pa"],
        "connected_path_cell_indices": list(
            map(int, analysis["cavity_to_surface_path_cell_indices"])
        ),
    }


def main() -> None:
    """Save a partial Cabaniss Figure 5 analogue from actual PyLith stress."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=INPUT)
    parser.add_argument("--reference", type=Path, default=REFERENCE)
    parser.add_argument("--output-stem", type=Path, default=OUTPUT)
    parser.add_argument("--summary", type=Path, default=SUMMARY)
    args = parser.parse_args()
    input_dir = args.input_dir.resolve()
    reference_path = args.reference.resolve()
    output_stem = args.output_stem.resolve()
    summary_path = args.summary.resolve()
    source_path = input_dir / "summary.json"
    source = json.loads(source_path.read_text(encoding="utf-8"))
    if source.get("paper_output_data_used") is not False:
        raise ValueError("stress reconstruction provenance is not independent")
    if file_sha256(reference_path) != source["equilibrium_sha256"]:
        raise ValueError("gravity reference differs from the fitted model")
    fig, axes = plt.subplots(4, 1, figsize=(8.1, 6.2), sharex=True, layout="constrained")
    first_vertices = None
    first_cells = None
    records = {}
    for ax, (case, label) in zip(axes, CASES, strict=True):
        if case == "elastic":
            vertices, cells, stress_voigt_pa, elastic_record = _elastic_stress_state()
            plane_offset_m = -1200.0
        else:
            case_summary = source["cases"][case]
            vertices, cells, stress_voigt_pa, output_sha256 = _stress_state(
                input_dir,
                reference_path,
                case,
                case_summary["forward_material_sha256"],
            )
            plane_offset_m = 0.0
        if first_vertices is None:
            first_vertices, first_cells = vertices, cells
        elif not np.array_equal(first_vertices, vertices) or not np.array_equal(
            first_cells, cells
        ):
            raise ValueError("elastic and Maxwell cases do not share the same PyLith mesh")
        polygons, cell_indices = _slice_polygons(vertices, cells, plane_offset_m)
        tensor = stress_voigt_to_tensor_pa(stress_voigt_pa)
        tensile = np.linalg.eigvalsh(tensor)[:, -1] > 0.0
        shear = (
            mohr_coulomb_yield_pa(
                tensor,
                cohesion_pa=1.0e6,
                friction_angle_deg=25.0,
                pore_pressure_pa=0.0,
            )
            >= 0.0
        )
        ax.add_collection(
            PolyCollection(
                polygons,
                facecolors="#f5f5f5",
                edgecolors="#dddddd",
                linewidths=0.15,
                zorder=1,
            )
        )
        ax.add_collection(
            PolyCollection(
                [poly for poly, index in zip(polygons, cell_indices, strict=True) if shear[index]],
                facecolors="#d48647",
                edgecolors="none",
                zorder=2,
            )
        )
        ax.add_collection(
            PolyCollection(
                [
                    poly
                    for poly, index in zip(polygons, cell_indices, strict=True)
                    if tensile[index]
                ],
                facecolors="#427bb4",
                edgecolors="none",
                zorder=3,
            )
        )
        _outline_cavity(ax, plane_offset_m)
        if case == "elastic":
            path_indices = np.asarray(elastic_record["connected_path_cell_indices"])
            centroids = vertices[cells[path_indices]].mean(axis=1)
            along = centroids @ np.asarray((-0.5, np.sqrt(3.0) / 2.0, 0.0)) / 1000.0
            across = centroids @ np.asarray((np.sqrt(3.0) / 2.0, 0.5, 0.0)) / 1000.0
            ax.plot(
                along,
                -centroids[:, 2] / 1000.0,
                color="#893c79",
                linestyle="--",
                marker="o",
                markersize=2.6,
                linewidth=1.1,
                zorder=10,
            )
            ax.text(
                0.01,
                0.06,
                "3-D path projected; section 1.2 km off axis",
                transform=ax.transAxes,
                ha="left",
                va="bottom",
                fontsize=7,
                color="#893c79",
            )
            elastic_record["path_off_axis_km"] = across.tolist()
        ax.set_xlim(-6.0, 6.0)
        ax.set_ylim(4.0, 0.0)
        ax.set_ylabel("Depth (km)")
        ax.set_title(label, loc="left", fontsize=9)
        ax.tick_params(labelsize=8)
        record = {
            "whole_mesh_shear_yield_cells": int(np.count_nonzero(shear)),
            "whole_mesh_tensile_cells": int(np.count_nonzero(tensile)),
            "section_shear_yield_cells": int(np.count_nonzero(shear[cell_indices])),
            "section_tensile_cells": int(np.count_nonzero(tensile[cell_indices])),
            "section_plane_offset_m": plane_offset_m,
        }
        if case == "elastic":
            record.update(elastic_record)
        else:
            record.update(
                {
                    "material_output_sha256": output_sha256,
                    "last_cavity_principal_stress_pa": case_summary[
                        "last_cavity_principal_stress_pa"
                    ],
                    "last_connected_shear_path": case_summary["last_connected_shear_path"],
                }
            )
        records[case] = record
    axes[-1].set_xlabel("Distance along N30°W reservoir axis (km)")
    axes[0].legend(
        handles=[
            Patch(facecolor="#d48647", label="Mohr–Coulomb shear yield"),
            Patch(facecolor="#427bb4", label="Positive principal tension"),
        ],
        frameon=False,
        fontsize=8,
        loc="upper right",
    )
    output_stem.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_stem.with_suffix(".pdf"))
    fig.savefig(output_stem.with_suffix(".png"), dpi=200)
    plt.close(fig)
    summary = {
        "status": "elastic_early_joint_screen_and_last_preeruption_maxwell_sections",
        "paper_output_data_used": False,
        "modeled_time_utc": source["last_grid_time_utc"],
        "source_summary_sha256": file_sha256(source_path),
        "gravity_reference_sha256": file_sha256(reference_path),
        "slice": "vertical N30W plane; elastic panel offset -1.2 km, Maxwell panels on axis",
        "tensile_strength_pa_assumption": 0.0,
        "cohesion_pa": 1.0e6,
        "friction_angle_deg": 25.0,
        "pore_pressure_pa_assumption": 0.0,
        "cases": records,
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {output_stem.with_suffix('.pdf')}")


if __name__ == "__main__":
    main()
