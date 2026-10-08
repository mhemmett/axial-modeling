"""Thermal-property preparation for PyLith spatial databases.

PyLith does not evaluate Young's modulus or viscosity as functions of
temperature during its mechanics solve. Phase 3 will compute a geotherm and
write spatially varying properties before PyLith starts.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np


def write_property_database(
    coordinates_m: np.ndarray,
    youngs_modulus_pa: np.ndarray,
    viscosity_pa_s: np.ndarray,
    output: str | Path,
) -> None:
    """Write temperature-dependent properties to a PyLith spatial database.

    Parameters
    ----------
    coordinates_m : numpy.ndarray
        Grid coordinates in meters.
    youngs_modulus_pa : numpy.ndarray
        Young's modulus values in pascals.
    viscosity_pa_s : numpy.ndarray
        Viscosity values in pascal-seconds.
    output : str or pathlib.Path
        Destination SimpleGridDB path.

    Notes
    -----
    The SimpleGridDB writer and constitutive-property mapping are deferred until
    Phase 3 because the published thermal tables remain unverified.
    """
    del coordinates_m, youngs_modulus_pa, viscosity_pa_s, output
    raise NotImplementedError("temperature-property database generation is a Phase 3 task")
