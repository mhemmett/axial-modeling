"""Input checks for the bounded ellipsoid mesh generator."""

from pathlib import Path

import pytest
from meshing.axial_ellipsoid_bpr import build_mesh


@pytest.mark.parametrize("domain_depth_m", [0.0, 2_500.0, float("nan")])
def test_ellipsoid_mesh_rejects_invalid_domain_depth(
    tmp_path: Path, domain_depth_m: float
) -> None:
    with pytest.raises(ValueError, match="domain_depth_m"):
        build_mesh(tmp_path / "invalid.msh", domain_depth_m=domain_depth_m)


@pytest.mark.parametrize(
    "coordinates",
    [((91.0, -130.0),), ((45.0, float("nan")),), ((45.0,),)],
)
def test_ellipsoid_mesh_rejects_invalid_station_coordinates(
    tmp_path: Path, coordinates: tuple[tuple[float, ...], ...]
) -> None:
    with pytest.raises(ValueError, match="station coordinates"):
        build_mesh(
            tmp_path / "invalid.msh",
            additional_station_coordinates_lat_lon_deg=coordinates,
        )
