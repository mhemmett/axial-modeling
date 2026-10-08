"""Export PyLith Maxwell state into spatial databases for same-mesh restarts."""

from __future__ import annotations

import argparse
from pathlib import Path

import h5py
import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]
TENSOR_COMPONENTS = ("xx", "yy", "zz", "xy", "yz", "xz")


def _write_simpledb(
    path: Path,
    names: tuple[str, ...],
    units: tuple[str, ...],
    coordinates: FloatArray,
    values: FloatArray,
) -> None:
    """Write a scattered 3D point database using PyLith's ASCII format."""
    if coordinates.ndim != 2 or coordinates.shape[1] != 3:
        raise ValueError("database coordinates must have shape (n, 3)")
    if values.shape != (coordinates.shape[0], len(names)):
        raise ValueError("database values do not match the coordinate and field counts")
    if len(names) != len(units) or coordinates.shape[0] == 0:
        raise ValueError("database fields and coordinates must be nonempty and consistent")
    if not np.all(np.isfinite(coordinates)) or not np.all(np.isfinite(values)):
        raise ValueError("database coordinates and values must be finite")

    path.parent.mkdir(parents=True, exist_ok=True)
    header = f"""#SPATIAL.ascii 1
SimpleDB {{
  num-values = {len(names)}
  value-names = {' '.join(names)}
  value-units = {' '.join(units)}
  num-locs = {coordinates.shape[0]}
  data-dim = 3
  space-dim = 3
  cs-data = cartesian {{
    to-meters = 1.0
    space-dim = 3
  }}
}}
"""
    with path.open("w", encoding="utf-8") as stream:
        stream.write(header)
        for coordinate, row in zip(coordinates, values, strict=True):
            fields = (*coordinate, *row)
            stream.write(" ".join(f"{value:.17e}" for value in fields) + "\n")


def _read_last_time(h5: h5py.File) -> float:
    """Return the final finite time value from a PyLith observer file."""
    time = np.asarray(h5["time"], dtype=float).reshape(-1)
    if time.size == 0 or not np.all(np.isfinite(time)):
        raise ValueError("PyLith HDF5 time field must contain finite values")
    return float(time[-1])


def write_maxwell_restart_databases(
    solution_h5: str | Path,
    material_h5: str | Path,
    output_dir: str | Path,
    *,
    prefix: str = "restart",
) -> tuple[Path, Path]:
    """Export displacement and Maxwell state fields from PyLith HDF5 output.

    The exported databases preserve values at vertices and tetrahedron
    centroids. Use them with the same mesh and nearest-point SimpleDB queries.
    ``cauchy_strain`` supplies the Maxwell ``total_strain`` state field.
    Interpolation to a different mesh is not verified by this utility.

    Parameters
    ----------
    solution_h5 : str or pathlib.Path
        PyLith domain observer file containing vertex displacement and mesh
        geometry.
    material_h5 : str or pathlib.Path
        PyLith material observer file containing viscous strain, total strain,
        cell topology, and geometry.
    output_dir : str or pathlib.Path
        Directory for the two SimpleDB files.
    prefix : str
        Filename prefix for the displacement and state databases.

    Returns
    -------
    tuple[pathlib.Path, pathlib.Path]
        Paths to the displacement and Maxwell-state databases.
    """
    solution_path = Path(solution_h5)
    material_path = Path(material_h5)
    destination = Path(output_dir)
    with h5py.File(solution_path, "r") as solution, h5py.File(
        material_path, "r"
    ) as material:
        solution_time = _read_last_time(solution)
        material_time = _read_last_time(material)
        if not np.isclose(solution_time, material_time, rtol=0.0, atol=1.0e-12):
            raise ValueError("solution and material observer files have different final times")

        vertices = np.asarray(solution["geometry/vertices"], dtype=float)
        material_vertices = np.asarray(material["geometry/vertices"], dtype=float)
        if vertices.shape != material_vertices.shape or not np.allclose(
            vertices, material_vertices, rtol=0.0, atol=1.0e-12
        ):
            raise ValueError("solution and material observer files use different vertices")

        displacement = np.asarray(solution["vertex_fields/displacement"][-1], dtype=float)
        if displacement.shape != vertices.shape:
            raise ValueError("displacement values do not match the mesh vertices")

        cells = np.asarray(material["viz/topology/cells"], dtype=int)
        if cells.ndim != 2 or cells.shape[1] != 4:
            raise ValueError("restart export currently requires a tetrahedral mesh")
        if np.any(cells < 0) or np.any(cells >= len(vertices)):
            raise ValueError("cell topology contains invalid vertex indices")
        centroids = vertices[cells].mean(axis=1)

        viscous_strain = np.asarray(material["cell_fields/viscous_strain"][-1], dtype=float)
        total_strain = np.asarray(material["cell_fields/cauchy_strain"][-1], dtype=float)
        expected_state_shape = (len(cells), len(TENSOR_COMPONENTS))
        if (
            viscous_strain.shape != expected_state_shape
            or total_strain.shape != expected_state_shape
        ):
            raise ValueError("Maxwell strain fields must have six values per tetrahedron")

    displacement_path = destination / f"{prefix}_displacement.spatialdb"
    _write_simpledb(
        displacement_path,
        ("displacement_x", "displacement_y", "displacement_z"),
        ("m", "m", "m"),
        vertices,
        displacement,
    )
    state_names = tuple(f"viscous_strain_{item}" for item in TENSOR_COMPONENTS) + tuple(
        f"total_strain_{item}" for item in TENSOR_COMPONENTS
    )
    state_path = destination / f"{prefix}_state.spatialdb"
    _write_simpledb(
        state_path,
        state_names,
        ("None",) * len(state_names),
        centroids,
        np.column_stack((viscous_strain, total_strain)),
    )
    return displacement_path, state_path


def main() -> None:
    """Export restart databases from a pair of PyLith HDF5 observer files."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("solution_h5", type=Path)
    parser.add_argument("material_h5", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--prefix", default="restart")
    args = parser.parse_args()
    displacement, state = write_maxwell_restart_databases(
        args.solution_h5,
        args.material_h5,
        args.output_dir,
        prefix=args.prefix,
    )
    print(f"displacement database: {displacement}")
    print(f"Maxwell state database: {state}")


if __name__ == "__main__":
    main()
