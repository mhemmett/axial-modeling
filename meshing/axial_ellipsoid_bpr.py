"""Generate a coarse ellipsoidal-reservoir mesh for the OOI BPR check."""

from __future__ import annotations

import argparse
import math
from pathlib import Path


def build_mesh(
    output: Path,
    lc_far: float = 10_000.0,
    lc_near: float = 1_200.0,
    max_tetrahedra: int = 4_000,
    local_refinement_size: float | None = None,
    station_refinement_size: float | None = None,
    domain_depth_m: float = 10_000.0,
    domain_width_m: float = 50_000.0,
    domain_length_m: float = 50_000.0,
    embed_station_points: bool = False,
    additional_station_coordinates_lat_lon_deg: tuple[tuple[float, float], ...] = (),
) -> int:
    """Write a box mesh with an ellipsoidal reservoir and specified base depth.

    The cavity center is 1.6 km below the free surface. The dimensions follow
    the written model specification. The 50 km × 50 km horizontal extent and
    10 km depth follow the project owner's model setup direction.
    """
    if lc_near <= 0.0 or lc_far <= lc_near:
        raise ValueError("mesh sizes must be positive and lc_near < lc_far")
    if max_tetrahedra <= 0:
        raise ValueError("max_tetrahedra must be positive")
    if not math.isfinite(domain_depth_m) or domain_depth_m <= 2_500.0:
        raise ValueError("domain_depth_m must be finite and exceed 2,500 m")
    horizontal_dimensions = (domain_width_m, domain_length_m)
    if not all(
        math.isfinite(value) and value > 2_500.0
        for value in horizontal_dimensions
    ):
        raise ValueError("horizontal domain dimensions must be finite and exceed 2,500 m")
    x_half = domain_width_m / 2.0
    y_half = domain_length_m / 2.0
    if local_refinement_size is not None and (
        local_refinement_size <= 0.0 or local_refinement_size >= lc_far
    ):
        raise ValueError("local_refinement_size must be positive and less than lc_far")
    if station_refinement_size is not None and (
        station_refinement_size <= 0.0 or station_refinement_size >= lc_near
    ):
        raise ValueError("station_refinement_size must be positive and less than lc_near")
    if any(
        not math.isfinite(value)
        for coordinate in additional_station_coordinates_lat_lon_deg
        for value in coordinate
    ):
        raise ValueError("station coordinates must be finite latitude/longitude pairs")
    if any(
        len(coordinate) != 2 or not -90.0 <= coordinate[0] <= 90.0
        for coordinate in additional_station_coordinates_lat_lon_deg
    ):
        raise ValueError("station coordinates must contain valid latitude/longitude pairs")
    try:
        import gmsh
    except ImportError as exc:
        raise RuntimeError("Gmsh's Python API is required; install environment.yml") from exc

    output.parent.mkdir(parents=True, exist_ok=True)
    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 1)
        gmsh.option.setNumber("Mesh.MshFileVersion", 4.1)
        gmsh.option.setNumber("Mesh.ElementOrder", 1)
        gmsh.model.add("axial_ellipsoid_bpr")

        occ = gmsh.model.occ
        box = occ.addBox(
            -x_half,
            -y_half,
            -domain_depth_m,
            domain_width_m,
            domain_length_m,
            domain_depth_m,
        )
        cavity = occ.addSphere(0.0, 0.0, -1_600.0, 1.0)
        occ.dilate([(3, cavity)], 0.0, 0.0, -1_600.0, 3_000.0, 1_500.0, 500.0)
        cut, _ = occ.cut([(3, box)], [(3, cavity)], removeObject=True, removeTool=True)
        occ.synchronize()
        volumes = [tag for dim, tag in cut if dim == 3]
        if len(volumes) != 1:
            raise RuntimeError(
                f"expected one material volume after cavity cut; found {len(volumes)}"
            )

        boundary_faces: dict[str, list[int]] = {
            "cavity": [],
            "top": [],
            "bottom": [],
            "x_neg": [],
            "x_pos": [],
            "y_neg": [],
            "y_pos": [],
        }
        tolerance = 1.0e-3
        for _, face in gmsh.model.getEntities(2):
            xmin, ymin, zmin, xmax, ymax, zmax = gmsh.model.getBoundingBox(2, face)
            if abs(zmin) < tolerance and abs(zmax) < tolerance:
                name = "top"
            elif (
                abs(zmin + domain_depth_m) < tolerance
                and abs(zmax + domain_depth_m) < tolerance
            ):
                name = "bottom"
            elif abs(xmin + x_half) < tolerance and abs(xmax + x_half) < tolerance:
                name = "x_neg"
            elif abs(xmin - x_half) < tolerance and abs(xmax - x_half) < tolerance:
                name = "x_pos"
            elif abs(ymin + y_half) < tolerance and abs(ymax + y_half) < tolerance:
                name = "y_neg"
            elif abs(ymin - y_half) < tolerance and abs(ymax - y_half) < tolerance:
                name = "y_pos"
            else:
                name = "cavity"
            boundary_faces[name].append(face)
        missing = [name for name, members in boundary_faces.items() if not members]
        if missing:
            raise RuntimeError(f"could not classify boundary surfaces: {missing}")
        gmsh.model.addPhysicalGroup(3, volumes, 1)
        gmsh.model.setPhysicalName(3, 1, "material-id:1")
        labels = {
            "cavity": 101,
            "top": 102,
            "bottom": 103,
            "x_neg": 104,
            "x_pos": 105,
            "y_neg": 106,
            "y_pos": 107,
        }
        for name, faces in boundary_faces.items():
            entities: dict[int, set[int]] = {2: set(faces)}
            for dimension in (2, 1):
                lower: set[int] = set()
                for entity in entities[dimension]:
                    _, downward = gmsh.model.getAdjacencies(dimension, entity)
                    lower.update(int(tag) for tag in downward)
                entities[dimension - 1] = lower
            for dimension, members in entities.items():
                gmsh.model.addPhysicalGroup(dimension, sorted(members), labels[name])
                gmsh.model.setPhysicalName(dimension, labels[name], name)

        distance = gmsh.model.mesh.field.add("Distance")
        gmsh.model.mesh.field.setNumbers(distance, "FacesList", boundary_faces["cavity"])
        threshold = gmsh.model.mesh.field.add("Threshold")
        gmsh.model.mesh.field.setNumber(threshold, "InField", distance)
        gmsh.model.mesh.field.setNumber(threshold, "SizeMin", lc_near)
        gmsh.model.mesh.field.setNumber(threshold, "SizeMax", lc_far)
        gmsh.model.mesh.field.setNumber(threshold, "DistMin", 2.0 * lc_near)
        gmsh.model.mesh.field.setNumber(threshold, "DistMax", 2.0 * lc_far)
        fields = [threshold]
        minimum_size = 0.75 * lc_near
        if local_refinement_size is not None:
            local_box = gmsh.model.mesh.field.add("Box")
            gmsh.model.mesh.field.setNumber(local_box, "VIn", local_refinement_size)
            gmsh.model.mesh.field.setNumber(local_box, "VOut", lc_far)
            gmsh.model.mesh.field.setNumber(local_box, "XMin", -3_500.0)
            gmsh.model.mesh.field.setNumber(local_box, "XMax", 4_500.0)
            gmsh.model.mesh.field.setNumber(local_box, "YMin", -2_200.0)
            gmsh.model.mesh.field.setNumber(local_box, "YMax", 2_200.0)
            gmsh.model.mesh.field.setNumber(local_box, "ZMin", -3_000.0)
            gmsh.model.mesh.field.setNumber(local_box, "ZMax", 0.0)
            gmsh.model.mesh.field.setNumber(local_box, "Thickness", 2_000.0)
            fields.append(local_box)
            minimum_size = min(minimum_size, local_refinement_size)
        if station_refinement_size is not None:
            from axialstress.bpr_mogi_calibration import (
                CENTRAL_CALDERA_LAT_LON_DEG,
                EAST_CALDERA_LAT_LON_DEG,
                local_east_north_offset_m,
            )

            # Shallow station boxes refine interpolation neighborhoods without
            # refining the ellipsoid 1.1 km below the Central site.
            station_coordinates = (
                CENTRAL_CALDERA_LAT_LON_DEG,
                EAST_CALDERA_LAT_LON_DEG,
            ) + additional_station_coordinates_lat_lon_deg
            for latitude_deg, longitude_deg in station_coordinates:
                east_m, north_m = local_east_north_offset_m(
                    latitude_deg,
                    longitude_deg,
                    origin_latitude_deg=CENTRAL_CALDERA_LAT_LON_DEG[0],
                    origin_longitude_deg=CENTRAL_CALDERA_LAT_LON_DEG[1],
                )
                station_box = gmsh.model.mesh.field.add("Box")
                gmsh.model.mesh.field.setNumber(station_box, "VIn", station_refinement_size)
                gmsh.model.mesh.field.setNumber(station_box, "VOut", lc_far)
                gmsh.model.mesh.field.setNumber(station_box, "XMin", east_m - 600.0)
                gmsh.model.mesh.field.setNumber(station_box, "XMax", east_m + 600.0)
                gmsh.model.mesh.field.setNumber(station_box, "YMin", north_m - 600.0)
                gmsh.model.mesh.field.setNumber(station_box, "YMax", north_m + 600.0)
                gmsh.model.mesh.field.setNumber(station_box, "ZMin", -300.0)
                gmsh.model.mesh.field.setNumber(station_box, "ZMax", 0.0)
                gmsh.model.mesh.field.setNumber(station_box, "Thickness", 300.0)
                fields.append(station_box)
            minimum_size = min(minimum_size, station_refinement_size)
        if embed_station_points or additional_station_coordinates_lat_lon_deg:
            from axialstress.bpr_mogi_calibration import (
                CENTRAL_CALDERA_LAT_LON_DEG,
                EAST_CALDERA_LAT_LON_DEG,
                local_east_north_offset_m,
            )

            if len(boundary_faces["top"]) != 1:
                raise RuntimeError("station points require one unpartitioned top surface")
            station_coordinates = (
                (
                    CENTRAL_CALDERA_LAT_LON_DEG,
                    EAST_CALDERA_LAT_LON_DEG,
                )
                if embed_station_points
                else ()
            ) + additional_station_coordinates_lat_lon_deg
            point_tags = []
            for latitude_deg, longitude_deg in station_coordinates:
                east_m, north_m = local_east_north_offset_m(
                    latitude_deg,
                    longitude_deg,
                    origin_latitude_deg=CENTRAL_CALDERA_LAT_LON_DEG[0],
                    origin_longitude_deg=CENTRAL_CALDERA_LAT_LON_DEG[1],
                )
                point_tags.append(occ.addPoint(east_m, north_m, 0.0))
            occ.synchronize()
            gmsh.model.mesh.embed(0, point_tags, 2, boundary_faces["top"][0])
        if len(fields) == 1:
            gmsh.model.mesh.field.setAsBackgroundMesh(threshold)
        else:
            combined = gmsh.model.mesh.field.add("Min")
            gmsh.model.mesh.field.setNumbers(combined, "FieldsList", fields)
            gmsh.model.mesh.field.setAsBackgroundMesh(combined)
        gmsh.option.setNumber("Mesh.MeshSizeMin", minimum_size)
        gmsh.option.setNumber("Mesh.MeshSizeMax", lc_far)
        if station_refinement_size is not None:
            gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary", 0)
        gmsh.model.mesh.generate(3)
        gmsh.write(str(output))

        _, element_tags, _ = gmsh.model.mesh.getElements(3)
        tetrahedron_count = sum(len(tags) for tags in element_tags)
        if tetrahedron_count == 0:
            raise RuntimeError(
                "mesh contains no tetrahedra; refine the cavity-adjacent mesh"
            )
        if tetrahedron_count > max_tetrahedra:
            raise RuntimeError(
                f"mesh has {tetrahedron_count} tetrahedra; increase lc-near or lc-far "
                f"to keep this setup below {max_tetrahedra:,} elements"
            )
        print(
            f"Wrote {output}: {tetrahedron_count} tetrahedra; "
            f"domain depth={domain_depth_m:g} m"
        )
        return tetrahedron_count
    finally:
        gmsh.finalize()


