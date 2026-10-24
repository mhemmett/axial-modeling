"""Plot observed Axial cycles from independent PyLith stress fields."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import UTC, datetime
from pathlib import Path

import h5py
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import plot_report_figure5_failure as previous
import source_value_maxwell_cases as maxwell
from matplotlib.collections import PolyCollection
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from axialstress.failure import mohr_coulomb_yield_pa, stress_voigt_to_tensor_pa
from axialstress.failure_analysis import analyze_stress_history
from axialstress.mesh_alignment import match_tetrahedral_cells
from axialstress.paper_bpr import file_sha256
from axialstress.surface_interpolation import interpolate_triangular_surface
from axialstress.topology import box_cavity_boundary_cells

ROOT = Path(__file__).resolve().parents[1]
HISTORICAL = ROOT / "data/processed/source_value_bpr_failure_1998_2011"
HISTORICAL_ELASTIC = ROOT / "data/processed/elastic_bpr_failure_1998_2011"
CURRENT = ROOT / "data/processed/source_value_bpr_failure_2011_2015"
POST = ROOT / "data/processed/source_value_ooi_failure_2015_present"
TECTONIC = ROOT / "data/processed"
BASIS = ROOT / "data/processed/refined_elastic_basis_400m"
REFERENCE = ROOT / "data/processed/refined_elastic_basis_400m/fixed-base-equilibrium-material.h5"
OUTPUT = ROOT / "figures/report_figure5_failure"
SUMMARY = ROOT / "data/processed/report_figure5_failure_summary.json"
MESH_M = 400
FINE_ROOT: Path | None = None
BASE_MAJOR = np.asarray((-0.5, np.sqrt(3.0) / 2.0, 0.0))
BASE_MINOR = np.asarray((np.sqrt(3.0) / 2.0, 0.5, 0.0))
HISTORICAL_ERUPTIONS = {
    "1998–2011": datetime(2011, 4, 6, 12, tzinfo=UTC),
    "2011–2015": datetime(2015, 4, 24, tzinfo=UTC),
}
CASES = (
    ("elastic", "Non-TD elastic"),
    ("constant_maxwell", "Non-TD viscoelastic"),
    ("tectonic_hydrothermal", "Stress + Full TD + hydrothermal"),
    ("hydrothermal_maxwell", "Full TD + hydrothermal"),
    ("thermal_maxwell", "Full TD"),
)


def _elastic_state(cycle: str, role: str) -> tuple | None:
    """Build an elastic stress field at first joint, eruption, or post-2015."""
    if cycle == "1998–2011":
        folder = HISTORICAL_ELASTIC
        summary_path = folder / "summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        series_path = folder / "pressure_failure.csv"
        first_date = summary["first_sampled_joint_failure_utc"]
        event_date = summary["observed_eruption_utc"]
    elif cycle == "2011–2015":
        folder = ROOT / f"data/processed/method_refined_fit_{MESH_M}m"
        summary_path = folder / "summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        series_path = folder / summary["pressure_history_csv"]
        if MESH_M == 400:
            _, _, _, first = previous._elastic_stress_state()
            first_date = first["first_joint_time_utc"]
        else:
            failure_path = ROOT / "data/processed/method_refined_failure_150m/summary.json"
            failure = json.loads(failure_path.read_text(encoding="utf-8"))
            if (
                failure.get("paper_output_data_used") is not False
                or failure["fit_summary_sha256"] != file_sha256(summary_path)
                or failure["basis_summary_sha256"] != file_sha256(BASIS / "basis_summary.json")
            ):
                raise ValueError("150 m elastic failure summary changed")
            first_date = failure["bpr_histories"]["1.0"]["strength_cases"]["0"][
                "first_joint_time_utc"
            ]
        event_date = summary["eruption_utc"]
    else:
        summary_path = (
            ROOT / "data/processed/report_post2015_failure_summary.json"
            if MESH_M == 400 else
            ROOT / "data/processed/method_refined_failure_150m/summary.json"
        )
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        series_path = ROOT / "data/processed/ooi_center_daily/center_relative_uplift.csv"
        first_date = (
            summary["elastic"]["first_confirmed_joint_utc"] if MESH_M == 400 else None
        )
        event_date = None
    if summary.get("paper_output_data_used") is not False:
        raise ValueError(f"elastic {cycle} provenance is incomplete")
    loaded_path = BASIS / "fixed-base-material.h5"
    if cycle == "1998–2011" and (
        summary["series_sha256"] != file_sha256(series_path)
        or summary["gravity_reference_sha256"] != file_sha256(REFERENCE)
        or summary["one_mpa_stress_sha256"] != file_sha256(loaded_path)
    ):
        raise ValueError("historical elastic pressure or stress fields changed")
    if cycle == "post-2015" and MESH_M == 400 and (
        summary["elastic"]["reference_sha256"] != file_sha256(REFERENCE)
        or summary["elastic"]["loaded_sha256"] != file_sha256(loaded_path)
    ):
        raise ValueError("post-2015 elastic PyLith stress fields changed")
    if cycle == "post-2015":
        obs_path = ROOT / "data/processed/ooi_center_daily/summary.json"
        observed = json.loads(obs_path.read_text(encoding="utf-8"))
        if (
            observed["series_sha256"] != file_sha256(series_path)
            or (MESH_M == 400 and summary["observation_summary_sha256"]
                != file_sha256(obs_path))
        ):
            raise ValueError("post-2015 observed depth series changed")
    with series_path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if cycle == "post-2015":
        if MESH_M == 400:
            compliance = float(summary["elastic"]["static_compliance_m_per_mpa"])
        else:
            surface_path = BASIS / "fixed-base-surface.h5"
            basis = json.loads((BASIS / "basis_summary.json").read_text(encoding="utf-8"))
            if (
                basis.get("paper_output_data_used") is not False
                or basis["output_sha256"][surface_path.name] != file_sha256(surface_path)
            ):
                raise ValueError("150 m elastic surface changed")
            with h5py.File(surface_path, "r") as surface:
                compliance = float(
                    interpolate_triangular_surface(
                        np.asarray(surface["geometry/vertices"]),
                        np.asarray(surface["viz/topology/cells"]),
                        np.asarray(surface["vertex_fields/displacement"][-1]),
                        (0.0, 0.0),
                    )[2]
                )
            if compliance <= 0.0:
                raise ValueError("150 m elastic compliance is nonpositive")
            threshold = float(summary["pressure_scan"]["0"]["refined_first_joint_pressure_mpa"])
        for row in rows:
            row["pressure_change_mpa"] = str(
                float(row["uplift_from_2015_baseline_m"]) / compliance
            )
        if MESH_M == 150:
            first = next(
                (row for row in rows if float(row["pressure_change_mpa"]) >= threshold),
                None,
            )
            first_date = first["time_utc"] if first is not None else None
    if role == "first" or (role == "post" and first_date is not None):
        if first_date is None:
            return None
        row = next((r for r in rows if r["time_utc"][:10] == first_date[:10]), None)
        if row is None:
            raise ValueError("elastic first-joint date is absent from fitted series")
        time_utc = row["time_utc"]
    else:
        row = rows[-1]
        time_utc = event_date or row["time_utc"]
    pressure_mpa = float(row["pressure_change_mpa"])
    with h5py.File(REFERENCE, "r") as material:
        vertices = np.asarray(material["geometry/vertices"], dtype=float)
        cells = np.asarray(material["viz/topology/cells"], dtype=np.int64)
        reference = np.asarray(material["cell_fields/cauchy_stress"][-1], dtype=float)
    with h5py.File(loaded_path, "r") as material:
        if not np.array_equal(vertices, material["geometry/vertices"][:]) or not np.array_equal(
            cells, material["viz/topology/cells"][:]
        ):
            raise ValueError("elastic basis meshes differ")
        loaded = np.asarray(material["cell_fields/cauchy_stress"][-1], dtype=float)
    stress = reference + pressure_mpa * (loaded - reference)
    cavity = box_cavity_boundary_cells(vertices, cells)["cavity"]
    earliest_tensile = None
    earliest_tensile_time = None
    for observation in rows:
        trial = reference[cavity] + float(observation["pressure_change_mpa"]) * (
            loaded[cavity] - reference[cavity]
        )
        principal = np.linalg.eigvalsh(stress_voigt_to_tensor_pa(trial))[:, -1]
        if principal.max() > 0.0:
            earliest_tensile = int(cavity[np.argmax(principal)])
            earliest_tensile_time = observation["time_utc"]
            break
    return vertices, cells, stress, {
        "time_utc": time_utc,
        "pressure_mpa": pressure_mpa,
        "stress_source_sha256": file_sha256(loaded_path),
        "source_summary_sha256": file_sha256(summary_path),
        "series_sha256": file_sha256(series_path),
        "first_tensile_cell_index": earliest_tensile,
        "first_tensile_time_utc": earliest_tensile_time,
        "held_pressure_to_event_days": (
            (datetime.fromisoformat(event_date) - datetime.fromisoformat(row["time_utc"]))
            .total_seconds() / 86_400.0
            if role == "event" and event_date else None
        ),
    }


def _maxwell_state(cycle: str, case: str, role: str) -> tuple | None:
    """Read first joint, eruption-date, or post-2015 PyLith stress."""
    tectonic = case == "tectonic_hydrothermal"
    if tectonic:
        suffix = "_150m" if MESH_M == 150 else ""
        folder = TECTONIC / (
            f"source_value_tectonic_{cycle.replace('–', '_').replace('-', '_')}{suffix}"
        )
        summary_path = folder / "summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        projected_width_m = 50_000.0 * (np.sqrt(3.0) / 2.0 + 0.5)
        if (
            summary.get("full_spreading_rate_mm_per_year") != 60.0
            or not np.isclose(
                summary.get("projected_spreading_width_m", 0.0), projected_width_m
            )
        ):
            raise ValueError("tectonic run does not use 60 mm/year across the N60E box span")
        series_path = folder / "pressure_failure.csv"
        material_path = folder / "tectonic_hydrothermal/output/maxwell-material.h5"
        expected_material_sha = summary["stress_sha256"]
    elif cycle == "1998–2011":
        folder = HISTORICAL / case
        summary_path = folder / "summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        series_path = folder / "pressure_failure.csv"
        material_path = folder / "bpr_pressure/output/maxwell-material.h5"
        expected_material_sha = summary["forward_material_sha256"]
    elif cycle == "2011–2015":
        summary_path = CURRENT / "summary.json"
        source = json.loads(summary_path.read_text(encoding="utf-8"))
        if source.get("paper_output_data_used") is not False:
            raise ValueError("2011–2015 PyLith fit provenance is incomplete")
        summary = source["cases"][case]
        series_path = CURRENT / summary["pressure_failure_csv"]
        material_path = CURRENT / "runs" / case / "bpr_pressure/output/maxwell-material.h5"
        expected_material_sha = summary["forward_material_sha256"]
    else:
        folder = POST / case
        summary_path = folder / "summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        series_path = folder / "pressure_failure.csv"
        material_path = folder / "bpr_pressure/output/maxwell-material.h5"
        expected_material_sha = summary["forward_material_sha256"]
    if summary.get("paper_output_data_used", False) is not False:
        raise ValueError(f"{cycle} {case} provenance is incomplete")
    if file_sha256(material_path) != expected_material_sha:
        raise ValueError(f"{cycle} {case} PyLith stress file changed")
    with series_path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if tectonic or cycle != "2011–2015":
        if file_sha256(series_path) != summary["series_sha256"]:
            raise ValueError(f"{cycle} {case} pressure/failure series changed")
    first_joint = next(
        (i for i, row in enumerate(rows) if row["joint_failure_zero_tensile_strength"] == "True"),
        None,
    )
    first_tensile = next(
        (i for i, row in enumerate(rows)
         if float(row["maximum_cavity_principal_stress_pa"]) > 0.0),
        None,
    )
    use_event = role == "event"
    if role == "first" and first_joint is None:
        if tectonic:
            return None
        suffix = cycle.replace("–", "_")
        event_dir = (
            FINE_ROOT / f"source_value_event_states_{suffix}_150m/{case}"
            if MESH_M == 150 else
            ROOT / f"data/processed/source_value_event_states_{suffix}/{case}"
        )
        event = json.loads((event_dir / "summary.json").read_text(encoding="utf-8"))
        if not event["joint_failure_zero_tensile_strength"]:
            return None
        use_event = True
    if (role in {"first", "post"}) and first_joint is not None:
        index = first_joint
    else:
        index = len(rows) - 1
    selected_path = material_path
    selected_time = rows[index]["time_utc"]
    selected_pressure = float(rows[index]["pressure_change_mpa"])
    held_days = None
    if use_event and not tectonic:
        suffix = cycle.replace("–", "_")
        event_dir = (
            FINE_ROOT / f"source_value_event_states_{suffix}_150m/{case}"
            if MESH_M == 150 else
            ROOT / f"data/processed/source_value_event_states_{suffix}/{case}"
        )
        event_summary_path = event_dir / "summary.json"
        event = json.loads(event_summary_path.read_text(encoding="utf-8"))
        selected_path = event_dir / "held_pressure_to_eruption/output/maxwell-material.h5"
        if (
            event.get("paper_output_data_used") is not False
            or event["fit_series_sha256"] != file_sha256(series_path)
            or event["event_stress_sha256"] != file_sha256(selected_path)
        ):
            raise ValueError(f"{cycle} {case} eruption continuation changed")
        selected_time = event["observed_eruption_utc"]
        selected_pressure = float(event["held_pressure_change_mpa"])
        held_days = event["hold_duration_days"]
        index = -1
    with h5py.File(selected_path, "r") as material:
        vertices = np.asarray(material["geometry/vertices"], dtype=float)
        cells = np.asarray(material["viz/topology/cells"], dtype=np.int64)
        increment = np.asarray(material["cell_fields/cauchy_stress"][index], dtype=float)
    reference = maxwell._reference_stress(REFERENCE, vertices, cells)
    first_tensile_cell = None
    if first_tensile is not None:
        with h5py.File(material_path, "r") as material:
            fitted_vertices = np.asarray(material["geometry/vertices"], dtype=float)
            fitted_cells = np.asarray(material["viz/topology/cells"], dtype=np.int64)
            fitted_increment = np.asarray(
                material["cell_fields/cauchy_stress"][first_tensile], dtype=float
            )
        fitted_to_selected = match_tetrahedral_cells(
            fitted_vertices, fitted_cells, vertices, cells
        )
        tensile_stress = reference + fitted_increment[fitted_to_selected]
        cavity = box_cavity_boundary_cells(vertices, cells)["cavity"]
        principal = np.linalg.eigvalsh(
            stress_voigt_to_tensor_pa(tensile_stress[cavity])
        )[:, -1]
        first_tensile_cell = int(cavity[np.argmax(principal)])
    elif use_event:
        cavity = box_cavity_boundary_cells(vertices, cells)["cavity"]
        principal = np.linalg.eigvalsh(
            stress_voigt_to_tensor_pa((reference + increment)[cavity])
        )[:, -1]
        if principal.max() > 0.0:
            first_tensile_cell = int(cavity[np.argmax(principal)])
    return vertices, cells, reference + increment, {
        "time_utc": selected_time,
        "pressure_mpa": selected_pressure,
        "source_summary_sha256": file_sha256(summary_path),
        "stress_source_sha256": file_sha256(selected_path),
        "first_tensile_cell_index": first_tensile_cell,
        "first_tensile_time_utc": (
            rows[first_tensile]["time_utc"] if first_tensile is not None
            else selected_time if first_tensile_cell is not None else None
        ),
        "held_pressure_to_event_days": held_days,
    }


def _path_section(
    vertices: np.ndarray, cells: np.ndarray, path_indices: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, float]:
    """Choose a vertical plane intersecting the most saved shear-path cells."""
    cavity_cells = set(map(int, box_cavity_boundary_cells(vertices, cells)["cavity"]))
    seed = next((int(index) for index in path_indices if index in cavity_cells), None)
    if seed is None:
        raise ValueError("connected path has no cavity-adjacent seed")
    path_vertices = vertices[cells[path_indices]]
    path_centroids = path_vertices.mean(axis=1)
    seed_vertices = vertices[cells[seed]]
    best = None
    for angle_deg in range(180):
        angle = np.deg2rad(angle_deg)
        along = np.asarray((np.cos(angle), np.sin(angle), 0.0))
        normal = np.asarray((-np.sin(angle), np.cos(angle), 0.0))
        seed_projection = seed_vertices @ normal
        support_m = np.hypot(
            3000.0 * float(normal @ BASE_MAJOR),
            1500.0 * float(normal @ BASE_MINOR),
        )
        low = max(float(seed_projection.min()) + 0.01, -0.995 * support_m)
        high = min(float(seed_projection.max()) - 0.01, 0.995 * support_m)
        if low >= high:
            continue
        projected_centroids = path_centroids @ normal
        offsets = np.unique(np.clip(
            np.r_[float(seed_vertices.mean(axis=0) @ normal),
                  np.median(projected_centroids), projected_centroids],
            low, high,
        ))
        projected_vertices = path_vertices @ normal
        for offset_m in offsets:
            hits = (projected_vertices.min(axis=1) < offset_m) & (
                projected_vertices.max(axis=1) > offset_m
            )
            score = (
                int(np.count_nonzero(hits)),
                -float(np.mean(np.abs(projected_centroids - offset_m))),
            )
            if best is None or score > best[0]:
                best = (score, along, normal, float(offset_m))
    if best is None or best[0][0] < 1:
        raise ValueError("no vertical section intersects the saved failure path")
    _, along, normal, offset_m = best
    if along @ BASE_MAJOR < 0.0:
        along, normal, offset_m = -along, -normal, -offset_m
    return along, normal, offset_m


def _rotated_slice_polygons(
    vertices: np.ndarray, cells: np.ndarray,
    along: np.ndarray, normal: np.ndarray, offset_m: float,
) -> tuple[list[np.ndarray], np.ndarray]:
    """Intersect saved tetrahedra after rotating into the common section basis."""
    transformed = vertices.copy()
    along_m = vertices @ along
    across_m = vertices @ normal - offset_m
    transformed[:, :2] = (
        along_m[:, None] * BASE_MAJOR[:2]
        + across_m[:, None] * BASE_MINOR[:2]
    )
    return previous._slice_polygons(transformed, cells, 0.0)


def _outline_rotated_cavity(
    ax: plt.Axes, along: np.ndarray, normal: np.ndarray, offset_m: float,
) -> None:
    """Draw the source ellipsoid's exact section at the selected vertical plane."""
    distance_km = np.linspace(-6.0, 6.0, 600)
    horizontal_m = (
        distance_km[:, None] * 1000.0 * along[None, :]
        + offset_m * normal[None, :]
    )
    radius_sq = 1.0 - (horizontal_m @ BASE_MAJOR / 3000.0) ** 2 - (
        horizontal_m @ BASE_MINOR / 1500.0
    ) ** 2
    inside = radius_sq >= 0.0
    if not np.any(inside):
        raise ValueError("chosen section misses the ideal ellipsoid")
    distance_km = distance_km[inside]
    radius_km = 0.5 * np.sqrt(radius_sq[inside])
    top, bottom = 1.6 - radius_km, 1.6 + radius_km
    ax.fill_between(distance_km, top, bottom, color="white", zorder=8)
    ax.plot(distance_km, top, color="0.2", linewidth=0.75, zorder=9)
    ax.plot(distance_km, bottom, color="0.2", linewidth=0.75, zorder=9)


