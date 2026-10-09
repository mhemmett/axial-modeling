"""Build initial PyLith Maxwell material databases from temperature fields."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from axialstress.spatialdb import write_simpledb
from axialstress.tetrahedral_interpolation import interpolate_tetrahedral_field
from axialstress.thermal import temperature_dependent_viscosity_pa_s

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]
TENSOR_COMPONENTS = ("xx", "yy", "zz", "xy", "yz", "xz")


def _wave_speeds_km_s(
    youngs_modulus_pa: FloatArray,
    density_kg_m3: float,
    poisson_ratio: float,
) -> tuple[FloatArray, FloatArray]:
    """Convert isotropic elastic properties to PyLith wave speeds."""
    shear_modulus = youngs_modulus_pa / (2.0 * (1.0 + poisson_ratio))
    bulk_modulus = youngs_modulus_pa / (3.0 * (1.0 - 2.0 * poisson_ratio))
    shear_velocity = np.sqrt(shear_modulus / density_kg_m3) / 1000.0
    compressional_velocity = np.sqrt(
        (bulk_modulus + 4.0 * shear_modulus / 3.0) / density_kg_m3
    ) / 1000.0
    return shear_velocity, compressional_velocity


def write_elastic_database(
    path: str | Path,
    vertices_m: FloatArray,
    tetrahedra: IntArray,
    youngs_modulus_pa_at_cells: FloatArray | float,
    *,
    density_kg_m3: float,
    poisson_ratio: float,
) -> Path:
    """Write cell-centered isotropic elastic properties as a PyLith SimpleDB.

    Parameters
    ----------
    path : str or pathlib.Path
        Destination filename for the PyLith SimpleDB.
    vertices_m : array_like
        Mesh coordinates in meters with shape ``(nvertices, 3)``.
    tetrahedra : array_like
        Zero-based tetrahedron vertex indices with shape ``(nelements, 4)``.
    youngs_modulus_pa_at_cells : array_like or float
        Young's modulus in pascals, scalar or one value per tetrahedron.
    density_kg_m3 : float
        Uniform density in kilograms per cubic meter.
    poisson_ratio : float
        Uniform Poisson ratio in the stable isotropic range ``(-1, 0.5)``.

    Returns
    -------
    pathlib.Path
        Path to the elastic-property SimpleDB file.
    """
    vertices = np.asarray(vertices_m, dtype=float)
    cells = np.asarray(tetrahedra, dtype=np.int64)
    modulus = np.asarray(youngs_modulus_pa_at_cells, dtype=float)
    if vertices.ndim != 2 or vertices.shape[1] != 3 or len(vertices) < 4:
        raise ValueError("vertices must have shape (n, 3) with at least four points")
    if cells.ndim != 2 or cells.shape[1] != 4 or len(cells) == 0:
        raise ValueError("tetrahedra must have shape (m, 4) with at least one element")
    if np.any(cells < 0) or np.any(cells >= len(vertices)):
        raise ValueError("tetrahedra contain invalid vertex indices")
    if not np.all(np.isfinite(vertices)):
        raise ValueError("mesh coordinates must be finite")
    if not np.isfinite(density_kg_m3) or density_kg_m3 <= 0.0:
        raise ValueError("density must be finite and positive")
    if not np.isfinite(poisson_ratio) or not -1.0 < poisson_ratio < 0.5:
        raise ValueError("Poisson ratio must be in the stable isotropic range (-1, 0.5)")
    try:
        modulus = np.broadcast_to(modulus, (len(cells),))
    except ValueError as exc:
        raise ValueError("Young's modulus must be scalar or one value per tetrahedron") from exc
    if not np.all(np.isfinite(modulus)) or np.any(modulus <= 0.0):
        raise ValueError("Young's modulus must be finite and positive")

    shear_velocity, compressional_velocity = _wave_speeds_km_s(
        modulus, density_kg_m3, poisson_ratio
    )
    centroids = vertices[cells].mean(axis=1)
    values = np.column_stack(
        (
            np.full(len(cells), density_kg_m3),
            shear_velocity,
            compressional_velocity,
        )
    )
    return write_simpledb(
        path,
        ("density", "vs", "vp"),
        ("kg/m**3", "km/s", "km/s"),
        centroids,
        values,
    )


def write_temperature_dependent_maxwell_database(
    path: str | Path,
    vertices_m: FloatArray,
    tetrahedra: IntArray,
    temperature_c_at_vertices: FloatArray,
    youngs_modulus_pa_at_cells: FloatArray | float,
    *,
    density_kg_m3: float,
    poisson_ratio: float,
    dorn_parameter_pa_s: float = 1.0e9,
    activation_energy_j_mol: float = 1.2e5,
    gas_constant_j_mol_k: float = 8.3114,
) -> Path:
    """Write cell-centered Maxwell properties and a zero initial state.

    Temperature and Young's modulus are sampled at tetrahedron centroids.
    Viscosity follows the Arrhenius law implemented in
    :func:`temperature_dependent_viscosity_pa_s`. Young's modulus is supplied
    explicitly because the printed temperature-dependent modulus equation is
    inconsistent with its accompanying brittle and ductile definitions.

    Parameters
    ----------
    path : str or pathlib.Path
        Destination filename for the PyLith SimpleDB.
    vertices_m : array_like
        Mesh coordinates in meters with shape ``(nvertices, 3)``.
    tetrahedra : array_like
        Zero-based tetrahedron vertex indices with shape ``(nelements, 4)``.
    temperature_c_at_vertices : array_like
        Nodal temperatures in degrees Celsius.
    youngs_modulus_pa_at_cells : array_like or float
        Explicit Young's modulus in pascals, scalar or one value per cell.
    density_kg_m3 : float
        Uniform density in kilograms per cubic meter.
    poisson_ratio : float
        Uniform Poisson ratio in the stable isotropic range ``(-1, 0.5)``.
    dorn_parameter_pa_s : float
        Arrhenius Dorn parameter in pascal-seconds.
    activation_energy_j_mol : float
        Activation energy in joules per mole.
    gas_constant_j_mol_k : float
        Gas constant in joules per mole-kelvin.

    Returns
    -------
    pathlib.Path
        Path to the material SimpleDB file.
    """
    vertices = np.asarray(vertices_m, dtype=float)
    cells = np.asarray(tetrahedra, dtype=np.int64)
    temperatures = np.asarray(temperature_c_at_vertices, dtype=float)
    if vertices.ndim != 2 or vertices.shape[1] != 3 or len(vertices) < 4:
        raise ValueError("vertices must have shape (n, 3) with at least four points")
    if cells.ndim != 2 or cells.shape[1] != 4 or len(cells) == 0:
        raise ValueError("tetrahedra must have shape (m, 4) with at least one element")
    if np.any(cells < 0) or np.any(cells >= len(vertices)):
        raise ValueError("tetrahedra contain invalid vertex indices")
    if temperatures.shape != (len(vertices),):
        raise ValueError("temperature must have one value per mesh vertex")
    if not np.all(np.isfinite(vertices)) or not np.all(np.isfinite(temperatures)):
        raise ValueError("mesh coordinates and temperatures must be finite")
    if not np.isfinite(density_kg_m3) or density_kg_m3 <= 0.0:
        raise ValueError("density must be finite and positive")
    if not np.isfinite(poisson_ratio) or not -1.0 < poisson_ratio < 0.5:
        raise ValueError("Poisson ratio must be in the stable isotropic range (-1, 0.5)")

    cell_temperature = temperatures[cells].mean(axis=1)
    youngs_modulus = np.asarray(youngs_modulus_pa_at_cells, dtype=float)
    try:
        youngs_modulus = np.broadcast_to(youngs_modulus, (len(cells),))
    except ValueError as exc:
        raise ValueError("Young's modulus must be scalar or one value per tetrahedron") from exc
    if not np.all(np.isfinite(youngs_modulus)) or np.any(youngs_modulus <= 0.0):
        raise ValueError("Young's modulus must be finite and positive")

    return _write_maxwell_database_at_cell_temperatures(
        path,
        vertices,
        cells,
        cell_temperature,
        youngs_modulus,
        density_kg_m3=density_kg_m3,
        poisson_ratio=poisson_ratio,
        dorn_parameter_pa_s=dorn_parameter_pa_s,
        activation_energy_j_mol=activation_energy_j_mol,
        gas_constant_j_mol_k=gas_constant_j_mol_k,
    )


def _write_maxwell_database_at_cell_temperatures(
    path: str | Path,
    vertices: FloatArray,
    cells: IntArray,
    cell_temperature_c: FloatArray,
    youngs_modulus_pa: FloatArray,
    *,
    density_kg_m3: float,
    poisson_ratio: float,
    dorn_parameter_pa_s: float,
    activation_energy_j_mol: float,
    gas_constant_j_mol_k: float,
) -> Path:
    """Write PyLith Maxwell properties from temperatures at element centers."""
    centroids = vertices[cells].mean(axis=1)
    if cell_temperature_c.shape != (len(cells),):
        raise ValueError("cell_temperature_c must have one value per tetrahedron")
    if not np.all(np.isfinite(cell_temperature_c)):
        raise ValueError("cell temperatures must be finite")
    modulus = np.asarray(youngs_modulus_pa, dtype=float)
    try:
        modulus = np.broadcast_to(modulus, (len(cells),))
    except ValueError as exc:
        raise ValueError("Young's modulus must be scalar or one value per tetrahedron") from exc
    if not np.all(np.isfinite(modulus)) or np.any(modulus <= 0.0):
        raise ValueError("Young's modulus must be finite and positive")
    if not np.isfinite(density_kg_m3) or density_kg_m3 <= 0.0:
        raise ValueError("density must be finite and positive")
    if not np.isfinite(poisson_ratio) or not -1.0 < poisson_ratio < 0.5:
        raise ValueError("Poisson ratio must be in the stable isotropic range (-1, 0.5)")

    shear_velocity_km_s, compressional_velocity_km_s = _wave_speeds_km_s(
        modulus, density_kg_m3, poisson_ratio
    )
    viscosity_pa_s = temperature_dependent_viscosity_pa_s(
        cell_temperature_c,
        dorn_parameter_pa_s=dorn_parameter_pa_s,
        activation_energy_j_mol=activation_energy_j_mol,
        gas_constant_j_mol_k=gas_constant_j_mol_k,
    )

    names = (
        "density",
        "vs",
        "vp",
        "viscosity",
        *(f"viscous_strain_{component}" for component in TENSOR_COMPONENTS),
        *(f"total_strain_{component}" for component in TENSOR_COMPONENTS),
    )
    units = ("kg/m**3", "km/s", "km/s", "Pa*s", *("None" for _ in range(12)))
    values = np.column_stack(
        (
            np.full(len(cells), density_kg_m3),
            shear_velocity_km_s,
            compressional_velocity_km_s,
            viscosity_pa_s,
            np.zeros((len(cells), 12)),
        )
    )
    return write_simpledb(path, names, units, centroids, values)


def write_maxwell_database_from_thermal_archive(
    thermal_archive_path: str | Path,
    database_path: str | Path,
    youngs_modulus_pa: float,
    *,
    density_kg_m3: float,
    poisson_ratio: float,
    mechanics_vertices_m: FloatArray | None = None,
    mechanics_tetrahedra: IntArray | None = None,
    dorn_parameter_pa_s: float = 1.0e9,
    activation_energy_j_mol: float = 1.2e5,
    gas_constant_j_mol_k: float = 8.3114,
) -> Path:
    """Write Maxwell properties from a saved tetrahedral temperature field.

    Parameters
    ----------
    thermal_archive_path : str or pathlib.Path
        Compressed archive written by ``axialstress.thermal_model``.
    database_path : str or pathlib.Path
        Destination path for the PyLith material SimpleDB.
    youngs_modulus_pa : float
        Explicit uniform Young's modulus in pascals. The written temperature
        law remains unresolved and is not inferred here.
    density_kg_m3 : float
        Uniform density in kilograms per cubic meter.
    poisson_ratio : float
        Uniform Poisson ratio in the stable isotropic range ``(-1, 0.5)``.
    mechanics_vertices_m : array_like, optional
        Coordinates of the mechanics mesh in meters. When supplied with
        ``mechanics_tetrahedra``, thermal temperature is interpolated from the
        archive mesh to mechanics element centers.
    mechanics_tetrahedra : array_like, optional
        Zero-based mechanics tetrahedron vertex indices.
    dorn_parameter_pa_s : float
        Arrhenius Dorn parameter in pascal-seconds.
    activation_energy_j_mol : float
        Arrhenius activation energy in joules per mole.
    gas_constant_j_mol_k : float
        Gas constant in joules per mole-kelvin.

    Returns
    -------
    pathlib.Path
        Path to the material SimpleDB file.
    """
    with np.load(thermal_archive_path, allow_pickle=False) as archive:
        required = {"vertices_m", "tetrahedra", "temperature_c"}
        missing = sorted(required - set(archive.files))
        if missing:
            raise ValueError(f"thermal archive is missing arrays: {missing}")
        thermal_vertices = np.asarray(archive["vertices_m"], dtype=float)
        thermal_cells = np.asarray(archive["tetrahedra"], dtype=np.int64)
        thermal_temperature = np.asarray(archive["temperature_c"], dtype=float)
        if (mechanics_vertices_m is None) != (mechanics_tetrahedra is None):
            raise ValueError(
                "mechanics_vertices_m and mechanics_tetrahedra must be supplied together"
            )
        if mechanics_vertices_m is None:
            mechanics_vertices = thermal_vertices
            mechanics_cells = thermal_cells
        else:
            mechanics_vertices = np.asarray(mechanics_vertices_m, dtype=float)
            mechanics_cells = np.asarray(mechanics_tetrahedra, dtype=np.int64)
        if (
            mechanics_vertices.ndim != 2
            or mechanics_vertices.shape[1] != 3
            or len(mechanics_vertices) < 4
        ):
            raise ValueError("mechanics vertices must have shape (n, 3)")
        if not np.all(np.isfinite(mechanics_vertices)):
            raise ValueError("mechanics vertices must be finite")
        if mechanics_cells.ndim != 2 or mechanics_cells.shape[1] != 4 or not len(
            mechanics_cells
        ):
            raise ValueError("mechanics tetrahedra must have nonempty shape (m, 4)")
        if np.any(mechanics_cells < 0) or np.any(
            mechanics_cells >= len(mechanics_vertices)
        ):
            raise ValueError("mechanics tetrahedra contain invalid vertex indices")
        mechanics_centroids = mechanics_vertices[mechanics_cells].mean(axis=1)
        cell_temperature = interpolate_tetrahedral_field(
            thermal_vertices,
            thermal_cells,
            thermal_temperature,
            mechanics_centroids,
        )
        modulus = np.asarray(youngs_modulus_pa, dtype=float)
        try:
            modulus = np.broadcast_to(modulus, (len(mechanics_cells),))
        except ValueError as exc:
            raise ValueError(
                "Young's modulus must be scalar or one value per mechanics tetrahedron"
            ) from exc
        if not np.all(np.isfinite(modulus)) or np.any(modulus <= 0.0):
            raise ValueError("Young's modulus must be finite and positive")
        return _write_maxwell_database_at_cell_temperatures(
            database_path,
            mechanics_vertices,
            mechanics_cells,
            cell_temperature,
            modulus,
            density_kg_m3=density_kg_m3,
            poisson_ratio=poisson_ratio,
            dorn_parameter_pa_s=dorn_parameter_pa_s,
            activation_energy_j_mol=activation_energy_j_mol,
            gas_constant_j_mol_k=gas_constant_j_mol_k,
        )


def main() -> None:
    """Build a PyLith Maxwell database from a saved thermal solution."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--thermal-archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--youngs-modulus-pa", type=float, required=True)
    parser.add_argument("--density-kg-m3", type=float, required=True)
    parser.add_argument("--poisson-ratio", type=float, required=True)
    parser.add_argument("--dorn-parameter-pa-s", type=float, default=1.0e9)
    parser.add_argument("--activation-energy-j-mol", type=float, default=1.2e5)
    parser.add_argument("--gas-constant-j-mol-k", type=float, default=8.3114)
    args = parser.parse_args()
    result = write_maxwell_database_from_thermal_archive(
        args.thermal_archive,
        args.output,
        args.youngs_modulus_pa,
        density_kg_m3=args.density_kg_m3,
        poisson_ratio=args.poisson_ratio,
        dorn_parameter_pa_s=args.dorn_parameter_pa_s,
        activation_energy_j_mol=args.activation_energy_j_mol,
        gas_constant_j_mol_k=args.gas_constant_j_mol_k,
    )
    print(f"Wrote temperature-dependent Maxwell properties to {result}.")


if __name__ == "__main__":
    main()
