"""Sweep diagnostic failure parameters over saved raw-BPR stress histories."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import h5py
import matplotlib
import numpy as np

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from axialstress.failure_threshold_sensitivity import analyze_failure_threshold_grid
from axialstress.topology import TetrahedralFaceGraph

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MATERIAL_ROOT = (
    ROOT / "pylith" / "step13_historical_generalized_maxwell_bpr" / "output"
)
DEFAULT_OUTPUT_JSON = (
    ROOT
    / "data"
    / "processed"
    / "axial_historical_bpr"
    / "failure_threshold_sensitivity"
    / "summary.json"
)
DEFAULT_FIGURE_STEM = ROOT / "figures" / "historical_failure_threshold_sensitivity"

COHESION_MPA = (1.0, 5.0, 10.0)
FRICTION_ANGLE_DEG = (15.0, 25.0, 35.0)
PORE_PRESSURE_MPA = (0.0, 10.0, 25.0)

WINDOWS = (
    ("1995_1996", "deployment-overlap"),
    ("1998", "eruption-window"),
    ("2002_2004", "deployment-overlap"),
    ("2003_2005", "deployment-overlap"),
    ("2005_2007", "deployment-overlap"),
    ("2007_2009", "deployment-overlap"),
    ("2011", "eruption-window"),
    ("2011_2013", "deployment-overlap"),
    ("2013_2015", "deployment-overlap"),
    ("2015_2017", "deployment-overlap"),
    ("2018_2020", "deployment-overlap"),
    ("2020_2022", "deployment-overlap"),
)


def _read_material_history(path: Path) -> tuple[np.ndarray, ...]:
    """Read mesh, stress, and time arrays from a completed PyLith output."""
    with h5py.File(path, "r") as material:
        required = (
            "geometry/vertices",
            "viz/topology/cells",
            "cell_fields/cauchy_stress",
            "time",
        )
        missing = [name for name in required if name not in material]
        if missing:
            raise ValueError(f"{path} is missing PyLith datasets: {missing}")
        vertices_m = np.asarray(material["geometry/vertices"], dtype=float)
        tetrahedra = np.asarray(material["viz/topology/cells"], dtype=np.int64)
        stress_history_pa = np.asarray(material["cell_fields/cauchy_stress"], dtype=float)
        time_s = np.asarray(material["time"], dtype=float).reshape(-1)
    return vertices_m, tetrahedra, stress_history_pa, time_s


def _comparison_result(
    name: str,
    comparison_type: str,
    material_path: Path,
    face_graph: TetrahedralFaceGraph | None,
    shared_mesh: tuple[np.ndarray, np.ndarray] | None,
) -> tuple[dict[str, Any], TetrahedralFaceGraph, tuple[np.ndarray, np.ndarray]]:
    """Analyze one window and verify its mesh matches the shared topology."""
    vertices_m, tetrahedra, stress_history_pa, time_s = _read_material_history(material_path)
    boundaries = (vertices_m, tetrahedra)
    if shared_mesh is not None and not all(
        np.array_equal(previous, current)
        for previous, current in zip(shared_mesh, boundaries, strict=True)
    ):
        raise ValueError(f"historical comparison {name} does not use the shared mesh")
    if face_graph is None:
        face_graph = TetrahedralFaceGraph(tetrahedra)
    elif face_graph.cell_count != len(tetrahedra):
        raise ValueError(f"mesh cell count differs in comparison {name}")

    parameter_results = analyze_failure_threshold_grid(
        vertices_m,
        tetrahedra,
        stress_history_pa,
        time_s,
        cohesion_pa_values=tuple(value * 1.0e6 for value in COHESION_MPA),
        friction_angle_deg_values=FRICTION_ANGLE_DEG,
        pore_pressure_pa_values=tuple(value * 1.0e6 for value in PORE_PRESSURE_MPA),
        face_graph=face_graph,
    )
    return (
        {
            "comparison": name,
            "comparison_type": comparison_type,
            "material_output": str(
                material_path.relative_to(ROOT)
                if material_path.is_relative_to(ROOT)
                else material_path
            ),
            "record_count": len(time_s),
            "start_time_s": float(time_s[0]),
            "end_time_s": float(time_s[-1]),
            "parameters": parameter_results,
        },
        face_graph,
        boundaries,
    )


def _plot_summary(summary: dict[str, Any], figure_stem: Path) -> tuple[Path, Path]:
    """Plot saved-record path fractions for each friction angle."""
    import matplotlib.colors as colors

    comparisons = summary["comparisons"]
    names = [entry["comparison"] for entry in comparisons]
    columns = [
        f"{cohesion:g}/{pore:g}"
        for cohesion in COHESION_MPA
        for pore in PORE_PRESSURE_MPA
    ]
    matrices = []
    for friction in FRICTION_ANGLE_DEG:
        matrix = np.full((len(comparisons), len(columns)), np.nan)
        for row, comparison in enumerate(comparisons):
            for result in comparison["parameters"]:
                if result["friction_angle_deg"] != friction:
                    continue
                column = (
                    COHESION_MPA.index(result["cohesion_pa"] / 1.0e6)
                    * len(PORE_PRESSURE_MPA)
                    + PORE_PRESSURE_MPA.index(result["pore_pressure_pa"] / 1.0e6)
                )
                matrix[row, column] = result["path_record_fraction"]
        matrices.append(matrix)

    figure_stem.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 3, figsize=(14, 7), sharey=True, constrained_layout=True)
    cmap = plt.get_cmap("viridis").copy()
    cmap.set_bad("#eeeeee")
    image = None
    for axis, friction, matrix in zip(axes, FRICTION_ANGLE_DEG, matrices, strict=True):
        image = axis.imshow(
            np.ma.masked_invalid(matrix),
            aspect="auto",
            interpolation="nearest",
            cmap=cmap,
            norm=colors.Normalize(vmin=0.0, vmax=1.0),
        )
        axis.set_title(rf"$\phi={friction:g}^\circ$")
        axis.set_xticks(np.arange(len(columns)), columns, rotation=55, ha="right")
        axis.set_xlabel("Cohesion / pore pressure (MPa)")
        axis.grid(False)
    axes[0].set_yticks(np.arange(len(names)), names)
    axes[0].set_ylabel("Raw-BPR comparison window")
    if image is not None:
        colorbar = fig.colorbar(image, ax=axes, shrink=0.82, pad=0.02)
        colorbar.set_label("Fraction of saved records with a connected shear path")
    fig.suptitle("Historical failure-threshold sensitivity")
    png_path = figure_stem.with_suffix(".png")
    pdf_path = figure_stem.with_suffix(".pdf")
    fig.savefig(png_path, dpi=180)
    fig.savefig(pdf_path)
    plt.close(fig)
    return png_path, pdf_path


def main() -> None:
    """Sweep diagnostic parameters over the 12 completed historical windows."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--material-root", type=Path, default=DEFAULT_MATERIAL_ROOT)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--figure-stem", type=Path, default=DEFAULT_FIGURE_STEM)
    args = parser.parse_args()
    args.material_root = args.material_root.resolve()
    args.output_json = args.output_json.resolve()
    args.figure_stem = args.figure_stem.resolve()

    comparisons = []
    face_graph = None
    shared_mesh = None
    for name, comparison_type in WINDOWS:
        material_path = args.material_root / name / "output" / "genmaxwell-material.h5"
        if not material_path.is_file():
            raise FileNotFoundError(
                f"missing historical PyLith output {material_path}; run the "
                "historical generalized Maxwell BPR checks first"
            )
        result, face_graph, mesh = _comparison_result(
            name, comparison_type, material_path, face_graph, shared_mesh
        )
        if shared_mesh is None:
            shared_mesh = mesh
        comparisons.append(result)
        print(
            f"{name}: {result['record_count']} saved stress records; "
            f"{len(result['parameters'])} parameter combinations"
        )

    summary = {
        "method": "diagnostic Mohr-Coulomb parameter sweep on saved raw-BPR stress histories",
        "observation_provenance": "original raw NCEI/MGDS BPR channels",
        "paper_publication_data_used": False,
        "mesh_tetrahedra": int(face_graph.cell_count) if face_graph else None,
        "mesh_is_converged": False,
        "parameter_grid": {
            "cohesion_mpa": list(COHESION_MPA),
            "friction_angle_deg": list(FRICTION_ANGLE_DEG),
            "pore_pressure_mpa": list(PORE_PRESSURE_MPA),
            "friction_interpretation": "tabulated angle applied directly as phi",
            "tensile_strength": (
                "not assigned; report maximum cavity tensile stress on saved "
                "records that also have a shear path"
            ),
            "parameter_status": (
                "diagnostic scenarios; only 1 MPa cohesion, 25 degree friction, "
                "and zero pore pressure match the current proxy; none are "
                "physically calibrated"
            ),
        },
        "comparison_labels": {
            "eruption-window": "1998 and 2011 benchmark windows",
            "deployment-overlap": (
                "other raw BPR deployment comparisons; not labeled as "
                "no-eruption controls"
            ),
        },
        "limitations": [
            (
                "Center-fitted pressure histories include the observed "
                "deformation over each full window and are retrospective"
            ),
            (
                "the synthetic generalized Maxwell branches and "
                "static-compliance pressure scale remain provisional"
            ),
            "the shared ellipsoid mesh is not converged",
            "raw BPR channels retain ocean variability and instrument drift",
            "path states are evaluated at saved PyLith records without time interpolation",
            "the diagnostic parameter grid is not a sourced or calibrated rock-strength range",
        ],
        "comparisons": comparisons,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    png_path, pdf_path = _plot_summary(summary, args.figure_stem)
    print(f"wrote {args.output_json}, {png_path}, and {pdf_path}")


if __name__ == "__main__":
    main()
