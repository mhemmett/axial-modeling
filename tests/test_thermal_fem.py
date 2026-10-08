"""Tests for the linear-tetrahedron steady heat solver."""

import numpy as np
import pytest

from axialstress.thermal_fem import solve_steady_temperature_tetrahedral


@pytest.fixture
def cube_mesh() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    axis = np.linspace(0.0, 1.0, 3)
    vertices = np.array([(x, y, z) for x in axis for y in axis for z in axis])

    def node(i: int, j: int, k: int) -> int:
        return 9 * i + 3 * j + k

    tetrahedra = []
    for i in range(2):
        for j in range(2):
            for k in range(2):
                cube = [
                    node(i, j, k),
                    node(i + 1, j, k),
                    node(i, j + 1, k),
                    node(i + 1, j + 1, k),
                    node(i, j, k + 1),
                    node(i + 1, j, k + 1),
                    node(i, j + 1, k + 1),
                    node(i + 1, j + 1, k + 1),
                ]
                tetrahedra.extend(
                    [
                        [cube[0], cube[1], cube[3], cube[7]],
                        [cube[0], cube[3], cube[2], cube[7]],
                        [cube[0], cube[2], cube[6], cube[7]],
                        [cube[0], cube[6], cube[4], cube[7]],
                        [cube[0], cube[4], cube[5], cube[7]],
                        [cube[0], cube[5], cube[1], cube[7]],
                    ]
                )
    return vertices, np.asarray(tetrahedra), 1.0 - vertices[:, 2]


def test_recovers_linear_geotherm_for_constant_conductivity(
    cube_mesh: tuple[np.ndarray, np.ndarray, np.ndarray],
) -> None:
    vertices, cells, depth = cube_mesh
    boundary = {
        **{int(i): 10.0 for i in np.flatnonzero(vertices[:, 2] == 1.0)},
        **{int(i): 110.0 for i in np.flatnonzero(vertices[:, 2] == 0.0)},
    }

    solution = solve_steady_temperature_tetrahedral(
        vertices,
        cells,
        depth,
        boundary,
        conductivity=lambda temperature, depth_m: 3.0,
    )

    np.testing.assert_allclose(solution.temperature_c, 10.0 + 100.0 * depth, atol=1.0e-10)
    assert solution.iterations <= 3


def test_variable_conductivity_solution_is_finite_and_respects_boundaries(
    cube_mesh: tuple[np.ndarray, np.ndarray, np.ndarray],
) -> None:
    vertices, cells, depth = cube_mesh
    boundary = {
        **{int(i): 0.0 for i in np.flatnonzero(vertices[:, 2] == 1.0)},
        **{int(i): 100.0 for i in np.flatnonzero(vertices[:, 2] == 0.0)},
    }

    solution = solve_steady_temperature_tetrahedral(
        vertices,
        cells,
        depth,
        boundary,
        conductivity=lambda temperature, depth_m: 2.0 + 0.01 * temperature + 0.1 * depth_m,
    )

    assert np.all(np.isfinite(solution.temperature_c))
    assert np.all((solution.temperature_c >= 0.0) & (solution.temperature_c <= 100.0))
    assert solution.relative_change <= 1.0e-9


def test_uniform_heat_production_matches_the_one_dimensional_solution(
    cube_mesh: tuple[np.ndarray, np.ndarray, np.ndarray],
) -> None:
    vertices, cells, depth = cube_mesh
    boundary = {
        **{int(i): 0.0 for i in np.flatnonzero(vertices[:, 2] == 1.0)},
        **{int(i): 0.0 for i in np.flatnonzero(vertices[:, 2] == 0.0)},
    }

    solution = solve_steady_temperature_tetrahedral(
        vertices,
        cells,
        depth,
        boundary,
        conductivity=lambda temperature, depth_m: 2.0,
        heat_production_w_m3=8.0,
    )

    center = np.flatnonzero(np.all(vertices == [0.5, 0.5, 0.5], axis=1))[0]
    assert solution.temperature_c[center] == pytest.approx(0.5, abs=1.0e-10)


def test_rejects_degenerate_tetrahedron() -> None:
    vertices = np.array(
        [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [1.0, 1.0, 0.0]]
    )

    with pytest.raises(ValueError, match="nonzero volume"):
        solve_steady_temperature_tetrahedral(
            vertices,
            np.array([[0, 1, 2, 3]]),
            np.zeros(4),
            {0: 0.0},
            conductivity=lambda temperature, depth_m: 1.0,
        )
