"""Read displacement and stress arrays from PyLith HDF5 output."""

from __future__ import annotations

from pathlib import Path

import h5py
import numpy as np


def read_field(filename: str | Path, field: str) -> np.ndarray:
    """Read the final time slice of a PyLith vertex or cell field.

    Parameters
    ----------
    filename : str or pathlib.Path
        PyLith HDF5 output file.
    field : str
        Dataset name, such as ``displacement`` or ``cauchy_stress``.

    Returns
    -------
    numpy.ndarray
        Field values from the last stored time step.

    Raises
    ------
    KeyError
        If the requested field is not present in a vertex or cell field group.
    """
    with h5py.File(filename, "r") as h5file:
        for group_name in ("vertex_fields", "cell_fields"):
            path = f"{group_name}/{field}"
            if path in h5file:
                values = np.asarray(h5file[path])
                if values.ndim >= 3:
                    return values[-1]
                if values.ndim == 2 and "time" in h5file and values.shape[0] == len(h5file["time"]):
                    return values[-1]
                return values
    raise KeyError(f"field {field!r} was not found in {filename}")


def read_vertices(filename: str | Path) -> np.ndarray:
    """Read mesh coordinates from a PyLith HDF5 output file, in meters.

    Parameters
    ----------
    filename : str or pathlib.Path
        PyLith HDF5 output file containing a ``geometry/vertices`` dataset.

    Returns
    -------
    numpy.ndarray
        Vertex coordinates with shape ``(nvertices, 3)``.
    """
    with h5py.File(filename, "r") as h5file:
        return np.asarray(h5file["geometry/vertices"])
