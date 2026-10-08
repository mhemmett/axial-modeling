"""Analytical elastic references used to verify numerical mechanics."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]


def mogi_surface_displacement_m(
    x_m: FloatArray | float,
    y_m: FloatArray | float,
    *,
    source_depth_m: float,
    source_radius_m: float,
    pressure_change_pa: FloatArray | float,
    bulk_modulus_pa: float,
    shear_modulus_pa: float,
) -> FloatArray:
    """Calculate the elastic half-space displacement above a spherical source.

    Parameters
    ----------
    x_m, y_m : array_like or float
        Surface coordinates relative to the source axis, in meters.
    source_depth_m : float
        Positive-down depth to the source center, in meters.
    source_radius_m : float
        Spherical source radius, in meters.
    pressure_change_pa : array_like or float
        Pressure change in pascals; positive values represent inflation.
    bulk_modulus_pa : float
        Host-rock bulk modulus in pascals.
    shear_modulus_pa : float
        Host-rock shear modulus in pascals.

    Returns
    -------
    numpy.ndarray
        Displacement components ``(u_x, u_y, u_z)`` in meters, with the last
        axis containing the three Cartesian components.

    Notes
    -----
    This is the homogeneous elastic spherical-source reference in Eqs. 1–2 of
    ``docs/model_specification.md``. It is an analytical benchmark and does
    not account for a finite mesh, ellipsoidal reservoir, layering, or
    viscoelastic response.
    """
    x, y, pressure = np.broadcast_arrays(
        np.asarray(x_m, dtype=float),
        np.asarray(y_m, dtype=float),
        np.asarray(pressure_change_pa, dtype=float),
    )
    if not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)):
        raise ValueError("surface coordinates must be finite")
    if not np.all(np.isfinite(pressure)):
        raise ValueError("pressure change must be finite")
    source_parameters = (source_depth_m, source_radius_m)
    if not np.all(np.isfinite(source_parameters)) or np.any(
        np.asarray(source_parameters) <= 0.0
    ):
        raise ValueError("source depth and radius must be finite and positive")
    elastic_parameters = (bulk_modulus_pa, shear_modulus_pa)
    if not np.all(np.isfinite(elastic_parameters)) or np.any(
        np.asarray(elastic_parameters) <= 0.0
    ):
        raise ValueError("bulk and shear moduli must be finite and positive")

    distance = np.hypot(np.hypot(x, y), source_depth_m)
    compliance = (3.0 * bulk_modulus_pa + 4.0 * shear_modulus_pa) / (
        2.0 * shear_modulus_pa * (3.0 * bulk_modulus_pa + shear_modulus_pa)
    )
    with np.errstate(over="raise", invalid="raise", divide="raise"):
        amplitude = pressure * source_radius_m**3 * compliance / distance**3
        displacement = np.stack(
        (amplitude * x, amplitude * y, amplitude * source_depth_m), axis=-1
        )
    if not np.all(np.isfinite(displacement)):
        raise ValueError("parameters produce non-finite displacement")
    return displacement
