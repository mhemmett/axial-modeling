"""Calibrate a PyLith ellipsoid compliance response to independent OOI BPR data."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import h5py
import numpy as np
from numpy.typing import NDArray

from axialstress.bpr_mogi_calibration import (
    CENTRAL_CALDERA_LAT_LON_DEG,
    EAST_CALDERA_LAT_LON_DEG,
    local_east_north_offset_m,
)
from axialstress.bpr_observations import BprSeries
from axialstress.surface_interpolation import interpolate_triangular_surface

FloatArray = NDArray[np.float64]
ELASTIC_YOUNGS_MODULUS_PA = 50.0e9
ELASTIC_POISSON_RATIO = 0.25
ELASTIC_DENSITY_KG_M3 = 2800.0
UNIT_PRESSURE_MPA = 1.0


@dataclass(frozen=True)
class EllipsoidBprCalibration:
    """Aligned OOI observations and the pressure series inferred from Central."""

    times_utc: tuple[datetime, ...]
    central_uplift_m: FloatArray
    central_prediction_m: FloatArray
    east_uplift_m: FloatArray
    east_prediction_m: FloatArray
    pressure_change_mpa: FloatArray
    east_residual_m: FloatArray
    central_quality_codes: tuple[str, ...]
    east_quality_codes: tuple[str, ...]
    central_compliance_m_per_mpa: float
    east_compliance_m_per_mpa: float
    east_offset_east_m: float
    east_offset_north_m: float

    def summary(self) -> dict[str, object]:
        """Return model assumptions, sampling, and Eastern-site skill metrics."""
        observed_norm = float(np.linalg.norm(self.east_uplift_m))
        correlation = (
            float(np.corrcoef(self.east_uplift_m, self.east_prediction_m)[0, 1])
            if np.std(self.east_uplift_m) > 0.0
            and np.std(self.east_prediction_m) > 0.0
            else None
        )
        return {
            "method": "PyLith static elastic ellipsoid compliance calibrated at Central BPR",
            "record_count": len(self.times_utc),
            "start_time_utc": self.times_utc[0].isoformat(),
            "end_time_utc": self.times_utc[-1].isoformat(),
            "central_quality_codes": sorted(set(self.central_quality_codes)),
            "east_quality_codes": sorted(set(self.east_quality_codes)),
            "youngs_modulus_pa": ELASTIC_YOUNGS_MODULUS_PA,
            "poisson_ratio": ELASTIC_POISSON_RATIO,
            "poisson_ratio_status": "assumed; not specified in the written benchmark",
            "density_kg_m3": ELASTIC_DENSITY_KG_M3,
            "density_status": "setup assumption",
            "reservoir_dimensions_km": [6.0, 3.0, 1.0],
            "reservoir_center_depth_km": 1.6,
            "domain_dimensions_km": [40.0, 40.0, 20.0],
            "boundary_conditions": "fixed base, roller sides, free top",
            "unit_pressure_mpa": UNIT_PRESSURE_MPA,
            "central_compliance_m_per_mpa": self.central_compliance_m_per_mpa,
            "east_compliance_m_per_mpa": self.east_compliance_m_per_mpa,
            "source_axis_location_assumption": "Central Caldera BPR coordinates",
            "east_offset_east_m": self.east_offset_east_m,
            "east_offset_north_m": self.east_offset_north_m,
            "pressure_change_min_mpa": float(np.min(self.pressure_change_mpa)),
            "pressure_change_max_mpa": float(np.max(self.pressure_change_mpa)),
            "east_rmse_m": float(np.sqrt(np.mean(self.east_residual_m**2))),
            "east_relative_l2_error": (
                float(np.linalg.norm(self.east_residual_m) / observed_norm)
                if observed_norm > 0.0
                else None
            ),
            "east_correlation": correlation,
            "central_fit_is_calibration": True,
            "east_site_is_held_out_check": True,
            "qc_filter_applied": False,
            "limitations": [
                "static linear elasticity omits viscoelastic memory",
                "uniform host properties omit temperature-dependent rheologies",
                "the fixed base and roller side conditions are setup assumptions",
            ],
            "observation_provenance": "independent OOI BPR records only",
        }


def read_ellipsoid_unit_response(
    surface_hdf5: Path,
    *,
    central_xy_m: tuple[float, float] = (0.0, 0.0),
    east_xy_m: tuple[float, float] | None = None,
) -> tuple[FloatArray, FloatArray]:
    """Read and interpolate final surface displacement at Central and Eastern."""
    if east_xy_m is None:
        east_offset, north_offset = local_east_north_offset_m(
            EAST_CALDERA_LAT_LON_DEG[0],
            EAST_CALDERA_LAT_LON_DEG[1],
            origin_latitude_deg=CENTRAL_CALDERA_LAT_LON_DEG[0],
            origin_longitude_deg=CENTRAL_CALDERA_LAT_LON_DEG[1],
        )
        east_xy_m = (east_offset, north_offset)
    with h5py.File(surface_hdf5, "r") as surface:
        required = (
            "time",
            "geometry/vertices",
            "viz/topology/cells",
            "vertex_fields/displacement",
        )
        if any(name not in surface for name in required):
            raise ValueError(f"PyLith surface file is missing a required dataset: {surface_hdf5}")
        output_times = np.asarray(surface["time"], dtype=float).reshape(-1)
        vertices = np.asarray(surface["geometry/vertices"], dtype=float)
        cells = np.asarray(surface["viz/topology/cells"], dtype=np.int64)
        displacement = np.asarray(surface["vertex_fields/displacement"], dtype=float)
    if not len(output_times) or not np.isclose(output_times[-1], 1.0, rtol=0.0, atol=1.0e-12):
        raise ValueError("PyLith unit-response output did not reach the configured 1 s end time")
    if displacement.ndim == 3:
        displacement = displacement[-1]
    if displacement.shape != vertices.shape:
        raise ValueError("surface displacement shape does not match its vertices")
    if not np.all(np.isfinite(displacement)):
        raise ValueError("surface displacement contains non-finite values")
    if not np.allclose(vertices[:, 2], vertices[0, 2], rtol=0.0, atol=1.0e-7):
        raise ValueError("surface interpolation expects a horizontal PyLith boundary")
    central = interpolate_triangular_surface(vertices, cells, displacement, central_xy_m)
    east = interpolate_triangular_surface(vertices, cells, displacement, east_xy_m)
    return np.asarray(central, dtype=float), np.asarray(east, dtype=float)


def calibrate_ellipsoid_to_bpr(
    central: BprSeries,
    east: BprSeries,
    *,
    central_unit_response_m: float,
    east_unit_response_m: float,
    central_lat_lon_deg: tuple[float, float] = CENTRAL_CALDERA_LAT_LON_DEG,
    east_lat_lon_deg: tuple[float, float] = EAST_CALDERA_LAT_LON_DEG,
) -> EllipsoidBprCalibration:
    """Fit elastic pressure to Central uplift and predict Eastern uplift.

    Unit responses are vertical displacements for the configured 1 MPa
    overpressure. Each observation series is referenced to the first common
    finite sample. OOI quality codes are retained but not used as filters.
    """
    if central.site.lower() != "central" or east.site.lower() not in ("east", "eastern"):
        raise ValueError("central and east inputs must identify the two OOI BPR sites")
    if (
        not np.isfinite(central_unit_response_m)
        or central_unit_response_m <= 0.0
        or not np.isfinite(east_unit_response_m)
    ):
        raise ValueError("unit responses must be finite and central uplift must be positive")

    central_by_time = {
        time: (float(uplift), quality)
        for time, uplift, quality in zip(
            central.times_utc, central.uplift_m, central.quality_codes, strict=True
        )
    }
    east_by_time = {
        time: (float(uplift), quality)
        for time, uplift, quality in zip(
            east.times_utc, east.uplift_m, east.quality_codes, strict=True
        )
    }
    common_times = sorted(central_by_time.keys() & east_by_time.keys())
    valid_times = [
        time
        for time in common_times
        if np.isfinite(central_by_time[time][0]) and np.isfinite(east_by_time[time][0])
    ]
    if not valid_times:
        raise ValueError("BPR series have no common finite daily observations")

    central_raw = np.asarray([central_by_time[time][0] for time in valid_times])
    east_raw = np.asarray([east_by_time[time][0] for time in valid_times])
    central_uplift = central_raw - central_raw[0]
    east_uplift = east_raw - east_raw[0]
    pressure_mpa = central_uplift / central_unit_response_m
    central_prediction = pressure_mpa * central_unit_response_m
    east_prediction = pressure_mpa * east_unit_response_m
    east_offset, north_offset = local_east_north_offset_m(
        east_lat_lon_deg[0],
        east_lat_lon_deg[1],
        origin_latitude_deg=central_lat_lon_deg[0],
        origin_longitude_deg=central_lat_lon_deg[1],
    )
    return EllipsoidBprCalibration(
        times_utc=tuple(valid_times),
        central_uplift_m=central_uplift,
        central_prediction_m=central_prediction,
        east_uplift_m=east_uplift,
        east_prediction_m=east_prediction,
        pressure_change_mpa=pressure_mpa,
        east_residual_m=east_uplift - east_prediction,
        central_quality_codes=tuple(central_by_time[time][1] for time in valid_times),
        east_quality_codes=tuple(east_by_time[time][1] for time in valid_times),
        central_compliance_m_per_mpa=central_unit_response_m,
        east_compliance_m_per_mpa=east_unit_response_m,
        east_offset_east_m=east_offset,
        east_offset_north_m=north_offset,
    )
