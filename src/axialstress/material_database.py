"""Build initial PyLith Maxwell material databases from temperature fields."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from axialstress.spatialdb import write_simpledb
from axialstress.thermal import temperature_dependent_viscosity_pa_s

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]
TENSOR_COMPONENTS = ("xx", "yy", "zz", "xy", "yz", "xz")


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

    shear_modulus = youngs_modulus / (2.0 * (1.0 + poisson_ratio))
    bulk_modulus = youngs_modulus / (3.0 * (1.0 - 2.0 * poisson_ratio))
    shear_velocity_km_s = np.sqrt(shear_modulus / density_kg_m3) / 1000.0
    compressional_velocity_km_s = np.sqrt(
        (bulk_modulus + 4.0 * shear_modulus / 3.0) / density_kg_m3
    ) / 1000.0
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
