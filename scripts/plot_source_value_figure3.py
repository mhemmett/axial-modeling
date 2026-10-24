"""Plot PyLith input-property sections in the layout of Cabaniss Figure 3."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LogNorm, Normalize
from scipy.spatial import cKDTree

from axialstress.paper_bpr import file_sha256
from axialstress.thermal import (
    evaluate_eq16_youngs_modulus_pa,
    hydrothermal_conductivity_w_mk,
    temperature_dependent_viscosity_pa_s,
)

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "processed" / "source_value_bpr_failure_2011_2015"
OUTPUT = ROOT / "figures" / "source_value_figure3_properties"
CASE_NAMES = (
    ("elastic", "Elastic baseline"),
    ("constant_maxwell", "Non-TD Maxwell"),
    ("thermal_maxwell", "Thermal Maxwell"),
    ("hydrothermal_maxwell", "Hydrothermal Maxwell"),
)


def _section_grid() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Return an N30W major-axis section, in kilometers and mesh meters."""
    distance_km = np.linspace(0.0, 10.0, 221)
    depth_km = np.linspace(0.0, 4.0, 101)
    distance, depth = np.meshgrid(distance_km, depth_km)
    distance_m = distance * 1000.0
    points_m = np.column_stack(
        (
            -0.5 * distance_m.ravel(),
            np.sqrt(3.0) / 2.0 * distance_m.ravel(),
            -1000.0 * depth.ravel(),
        )
    )
    cavity = (distance / 3.0) ** 2 + ((depth - 1.6) / 0.5) ** 2 < 1.0
    return distance, depth, points_m, cavity


def _thermal_fields(
    archive_path: Path, points_m: np.ndarray, shape: tuple[int, int], cavity: np.ndarray, *,
    hydrothermal: bool,
) -> dict[str, np.ndarray]:
    """Sample nodal temperature and assigned cell properties in tetrahedra."""
    with np.load(archive_path, allow_pickle=False) as archive:
        vertices = np.asarray(archive["vertices_m"], dtype=float)
        cells = np.asarray(archive["tetrahedra"], dtype=np.int64)
        nodal_temperature_c = np.asarray(archive["temperature_c"], dtype=float)
    cell_temperature_c = nodal_temperature_c[cells].mean(axis=1)
    centroids = vertices[cells].mean(axis=1)
    nearest = cKDTree(centroids)
    indices = np.full(len(points_m), -1, dtype=np.int64)
    temperature_c = np.full(len(points_m), np.nan)
    for start in range(0, len(points_m), 1024):
        stop = min(start + 1024, len(points_m))
        query = points_m[start:stop]
        candidate = np.asarray(nearest.query(query, k=64)[1], dtype=np.int64)
        corners = vertices[cells[candidate]]
        origin = corners[:, :, 0, :]
        basis = np.stack(
            (corners[:, :, 1, :] - origin,
             corners[:, :, 2, :] - origin,
             corners[:, :, 3, :] - origin),
            axis=-1,
        )
        barycentric = np.linalg.solve(
            basis, (query[:, None, :] - origin)[..., None]
        )[..., 0]
        inside = np.all(barycentric >= -1.0e-7, axis=-1) & (
            np.sum(barycentric, axis=-1) <= 1.0 + 1.0e-7
        )
        found = np.any(inside, axis=1)
        chosen = np.argmax(inside, axis=1)
        local = np.arange(len(query))
        selected_cells = candidate[local, chosen]
        indices[start:stop][found] = selected_cells[found]
        weights = barycentric[local, chosen]
        nodal = nodal_temperature_c[cells[selected_cells]]
        temperature_c[start:stop][found] = (
            nodal[:, 0] * (1.0 - np.sum(weights, axis=1))
            + np.sum(nodal[:, 1:] * weights, axis=1)
        )[found]
    outside_domain = (indices < 0) & ~cavity.ravel()
    if np.any(outside_domain):
        raise ValueError(
            f"{np.count_nonzero(outside_domain)} displayed section points have no tetrahedron"
        )
    indices[indices < 0] = nearest.query(points_m[indices < 0])[1]
    temperature_c[~np.isfinite(temperature_c)] = cell_temperature_c[
        indices[~np.isfinite(temperature_c)]
    ]
    temperature_c = temperature_c.reshape(shape)
    cell_temperature_on_section_c = cell_temperature_c[indices].reshape(shape)
    depth_m = -points_m[:, 2].reshape(shape)
    conductivity = (
        hydrothermal_conductivity_w_mk(temperature_c, depth_m)
        if hydrothermal
        else np.full(shape, 3.0)
    )
    return {
        "modulus": evaluate_eq16_youngs_modulus_pa(cell_temperature_on_section_c) / 1.0e9,
        "viscosity": temperature_dependent_viscosity_pa_s(cell_temperature_on_section_c),
        "temperature": temperature_c,
        "conductivity": conductivity,
    }


def _outline_cavity(ax: plt.Axes) -> None:
    """Draw the paper-specified 3 km by 0.5 km cavity half-section."""
    distance_km = np.linspace(0.0, 3.0, 250)
    radius = np.sqrt(np.maximum(0.0, 1.0 - (distance_km / 3.0) ** 2))
    top = 1.6 - 0.5 * radius
    bottom = 1.6 + 0.5 * radius
    ax.fill_between(distance_km, top, bottom, color="white", zorder=5)
    ax.plot(distance_km, top, color="black", linewidth=0.8, zorder=6)
    ax.plot(distance_km, bottom, color="black", linewidth=0.8, zorder=6)