def _draw_section(
    ax: plt.Axes,
    vertices: np.ndarray,
    cells: np.ndarray,
    stress: np.ndarray,
    state: dict,
    cycle: str,
    role: str,
) -> dict:
    """Color a saved-mesh section and expose the joint path when present."""
    tensor = stress_voigt_to_tensor_pa(stress)
    tension = np.linalg.eigvalsh(tensor)[:, -1] > 0.0
    shear = (
        mohr_coulomb_yield_pa(
            tensor, cohesion_pa=1.0e6, friction_angle_deg=25.0, pore_pressure_pa=0.0
        )
        >= 0.0
    )
    analysis = analyze_stress_history(
        vertices,
        cells,
        stress[np.newaxis],
        np.asarray([0.0]),
        cohesion_pa=1.0e6,
        friction_angle_deg=25.0,
        pore_pressure_pa=0.0,
    )["records"][0]
    joint = bool(
        analysis["cavity_to_surface_shear_path_found"]
        and analysis["maximum_cavity_principal_stress_pa"] > 0.0
    )
    if "first_joint_state" in state and joint != state["first_joint_state"]:
        raise ValueError("saved Maxwell failure flag differs from selected PyLith state")
    path_indices = np.asarray(
        analysis["cavity_to_surface_path_cell_indices"], dtype=np.int64
    )
    if MESH_M == 150 and joint:
        along_axis, plane_normal, plane_offset_m = _path_section(
            vertices, cells, path_indices
        )
        polygons, indices = _rotated_slice_polygons(
            vertices, cells, along_axis, plane_normal, plane_offset_m
        )
    else:
        along_axis, plane_normal, plane_offset_m = BASE_MAJOR, BASE_MINOR, 0.0
        polygons, indices = previous._slice_polygons(vertices, cells, 0.0)
    ax.add_collection(
        PolyCollection(
            polygons, facecolors="#f5f5f5", edgecolors="#dddddd", linewidths=0.15, zorder=1
        )
    )
    ax.add_collection(
        PolyCollection(
            [poly for poly, index in zip(polygons, indices, strict=True) if shear[index]],
            facecolors="#d48647",
            edgecolors="none",
            zorder=2,
        )
    )
    ax.add_collection(
        PolyCollection(
            [poly for poly, index in zip(polygons, indices, strict=True) if tension[index]],
            facecolors="#427bb4",
            edgecolors="none",
            zorder=3,
        )
    )
    cut_path_cells = set(map(int, path_indices)) & set(map(int, indices)) if joint else set()
    if MESH_M == 150 and cut_path_cells:
        ax.add_collection(
            PolyCollection(
                [poly for poly, index in zip(polygons, indices, strict=True)
                 if int(index) in cut_path_cells],
                facecolors="none", edgecolors="#893c79", linewidths=0.9, zorder=7,
            )
        )
    if MESH_M == 150 and joint:
        _outline_rotated_cavity(ax, along_axis, plane_normal, plane_offset_m)
    else:
        previous._outline_cavity(ax, 0.0)
    if joint:
        centroids = vertices[cells[path_indices]].mean(axis=1)
        along = centroids @ along_axis / 1000.0
        ax.plot(
            along,
            -centroids[:, 2] / 1000.0,
            color="#893c79",
            linestyle="--",
            marker="o",
            markersize=2.5,
            linewidth=1.0,
            zorder=10,
        )
    tensile_cell = state["first_tensile_cell_index"]
    tensile_arrow = None
    if analysis["maximum_cavity_principal_stress_pa"] > 0.0 and tensile_cell is not None:
        centroid = vertices[cells[tensile_cell]].mean(axis=0)
        along_km = float(centroid @ along_axis / 1000.0)
        depth_km = float(-centroid[2] / 1000.0)
        off_plane_km = float((centroid @ plane_normal - plane_offset_m) / 1000.0)
        ax.annotate(
            "",
            xy=(along_km, depth_km),
            xytext=(along_km + (0.8 if along_km < 0.0 else -0.8), depth_km + 0.5),
            arrowprops={"arrowstyle": "->", "color": "#252525", "lw": 1.0},
            zorder=12,
        )
        tensile_arrow = {
            "cavity_cell_index": tensile_cell,
            "first_tensile_time_utc": state["first_tensile_time_utc"],
            "along_axis_km": along_km,
            "depth_km": depth_km,
            "off_section_km": off_plane_km,
        }
    ax.set_xlim(-6.0, 6.0)
    ax.set_ylim(4.0, 0.0)
    ax.set_ylabel("Depth (km)", fontsize=8)
    negative_pressure_joint = joint and state["pressure_mpa"] < 0.0
    state_label = "joint" if joint else "no joint"
    if negative_pressure_joint:
        state_label = "joint at negative ΔP"
    gap_state = (
        cycle == "1998–2011" and role == "first" and joint
        and "1998-08-04" <= state["time_utc"][:10] < "2000-07-06"
    )
    if gap_state:
        state_label += "\n1998–2000 BPR gap"
    ax.set_title(
        f"{state['time_utc'][:10]}  ΔP={state['pressure_mpa']:.2f} MPa\n{state_label}",
        loc="left",
        fontsize=7,
    )
    lead_days = None
    if role == "first" and joint and cycle in HISTORICAL_ERUPTIONS:
        lead_days = (
            HISTORICAL_ERUPTIONS[cycle] - datetime.fromisoformat(state["time_utc"])
        ).total_seconds() / 86400.0
        if lead_days < 0.0:
            raise ValueError("first sampled joint crossing follows the eruption")
        ax.text(
            0.97, 0.06, f"{lead_days:.0f} days early",
            transform=ax.transAxes, ha="right", va="bottom", fontsize=7,
            color="#4b2c4a",
        )
    ax.tick_params(labelsize=7)
    return {
        **state,
        "joint_failure_at_displayed_state": joint,
        "whole_mesh_shear_yield_cells": int(np.count_nonzero(shear)),
        "whole_mesh_tensile_cells": int(np.count_nonzero(tension)),
        "section_shear_yield_cells": int(np.count_nonzero(shear[indices])),
        "section_tensile_cells": int(np.count_nonzero(tension[indices])),
        "connected_path_cell_indices": list(
            map(int, analysis["cavity_to_surface_path_cell_indices"])
        ),
        "section_plane_offset_m": plane_offset_m,
        "section_azimuth_deg_clockwise_from_north": float(
            np.degrees(np.arctan2(along_axis[0], along_axis[1])) % 360.0
        ),
        "section_path_cells_intersected": len(cut_path_cells),
        "first_joint_within_1998_2000_observation_gap": gap_state,
        "joint_under_negative_pressure_change": negative_pressure_joint,
        "retrospective_lead_days_before_observed_eruption": lead_days,
        "first_tensile_arrow": tensile_arrow,
        "cavity_tensile_failure": analysis["maximum_cavity_principal_stress_pa"] > 0.0,
        "maximum_cavity_principal_stress_pa": analysis["maximum_cavity_principal_stress_pa"],
        "held_pressure_to_event_days": state.get("held_pressure_to_event_days"),
    }


