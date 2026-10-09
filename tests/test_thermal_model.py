"""Checks for thermal-model boundary construction."""

import numpy as np
import pytest

from axialstress.thermal_model import geothermal_dirichlet_conditions


def test_geothermal_boundaries_use_depth_and_reservoir_temperature() -> None:
    vertices = np.array(
        [
            [0.0, 0.0, 0.0],
            [0.0, 0.0, -20_000.0],
            [-1000.0, 0.0, -5000.0],
            [0.0, -1000.0, -3000.0],
            [0.0, 1000.0, -3000.0],
            [0.0, 0.0, -1600.0],
        ]
    )
    boundaries = {
        "top": [0],
        "bottom": [1],
        "x_neg": [2],
        "x_pos": [2],
        "y_neg": [3],
        "y_pos": [4],
        "cavity": [5],
    }

    conditions = geothermal_dirichlet_conditions(vertices, boundaries)

    assert conditions == {0: 0.0, 1: 600.0, 2: 150.0, 3: 90.0, 4: 90.0, 5: 1200.0}


def test_geothermal_boundaries_reject_reservoir_overlap() -> None:
    vertices = np.array(
        [
            [0.0, 0.0, 0.0],
            [0.0, 0.0, -1000.0],
            [0.0, 0.0, -2000.0],
            [0.0, 0.0, -3000.0],
        ]
    )
    boundaries = {
        "top": [0],
        "bottom": [1],
        "x_neg": [2],
        "x_pos": [2],
        "y_neg": [3],
        "y_pos": [3],
        "cavity": [2],
    }

    with pytest.raises(ValueError, match="overlap"):
        geothermal_dirichlet_conditions(vertices, boundaries)


def test_geothermal_boundaries_reject_missing_physical_groups() -> None:
    vertices = np.zeros((4, 3))
    boundaries = {name: [0] for name in ("top", "bottom", "x_neg", "x_pos", "y_neg", "cavity")}

    with pytest.raises(ValueError, match="missing=.*y_pos"):
        geothermal_dirichlet_conditions(vertices, boundaries)
