"""Checks for the Winkler boundary-condition sign and units."""

import pytest

from axialstress.winkler import bottom_normal_traction_pa


@pytest.mark.parametrize(
    ("displacement_m", "expected_pa"),
    [(0.0, 0.0), (0.2, 1_000.0), (-0.2, -1_000.0)],
)
def test_bottom_normal_traction_uses_restoring_sign(
    displacement_m: float,
    expected_pa: float,
) -> None:
    """Positive upward base motion produces downward restoring traction."""
    assert bottom_normal_traction_pa(displacement_m, 5_000.0) == expected_pa


def test_bottom_normal_traction_converts_global_offset() -> None:
    """The bottom-normal offset has the opposite sign from global vertical."""
    assert bottom_normal_traction_pa(0.2, 5_000.0, 250.0) == 750.0


@pytest.mark.parametrize(
    ("displacement_m", "stiffness_pa_per_m", "offset_pa"),
    [(float("nan"), 1.0, 0.0), (0.0, float("inf"), 0.0), (0.0, 1.0, float("nan"))],
)
def test_bottom_normal_traction_rejects_non_finite_values(
    displacement_m: float,
    stiffness_pa_per_m: float,
    offset_pa: float,
) -> None:
    """The boundary kernel rejects non-finite inputs."""
    with pytest.raises(ValueError, match="must be finite"):
        bottom_normal_traction_pa(displacement_m, stiffness_pa_per_m, offset_pa)


def test_bottom_normal_traction_rejects_negative_stiffness() -> None:
    """A negative restoring stiffness is physically invalid."""
    with pytest.raises(ValueError, match="must be nonnegative"):
        bottom_normal_traction_pa(0.0, -1.0)
