"""Read a PyLith unit-pressure surface displacement response."""

from __future__ import annotations

from pathlib import Path

import h5py
import numpy as np
from numpy.typing import NDArray

from axialstress.coordinates import (
    CENTRAL_CALDERA_LAT_LON_DEG,
    EAST_CALDERA_LAT_LON_DEG,
    local_east_north_offset_m,
)
from axialstress.surface_interpolation import interpolate_triangular_surface

FloatArray = NDArray[np.float64]


def read_ellipsoid_unit_response(
    surface_hdf5: Path,
    *,
    central_xy_m: tuple[float, float] = (0.0, 0.0),
    east_xy_m: tuple[float, float] | None = None,
) -> tuple[FloatArray, FloatArray]:
    """Interpolate final surface displacement at two fixed model locations."""
    if east_xy_m is None:
        east_offset, north_offset = local_east_north_offset_m(
            EAST_CALDERA_LAT_LON_DEG[0],
            EAST_CALDERA_LAT_LON_DEG[1],
            origin_latitude_deg=CENTRAL_CALDERA_LAT_LON_DEG[0],
            origin_longitude_deg=CENTRAL_CALDERA_LAT_LON_DEG[1],
        )
        east_xy_m = (east_offset, north_offset)
    with h5py.File(surface_hdf5, "r") as surface:
        required = (
            "time",
            "geometry/vertices",
            "viz/topology/cells",
            "vertex_fields/displacement",
        )
        if any(name not in surface for name in required):
            raise ValueError(f"PyLith surface file is missing a required dataset: {surface_hdf5}")
        output_times = np.asarray(surface["time"], dtype=float).reshape(-1)
        vertices = np.asarray(surface["geometry/vertices"], dtype=float)
        cells = np.asarray(surface["viz/topology/cells"], dtype=np.int64)
        displacement = np.asarray(surface["vertex_fields/displacement"], dtype=float)
    if not len(output_times) or not np.isclose(output_times[-1], 1.0, rtol=0.0, atol=1.0e-12):
        raise ValueError("PyLith unit-response output did not reach the configured 1 s end time")
    if displacement.ndim == 3:
        displacement = displacement[-1]
    if displacement.shape != vertices.shape:
        raise ValueError("surface displacement shape does not match its vertices")
    if not np.all(np.isfinite(displacement)):
        raise ValueError("surface displacement contains non-finite values")
    if not np.allclose(vertices[:, 2], vertices[0, 2], rtol=0.0, atol=1.0e-7):
        raise ValueError("surface interpolation expects a horizontal PyLith boundary")
    central = interpolate_triangular_surface(vertices, cells, displacement, central_xy_m)
    east = interpolate_triangular_surface(vertices, cells, displacement, east_xy_m)
    return np.asarray(central, dtype=float), np.asarray(east, dtype=float)
