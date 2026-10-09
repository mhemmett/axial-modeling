"""Tests for linear viscoelastic pressure-history inversion."""

from __future__ import annotations

import numpy as np
import pytest

from axialstress.maxwell_pressure_inversion import (
    invert_pressure_history,
    ramp_response_operator,
)


def test_ramp_response_operator_maps_pressure_levels_to_uplift() -> None:
    response = np.asarray([0.2, 0.3, 0.4])
    pressure = np.asarray([1.0, 1.5, 1.0])
    expected = np.asarray(
        [
            0.2,
            0.3 + 0.2 * 0.5,
            0.4 + 0.3 * 0.5 + 0.2 * -0.5,
        ]
    )

    observed = ramp_response_operator(response) @ pressure

    np.testing.assert_allclose(observed, expected, rtol=0.0, atol=1.0e-14)


def test_pressure_inverse_recovers_linear_pressure_without_curvature() -> None:
    count = 24
    kernel = 0.02 + 0.001 * np.arange(count)
    response = ramp_response_operator(kernel)
    expected_pressure = np.linspace(0.1, 2.4, count)
    observed = response @ expected_pressure

    result = invert_pressure_history(response, observed)

    np.testing.assert_allclose(result.pressure_mpa, expected_pressure, atol=1.0e-8)
    assert result.rmse_m < 1.0e-10
    assert result.effective_parameters < count


def test_pressure_inverse_smooths_measurement_noise() -> None:
    count = 36
    time = np.linspace(0.0, 1.0, count)
    kernel = 0.03 + 0.001 * np.arange(count)
    response = ramp_response_operator(kernel)
    expected_pressure = 8.0 * time + 0.4 * np.sin(2.0 * np.pi * time)
    clean_uplift = response @ expected_pressure
    noisy_uplift = clean_uplift + 0.002 * np.sin(19.0 * np.pi * time)

    result = invert_pressure_history(response, noisy_uplift)

    assert np.all(np.isfinite(result.pressure_mpa))
    assert result.regularization > 0.0
    assert result.rmse_m < 0.002
    assert np.max(np.abs(np.diff(result.pressure_mpa, n=2))) < 0.2


@pytest.mark.parametrize(
    "response, uplift",
    [
        (np.ones((4, 4)), np.ones(4)),
        (np.ones((5, 4)), np.ones(5)),
        (np.full((5, 5), np.nan), np.ones(5)),
    ],
)
def test_pressure_inverse_rejects_invalid_shapes_and_values(
    response: np.ndarray, uplift: np.ndarray
) -> None:
    with pytest.raises(ValueError):
        invert_pressure_history(response, uplift)


def test_ramp_response_operator_rejects_nonpositive_initial_response() -> None:
    with pytest.raises(ValueError, match="first ramp response"):
        ramp_response_operator(np.asarray([0.0, 0.1]))
