"""Tests for barycentric interpolation on triangular surface meshes."""

import numpy as np
import pytest

from axialstress.surface_interpolation import interpolate_triangular_surface


def test_interpolates_affine_vector_field_inside_triangle() -> None:
    vertices = np.array(
        [[0.0, 0.0, 0.0], [2.0, 0.0, 0.0], [0.0, 2.0, 0.0]],
    )
    values = np.column_stack((vertices[:, 0] + vertices[:, 1], 2.0 * vertices[:, 0]))

    result = interpolate_triangular_surface(
        vertices,
        np.array([[0, 1, 2]]),
        values,
        (0.5, 0.75),
    )

    np.testing.assert_allclose(result, [1.25, 1.0])


def test_interpolates_point_on_shared_edge() -> None:
    vertices = np.array(
        [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0]],
    )
    values = vertices[:, 0] + 3.0 * vertices[:, 1]

    result = interpolate_triangular_surface(
        vertices,
        np.array([[0, 1, 2], [0, 2, 3]]),
        values,
        (0.5, 0.5),
    )

    np.testing.assert_allclose(result, [2.0])


def test_rejects_points_outside_the_surface() -> None:
    vertices = np.array(
        [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
    )
    with pytest.raises(ValueError, match="outside"):
        interpolate_triangular_surface(
            vertices,
            np.array([[0, 1, 2]]),
            np.ones(3),
            (1.0, 1.0),
        )
