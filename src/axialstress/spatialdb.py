"""Write ASCII SimpleDB files for PyLith spatial fields."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]


def write_simpledb(
    path: str | Path,
    value_names: tuple[str, ...],
    value_units: tuple[str, ...],
    coordinates_m: FloatArray,
    values: FloatArray,
) -> Path:
    """Write finite three-dimensional point data in PyLith ASCII format.

    Parameters
    ----------
    path : str or pathlib.Path
        Destination filename.
    value_names : tuple of str
        PyLith field names, one per value column.
    value_units : tuple of str
        Units corresponding to ``value_names``.
    coordinates_m : array_like
        Point coordinates in meters with shape ``(npoints, 3)``.
    values : array_like
        Field values with shape ``(npoints, len(value_names))``.

    Returns
    -------
    pathlib.Path
        Path to the written SimpleDB file.
    """
    destination = Path(path)
    coordinates = np.asarray(coordinates_m, dtype=float)
    field_values = np.asarray(values, dtype=float)
    if coordinates.ndim != 2 or coordinates.shape[1] != 3:
        raise ValueError("database coordinates must have shape (n, 3)")
    if field_values.shape != (coordinates.shape[0], len(value_names)):
        raise ValueError("database values do not match the coordinate and field counts")
    if not value_names or len(value_names) != len(value_units) or coordinates.shape[0] == 0:
        raise ValueError("database fields and coordinates must be nonempty and consistent")
    if not np.all(np.isfinite(coordinates)) or not np.all(np.isfinite(field_values)):
        raise ValueError("database coordinates and values must be finite")

    destination.parent.mkdir(parents=True, exist_ok=True)
    header = f"""#SPATIAL.ascii 1
SimpleDB {{
  num-values = {len(value_names)}
  value-names = {' '.join(value_names)}
  value-units = {' '.join(value_units)}
  num-locs = {coordinates.shape[0]}
  data-dim = 3
  space-dim = 3
  cs-data = cartesian {{
    to-meters = 1.0
    space-dim = 3
  }}
}}
"""
    with destination.open("w", encoding="utf-8") as stream:
        stream.write(header)
        for coordinate, row in zip(coordinates, field_values, strict=True):
            fields = (*coordinate, *row)
            stream.write(" ".join(f"{value:.17e}" for value in fields) + "\n")
    return destination
