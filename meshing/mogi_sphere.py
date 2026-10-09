"""Generate a bounded elastic half-space mesh with a spherical source cavity."""

from __future__ import annotations

import argparse
from pathlib import Path


def build_mesh(
    output: Path,
    *,
    half_width_m: float = 25_000.0,
    bottom_depth_m: float = 10_000.0,
    source_depth_m: float = 4_000.0,
    source_radius_m: float = 700.0,
    lc_far_m: float = 12_000.0,
    lc_near_m: float = 75.0,
) -> int:
    """Build and write a tetrahedral spherical-cavity benchmark mesh.

    Parameters
    ----------
    output : pathlib.Path
        Destination for the Gmsh 4.x mesh in meter-based Cartesian coordinates.
    half_width_m : float
        Positive half-width of the square horizontal domain, in meters.
    bottom_depth_m : float
        Positive-down depth of the fixed base, in meters.
    source_depth_m : float
        Positive-down depth of the spherical source center, in meters.
    source_radius_m : float
        Spherical cavity radius, in meters.
    lc_far_m : float
        Target element edge length away from the source, in meters.
    lc_near_m : float
        Target element edge length near the source, in meters.

    Returns
    -------
    int
        Number of linear tetrahedra written to ``output``.
    """
    dimensions = (half_width_m, bottom_depth_m, source_depth_m, source_radius_m)
    if any(value <= 0.0 for value in dimensions):
        raise ValueError("domain and source dimensions must be positive")
    if source_depth_m + source_radius_m >= bottom_depth_m:
        raise ValueError("source cavity must remain above the fixed base")
    if source_depth_m - source_radius_m <= 0.0:
        raise ValueError("source cavity must remain below the free surface")
    if not 0.0 < lc_near_m < lc_far_m:
        raise ValueError("mesh sizes must be positive and lc_near < lc_far")

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
        gmsh.model.add("mogi_spherical_source")
        occ = gmsh.model.occ
        box = occ.addBox(
            -half_width_m,
            -half_width_m,
            -bottom_depth_m,
            2.0 * half_width_m,
            2.0 * half_width_m,
            bottom_depth_m,
        )
        sphere = occ.addSphere(0.0, 0.0, -source_depth_m, source_radius_m)
        result, _ = occ.cut([(3, box)], [(3, sphere)], removeObject=True, removeTool=True)
        occ.synchronize()
        volumes = [tag for dim, tag in result if dim == 3]
        if len(volumes) != 1:
            raise RuntimeError(f"expected one solid volume, found {len(volumes)}")

        tolerance = 1.0e-3
        groups: dict[str, list[int]] = {
            "top": [],
            "bottom": [],
            "x_neg": [],
            "x_pos": [],
            "y_neg": [],
            "y_pos": [],
            "cavity": [],
        }
        for _, face in gmsh.model.getEntities(2):
            xmin, ymin, zmin, xmax, ymax, zmax = gmsh.model.getBoundingBox(2, face)
            if abs(zmin) < tolerance and abs(zmax) < tolerance:
                groups["top"].append(face)
            elif (
                abs(zmin + bottom_depth_m) < tolerance
                and abs(zmax + bottom_depth_m) < tolerance
            ):
                groups["bottom"].append(face)
            elif abs(xmin + half_width_m) < tolerance and abs(xmax + half_width_m) < tolerance:
                groups["x_neg"].append(face)
            elif abs(xmin - half_width_m) < tolerance and abs(xmax - half_width_m) < tolerance:
                groups["x_pos"].append(face)
            elif abs(ymin + half_width_m) < tolerance and abs(ymax + half_width_m) < tolerance:
                groups["y_neg"].append(face)
            elif abs(ymin - half_width_m) < tolerance and abs(ymax - half_width_m) < tolerance:
                groups["y_pos"].append(face)
            else:
                groups["cavity"].append(face)
        if any(not entities for entities in groups.values()):
            missing = [name for name, entities in groups.items() if not entities]
            raise RuntimeError(f"could not classify surfaces: {missing}")

        gmsh.model.addPhysicalGroup(3, volumes, 1)
        gmsh.model.setPhysicalName(3, 1, "material-id:1")
        physical_tags = {
            "cavity": 101,
            "top": 102,
            "bottom": 103,
            "x_neg": 104,
            "x_pos": 105,
            "y_neg": 106,
            "y_pos": 107,
        }
        for name, faces in groups.items():
            entities_by_dimension: dict[int, set[int]] = {2: set(faces)}
            for dimension in (2, 1):
                lower_entities: set[int] = set()
                for entity in entities_by_dimension[dimension]:
                    _, downward = gmsh.model.getAdjacencies(dimension, entity)
                    lower_entities.update(int(tag) for tag in downward)
                entities_by_dimension[dimension - 1] = lower_entities
            for dimension, entities in entities_by_dimension.items():
                tag = physical_tags[name]
                gmsh.model.addPhysicalGroup(dimension, sorted(entities), tag)
                gmsh.model.setPhysicalName(dimension, tag, name)

        distance = gmsh.model.mesh.field.add("Distance")
        gmsh.model.mesh.field.setNumbers(distance, "FacesList", groups["cavity"])
        threshold = gmsh.model.mesh.field.add("Threshold")
        gmsh.model.mesh.field.setNumber(threshold, "InField", distance)
        gmsh.model.mesh.field.setNumber(threshold, "SizeMin", lc_near_m)
        gmsh.model.mesh.field.setNumber(threshold, "SizeMax", lc_far_m)
        gmsh.model.mesh.field.setNumber(threshold, "DistMin", 0.0)
        gmsh.model.mesh.field.setNumber(
            threshold, "DistMax", min(0.25 * half_width_m, source_depth_m)
        )
        axis_refinement = gmsh.model.mesh.field.add("Ball")
        gmsh.model.mesh.field.setNumber(axis_refinement, "XCenter", 0.0)
        gmsh.model.mesh.field.setNumber(axis_refinement, "YCenter", 0.0)
        gmsh.model.mesh.field.setNumber(axis_refinement, "ZCenter", 0.0)
        gmsh.model.mesh.field.setNumber(axis_refinement, "Radius", 6_000.0)
        gmsh.model.mesh.field.setNumber(axis_refinement, "Thickness", 1_000.0)
        gmsh.model.mesh.field.setNumber(axis_refinement, "VIn", 3_000.0)
        gmsh.model.mesh.field.setNumber(axis_refinement, "VOut", lc_far_m)
        background = gmsh.model.mesh.field.add("Min")
        gmsh.model.mesh.field.setNumbers(background, "FieldsList", [threshold, axis_refinement])
        gmsh.model.mesh.field.setAsBackgroundMesh(background)
        gmsh.option.setNumber("Mesh.MeshSizeMin", lc_near_m)
        gmsh.option.setNumber("Mesh.MeshSizeMax", lc_far_m)
        gmsh.model.mesh.generate(3)
        gmsh.write(str(output))
        _, element_tags, _ = gmsh.model.mesh.getElements(3)
        tetrahedron_count = sum(len(tags) for tags in element_tags)
        print(f"Wrote {output}: {tetrahedron_count} tetrahedra")
        return tetrahedron_count
    finally:
        gmsh.finalize()


def main() -> None:
    """Parse arguments and write the spherical-source benchmark mesh."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("mesh/mogi_sphere.msh"))
    parser.add_argument("--half-width", type=float, default=25_000.0, help="half-width in m")
    parser.add_argument("--bottom-depth", type=float, default=10_000.0, help="depth in m")
    parser.add_argument("--source-depth", type=float, default=4_000.0, help="depth in m")
    parser.add_argument("--source-radius", type=float, default=700.0, help="radius in m")
    parser.add_argument("--lc-far", type=float, default=12_000.0, help="far size in m")
    parser.add_argument("--lc-near", type=float, default=75.0, help="near size in m")
    args = parser.parse_args()
    build_mesh(
        args.output,
        half_width_m=args.half_width,
        bottom_depth_m=args.bottom_depth,
        source_depth_m=args.source_depth,
        source_radius_m=args.source_radius,
        lc_far_m=args.lc_far,
        lc_near_m=args.lc_near,
    )


if __name__ == "__main__":
    main()
