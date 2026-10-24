"""Check datum removal and identifiability in Center pressure inversion."""

from __future__ import annotations

import numpy as np
import pytest

from axialstress.deployment_pressure import (
    DepthObservation,
    UpliftConstraint,
    fit_deployment_relative_pressure,
)


def test_pressure_fit_is_invariant_to_deployment_datums() -> None:
    response = np.diag(np.asarray([0.0] + [0.02] * 8))
    expected = np.linspace(0.0, 4.0, 9)
    sites = (("early", 0, 5, 1515.0), ("late", 4, 9, 1520.0))

    def observations(offset_m: float) -> list[DepthObservation]:
        return [
            DepthObservation(
                deployment,
                index,
                datum + (offset_m if deployment == "late" else 0.0) - (response @ expected)[index],
            )
            for deployment, start, stop, datum in sites
            for index in range(start, stop)
        ]

    baseline = fit_deployment_relative_pressure(response, observations(0.0))
    shifted = fit_deployment_relative_pressure(response, observations(12.0))

    np.testing.assert_allclose(baseline.pressure_mpa, shifted.pressure_mpa, atol=1e-9)
    np.testing.assert_allclose(baseline.pressure_mpa, expected, atol=1e-9)
    assert baseline.rmse_m < 1e-10


def test_gap_pressure_requires_regularization() -> None:
    response = np.diag(np.asarray([0.0] + [0.02] * 9))
    observations = [
        DepthObservation("first", index, 1515.0 - 0.02 * index) for index in range(3)
    ] + [DepthObservation("second", index, 1520.0 - 0.02 * index) for index in range(7, 10)]

    with pytest.raises(ValueError, match="not identified"):
        fit_deployment_relative_pressure(response, observations, curvature_weight=0.0)
    result = fit_deployment_relative_pressure(response, observations)
    assert result.design_rank < len(result.pressure_mpa) - 1
    assert np.all(np.isfinite(result.pressure_mpa))


def test_explicit_gap_uplift_changes_pressure_without_becoming_an_observation() -> None:
    response = np.diag(np.asarray([0.0] + [0.02] * 9))
    observations = [
        DepthObservation("first", index, 1515.0 - 0.02 * index) for index in range(3)
    ] + [
        DepthObservation("second", index, 1520.0 - 0.02 * index)
        for index in range(7, 10)
    ]
    constraint = UpliftConstraint(2, 7, 0.4)
    result = fit_deployment_relative_pressure(
        response, observations, uplift_constraint=constraint,
    )

    modeled_uplift = response @ result.pressure_mpa
    assert modeled_uplift[7] - modeled_uplift[2] == pytest.approx(0.4, abs=1e-9)
    assert len(result.observed_relative_uplift_m) == len(observations) - 2
    assert result.rmse_m < 0.02


def test_pressure_fit_rejects_duplicate_grid_samples() -> None:
    response = np.diag(np.asarray([0.0, 0.02, 0.02]))
    with pytest.raises(ValueError, match="distinct grid samples"):
        fit_deployment_relative_pressure(
            response,
            [DepthObservation("a", 1, 1515.0), DepthObservation("a", 1, 1515.0)],
        )
