"""Plot Axial bathymetry, eruptive products, seismicity, and Vp proxies."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import subprocess
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from PIL import Image
from scipy.ndimage import gaussian_filter, label

ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = ROOT / "data" / "raw" / "figure1"
OUTPUT_STEM = ROOT / "figures" / "figure1_axial_geologic_map"
SUMMARY_PATH = ROOT / "data" / "processed" / "figure1_axial_geologic_map_summary.json"

ORIGIN_LATITUDE_DEG = 45.91792
ORIGIN_LONGITUDE_DEG = -129.99305
LOCAL_GRID_ROTATION_DEG = 12.8749
KM_PER_DEGREE = 111.195
MAP_LIMITS_KM = (-25.0, 25.0)
VP_SLICE_DEPTH_KM_BSL = 3.5
VP_THRESHOLD_KM_S = 5.0
VP_SMOOTH_SIGMA_GRID_CELLS = 2.0
VP_MIN_COMPONENT_CELLS = 200

FLOW_COLORS = {1998: "#e76f51", 2011: "#f4a261", 2015: "#2a9d8f"}
FLOW_LABELS = {1998: "1998 lava flow", 2011: "2011 lava flow", 2015: "2015 lava flow"}


def sha256_file(path: Path) -> str:
    """Return a file's SHA-256 checksum."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def one_file(directory: Path, pattern: str) -> Path:
    """Find exactly one source file matching a dataset-specific pattern."""
    matches = sorted(directory.rglob(pattern))
    if len(matches) != 1:
        raise FileNotFoundError(
            f"expected one {pattern!r} below {directory}, found {len(matches)}"
        )
    return matches[0]


def geographic_to_local_km(
    longitude_deg: np.ndarray | float, latitude_deg: np.ndarray | float
) -> tuple[np.ndarray, np.ndarray]:
    """Project nearby WGS84 coordinates into east and north kilometers."""
    east_km = (
        (np.asarray(longitude_deg) - ORIGIN_LONGITUDE_DEG)
        * KM_PER_DEGREE
        * np.cos(np.deg2rad(ORIGIN_LATITUDE_DEG))
    )
    north_km = (np.asarray(latitude_deg) - ORIGIN_LATITUDE_DEG) * KM_PER_DEGREE
    return east_km, north_km


def velocity_grid_to_local_km(
    x_km: np.ndarray | float, y_km: np.ndarray | float
) -> tuple[np.ndarray, np.ndarray]:
    """Rotate MGDS local grid coordinates into map east/north axes."""
    angle = np.deg2rad(LOCAL_GRID_ROTATION_DEG)
    east_km = x_km * np.cos(angle) + y_km * np.sin(angle)
    north_km = -x_km * np.sin(angle) + y_km * np.cos(angle)
    return east_km, north_km


