"""Invert a linear viscoelastic pressure history from its ramp response."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]


@dataclass(frozen=True)
class PressureInversion:
    """Regularized pressure history and its center-site fit diagnostics."""

    pressure_mpa: FloatArray
    predicted_uplift_m: FloatArray
    regularization: float
    effective_parameters: float
    rmse_m: float


def ramp_response_operator(ramp_response_m: FloatArray) -> FloatArray:
    """Build a pressure-to-uplift matrix from one PyLith ramp response.

    Parameters
    ----------
    ramp_response_m : array_like
        Center uplift, in meters, at successive equal intervals after pressure
        ramps from zero to one megapascal during the first interval and then
        remains at one megapascal. The first value is the response at the end
        of that first interval.

    Returns
    -------
    numpy.ndarray
        Matrix mapping pressure levels at the interval endpoints, in MPa, to
        uplift at those endpoints, in meters. Pressure is zero at the initial
        baseline time.

    Notes
    -----
    Linear Maxwell mechanics obeys superposition for fixed material fields,
    geometry, and boundary conditions. Each successive pressure increment is
    represented by a shifted copy of the unit ramp response. The returned
    operator therefore reproduces the discrete piecewise-linear pressure
    history used by the time-history database.
    """
    response = np.asarray(ramp_response_m, dtype=float)
    if response.ndim != 1 or len(response) < 2 or not np.all(np.isfinite(response)):
        raise ValueError("ramp response must contain at least two finite samples")
    if response[0] <= 0.0:
        raise ValueError("the first ramp response must be positive")

    count = len(response)
    increment_operator = np.eye(count, dtype=float)
    increment_operator[np.arange(1, count), np.arange(count - 1)] = -1.0
    uplift_from_increments = np.zeros((count, count), dtype=float)
    for row in range(count):
        uplift_from_increments[row, : row + 1] = response[row::-1]
    return uplift_from_increments @ increment_operator


def invert_pressure_history(
    pressure_to_uplift_m_per_mpa: FloatArray,
    observed_uplift_m: FloatArray,
) -> PressureInversion:
    """Fit pressure to a center uplift history with GCV-selected smoothing.

    Parameters
    ----------
    pressure_to_uplift_m_per_mpa : array_like
        Square response matrix mapping pressure levels to uplift, in meters
        per megapascal.
    observed_uplift_m : array_like
        Finite observed uplift at the same equally spaced interval endpoints,
        in meters. The initial zero-baseline sample is excluded.

    Returns
    -------
    PressureInversion
        Pressure in MPa, model-fit uplift in meters, selected dimensionless
        smoothing strength, effective fit degrees of freedom, and RMSE.

    Notes
    -----
    The generalized cross-validation score selects the coefficient on the
    squared second difference of pressure. This limits amplification of
    observation-scale variability without using the held-out station. The
    penalty is a stated inverse-problem assumption, not a source-specified
    pressure prior.
    """
    response = np.asarray(pressure_to_uplift_m_per_mpa, dtype=float)
    observed = np.asarray(observed_uplift_m, dtype=float)
    if (
        response.ndim != 2
        or response.shape[0] != response.shape[1]
        or response.shape[0] < 5
        or observed.shape != (response.shape[0],)
    ):
        raise ValueError("response matrix and uplift series must be matched square data")
    if not np.all(np.isfinite(response)) or not np.all(np.isfinite(observed)):
        raise ValueError("response matrix and uplift series must be finite")
    if np.any(np.diag(response) <= 0.0):
        raise ValueError("response matrix must have positive diagonal compliance")

    count = len(observed)
    uplift_scale_m = max(float(np.std(observed)), float(np.max(np.abs(observed))) * 1.0e-6)
    pressure_scale_mpa = uplift_scale_m / float(np.median(np.diag(response)))
    design = response * pressure_scale_mpa / uplift_scale_m
    target = observed / uplift_scale_m
    curvature = np.zeros((count - 2, count), dtype=float)
    rows = np.arange(count - 2)
    curvature[rows, rows] = 1.0
    curvature[rows, rows + 1] = -2.0
    curvature[rows, rows + 2] = 1.0
    normal_data = design.T @ design
    normal_smoothing = curvature.T @ curvature
    rhs = design.T @ target

    candidates = np.concatenate(([0.0], np.logspace(-8.0, 8.0, 81)))
    best_score = float("inf")
    best_result: tuple[float, FloatArray, float] | None = None
    for regularization in candidates:
        normal = normal_data + regularization * normal_smoothing
        try:
            scaled_pressure = np.linalg.solve(normal, rhs)
            influence = np.linalg.solve(normal, normal_data)
        except np.linalg.LinAlgError:
            continue
        residual = target - design @ scaled_pressure
        effective_parameters = float(np.trace(influence))
        denominator = count - effective_parameters
        if denominator <= np.finfo(float).eps:
            continue
        score = float(np.dot(residual, residual) / denominator**2)
        if score < best_score:
            best_score = score
            best_result = (float(regularization), scaled_pressure, effective_parameters)

    if best_result is None:
        raise ValueError("pressure inversion could not find a finite GCV solution")
    regularization, scaled_pressure, effective_parameters = best_result
    pressure = scaled_pressure * pressure_scale_mpa
    predicted = response @ pressure
    rmse = float(np.sqrt(np.mean((predicted - observed) ** 2)))
    return PressureInversion(
        pressure_mpa=pressure,
        predicted_uplift_m=predicted,
        regularization=regularization,
        effective_parameters=effective_parameters,
        rmse_m=rmse,
    )
