"""Check closed-surface volume against analytic tetrahedron deformation."""

import numpy as np
import pytest

from axialstress.cavity_volume import cavity_volume_history, orient_closed_cavity


def tetrahedron():
    vertices = np.array([
        [0.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, 0.0, 1.0],
    ])
    faces = np.array([
        [0, 1, 2], [0, 1, 3], [0, 2, 3], [1, 2, 3],
    ])
    return vertices, faces


def test_uniform_expansion_matches_exact_and_first_order_volume() -> None:
    vertices, faces = tetrahedron()
    displacement = np.stack([np.zeros_like(vertices), 0.1 * vertices])
    history = cavity_volume_history(vertices, faces, displacement)
    assert history["reference_volume_m3"] == pytest.approx(1.0 / 6.0)
    assert history["geometric_change_m3"] == pytest.approx(
        [0.0, (1.1**3 - 1.0) / 6.0]
    )
    assert history["first_order_change_m3"] == pytest.approx([0.0, 0.05])


def test_translation_does_not_change_closed_cavity_volume() -> None:
    vertices, faces = tetrahedron()
    displacement = np.broadcast_to([3.0, -2.0, 7.0], (1, 4, 3))
    history = cavity_volume_history(vertices, faces, displacement)
    assert history["geometric_change_m3"][0] == pytest.approx(0.0, abs=1e-14)
    assert history["first_order_change_m3"][0] == pytest.approx(0.0, abs=1e-14)


def test_rejects_extra_triangle_that_makes_surface_non_manifold() -> None:
    vertices, faces = tetrahedron()
    with pytest.raises(ValueError, match="non-manifold"):
        orient_closed_cavity(vertices, np.vstack([faces, faces[0]]))