def main() -> None:
    """Write five model rows and three observation periods from PyLith."""
    global HISTORICAL, HISTORICAL_ELASTIC, CURRENT, POST, TECTONIC
    global BASIS, REFERENCE, OUTPUT, SUMMARY, MESH_M, FINE_ROOT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mesh-m", type=int, choices=(400, 150), default=400)
    parser.add_argument("--fine-root", type=Path)
    args = parser.parse_args()
    MESH_M = args.mesh_m
    if MESH_M == 150:
        if args.fine_root is None:
            parser.error("--fine-root is required for the 150 m sections")
        FINE_ROOT = args.fine_root.resolve()
        HISTORICAL = FINE_ROOT / "source_value_bpr_failure_1998_2011_150m"
        HISTORICAL_ELASTIC = FINE_ROOT / "elastic_bpr_failure_1998_2011_150m"
        CURRENT = FINE_ROOT / "source_value_bpr_failure_2011_2015_150m"
        POST = FINE_ROOT / "source_value_ooi_failure_2015_present_150m"
        TECTONIC = FINE_ROOT
        BASIS = ROOT / "data/processed/refined_elastic_basis_150m"
        REFERENCE = BASIS / "fixed-base-equilibrium-material.h5"
        OUTPUT = ROOT / "figures/report_figure5_failure"
        SUMMARY = ROOT / "data/processed/report_figure5_failure_summary.json"
    figure, axes = plt.subplots(
        5,
        5,
        figsize=(14.0, 8.5),
        sharex=True,
        sharey=True,
        layout="constrained",
    )
    records = {}
    baseline_mesh = None
    columns = (
        ("1998–2011", "first"),
        ("1998–2011", "event"),
        ("2011–2015", "first"),
        ("2011–2015", "event"),
        ("post-2015", "post"),
    )
    headers = (
        "1998–2011: first joint", "Observed: 6 Apr 2011",
        "2011–2015: first joint", "Observed: 24 Apr 2015",
        "Post-2015: first joint or latest",
    )
    for row, (case, label) in enumerate(CASES):
        records[case] = {}
        for column, (cycle, role) in enumerate(columns):
            ax = axes[row, column]
            ax.set_facecolor(
                "#f5f4f1" if column < 2 else "#eff5f8" if column < 4 else "#eff5ef"
            )
            result = (
                _elastic_state(cycle, role)
                if case == "elastic"
                else _maxwell_state(cycle, case, role)
            )
            if result is None:
                ax.text(
                    0.5, 0.5, "No joint failure\nthrough observed eruption",
                    transform=ax.transAxes, ha="center", va="center", fontsize=8,
                )
                ax.set_xlim(-6.0, 6.0)
                ax.set_ylim(4.0, 0.0)
                record = {"no_sampled_joint_failure": True}
            else:
                vertices, cells, stress, state = result
                if baseline_mesh is None:
                    baseline_mesh = (vertices, cells)
                else:
                    match_tetrahedral_cells(
                        baseline_mesh[0], baseline_mesh[1], vertices, cells
                    )
                record = _draw_section(ax, vertices, cells, stress, state, cycle, role)
            records[case][f"{cycle}:{role}"] = record
            if column == 0:
                ax.set_ylabel(f"{label}\nDepth (km)", fontsize=8)
            if row == 0:
                ax.text(
                    0.5, 1.38, headers[column], ha="center", va="bottom",
                    transform=ax.transAxes, fontsize=8.5, fontweight="bold",
                )
    for ax in axes[-1]:
        ax.set_xlabel(
            "Section distance (km)" if MESH_M == 150 else "N30°W distance (km)",
            fontsize=7,
        )
    legend_handles = [
            Patch(facecolor="#d48647", label="Mohr–Coulomb yield"),
            Patch(facecolor="#427bb4", label="Principal tension"),
            Line2D([0], [0], color="#893c79", linestyle="--", label="3D shear path"),
            Line2D([0], [0], color="#252525", marker=">", linestyle="None",
                   label="First cavity tensile cell (projected)"),
    ]
    if MESH_M == 150:
        legend_handles.append(
            Patch(facecolor="none", edgecolor="#893c79", label="Path cells in slice")
        )
    figure.legend(
        handles=legend_handles,
        frameon=False,
        fontsize=8,
        loc="outside lower center",
        ncol=len(legend_handles),
    )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(OUTPUT.with_suffix(".pdf"))
    figure.savefig(OUTPUT.with_suffix(".png"), dpi=200)
    plt.close(figure)
    summary = {
        "status": "conditional_five_case_three_period_PyLith_failure_sections",
        "paper_output_data_used": False,
        "mesh_target_m": MESH_M,
        "mesh_tetrahedra": len(baseline_mesh[1]),
        "gravity_reference_sha256": file_sha256(REFERENCE),
        "section": (
            "failure-state vertical plane selected to intersect the most saved 3D "
            "path cells; central N30W plane for other states"
            if MESH_M == 150 else "common center plane along N30W reservoir axis"
        ),
        "path_display": (
            "three-dimensional connected path projected onto a rotated section "
            "that intersects the most path cells at joint failure; central section "
            "otherwise"
            if MESH_M == 150 else
            "three-dimensional connected path projected onto center section"
        ),
        "arrow_display": "first sampled tensile cavity cell projected onto displayed section",
        "cavity_tensile_rule": "one cavity-adjacent element with positive principal stress",
        "tensile_strength_pa_assumption": 0.0,
        "cohesion_pa": 1.0e6,
        "friction_angle_deg": 25.0,
        "pore_pressure_pa_assumption": 0.0,
        "cases": records,
    }
    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUTPUT.with_suffix('.pdf')}")


if __name__ == "__main__":
    main()