def load_geotiff(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Read the GMRT float raster and its WGS84 pixel-center coordinates."""
    with Image.open(path) as image:
        values = np.asarray(image, dtype=np.float32)
        tags = image.tag_v2
        tiepoint = np.asarray(tags[33922], dtype=float)
        pixel_scale = np.asarray(tags[33550], dtype=float)
    if values.ndim != 2 or tiepoint.size < 6 or pixel_scale.size < 2:
        raise ValueError(f"unsupported GMRT GeoTIFF layout: {path}")

    longitude = tiepoint[3] + np.arange(values.shape[1]) * pixel_scale[0]
    latitude = tiepoint[4] - np.arange(values.shape[0]) * pixel_scale[1]
    east_km, _ = geographic_to_local_km(longitude, ORIGIN_LATITUDE_DEG)
    _, north_km = geographic_to_local_km(ORIGIN_LONGITUDE_DEG, latitude)
    return np.ma.masked_invalid(values), east_km, north_km


def read_table_groups(
    path: Path, *, group_column: str, longitude_column: str, latitude_column: str
) -> list[np.ndarray]:
    """Read tabular outline vertices and preserve their feature grouping."""
    groups: dict[str, list[tuple[float, float]]] = defaultdict(list)
    with gzip.open(path, "rt", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        for row in reader:
            groups[row[group_column]].append(
                (float(row[longitude_column]), float(row[latitude_column]))
            )
    return [np.asarray(groups[key], dtype=float) for key in sorted(groups, key=int)]


def read_1998_lava_polygons(path: Path) -> list[np.ndarray]:
    """Read the grouped ASCII coordinate records for the 1998 lava flow."""
    groups: dict[str, list[tuple[float, float]]] = defaultdict(list)
    current_id: str | None = None
    with gzip.open(path, "rt", encoding="utf-8-sig") as stream:
        for raw_line in stream:
            line = raw_line.strip()
            if not line:
                continue
            fields = [field.strip() for field in line.split(",")]
            if len(fields) == 1:
                current_id = None if line.upper() == "END" else fields[0]
            elif len(fields) == 3:
                current_id = fields[0]
                longitude, latitude = map(float, fields[1:])
                groups[current_id].append((longitude, latitude))
            elif len(fields) == 2 and current_id is not None:
                longitude, latitude = map(float, fields)
                groups[current_id].append((longitude, latitude))
    return [np.asarray(groups[key], dtype=float) for key in sorted(groups, key=int)]


def read_1998_fissures(path: Path) -> list[np.ndarray]:
    """Read the ID-delimited 1998 fissure polylines."""
    groups: dict[str, list[tuple[float, float]]] = defaultdict(list)
    current_id: str | None = None
    with gzip.open(path, "rt", encoding="utf-8-sig") as stream:
        for raw_line in stream:
            line = raw_line.strip()
            if not line:
                continue
            if line.upper() == "END":
                current_id = None
            elif "," not in line:
                current_id = line
            elif current_id is not None:
                longitude, latitude = map(float, line.split(","))
                groups[current_id].append((longitude, latitude))
    return [np.asarray(groups[key], dtype=float) for key in sorted(groups, key=int)]


def load_flows() -> tuple[dict[int, list[np.ndarray]], dict[int, list[np.ndarray]]]:
    """Load lava polygons and fissure lines from three MGDS archives."""
    flow_groups: dict[int, list[np.ndarray]] = {}
    fissure_groups: dict[int, list[np.ndarray]] = {}
    directories = {
        1998: RAW_ROOT / "mgds" / "clague-1998",
        2011: RAW_ROOT / "mgds" / "clague-2011",
        2015: RAW_ROOT / "mgds" / "clague-2015",
    }
    flow_groups[1998] = read_1998_lava_polygons(
        one_file(directories[1998], "Axial-1998-lava-geo.txt.gz")
    )
    fissure_groups[1998] = read_1998_fissures(
        one_file(directories[1998], "Axial-1998-Fissures.txt.gz")
    )
    for year in (2011, 2015):
        directory = directories[year]
        flow_groups[year] = read_table_groups(
            one_file(directory, f"Axial-{year}-lava-points-geo-v2.txt.gz"),
            group_column="ORIG_FID",
            longitude_column="LONGITUDE",
            latitude_column="LATITUDE",
        )
        fissure_groups[year] = read_table_groups(
            one_file(directory, f"Axial-{year}-fissures-points-geo-v2.txt.gz"),
            group_column="ORIG_FID",
            longitude_column="LONGITUDE",
            latitude_column="LATITUDE",
        )
    return flow_groups, fissure_groups


def load_earthquakes(path: Path) -> np.ndarray:
    """Read the 13-column MGDS relocated earthquake catalog."""
    events = np.loadtxt(path, dtype=float)
    if events.ndim != 2 or events.shape[1] != 13:
        raise ValueError("Arnulf earthquake catalog must contain 13 columns")
    if not np.all(np.isfinite(events[:, [3, 4, 6]])):
        raise ValueError("earthquake longitude, latitude, and magnitude must be finite")
    return events


def validate_catalog_coordinates(events: np.ndarray) -> dict[str, float]:
    """Check the geographic projection against the catalog's local x/y fields."""
    east_km, north_km = geographic_to_local_km(events[:, 3], events[:, 4])
    angle = np.deg2rad(LOCAL_GRID_ROTATION_DEG)
    x_km = east_km * np.cos(angle) - north_km * np.sin(angle)
    y_km = east_km * np.sin(angle) + north_km * np.cos(angle)
    rms_x_km = float(np.sqrt(np.mean((x_km - events[:, 0]) ** 2)))
    rms_y_km = float(np.sqrt(np.mean((y_km - events[:, 1]) ** 2)))
    if max(rms_x_km, rms_y_km) > 0.001:
        raise ValueError(
            "geographic earthquake coordinates do not match the source local grid: "
            f"x RMS={rms_x_km:.6f} km, y RMS={rms_y_km:.6f} km"
        )
    return {"x_rms_km": rms_x_km, "y_rms_km": rms_y_km}


def load_vp_slice(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[dict[str, float]]]:
    """Read a horizontal Vp slice and select summit and eastern low-Vp regions."""
    x_grid = np.arange(-15.0, 15.0001, 0.1)
    y_grid = np.arange(-20.0, 20.0001, 0.1)
    velocity = np.full((len(y_grid), len(x_grid)), np.nan, dtype=np.float32)
    with gzip.open(path, "rt", encoding="ascii") as stream:
        for line in stream:
            x_value, y_value, z_value, vp_value = line.split()
            if float(z_value) != VP_SLICE_DEPTH_KM_BSL:
                continue
            vp = float(vp_value)
            if np.isfinite(vp):
                x_index = round((float(x_value) + 15.0) / 0.1)
                y_index = round((float(y_value) + 20.0) / 0.1)
                velocity[y_index, x_index] = vp

    if np.count_nonzero(np.isfinite(velocity)) < 10_000:
        raise ValueError("tomography slice contains too few valid velocity samples")
    valid = np.isfinite(velocity)
    weights = gaussian_filter(valid.astype(float), sigma=VP_SMOOTH_SIGMA_GRID_CELLS)
    smoothed = gaussian_filter(
        np.nan_to_num(velocity, nan=0.0) * valid,
        sigma=VP_SMOOTH_SIGMA_GRID_CELLS,
    ) / np.maximum(weights, 1.0e-12)
    smoothed[weights < 0.9] = np.nan
    low_vp = np.isfinite(smoothed) & (smoothed <= VP_THRESHOLD_KM_S)
    component_labels, _ = label(low_vp, structure=np.ones((3, 3), dtype=int))

    components: list[dict[str, float]] = []
    for component_id in np.unique(component_labels):
        if component_id == 0:
            continue
        rows, columns = np.where(component_labels == component_id)
        if len(columns) < VP_MIN_COMPONENT_CELLS:
            continue
        components.append(
            {
                "id": int(component_id),
                "x_km": float(np.mean(x_grid[columns])),
                "y_km": float(np.mean(y_grid[rows])),
                "cells": int(len(columns)),
            }
        )
    main_candidates = [
        component
        for component in components
        if -5.0 <= component["x_km"] <= 5.0
        and -5.0 <= component["y_km"] <= 8.0
    ]
    secondary_candidates = [
        component
        for component in components
        if 5.0 <= component["x_km"] <= 15.0
        and -5.0 <= component["y_km"] <= 8.0
    ]
    if not main_candidates or not secondary_candidates:
        raise ValueError(
            "could not isolate summit and eastern low-Vp components; "
            f"candidates were {components}"
        )
    main = min(
        main_candidates,
        key=lambda item: (
            item["x_km"] ** 2 + item["y_km"] ** 2,
            -item["cells"],
        ),
    )
    secondary = min(
        secondary_candidates,
        key=lambda item: (
            (item["x_km"] - 8.0) ** 2 + (item["y_km"] - 2.0) ** 2,
            -item["cells"],
        ),
    )
    if main["id"] == secondary["id"]:
        raise ValueError("summit and eastern low-Vp selections resolved to one region")
    return x_grid, y_grid, component_labels, [main, secondary]


def convert_vertices(vertices: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Convert a longitude/latitude array to map east/north kilometers."""
    return geographic_to_local_km(vertices[:, 0], vertices[:, 1])


def draw_map(*, output_stem: Path, summary_path: Path) -> dict[str, object]:
    """Render the 50 km square overview and record its source and method details."""
    bathy_path = RAW_ROOT / "gmrt" / "axial_gmrt_high_50km.tif"
    eq_path = one_file(
        RAW_ROOT / "mgds" / "arnulf-earthquakes",
        "Axial_EQs_3Dreloc_Arnulf_etal_51197events.txt.gz",
    )
    vp_path = one_file(
        RAW_ROOT / "mgds" / "arnulf-vp-model",
        "Axial3D_VPmask_Arnulf_etal.xyzv.gz",
    )
    for source in (bathy_path, eq_path, vp_path):
        if not source.exists():
            raise FileNotFoundError(
                f"missing Figure 1 input {source}; run data/fetch_figure1_sources.py"
            )

    bathymetry, bathy_east, bathy_north = load_geotiff(bathy_path)
    flows, fissures = load_flows()
    events = load_earthquakes(eq_path)
    coordinate_check = validate_catalog_coordinates(events)
    x_vp, y_vp, vp_labels, vp_components = load_vp_slice(vp_path)
    x_mesh, y_mesh = np.meshgrid(x_vp, y_vp)
    vp_east, vp_north = velocity_grid_to_local_km(x_mesh, y_mesh)

    fig, ax = plt.subplots(figsize=(10.4, 10.4))
    fig.subplots_adjust(left=0.10, right=0.97, top=0.92, bottom=0.12)
    ax.imshow(
        bathymetry,
        extent=(
            bathy_east[0],
            bathy_east[-1],
            bathy_north[-1],
            bathy_north[0],
        ),
        origin="upper",
        cmap="Blues_r",
        vmin=-2900,
        vmax=-1350,
        interpolation="bilinear",
        zorder=0,
    )
    contour = ax.contour(
        bathy_east[::4],
        bathy_north[::4],
        bathymetry[::4, ::4],
        levels=np.arange(-2800, -1399, 200),
        colors="#31485b",
        linewidths=0.42,
        alpha=0.58,
        zorder=1,
    )
    ax.clabel(contour, inline=True, fontsize=6, fmt=lambda value: f"{value:.0f}")

    flow_vertex_count: dict[str, int] = {}
    for year, polygons in flows.items():
        vertex_count = 0
        for polygon in polygons:
            if len(polygon) < 3:
                continue
            east, north = convert_vertices(polygon)
            vertex_count += len(polygon)
            ax.fill(
                east,
                north,
                facecolor=FLOW_COLORS[year],
                edgecolor=FLOW_COLORS[year],
                alpha=0.48,
                linewidth=0.7,
                zorder=3,
            )
        flow_vertex_count[str(year)] = vertex_count
    for year, lines in fissures.items():
        for line in lines:
            if len(line) < 2:
                continue
            east, north = convert_vertices(line)
            ax.plot(
                east,
                north,
                color=FLOW_COLORS[year],
                lw=0.72,
                ls="--",
                alpha=0.9,
                zorder=6,
            )

    earthquake_east, earthquake_north = geographic_to_local_km(
        events[:, 3], events[:, 4]
    )
    ax.scatter(
        earthquake_east,
        earthquake_north,
        s=1.2,
        c="#1b263b",
        alpha=0.16,
        linewidths=0,
        rasterized=True,
        zorder=2,
    )
    larger_events = events[:, 6] >= 1.0
    ax.scatter(
        earthquake_east[larger_events],
        earthquake_north[larger_events],
        s=9,
        c="#111827",
        alpha=0.42,
        linewidths=0,
        rasterized=True,
        zorder=2.5,
    )

    component_records = {}
    for component, name in zip(vp_components, ("MMR proxy", "SMR proxy"), strict=True):
        mask = (vp_labels == int(component["id"])).astype(float)
        ax.contour(
            vp_east,
            vp_north,
            mask,
            levels=[0.5],
            colors="#242424",
            linewidths=1.8,
            linestyles="--",
            zorder=7,
        )
        label_east, label_north = velocity_grid_to_local_km(
            component["x_km"], component["y_km"]
        )
        ax.text(
            float(label_east),
            float(label_north),
            name,
            ha="center",
            va="center",
            fontsize=8,
            color="#151515",
            weight="bold",
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.8, "pad": 1.5},
            zorder=8,
        )
        component_records[name] = {
            "tomography_grid_centroid_km": [
                component["x_km"],
                component["y_km"],
            ],
            "component_cells": component["cells"],
        }

    stations = {
        "Central Caldera": (45.954850, -130.008772),
        "Eastern Caldera": (45.939888, -129.974113),
    }
    for name, (latitude, longitude) in stations.items():
        east, north = geographic_to_local_km(longitude, latitude)
        ax.scatter(
            east,
            north,
            marker="^",
            s=54,
            facecolor="#ffdd57",
            edgecolor="#171717",
            linewidth=0.85,
            zorder=10,
        )
        offset = (-42, 7) if name == "Central Caldera" else (7, 7)
        ax.annotate(
            name,
            (east, north),
            xytext=offset,
            textcoords="offset points",
            fontsize=7,
            color="#111827",
            zorder=11,
        )

    handles = [
        *(
            Patch(
                facecolor=FLOW_COLORS[year],
                edgecolor=FLOW_COLORS[year],
                label=FLOW_LABELS[year],
            )
            for year in (1998, 2011, 2015)
        ),
        Line2D(
            [0],
            [0],
            marker=".",
            color="none",
            markerfacecolor="#1b263b",
            markeredgecolor="none",
            markersize=5,
            label="2015 relocated earthquakes (51,197)",
        ),
        Line2D(
            [0],
            [0],
            color="#242424",
            lw=1.8,
            ls="--",
            label="Vp ≤ 5.0 km/s proxy boundary",
        ),
        Line2D(
            [0],
            [0],
            marker="^",
            color="none",
            markerfacecolor="#ffdd57",
            markeredgecolor="#171717",
            markersize=7,
            label="OOI BPR",
        ),
    ]
    ax.legend(
        handles=handles,
        loc="upper left",
        frameon=True,
        framealpha=0.94,
        fontsize=8,
    )
    ax.set(
        xlim=MAP_LIMITS_KM,
        ylim=MAP_LIMITS_KM,
        xlabel="East of tomography-grid center (km)",
        ylabel="North of tomography-grid center (km)",
        title="Axial Seamount: independent surface and subsurface observations",
        aspect="equal",
    )
    ax.set_xticks(np.arange(-25, 26, 5))
    ax.set_yticks(np.arange(-25, 26, 5))
    ax.grid(color="white", alpha=0.48, linewidth=0.55, zorder=1.5)
    fig.text(
        0.5,
        0.025,
        "Bathymetry: GMRT GridServer. Lava/fissure outlines: MGDS 1998, 2011, 2015. "
        "Earthquakes and Vp: Arnulf et al. (2018), MGDS. Dashed boundaries are "
        "project-derived Vp proxies.",
        ha="center",
        va="bottom",
        fontsize=6.8,
        color="#202b35",
    )
    ax.annotate(
        "N",
        xy=(0.94, 0.91),
        xytext=(0.94, 0.81),
        xycoords="axes fraction",
        ha="center",
        va="center",
        arrowprops={"arrowstyle": "-|>", "lw": 1.2, "color": "#222"},
        fontsize=9,
        weight="bold",
        zorder=12,
    )
    bar_y = -23.0
    bar_x0, bar_x1 = -22.5, -12.5
    ax.plot([bar_x0, bar_x1], [bar_y, bar_y], color="black", lw=2.4, zorder=12)
    ax.plot([bar_x0, bar_x0], [bar_y - 0.25, bar_y + 0.25], color="black", lw=1.1, zorder=12)
    ax.plot([bar_x1, bar_x1], [bar_y - 0.25, bar_y + 0.25], color="black", lw=1.1, zorder=12)
    ax.text((bar_x0 + bar_x1) / 2, bar_y + 0.55, "10 km", ha="center", fontsize=7, zorder=12)

    output_stem.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_stem.with_suffix(".png"), dpi=300)
    fig.savefig(output_stem.with_suffix(".pdf"), dpi=300)
    plt.close(fig)
    try:
        revision = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        revision = "unknown"

    summary: dict[str, object] = {
        "project_revision": revision,
        "map_domain_km": [50, 50],
        "tomography_grid_center_lat_lon": [
            ORIGIN_LATITUDE_DEG,
            ORIGIN_LONGITUDE_DEG,
        ],
        "tomography_grid_rotation_deg": LOCAL_GRID_ROTATION_DEG,
        "earthquake_count": int(len(events)),
        "earthquake_catalog_time_span": "2015-01 through 2015-11",
        "earthquake_coordinate_projection_rms_km": coordinate_check,
        "lava_flow_vertices_by_eruption": flow_vertex_count,
        "selected_low_vp_components": component_records,
        "reservoir_proxy_method": {
            "source": "Arnulf et al. P-wave grid, MGDS DOI 10.1594/IEDA/324420",
            "slice_depth_km_below_sea_level": VP_SLICE_DEPTH_KM_BSL,
            "gaussian_smoothing_sigma_grid_cells": VP_SMOOTH_SIGMA_GRID_CELLS,
            "velocity_threshold_km_s": VP_THRESHOLD_KM_S,
            "interpretation": (
                "project-derived geometric proxies, not the migrated MMR "
                "constraint or an official reservoir outline"
            ),
        },
        "inputs": {
            "bathymetry": {
                "path": str(bathy_path.relative_to(ROOT)),
                "sha256": sha256_file(bathy_path),
            },
            "earthquakes": {
                "path": str(eq_path.relative_to(ROOT)),
                "sha256": sha256_file(eq_path),
            },
            "velocity_grid": {
                "path": str(vp_path.relative_to(ROOT)),
                "sha256": sha256_file(vp_path),
            },
            "flow_archives": {
                str(year): sorted(
                    sha256_file(path)
                    for path in (RAW_ROOT / "mgds" / f"clague-{year}").glob("**/*.gz")
                )
                for year in (1998, 2011, 2015)
            },
        },
        "outputs": [
            str(output_stem.with_suffix(suffix).relative_to(ROOT))
            for suffix in (".png", ".pdf")
        ],
        "publication_associated_data_used": False,
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    """Generate the authorized-data Axial overview map."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-stem", type=Path, default=OUTPUT_STEM)
    parser.add_argument("--summary", type=Path, default=SUMMARY_PATH)
    args = parser.parse_args()
    print(json.dumps(draw_map(output_stem=args.output_stem, summary_path=args.summary), indent=2))


if __name__ == "__main__":
    main()
