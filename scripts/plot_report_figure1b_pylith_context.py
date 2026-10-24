"""Relate observed Axial bathymetry to the saved three-dimensional PyLith mesh."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from itertools import combinations
from pathlib import Path

import h5py
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import plot_figure1_map as mapdata
from matplotlib import cm, colors
from matplotlib.colors import LightSource
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from scipy.interpolate import RegularGridInterpolator

from axialstress.paper_bpr import file_sha256

ROOT = Path(__file__).resolve().parents[1]
BATHYMETRY = ROOT / "data" / "raw" / "figure1" / "gmrt" / "axial_gmrt_high_50km.tif"
BASIS = ROOT / "data" / "processed" / "refined_elastic_basis_150m"
MESH_OUTPUT = BASIS / "fixed-base-equilibrium-material.h5"
OUTPUT = ROOT / "figures" / "report_figure1b_pylith_context"
SUMMARY = ROOT / "data" / "processed" / "report_figure1b_pylith_context_summary.json"
WINDOW_HALF_WIDTH_KM = 8.0
WINDOW_DEPTH_KM = 3.5
BATHY_DISPLAY_LIFT_KM = 1.1


def _cavity_faces(vertices_m: np.ndarray, cells: np.ndarray) -> np.ndarray:
    """Return triangular cavity-boundary faces from saved PyLith tetrahedra."""
    counts = Counter(
        tuple(sorted(face))
        for cell in cells
        for face in combinations(map(int, cell), 3)
    )
    boundary = np.asarray([face for face, count in counts.items() if count == 1])
    coordinates = vertices_m[boundary]
    minimum = vertices_m.min(axis=0)
    maximum = vertices_m.max(axis=0)
    outer = np.zeros(len(boundary), dtype=bool)
    for axis in range(3):
        for value in (minimum[axis], maximum[axis]):
            outer |= np.all(np.abs(coordinates[:, :, axis] - value) < 1.0e-6, axis=1)
    return boundary[~outer]


def _load_mesh(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, object]]:
    """Read and verify the actual 150 m gravity-equilibrium PyLith mesh."""
    basis_path = BASIS / "basis_summary.json"
    basis = json.loads(basis_path.read_text(encoding="utf-8"))
    if (
        basis.get("paper_output_data_used") is not False
        or basis["output_sha256"][path.name] != file_sha256(path)
    ):
        raise ValueError("saved PyLith mesh differs from its model provenance")
    with h5py.File(path, "r") as model:
        vertices_m = np.asarray(model["geometry/vertices"], dtype=float)
        cells = np.asarray(model["viz/topology/cells"], dtype=np.int64)
    if (
        len(cells) != basis["mesh_tetrahedra"]
        or not np.allclose(vertices_m.min(axis=0), (-25_000, -25_000, -10_000))
        or not np.allclose(vertices_m.max(axis=0), (25_000, 25_000, 0))
    ):
        raise ValueError("PyLith mesh bounds or cell count differ from the recorded model")
    cavity_faces = _cavity_faces(vertices_m, cells)
    if len(cavity_faces) != basis["cavity_faces"]:
        raise ValueError("meshed cavity surface differs from the basis summary")
    return vertices_m, cells, cavity_faces, basis


def _local_bathymetry(
    path: Path,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, float, dict[str, object]]:
    """Sample GMRT depth above a display origin at the archived Center BPR."""
    bathy_m, east_km, north_km = mapdata.load_geotiff(path)
    center_lat, center_lon = mapdata.CENTER_2011_2013_BPR_LAT_LON_DEG
    center_east_km, center_north_km = mapdata.geographic_to_local_km(
        center_lon, center_lat
    )
    values_m = np.ma.filled(bathy_m, np.nan)
    interpolator = RegularGridInterpolator(
        (north_km[::-1], east_km),
        values_m[::-1],
        bounds_error=True,
    )
    axis_km = np.linspace(-WINDOW_HALF_WIDTH_KM, WINDOW_HALF_WIDTH_KM, 81)
    x_km, y_km = np.meshgrid(axis_km, axis_km)
    query = np.stack((y_km + center_north_km, x_km + center_east_km), axis=-1)
    sampled_m = interpolator(query)
    center_depth_m = float(interpolator((center_north_km, center_east_km)))
    if not np.all(np.isfinite(sampled_m)) or center_depth_m >= 0.0:
        raise ValueError("GMRT summit bathymetry is missing or has unexpected sign")
    metadata = {
        "gmrt_tif_sha256": file_sha256(path),
        "display_origin_latitude_longitude_deg": [center_lat, center_lon],
        "gmrt_depth_at_display_origin_m_below_sea_level": -center_depth_m,
        "window_gmrt_depth_range_m_below_sea_level": [
            float(-np.max(sampled_m)),
            float(-np.min(sampled_m)),
        ],
    }
    return x_km, y_km, sampled_m, center_depth_m, metadata


def _draw_crop_box(ax: plt.Axes) -> None:
    """Draw a summit window within the larger PyLith domain."""
    edge = WINDOW_HALF_WIDTH_KM
    for z_km in (0.0, -WINDOW_DEPTH_KM):
        for x1, y1, x2, y2 in (
            (-edge, -edge, edge, -edge),
            (edge, -edge, edge, edge),
            (edge, edge, -edge, edge),
            (-edge, edge, -edge, -edge),
        ):
            ax.plot((x1, x2), (y1, y2), (z_km, z_km), color="0.4", linewidth=0.7)
    for x_km in (-edge, edge):
        for y_km in (-edge, edge):
            ax.plot(
                (x_km, x_km),
                (y_km, y_km),
                (-WINDOW_DEPTH_KM, 0.0),
                color="0.5",
                linewidth=0.65,
            )


def main() -> None:
    """Save the observed bathymetry and actual PyLith cavity in one view."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bathymetry", type=Path, default=BATHYMETRY)
    parser.add_argument("--mesh-output", type=Path, default=MESH_OUTPUT)
    parser.add_argument("--output-stem", type=Path, default=OUTPUT)
    parser.add_argument("--summary", type=Path, default=SUMMARY)
    args = parser.parse_args()
    vertices_m, cells, cavity_faces, basis = _load_mesh(args.mesh_output.resolve())
    x_km, y_km, bathy_m, center_depth_m, bathy_metadata = _local_bathymetry(
        args.bathymetry.resolve()
    )
    bathy_z_km = (bathy_m - center_depth_m) / 1000.0 + BATHY_DISPLAY_LIFT_KM
    if np.min(bathy_z_km) <= 0.0:
        raise ValueError("display lift does not separate bathymetry from the flat model top")
    visible_bathy = bathy_z_km.copy()
    quarter_cutaway = (x_km >= 0.0) & (y_km >= 0.0)
    visible_bathy[quarter_cutaway] = np.nan

    figure = plt.figure(figsize=(6.4, 5.0))
    ax = figure.add_axes((0.02, 0.16, 0.78, 0.73), projection="3d")
    normalization = colors.Normalize(vmin=-2.4, vmax=-1.4)
    bathy_colors = cm.turbo(normalization(bathy_m / 1000.0))
    ax.plot_surface(
        x_km,
        y_km,
        visible_bathy,
        facecolors=bathy_colors,
        shade=True,
        lightsource=LightSource(azdeg=310, altdeg=55),
        linewidth=0,
        antialiased=False,
        alpha=0.94,
        rstride=1,
        cstride=1,
    )
    ax.contour(
        x_km,
        y_km,
        visible_bathy,
        levels=[
            (elevation_m - center_depth_m) / 1000.0 + BATHY_DISPLAY_LIFT_KM
            for elevation_m in (-2100, -1900, -1700, -1500)
        ],
        colors="0.22",
        linewidths=0.45,
        alpha=0.55,
    )
    center = x_km.shape[0] // 2
    ax.plot(
        np.zeros(len(x_km[center:, center])),
        y_km[center:, center],
        bathy_z_km[center:, center],
        color="0.2",
        linewidth=0.8,
    )
    ax.plot(
        x_km[center, center:],
        np.zeros(len(y_km[center, center:])),
        bathy_z_km[center, center:],
        color="0.2",
        linewidth=0.8,
    )
    ax.add_collection3d(
        Poly3DCollection(
            vertices_m[cavity_faces] / 1000.0,
            facecolor="#d78048",
            edgecolor="#764927",
            linewidth=0.2,
            alpha=0.95,
        )
    )
    top = np.asarray(
        [
            [-WINDOW_HALF_WIDTH_KM, -WINDOW_HALF_WIDTH_KM, 0.0],
            [WINDOW_HALF_WIDTH_KM, -WINDOW_HALF_WIDTH_KM, 0.0],
            [WINDOW_HALF_WIDTH_KM, WINDOW_HALF_WIDTH_KM, 0.0],
            [-WINDOW_HALF_WIDTH_KM, WINDOW_HALF_WIDTH_KM, 0.0],
        ]
    )
    ax.add_collection3d(
        Poly3DCollection([top], facecolor="#b4c5ce", alpha=0.09, edgecolor="none")
    )
    _draw_crop_box(ax)
    ax.plot((0, 0), (0, 0), (0.0, BATHY_DISPLAY_LIFT_KM), color="white", linewidth=1.3)
    ax.scatter(0, 0, BATHY_DISPLAY_LIFT_KM, color="white", edgecolors="black", s=28)
    ax.set_xlim(-WINDOW_HALF_WIDTH_KM, WINDOW_HALF_WIDTH_KM)
    ax.set_ylim(-WINDOW_HALF_WIDTH_KM, WINDOW_HALF_WIDTH_KM)
    ax.set_zlim(-WINDOW_DEPTH_KM, 1.4)
    ax.set_box_aspect((1, 1, 0.67))
    ax.view_init(elev=48, azim=35)
    ax.set_xlabel("East (km)", labelpad=4)
    ax.set_ylabel("North (km)", labelpad=4)
    ax.set_zlabel("z (km)", labelpad=4)
    ax.tick_params(labelsize=7, pad=1)
    figure.text(0.04, 0.96, "b  Observed summit relief and PyLith cavity", fontsize=11)
    figure.text(
        0.05,
        0.07,
        "GMRT relief raised 1.1 km for display; PyLith top is flat at z = 0.\n"
        "Northeast quarter removed for display; remaining caldera relief is observed.\n"
        "White dot: archived Center BPR at assumed model origin.",
        fontsize=7,
        color="0.25",
    )
    scalar = cm.ScalarMappable(norm=normalization, cmap=cm.turbo)
    scalar.set_array([])
    colorbar_ax = figure.add_axes((0.87, 0.28, 0.025, 0.42))
    colorbar = figure.colorbar(scalar, cax=colorbar_ax)
    colorbar.set_label("GMRT elevation (km)", fontsize=8)
    colorbar.ax.tick_params(labelsize=7)
    output_stem = args.output_stem.resolve()
    output_stem.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_stem.with_suffix(".pdf"))
    figure.savefig(output_stem.with_suffix(".png"), dpi=200)
    plt.close(figure)
    record = {
        "paper_output_data_used": False,
        "observation_input": bathy_metadata,
        "pylith_mesh_output_sha256": file_sha256(args.mesh_output.resolve()),
        "pylith_basis_summary_sha256": file_sha256(BASIS / "basis_summary.json"),
        "mesh_tetrahedra": len(cells),
        "meshed_cavity_triangles": len(cavity_faces),
        "mesh_domain_km": [50.0, 50.0, 10.0],
        "display_window_km": [
            2 * WINDOW_HALF_WIDTH_KM,
            2 * WINDOW_HALF_WIDTH_KM,
            WINDOW_DEPTH_KM,
        ],
        "display_origin_assumption": "model origin placed at 2011–2013 Center BPR coordinate",
        "observed_bathymetry_not_model_boundary": True,
        "bathy_vertical_display_lift_km": BATHY_DISPLAY_LIFT_KM,
        "bathy_display_z_range_km": [float(np.min(bathy_z_km)), float(np.max(bathy_z_km))],
        "vertical_display_exaggeration": 0.67 / (
            (WINDOW_DEPTH_KM + 1.4) / (2 * WINDOW_HALF_WIDTH_KM)
        ),
        "bathy_cutaway": "northeast quarter (east >= 0 km, north >= 0 km)",
        "model_top_is_flat_z_m": 0.0,
        "basis_cavity_volume_m3": basis["cavity_volume_m3"],
    }
    summary_path = args.summary.resolve()
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {output_stem.with_suffix('.pdf')}")


if __name__ == "__main__":
    main()
