"""Tests for OOI calibration of the PyLith ellipsoid compliance response."""

from datetime import UTC, datetime, timedelta

import h5py
import numpy as np
import pytest

from axialstress.bpr_observations import BprSeries
from axialstress.ellipsoid_bpr_calibration import (
    calibrate_ellipsoid_to_bpr,
    read_ellipsoid_unit_response,
)


def _series(site: str, values: list[float], quality: str) -> BprSeries:
    start = datetime(2020, 1, 1, tzinfo=UTC)
    times = tuple(start + timedelta(days=index) for index in range(len(values)))
    return BprSeries(site, times, np.asarray(values), tuple(quality for _ in values))


def test_calibration_recovers_known_linear_eastern_response() -> None:
    central = _series("central", [10.0, 12.0, 14.0], "2")
    east = _series("east", [5.0, 5.5, 6.0], "2")

    result = calibrate_ellipsoid_to_bpr(
        central,
        east,
        central_unit_response_m=2.0,
        east_unit_response_m=0.5,
    )

    np.testing.assert_allclose(result.pressure_change_mpa, [0.0, 1.0, 2.0])
    np.testing.assert_allclose(result.central_prediction_m, [0.0, 2.0, 4.0])
    np.testing.assert_allclose(result.east_prediction_m, [0.0, 0.5, 1.0])
    np.testing.assert_allclose(result.east_residual_m, 0.0, atol=1.0e-14)
    assert result.central_quality_codes == ("2", "2", "2")
    assert result.summary()["east_site_is_held_out_check"] is True


def test_surface_hdf5_response_uses_triangles_and_last_time_step(tmp_path) -> None:
    path = tmp_path / "surface.h5"
    vertices = np.array(
        [[0.0, 0.0, 0.0], [2.0, 0.0, 0.0], [0.0, 2.0, 0.0]],
    )
    displacement = np.zeros((2, 3, 3))
    displacement[0, :, 2] = 100.0
    displacement[1, :, 2] = vertices[:, 0] + 2.0 * vertices[:, 1]
    with h5py.File(path, "w") as surface:
        surface.create_dataset("time", data=[[[1.0]]])
        surface.create_dataset("geometry/vertices", data=vertices)
        surface.create_dataset("viz/topology/cells", data=[[0, 1, 2]])
        surface.create_dataset("vertex_fields/displacement", data=displacement)

    central, east = read_ellipsoid_unit_response(
        path,
        central_xy_m=(0.5, 0.5),
        east_xy_m=(1.0, 0.5),
    )

    np.testing.assert_allclose(central, [0.0, 0.0, 1.5])
    np.testing.assert_allclose(east, [0.0, 0.0, 2.0])


def test_rejects_nonpositive_central_compliance() -> None:
    with pytest.raises(ValueError, match="positive"):
        calibrate_ellipsoid_to_bpr(
            _series("central", [0.0, 1.0], "2"),
            _series("east", [0.0, 1.0], "2"),
            central_unit_response_m=0.0,
            east_unit_response_m=0.1,
        )
