"""Plot hydrothermal temperature-dependent properties on the model midplane."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import matplotlib.tri as mtri
import numpy as np
from matplotlib.patches import Ellipse

from axialstress.thermal import (
    evaluate_eq16_youngs_modulus_pa,
    temperature_dependent_viscosity_pa_s,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARCHIVE = ROOT / "pylith/step03_steady_thermal/output/steady_thermal_hydrothermal.npz"
DEFAULT_OUTPUT_STEM = ROOT / "figures/thermal_property_slices"
SLICE_HALF_WIDTH_M = 700.0
X_LIMITS_KM = (-10.0, 10.0)
DEPTH_LIMITS_KM = (0.0, 10.0)


def _read_fields(archive_path: Path) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """Read the hydrothermal field and derive cell-centered model properties."""
    with np.load(archive_path, allow_pickle=False) as archive:
        required = {"vertices_m", "tetrahedra", "temperature_c", "cell_conductivity_w_mk"}
        missing = sorted(required - set(archive.files))
        if missing:
            raise ValueError(f"thermal archive is missing arrays: {missing}")
        vertices = np.asarray(archive["vertices_m"], dtype=float)
        tetrahedra = np.asarray(archive["tetrahedra"], dtype=np.int64)
        temperature_c = np.asarray(archive["temperature_c"], dtype=float)
        conductivity = np.asarray(archive["cell_conductivity_w_mk"], dtype=float)

    if vertices.ndim != 2 or vertices.shape[1] != 3 or not len(vertices):
        raise ValueError("vertices_m must have shape (n, 3)")
    if tetrahedra.ndim != 2 or tetrahedra.shape[1] != 4 or not len(tetrahedra):
        raise ValueError("tetrahedra must have shape (m, 4)")
    if np.any(tetrahedra < 0) or np.any(tetrahedra >= len(vertices)):
        raise ValueError("tetrahedra contain an invalid vertex index")
    if temperature_c.shape != (len(vertices),) or not np.all(np.isfinite(temperature_c)):
        raise ValueError("temperature_c must contain one finite value per vertex")
    if conductivity.shape != (len(tetrahedra),) or not np.all(np.isfinite(conductivity)):
        raise ValueError("cell conductivity must contain one finite value per tetrahedron")

    cell_vertices = vertices[tetrahedra]
    cell_temperature_c = temperature_c[tetrahedra].mean(axis=1)
    affine = np.concatenate(
        (np.ones((*cell_vertices.shape[:2], 1)), cell_vertices), axis=2
    )
    coefficients = np.linalg.solve(
        affine, temperature_c[tetrahedra, None]
    )[:, :, 0]
    gradient_c_per_km = np.linalg.norm(coefficients[:, 1:], axis=1) * 1000.0
    fields = {
        "Young's modulus (GPa)": evaluate_eq16_youngs_modulus_pa(cell_temperature_c)
        / 1.0e9,
        "log₁₀ viscosity (Pa s)": np.log10(
            temperature_dependent_viscosity_pa_s(cell_temperature_c)
        ),
        "Thermal gradient (°C km⁻¹)": gradient_c_per_km,
        "Conductivity (W m⁻¹ K⁻¹)": conductivity,
    }
    centers = cell_vertices.mean(axis=1)
    return centers, fields


def _slice_triangulation(
    centers_m: np.ndarray,
    fields: dict[str, np.ndarray],
) -> tuple[mtri.Triangulation, dict[str, np.ndarray]]:
    """Project cell centers near y=0 into a documented finite-thickness slice."""
    in_slice = np.abs(centers_m[:, 1]) <= SLICE_HALF_WIDTH_M
    in_view = (
        (centers_m[:, 0] / 1000.0 >= X_LIMITS_KM[0])
        & (centers_m[:, 0] / 1000.0 <= X_LIMITS_KM[1])
        & (-centers_m[:, 2] / 1000.0 >= DEPTH_LIMITS_KM[0])
        & (-centers_m[:, 2] / 1000.0 <= DEPTH_LIMITS_KM[1])
    )
    selected = in_slice & in_view
    if np.count_nonzero(selected) < 4:
        raise ValueError("mesh has too few cell centers in the requested midplane view")

    x_km = centers_m[selected, 0] / 1000.0
    depth_km = -centers_m[selected, 2] / 1000.0
    triangulation = mtri.Triangulation(x_km, depth_km)
    triangles = triangulation.triangles
    points = np.column_stack((x_km, depth_km))
    triangle_points = points[triangles]
    edge_lengths = np.linalg.norm(
        triangle_points - np.roll(triangle_points, 1, axis=1), axis=2
    )
    triangle_centers = triangle_points.mean(axis=1)
    in_cavity = (
        triangle_centers[:, 0] ** 2 / 3.0**2
        + (triangle_centers[:, 1] - 1.6) ** 2 / 0.5**2
        <= 1.0
    )
    triangulation.set_mask(np.any(edge_lengths > 4.0, axis=1) | in_cavity)
    selected_fields = {name: values[selected] for name, values in fields.items()}
    return triangulation, selected_fields


def plot_property_slices(archive_path: Path, output_stem: Path) -> tuple[Path, Path]:
    """Write PNG and PDF maps for one hydrothermal thermal-property solution."""
    centers_m, fields = _read_fields(archive_path)
    triangulation, sliced_fields = _slice_triangulation(centers_m, fields)
    output_stem.parent.mkdir(parents=True, exist_ok=True)

    figure, axes = plt.subplots(2, 2, figsize=(11.0, 7.4), constrained_layout=True)
    color_maps = ("viridis", "magma", "inferno", "cividis")
    for axis, (label, values), color_map in zip(
        axes.flat, sliced_fields.items(), color_maps, strict=True
    ):
        image = axis.tripcolor(
            triangulation,
            values,
            shading="gouraud",
            cmap=color_map,
            rasterized=True,
        )
        axis.add_patch(
            Ellipse(
                (0.0, 1.6),
                width=6.0,
                height=1.0,
                facecolor="white",
                edgecolor="#222222",
                linewidth=1.0,
                zorder=4,
            )
        )
        axis.set_xlim(*X_LIMITS_KM)
        axis.set_ylim(DEPTH_LIMITS_KM[1], DEPTH_LIMITS_KM[0])
        axis.set_xlabel("Distance east of source axis (km)")
        axis.set_ylabel("Depth below seafloor (km)")
        axis.set_title(label)
        axis.set_aspect("equal", adjustable="box")
        figure.colorbar(image, ax=axis, shrink=0.88)

    figure.suptitle(
        "Hydrothermal temperature-dependent property slice\n"
        "Eq. 15 viscosity; Eq. 16 as printed; Eq. 22 conductivity"
    )
    figure.text(
        0.5,
        -0.01,
        "Cell-center projection within |y| ≤ 0.7 km; white ellipse marks the reservoir. "
        "Side and basal temperatures use the assumed 30 °C/km geotherm. "
        "Eq. 16 conflicts with the stated brittle and ductile limits.",
        ha="center",
        va="top",
        fontsize=8.5,
    )
    png_path = output_stem.with_suffix(".png")
    pdf_path = output_stem.with_suffix(".pdf")
    figure.savefig(png_path, dpi=220, bbox_inches="tight")
    figure.savefig(pdf_path, bbox_inches="tight")
    plt.close(figure)
    return png_path, pdf_path


def main() -> None:
    """Parse the thermal archive and output path, then write the property figure."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--output-stem", type=Path, default=DEFAULT_OUTPUT_STEM)
    args = parser.parse_args()
    png_path, pdf_path = plot_property_slices(args.archive, args.output_stem)
    print(f"wrote {png_path} and {pdf_path}")


if __name__ == "__main__":
    main()
