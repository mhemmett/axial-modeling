"""Build initial PyLith Maxwell material databases from temperature fields."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from axialstress.spatialdb import write_simpledb
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


def write_generalized_maxwell_database(
    path: str | Path,
    vertices_m: FloatArray,
    tetrahedra: IntArray,
    youngs_modulus_pa_at_cells: FloatArray | float,
    *,
    density_kg_m3: float,
    poisson_ratio: float,
    viscosity_pa_s_by_branch: FloatArray,
    shear_modulus_ratio_by_branch: FloatArray,
) -> Path:
    """Write cell-centered properties and initial state for three PyLith branches.

    Parameters
    ----------
    path : str or pathlib.Path
        Destination filename for the PyLith SimpleDB.
    vertices_m : array_like
        Mesh coordinates in meters with shape ``(nvertices, 3)``.
    tetrahedra : array_like
        Zero-based tetrahedron vertex indices with shape ``(nelements, 4)``.
    youngs_modulus_pa_at_cells : array_like or float
        Unrelaxed Young's modulus in pascals, scalar or one value per cell.
    density_kg_m3 : float
        Uniform density in kilograms per cubic meter.
    poisson_ratio : float
        Uniform Poisson ratio in the stable isotropic range ``(-1, 0.5)``.
    viscosity_pa_s_by_branch : array_like
        Positive viscosities in pascal-seconds with shape ``(3,)`` or
        ``(3, nelements)``.
    shear_modulus_ratio_by_branch : array_like
        Positive branch fractions with shape ``(3,)`` or ``(3, nelements)``.
        Fractions may sum to at most one; PyLith assigns the remainder to its
        equilibrium spring.

    Returns
    -------
    pathlib.Path
        Path to the generalized Maxwell material SimpleDB file.

    Notes
    -----
    PyLith 5.0.2 implements three Maxwell branches. The caller must provide
    the branch viscosities and fractions; this function does not infer the
    paper's unresolved spectrum.
    """
    vertices = np.asarray(vertices_m, dtype=float)
    cells = np.asarray(tetrahedra, dtype=np.int64)
    modulus = np.asarray(youngs_modulus_pa_at_cells, dtype=float)
    viscosities = np.asarray(viscosity_pa_s_by_branch, dtype=float)
    ratios = np.asarray(shear_modulus_ratio_by_branch, dtype=float)
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

    expected_shape = (3, len(cells))
    if viscosities.shape == (3,):
        viscosities = np.broadcast_to(viscosities[:, np.newaxis], expected_shape)
    elif viscosities.shape != expected_shape:
        raise ValueError(
            "branch viscosities must have shape (3,) or (3, nelements)"
        )
    if not np.all(np.isfinite(viscosities)) or np.any(viscosities <= 0.0):
        raise ValueError("branch viscosities must be finite and positive")

    if ratios.shape == (3,):
        ratios = np.broadcast_to(ratios[:, np.newaxis], expected_shape)
    elif ratios.shape != expected_shape:
        raise ValueError("branch fractions must have shape (3,) or (3, nelements)")
    if not np.all(np.isfinite(ratios)) or np.any(ratios <= 0.0):
        raise ValueError("branch fractions must be finite and positive")
    if np.any(np.sum(ratios, axis=0) > 1.0):
        raise ValueError("branch fractions must sum to at most one in every cell")

    shear_velocity, compressional_velocity = _wave_speeds_km_s(
        modulus, density_kg_m3, poisson_ratio
    )
    centroids = vertices[cells].mean(axis=1)
    names = (
        "density",
        "vs",
        "vp",
        *(f"viscosity_{branch}" for branch in range(1, 4)),
        *(f"shear_modulus_ratio_{branch}" for branch in range(1, 4)),
        *(
            f"viscous_strain_{branch}_{component}"
            for branch in range(1, 4)
            for component in TENSOR_COMPONENTS
        ),
        *(f"total_strain_{component}" for component in TENSOR_COMPONENTS),
    )
    units = (
        "kg/m**3",
        "km/s",
        "km/s",
        *("Pa*s" for _ in range(3)),
        *("None" for _ in range(3 + 18 + 6)),
    )
    values = np.column_stack(
        (
            np.full(len(cells), density_kg_m3),
            shear_velocity,
            compressional_velocity,
            viscosities.T,
            ratios.T,
            np.zeros((len(cells), 24)),
        )
    )
    return write_simpledb(
        path,
        names,
        units,
        centroids,
        values,
    )


def write_temperature_dependent_generalized_maxwell_database(
    path: str | Path,
    vertices_m: FloatArray,
    tetrahedra: IntArray,
    temperature_c_at_vertices: FloatArray,
    youngs_modulus_pa_at_cells: FloatArray | float,
    *,
    density_kg_m3: float,
    poisson_ratio: float,
    reference_viscosity_pa_s_by_branch: FloatArray,
    reference_temperature_c: float,
    shear_modulus_ratio_by_branch: FloatArray,
    dorn_parameter_pa_s: float = 1.0e9,
    activation_energy_j_mol: float = 1.2e5,
    gas_constant_j_mol_k: float = 8.3114,
) -> Path:
    """Write three-branch properties with Arrhenius cellwise viscosities.

    Parameters
    ----------
    path : str or pathlib.Path
        Destination filename for the PyLith SimpleDB.
    vertices_m : array_like
        Mesh coordinates in meters with shape ``(nvertices, 3)``.
    tetrahedra : array_like
        Zero-based tetrahedron vertex indices with shape ``(nelements, 4)``.
    temperature_c_at_vertices : array_like
        Nodal steady temperatures in degrees Celsius.
    youngs_modulus_pa_at_cells : array_like or float
        Explicit unrelaxed modulus in pascals, scalar or one value per cell.
    density_kg_m3 : float
        Uniform density in kilograms per cubic meter.
    poisson_ratio : float
        Uniform Poisson ratio in the stable isotropic range ``(-1, 0.5)``.
    reference_viscosity_pa_s_by_branch : array_like
        Three synthetic branch viscosities at the reference temperature, in
        pascal-seconds. The paper's branch spectrum is not inferred.
    reference_temperature_c : float
        Temperature in degrees Celsius at which the supplied branch
        viscosities apply.
    shear_modulus_ratio_by_branch : array_like
        Positive shear fractions with shape ``(3,)`` or ``(3, nelements)``.
    dorn_parameter_pa_s : float
        Arrhenius Dorn parameter in pascal-seconds.
    activation_energy_j_mol : float
        Activation energy in joules per mole.
    gas_constant_j_mol_k : float
        Gas constant in joules per mole-kelvin.

    Returns
    -------
    pathlib.Path
        Path to the generalized Maxwell material SimpleDB file.

    Notes
    -----
    The Arrhenius temperature factor multiplies each caller-supplied branch
    viscosity. This verifies one-way thermal-to-material mapping without
    resolving the paper's branch spectrum or modulus law.
    """
    vertices = np.asarray(vertices_m, dtype=float)
    cells = np.asarray(tetrahedra, dtype=np.int64)
    temperatures = np.asarray(temperature_c_at_vertices, dtype=float)
    reference_viscosities = np.asarray(reference_viscosity_pa_s_by_branch, dtype=float)
    if vertices.ndim != 2 or vertices.shape[1] != 3 or len(vertices) < 4:
        raise ValueError("vertices must have shape (n, 3) with at least four points")
    if cells.ndim != 2 or cells.shape[1] != 4 or len(cells) == 0:
        raise ValueError("tetrahedra must have shape (m, 4) with at least one element")
    if np.any(cells < 0) or np.any(cells >= len(vertices)):
        raise ValueError("tetrahedra contain invalid vertex indices")
    if temperatures.shape != (len(vertices),) or not np.all(np.isfinite(temperatures)):
        raise ValueError("temperature must contain one finite value per mesh vertex")
    if reference_viscosities.shape != (3,):
        raise ValueError("reference viscosities must contain one value per branch")
    if not np.all(np.isfinite(reference_viscosities)) or np.any(
        reference_viscosities <= 0.0
    ):
        raise ValueError("reference branch viscosities must be finite and positive")
    if not np.isfinite(reference_temperature_c):
        raise ValueError("reference temperature must be finite")

    cell_temperature_c = temperatures[cells].mean(axis=1)
    cell_viscosity = temperature_dependent_viscosity_pa_s(
        cell_temperature_c,
        dorn_parameter_pa_s=dorn_parameter_pa_s,
        activation_energy_j_mol=activation_energy_j_mol,
        gas_constant_j_mol_k=gas_constant_j_mol_k,
    )
    reference_viscosity = temperature_dependent_viscosity_pa_s(
        reference_temperature_c,
        dorn_parameter_pa_s=dorn_parameter_pa_s,
        activation_energy_j_mol=activation_energy_j_mol,
        gas_constant_j_mol_k=gas_constant_j_mol_k,
    )
    viscosity_by_branch = reference_viscosities[:, np.newaxis] * (
        cell_viscosity / reference_viscosity
    )[np.newaxis, :]
    return write_generalized_maxwell_database(
        path,
        vertices,
        cells,
        youngs_modulus_pa_at_cells,
        density_kg_m3=density_kg_m3,
        poisson_ratio=poisson_ratio,
        viscosity_pa_s_by_branch=viscosity_by_branch,
        shear_modulus_ratio_by_branch=shear_modulus_ratio_by_branch,
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

    centroids = vertices[cells].mean(axis=1)
    cell_temperature = temperatures[cells].mean(axis=1)
    youngs_modulus = np.asarray(youngs_modulus_pa_at_cells, dtype=float)
    try:
        youngs_modulus = np.broadcast_to(youngs_modulus, (len(cells),))
    except ValueError as exc:
        raise ValueError("Young's modulus must be scalar or one value per tetrahedron") from exc
    if not np.all(np.isfinite(youngs_modulus)) or np.any(youngs_modulus <= 0.0):
        raise ValueError("Young's modulus must be finite and positive")

    shear_velocity_km_s, compressional_velocity_km_s = _wave_speeds_km_s(
        youngs_modulus, density_kg_m3, poisson_ratio
    )
    viscosity_pa_s = temperature_dependent_viscosity_pa_s(
        cell_temperature,
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
        return write_temperature_dependent_maxwell_database(
            database_path,
            archive["vertices_m"],
            archive["tetrahedra"],
            archive["temperature_c"],
            youngs_modulus_pa,
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
