"""Thermal-property laws and a one-dimensional conduction verification solver.

Temperatures use degrees Celsius at the public interface. The Arrhenius
viscosity converts them to kelvin before evaluation. The printed Young's
modulus law is exposed separately because it conflicts with the supplement's
brittle and ductile descriptions; it is not a validated model property.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
from numpy.typing import NDArray
from scipy.integrate import solve_bvp

FloatArray = NDArray[np.float64]


def evaluate_eq16_youngs_modulus_pa(
    temperature_c: FloatArray | float,
    *,
    ductile_modulus_pa: float = 25.0e9,
    brittle_modulus_pa: float = 50.0e9,
    smoothing_exponent: float = 12.0,
    smoothing_coefficient: float = 5.0,
    magma_temperature_c: float = 1200.0,
) -> FloatArray:
    """Evaluate the Young's-modulus equation exactly as printed in Eq. 16.

    The result is an equation transcription, not an accepted property law:
    with the listed parameters it increases with temperature and conflicts with
    the supplement's labels for brittle and ductile moduli.

    Parameters
    ----------
    temperature_c : array_like or float
        Temperature in degrees Celsius.
    ductile_modulus_pa : float
        ``ED`` in pascals.
    brittle_modulus_pa : float
        ``EB`` in pascals.
    smoothing_exponent : float
        ``AS`` in Eq. 16.
    smoothing_coefficient : float
        ``CS`` in Eq. 16.
    magma_temperature_c : float
        ``Tmax`` in Eq. 16, in degrees Celsius.

    Returns
    -------
    numpy.ndarray
        Modulus values in pascals, with the input shape.
    """
    temperature = np.asarray(temperature_c, dtype=float)
    if not np.all(np.isfinite(temperature)):
        raise ValueError("temperature must contain only finite values")
    modulus_parameters = (ductile_modulus_pa, brittle_modulus_pa)
    if not np.all(np.isfinite(modulus_parameters)) or np.any(np.asarray(modulus_parameters) <= 0):
        raise ValueError("Young's modulus values must be positive")
    smoothing_parameters = (smoothing_exponent, smoothing_coefficient)
    if not np.all(np.isfinite(smoothing_parameters)) or np.any(
        np.asarray(smoothing_parameters) <= 0
    ):
        raise ValueError("smoothing parameters must be positive")
    if not np.isfinite(magma_temperature_c) or magma_temperature_c <= 0:
        raise ValueError("magma temperature must be positive")

    exponent = smoothing_exponent * (1.0 - temperature / magma_temperature_c)
    with np.errstate(over="raise", invalid="raise"):
        denominator = 1.0 + smoothing_coefficient * np.exp(exponent)
    return ductile_modulus_pa + brittle_modulus_pa / denominator


def temperature_dependent_viscosity_pa_s(
    temperature_c: FloatArray | float,
    *,
    dorn_parameter_pa_s: float = 1.0e9,
    activation_energy_j_mol: float = 1.2e5,
    gas_constant_j_mol_k: float = 8.3114,
) -> FloatArray:
    """Calculate the Arrhenius viscosity in Eq. 15, returning pascal-seconds.

    Parameters
    ----------
    temperature_c : array_like or float
        Temperature in degrees Celsius.
    dorn_parameter_pa_s : float
        Dorn parameter ``AD`` in pascal-seconds.
    activation_energy_j_mol : float
        Activation energy ``EA`` in joules per mole.
    gas_constant_j_mol_k : float
        Gas constant ``Rg`` in joules per mole-kelvin.

    Returns
    -------
    numpy.ndarray
        Viscosity values in pascal-seconds, with the input shape.
    """
    temperature = np.asarray(temperature_c, dtype=float)
    if not np.all(np.isfinite(temperature)):
        raise ValueError("temperature must contain only finite values")
    arrhenius_parameters = (dorn_parameter_pa_s, activation_energy_j_mol)
    if not np.all(np.isfinite(arrhenius_parameters)) or np.any(
        np.asarray(arrhenius_parameters) <= 0
    ):
        raise ValueError("Dorn parameter and activation energy must be positive")
    if not np.isfinite(gas_constant_j_mol_k) or gas_constant_j_mol_k <= 0:
        raise ValueError("gas constant must be positive")
    temperature_k = temperature + 273.15
    if np.any(temperature_k <= 0):
        raise ValueError("temperature must be above absolute zero")
    with np.errstate(over="raise", invalid="raise"):
        return dorn_parameter_pa_s * np.exp(
            activation_energy_j_mol / (gas_constant_j_mol_k * temperature_k)
        )


def hydrothermal_conductivity_w_mk(
    temperature_c: FloatArray | float,
    depth_m: FloatArray | float,
    *,
    reference_conductivity_w_mk: float = 3.0,
    nusselt_number: float = 8.0,
    smoothing_coefficient: float = 0.75,
    cutoff_temperature_c: float = 600.0,
    cutoff_depth_m: float = 6000.0,
) -> FloatArray:
    """Evaluate the hydrothermal conductivity relation in Eq. 22.

    Parameters
    ----------
    temperature_c : array_like or float
        Temperature in degrees Celsius.
    depth_m : array_like or float
        Positive-down depth in meters.
    reference_conductivity_w_mk : float
        Reference conductivity ``k0`` in watts per meter-kelvin.
    nusselt_number : float
        Conductivity enhancement parameter ``Nu``.
    smoothing_coefficient : float
        Smoothing factor ``A``.
    cutoff_temperature_c : float
        Temperature scale ``Tmax`` in degrees Celsius.
    cutoff_depth_m : float
        Depth scale ``zmax`` in meters.

    Returns
    -------
    numpy.ndarray
        Conductivity in watts per meter-kelvin, broadcast over temperature and
        depth inputs.
    """
    temperature, depth = np.broadcast_arrays(
        np.asarray(temperature_c, dtype=float), np.asarray(depth_m, dtype=float)
    )
    if not np.all(np.isfinite(temperature)) or not np.all(np.isfinite(depth)):
        raise ValueError("temperature and depth must contain only finite values")
    if np.any(depth < 0):
        raise ValueError("depth must be positive-down and nonnegative")
    conductivity_parameters = (reference_conductivity_w_mk, nusselt_number)
    if not np.all(np.isfinite(conductivity_parameters)) or np.any(
        np.asarray(conductivity_parameters) <= 0
    ) or nusselt_number < 1:
        raise ValueError("conductivity must be positive and Nusselt number at least one")
    if not np.isfinite(smoothing_coefficient) or smoothing_coefficient < 0:
        raise ValueError("smoothing coefficient must be nonnegative")
    cutoff_parameters = (cutoff_temperature_c, cutoff_depth_m)
    if not np.all(np.isfinite(cutoff_parameters)) or np.any(
        np.asarray(cutoff_parameters) <= 0
    ):
        raise ValueError("temperature and depth scales must be positive")

    with np.errstate(over="raise", invalid="raise"):
        temperature_weight = np.exp(
            smoothing_coefficient * (1.0 - temperature / cutoff_temperature_c)
        )
        depth_weight = np.exp(smoothing_coefficient * (1.0 - depth / cutoff_depth_m))
        result = reference_conductivity_w_mk * (
            1.0 + (nusselt_number - 1.0) * temperature_weight * depth_weight
        )
    if not np.all(np.isfinite(result)):
        raise ValueError("conductivity parameters produce non-finite values")
    return result


def solve_steady_1d_temperature(
    depth_m: FloatArray,
    *,
    surface_temperature_c: float,
    bottom_temperature_c: float,
    conductivity: Callable[[FloatArray, FloatArray], FloatArray],
    heat_production_w_m3: float = 0.0,
    tolerance: float = 1.0e-6,
) -> FloatArray:
    """Solve a one-dimensional steady conduction verification problem.

    The solver evaluates ``d/dz(k dT/dz) = -Q`` on a positive-down depth axis.
    It is a verification component, not a model of the paper's unspecified
    three-dimensional thermal boundaries.

    Parameters
    ----------
    depth_m : numpy.ndarray
        Strictly increasing depth coordinates from the surface, in meters.
    surface_temperature_c : float
        Dirichlet temperature at zero depth, in degrees Celsius.
    bottom_temperature_c : float
        Dirichlet temperature at the final depth, in degrees Celsius.
    conductivity : callable
        Function ``conductivity(temperature_c, depth_m)`` returning positive
        conductivity in watts per meter-kelvin. It must accept arrays.
    heat_production_w_m3 : float
        Uniform heat production ``Q`` in watts per cubic meter.
    tolerance : float
        Relative tolerance passed to SciPy's boundary-value solver.

    Returns
    -------
    numpy.ndarray
        Temperature at each input depth, in degrees Celsius.
    """
    depth = np.asarray(depth_m, dtype=float)
    if depth.ndim != 1 or depth.size < 3:
        raise ValueError("depth must be a one-dimensional array with at least 3 values")
    if not np.all(np.isfinite(depth)) or not np.all(np.diff(depth) > 0):
        raise ValueError("depth coordinates must be finite and strictly increasing")
    if depth[0] != 0.0 or depth[-1] <= 0:
        raise ValueError("depth coordinates must start at zero and extend downward")
    if not np.isfinite(surface_temperature_c) or not np.isfinite(bottom_temperature_c):
        raise ValueError("boundary temperatures must be finite")
    if not np.isfinite(heat_production_w_m3):
        raise ValueError("heat production must be finite")
    if not np.isfinite(tolerance) or tolerance <= 0:
        raise ValueError("tolerance must be positive")

    linear_temperature = np.linspace(surface_temperature_c, bottom_temperature_c, depth.size)
    initial_conductivity = np.asarray(conductivity(linear_temperature, depth), dtype=float)
    if initial_conductivity.ndim == 0:
        initial_conductivity = np.full_like(depth, initial_conductivity)
    try:
        initial_conductivity = np.broadcast_to(initial_conductivity, depth.shape)
    except ValueError as exc:
        raise ValueError("conductivity must return a scalar or one value per depth") from exc
    if not np.all(np.isfinite(initial_conductivity)) or np.any(initial_conductivity <= 0):
        raise ValueError("conductivity must be finite and positive")

    initial_flux = float(np.mean(initial_conductivity)) * (
        bottom_temperature_c - surface_temperature_c
    ) / depth[-1]
    initial_state = np.vstack((linear_temperature, np.full_like(depth, initial_flux)))

    def rhs(z_m: FloatArray, state: FloatArray) -> FloatArray:
        values = np.asarray(conductivity(state[0], z_m), dtype=float)
        if values.ndim == 0:
            values = np.full_like(z_m, values)
        try:
            values = np.broadcast_to(values, z_m.shape)
        except ValueError as exc:
            raise ValueError("conductivity must return a scalar or one value per depth") from exc
        if not np.all(np.isfinite(values)) or np.any(values <= 0):
            raise ValueError("conductivity must be finite and positive")
        return np.vstack((state[1] / values, np.full_like(z_m, -heat_production_w_m3)))

    def boundary_conditions(left: FloatArray, right: FloatArray) -> FloatArray:
        return np.array(
            [left[0] - surface_temperature_c, right[0] - bottom_temperature_c]
        )

    solution = solve_bvp(
        rhs,
        boundary_conditions,
        depth,
        initial_state,
        tol=tolerance,
        max_nodes=10000,
    )
    if not solution.success:
        raise RuntimeError(f"steady conduction solve failed: {solution.message}")
    return np.asarray(solution.sol(depth)[0], dtype=float)
