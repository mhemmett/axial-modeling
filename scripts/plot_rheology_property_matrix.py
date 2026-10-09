"""Plot the four project rheologies as a 4 × 4 property matrix."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import matplotlib.tri as mtri
import numpy as np
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize
from matplotlib.patches import Ellipse

from axialstress.thermal import temperature_range_youngs_modulus_pa

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARCHIVE = ROOT / "data/processed/rheology_case_matrix_model_data.npz"
DEFAULT_OUTPUT_STEM = ROOT / "figures/figure3_rheology_property_matrix"
SLICE_HALF_WIDTH_M = 700.0
X_LIMITS_KM = (0.0, 25.0)
DEPTH_LIMITS_KM = (0.0, 10.0)
REFERENCE_VISCOSITY_PA_S_BY_BRANCH = np.array([1.0e18, 5.0e17, 2.0e18])
ACTIVATION_ENERGY_J_MOL = 1.2e5
GAS_CONSTANT_J_MOL_K = 8.3114
REFERENCE_TEMPERATURE_C = 1200.0

CASE_LABELS = (
    "Non-TD elastic",
    "Non-TD viscoelastic",
    "Full TD",
    "Full TD + hydrothermal",
)
ROW_LABELS = (
    "Young's modulus (GPa)",
    "log₁₀ viscosity (Pa s)",
    "Temperature (°C)",
    "Thermal conductivity (W m⁻¹ K⁻¹)",
)
COLOR_MAPS = ("viridis", "magma", "inferno", "cividis")


def _load_fields(path: Path) -> tuple[np.ndarray, list[list[np.ndarray | None]]]:
    """Load the thermal mesh archive and derive four property rows per case."""
    with np.load(path, allow_pickle=False) as archive:
        required = {
            "vertices_m",
            "tetrahedra",
            "baseline_temperature_c",
            "baseline_conductivity_w_mk",
            "hydrothermal_temperature_c",
            "hydrothermal_conductivity_w_mk",
        }
        missing = sorted(required - set(archive.files))
        if missing:
            raise ValueError(f"model archive is missing arrays: {missing}")
        vertices = np.asarray(archive["vertices_m"], dtype=float)
        cells = np.asarray(archive["tetrahedra"], dtype=np.int64)
        baseline_temperature = np.asarray(archive["baseline_temperature_c"], dtype=float)
        baseline_conductivity = np.asarray(
            archive["baseline_conductivity_w_mk"], dtype=float
        )
        hydro_temperature = np.asarray(archive["hydrothermal_temperature_c"], dtype=float)
        hydro_conductivity = np.asarray(
            archive["hydrothermal_conductivity_w_mk"], dtype=float
        )

    if vertices.ndim != 2 or vertices.shape[1] != 3 or len(vertices) == 0:
        raise ValueError("vertices_m must have shape (n, 3)")
    if cells.ndim != 2 or cells.shape[1] != 4 or len(cells) == 0:
        raise ValueError("tetrahedra must have shape (m, 4)")
    if np.any(cells < 0) or np.any(cells >= len(vertices)):
        raise ValueError("tetrahedra contain an invalid vertex index")
    for name, values in (
        ("baseline_temperature_c", baseline_temperature),
        ("hydrothermal_temperature_c", hydro_temperature),
    ):
        if values.shape != (len(vertices),) or not np.all(np.isfinite(values)):
            raise ValueError(f"{name} must contain one finite value per vertex")
    for name, values in (
        ("baseline_conductivity_w_mk", baseline_conductivity),
        ("hydrothermal_conductivity_w_mk", hydro_conductivity),
    ):
        if values.shape != (len(cells),) or not np.all(np.isfinite(values)):
            raise ValueError(f"{name} must contain one finite value per tetrahedron")

    cell_vertices = vertices[cells]
    centers = cell_vertices.mean(axis=1)
    cell_temperature_baseline = baseline_temperature[cells].mean(axis=1)
    cell_temperature_hydro = hydro_temperature[cells].mean(axis=1)
    constant_modulus_gpa = np.full(len(cells), 50.0)
    constant_viscosity_log = np.full(
        len(cells), np.mean(np.log10(REFERENCE_VISCOSITY_PA_S_BY_BRANCH))
    )
    branch_log_mean = np.mean(np.log10(REFERENCE_VISCOSITY_PA_S_BY_BRANCH))
    ref_inverse_temperature = 1.0 / (REFERENCE_TEMPERATURE_C + 273.15)

    def td_viscosity_log(temperature_c: np.ndarray) -> np.ndarray:
        """Return log mean of the three temperature-mapped branch viscosities."""
        inverse_temperature = 1.0 / (temperature_c + 273.15)
        log_factor = (
            ACTIVATION_ENERGY_J_MOL
            / (GAS_CONSTANT_J_MOL_K * np.log(10.0))
            * (inverse_temperature - ref_inverse_temperature)
        )
        return branch_log_mean + log_factor

    case_fields = [
        [constant_modulus_gpa, None, None, None],
        [constant_modulus_gpa.copy(), constant_viscosity_log, None, None],
        [
            temperature_range_youngs_modulus_pa(cell_temperature_baseline) / 1.0e9,
            td_viscosity_log(cell_temperature_baseline),
            cell_temperature_baseline,
            baseline_conductivity,
        ],
        [
            temperature_range_youngs_modulus_pa(cell_temperature_hydro) / 1.0e9,
            td_viscosity_log(cell_temperature_hydro),
            cell_temperature_hydro,
            hydro_conductivity,
        ],
    ]
    return centers, [list(row) for row in zip(*case_fields, strict=True)]


def _slice(
    centers_m: np.ndarray,
    fields: list[list[np.ndarray | None]],
) -> tuple[mtri.Triangulation, list[list[np.ndarray | None]]]:
    """Project mesh-cell fields into the finite-thickness center section."""
    in_slice = np.abs(centers_m[:, 1]) <= SLICE_HALF_WIDTH_M
    in_view = (
        (centers_m[:, 0] / 1000.0 >= X_LIMITS_KM[0])
        & (centers_m[:, 0] / 1000.0 <= X_LIMITS_KM[1])
        & (-centers_m[:, 2] / 1000.0 >= DEPTH_LIMITS_KM[0])
        & (-centers_m[:, 2] / 1000.0 <= DEPTH_LIMITS_KM[1])
    )
    selected = in_slice & in_view
    if np.count_nonzero(selected) < 4:
        raise ValueError("mesh has too few cell centers in the requested center section")

    x_km = centers_m[selected, 0] / 1000.0
    depth_km = -centers_m[selected, 2] / 1000.0
    triangulation = mtri.Triangulation(x_km, depth_km)
    points = np.column_stack((x_km, depth_km))
    triangle_points = points[triangulation.triangles]
    edge_lengths = np.linalg.norm(
        triangle_points - np.roll(triangle_points, 1, axis=1), axis=2
    )
    triangle_centers = triangle_points.mean(axis=1)
    in_cavity = (
        triangle_centers[:, 0] ** 2 / 3.0**2
        + (triangle_centers[:, 1] - 1.6) ** 2 / 0.5**2
        <= 1.0
    )
    triangulation.set_mask(np.any(edge_lengths > 12.0, axis=1) | in_cavity)
    selected_fields = [
        [None if values is None else values[selected] for values in row]
        for row in fields
    ]
    return triangulation, selected_fields


def plot_property_matrix(archive_path: Path, output_stem: Path) -> tuple[Path, Path]:
    """Write PNG and PDF panels of the properties passed to the four cases."""
    centers_m, fields = _load_fields(archive_path)
    triangulation, sliced_fields = _slice(centers_m, fields)
    output_stem.parent.mkdir(parents=True, exist_ok=True)

    limits = (
        (20.0, 50.0),
        _finite_limits(sliced_fields[1]),
        (0.0, 1200.0),
        _finite_limits(sliced_fields[3]),
    )
    figure = plt.figure(figsize=(18.5, 10.5), constrained_layout=False)
    grid = figure.add_gridspec(
        4,
        5,
        width_ratios=(1.0, 1.0, 1.0, 1.0, 0.055),
        left=0.075,
        right=0.965,
        bottom=0.13,
        top=0.88,
        wspace=0.08,
        hspace=0.22,
    )
    for row in range(4):
        for column in range(4):
            axis = figure.add_subplot(grid[row, column])
            values = sliced_fields[row][column]
            if values is None:
                axis.set_facecolor("#F5F5F5")
                axis.text(
                    0.5,
                    0.5,
                    "N/A\nnot used in this rheology",
                    ha="center",
                    va="center",
                    transform=axis.transAxes,
                    fontsize=9,
                    color="#555555",
                )
            else:
                low, high = limits[row]
                axis.tripcolor(
                    triangulation,
                    values,
                    shading="gouraud",
                    cmap=COLOR_MAPS[row],
                    vmin=low,
                    vmax=high,
                    rasterized=True,
                )
                axis.add_patch(
                    Ellipse(
                        (0.0, 1.6),
                        width=6.0,
                        height=1.0,
                        facecolor="white",
                        edgecolor="#222222",
                        linewidth=0.9,
                        zorder=4,
                    )
                )
            axis.set_xlim(*X_LIMITS_KM)
            axis.set_ylim(DEPTH_LIMITS_KM[1], DEPTH_LIMITS_KM[0])
            axis.tick_params(labelsize=7)
            if row == 0:
                axis.set_title(CASE_LABELS[column], fontsize=10, pad=8)
            if column == 0:
                axis.set_ylabel(ROW_LABELS[row], fontsize=9)
            else:
                axis.set_yticklabels([])
            if row == 3:
                axis.set_xlabel("Distance right of reservoir center (km)", fontsize=8)
            else:
                axis.set_xticklabels([])
            axis.set_aspect("auto")

        low, high = limits[row]
        colorbar_axis = figure.add_subplot(grid[row, 4])
        colorbar = figure.colorbar(
            ScalarMappable(norm=Normalize(low, high), cmap=COLOR_MAPS[row]),
            cax=colorbar_axis,
        )
        colorbar.ax.tick_params(labelsize=7)
        colorbar.set_label(ROW_LABELS[row], fontsize=8)

    figure.suptitle(
        "Four-case PyLith material and thermal fields",
        fontsize=14,
        y=0.96,
    )
    figure.text(
        0.5,
        0.04,
        "Right half-section shown by symmetry; x is distance from the reservoir center. "
        "Cell-center projection within |y| ≤ 0.7 km; white half-ellipse marks the cavity. "
        "Young's modulus uses a linear 50–20 GPa interpolation from 0–1200 °C. "
        "Viscosity shows the geometric mean of three synthetic Maxwell branches. "
        "Thermal fields are enabled only for the temperature-dependent cases. "
        "Project outputs use a depth range of 0–10 km and a 50 km × 50 km domain.",
        ha="center",
        va="center",
        fontsize=8,
    )
    png_path = output_stem.with_suffix(".png")
    pdf_path = output_stem.with_suffix(".pdf")
    figure.savefig(png_path, dpi=220, bbox_inches="tight")
    figure.savefig(pdf_path, bbox_inches="tight")
    plt.close(figure)
    return png_path, pdf_path


def _finite_limits(row_fields: list[np.ndarray | None]) -> tuple[float, float]:
    """Return shared limits from finite values in one row of panels."""
    arrays = [values[np.isfinite(values)] for values in row_fields if values is not None]
    arrays = [values for values in arrays if values.size]
    if not arrays:
        raise ValueError("a plotted property row contains no finite values")
    values = np.concatenate(arrays)
    low, high = float(np.min(values)), float(np.max(values))
    if np.isclose(low, high):
        padding = max(1.0e-6, abs(low) * 1.0e-6)
        return low - padding, high + padding
    return low, high


def main() -> None:
    """Parse model archive and figure paths, then write the property matrix."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--output-stem", type=Path, default=DEFAULT_OUTPUT_STEM)
    args = parser.parse_args()
    png_path, pdf_path = plot_property_matrix(args.archive, args.output_stem)
    print(f"wrote {png_path} and {pdf_path}")


if __name__ == "__main__":
    main()