def main() -> None:
    """Write four-rheology property slices from source inputs and local solves."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=INPUT)
    parser.add_argument("--output-stem", type=Path, default=OUTPUT)
    parser.add_argument("--mesh-m", type=int, choices=(400, 150), default=400)
    args = parser.parse_args()
    args.input_dir = args.input_dir.resolve()
    args.output_stem = args.output_stem.resolve()
    source = json.loads((args.input_dir / "summary.json").read_text(encoding="utf-8"))
    if source.get("status") != "conditional_bpr_failure_reconstruction_temporally_unresolved":
        raise ValueError("source-value BPR summary has an unexpected status")
    basis_mesh = (
        ROOT / f"data/processed/refined_elastic_basis_{args.mesh_m}m/axial_ellipsoid.msh"
    )
    if (
        source.get("paper_output_data_used") is not False
        or source["mesh_sha256"] != file_sha256(basis_mesh)
    ):
        raise ValueError("Figure 3 properties do not match the selected PyLith mesh")
    if "constant_maxwell" not in source["cases"]:
        raise ValueError("Figure 3 analogue requires the non-TD Maxwell case")
    distance, depth, points_m, cavity = _section_grid()
    shape = distance.shape
    constant = source["cases"]["constant_maxwell"]
    fields = {
        "elastic": {
            "modulus": np.full(shape, 50.0),
            "viscosity": None,
            "temperature": None,
            "conductivity": None,
        },
        "constant_maxwell": {
            "modulus": np.full(shape, constant["youngs_modulus_range_pa"][0] / 1.0e9),
            "viscosity": np.full(shape, constant["viscosity_range_pa_s"][0]),
            "temperature": None,
            "conductivity": None,
        },
    }
    for case, hydrothermal in (("thermal_maxwell", False), ("hydrothermal_maxwell", True)):
        archive = args.input_dir / f"{case}_temperature.npz"
        expected_hash = source["cases"][case]["property_notes"]["temperature_archive_sha256"]
        if file_sha256(archive) != expected_hash:
            raise ValueError(f"temperature archive changed for {case}")
        fields[case] = _thermal_fields(
            archive, points_m, shape, cavity, hydrothermal=hydrothermal
        )

    conductivity_max = float(
        np.max(fields["hydrothermal_maxwell"]["conductivity"])
    )
    rows = (
        ("modulus", "Young's modulus (GPa)", "turbo", Normalize(20.0, 60.0)),
        ("viscosity", "Viscosity (Pa s)", "turbo_r", LogNorm(1.0e13, 1.0e31)),
        ("temperature", "Temperature (°C)", "inferno", Normalize(0.0, 1200.0)),
        (
            "conductivity", "Conductivity (W m$^{-1}$ K$^{-1}$)",
            "turbo", Normalize(3.0, conductivity_max),
        ),
    )
    fig, axes = plt.subplots(4, 4, figsize=(11.2, 7.2), sharex=True, sharey=True)
    fig.subplots_adjust(left=0.16, right=0.88, bottom=0.10, top=0.88, hspace=0.10, wspace=0.08)
    for column, (case, title) in enumerate(CASE_NAMES):
        axes[0, column].set_title(title, fontsize=10)
        for row, (field, _, cmap, norm) in enumerate(rows):
            ax = axes[row, column]
            values = fields[case][field]
            if values is None:
                ax.set_facecolor("white")
                ax.text(0.62, 0.55, "N/A", ha="center", va="center", transform=ax.transAxes)
            else:
                masked = np.ma.array(values, mask=cavity)
                ax.pcolormesh(distance, depth, masked, shading="nearest", cmap=cmap, norm=norm)
                if field == "temperature":
                    ax.contour(
                        distance, depth, masked, levels=[600.0, 750.0],
                        colors="white", linewidths=0.65,
                    )
            _outline_cavity(ax)
            ax.set_xlim(0.0, 10.0)
            ax.set_ylim(4.0, 0.0)
            ax.set_aspect("equal")
            ax.tick_params(labelsize=7)
            if row == 3:
                ax.set_xlabel("Distance along N30°W (km)", fontsize=8)
            if column == 0:
                ax.set_ylabel("Depth (km)", fontsize=8)
    for row, (_, label, cmap, norm) in enumerate(rows):
        fig.text(
            0.035, 0.78 - row * 0.195,
            ("Young's modulus", "Viscosity", "Temperature", "Conductivity")[row],
            rotation=90, ha="center", va="center", fontsize=9, fontweight="bold",
        )
        cax = fig.add_axes((0.91, 0.70 - row * 0.20, 0.015, 0.16))
        colorbar = fig.colorbar(
            plt.cm.ScalarMappable(norm=norm, cmap=cmap), cax=cax
        )
        colorbar.set_label(label, fontsize=8)
        colorbar.ax.tick_params(labelsize=7)
    args.output_stem.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output_stem.with_suffix(".pdf"))
    fig.savefig(args.output_stem.with_suffix(".png"), dpi=200)
    plt.close(fig)
    print(f"wrote {args.output_stem.with_suffix('.pdf')}")


if __name__ == "__main__":
    main()
