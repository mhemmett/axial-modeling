"""Synthetic checks for the OOI-constrained elastic Mogi calibration."""

from datetime import UTC, datetime, timedelta

import numpy as np

from axialstress.benchmarks import mogi_surface_displacement_m
from axialstress.bpr_mogi_calibration import (
    CENTRAL_CALDERA_LAT_LON_DEG,
    EAST_CALDERA_LAT_LON_DEG,
    calibrate_mogi_to_bpr,
    local_east_north_offset_m,
)
from axialstress.bpr_observations import BprSeries


def test_ooi_station_offset_has_expected_east_and_north_signs() -> None:
    east_m, north_m = local_east_north_offset_m(
        *EAST_CALDERA_LAT_LON_DEG,
        origin_latitude_deg=CENTRAL_CALDERA_LAT_LON_DEG[0],
        origin_longitude_deg=CENTRAL_CALDERA_LAT_LON_DEG[1],
    )

    assert 2500.0 < east_m < 3000.0
    assert -1900.0 < north_m < -1400.0


def test_central_calibration_recovers_mogi_pressure_and_east_response() -> None:
    times = tuple(
        datetime(2020, 1, 1, tzinfo=UTC) + timedelta(days=day) for day in range(3)
    )
    pressure_pa = np.array([0.0, 1.5e6, 3.0e6])
    youngs_modulus_pa = 60.0e9
    poisson_ratio = 0.25
    shear_modulus_pa = youngs_modulus_pa / (2.0 * (1.0 + poisson_ratio))
    bulk_modulus_pa = youngs_modulus_pa / (3.0 * (1.0 - 2.0 * poisson_ratio))
    east_offset_m, north_offset_m = local_east_north_offset_m(
        *EAST_CALDERA_LAT_LON_DEG,
        origin_latitude_deg=CENTRAL_CALDERA_LAT_LON_DEG[0],
        origin_longitude_deg=CENTRAL_CALDERA_LAT_LON_DEG[1],
    )
    central_uplift = mogi_surface_displacement_m(
        0.0,
        0.0,
        source_depth_m=4000.0,
        source_radius_m=700.0,
        pressure_change_pa=pressure_pa,
        bulk_modulus_pa=bulk_modulus_pa,
        shear_modulus_pa=shear_modulus_pa,
    )[:, 2]
    east_uplift = mogi_surface_displacement_m(
        east_offset_m,
        north_offset_m,
        source_depth_m=4000.0,
        source_radius_m=700.0,
        pressure_change_pa=pressure_pa,
        bulk_modulus_pa=bulk_modulus_pa,
        shear_modulus_pa=shear_modulus_pa,
    )[:, 2]
    central = BprSeries("central", times, central_uplift, ("2",) * 3)
    east = BprSeries("east", times, east_uplift, ("2",) * 3)

    result = calibrate_mogi_to_bpr(central, east)

    np.testing.assert_allclose(result.pressure_change_pa, pressure_pa, rtol=1e-12)
    np.testing.assert_allclose(result.central_prediction_m, central_uplift, atol=1e-14)
    np.testing.assert_allclose(result.east_prediction_m, east_uplift, atol=1e-14)
    np.testing.assert_allclose(result.east_residual_m, 0.0, atol=1e-14)
    assert result.summary()["qc_filter_applied"] is False