def main() -> None:
    """Generate the elastic ellipsoid diagnostic mesh."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("pylith/step05_ellipsoid_elastic/mesh/axial_ellipsoid.msh"),
    )
    parser.add_argument("--lc-far", type=float, default=10_000.0)
    parser.add_argument("--lc-near", type=float, default=1_200.0)
    parser.add_argument("--max-tetrahedra", type=int, default=4_000)
    parser.add_argument("--domain-depth-m", type=float, default=10_000.0)
    parser.add_argument("--domain-width-m", type=float, default=50_000.0)
    parser.add_argument("--domain-length-m", type=float, default=50_000.0)
    parser.add_argument(
        "--embed-station-points",
        action="store_true",
        help="constrain the surface mesh to include Central and Eastern BPR locations",
    )
    parser.add_argument(
        "--embed-station-coordinate",
        action="append",
        default=[],
        metavar="LATITUDE,LONGITUDE",
        help="also embed a custom BPR location; may be repeated",
    )
    parser.add_argument("--local-refinement-size", type=float)
    parser.add_argument("--station-refinement-size", type=float)
    args = parser.parse_args()
    try:
        station_coordinates = tuple(
            tuple(float(value) for value in item.split(","))
            for item in args.embed_station_coordinate
        )
    except ValueError as exc:
        raise SystemExit("--embed-station-coordinate expects LATITUDE,LONGITUDE") from exc
    if any(len(coordinate) != 2 for coordinate in station_coordinates):
        raise SystemExit("--embed-station-coordinate expects LATITUDE,LONGITUDE")
    build_mesh(
        args.output,
        args.lc_far,
        args.lc_near,
        args.max_tetrahedra,
        args.local_refinement_size,
        args.station_refinement_size,
        args.domain_depth_m,
        args.domain_width_m,
        args.domain_length_m,
        embed_station_points=args.embed_station_points,
        additional_station_coordinates_lat_lon_deg=station_coordinates,
    )


if __name__ == "__main__":
    main()
