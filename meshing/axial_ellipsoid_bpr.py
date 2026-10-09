"""Generate a coarse ellipsoidal-reservoir mesh for the OOI BPR check."""

from __future__ import annotations

import argparse
from pathlib import Path


def build_mesh(output: Path, lc_far: float = 10_000.0, lc_near: float = 1_200.0) -> int:
    """Write a 40 km × 40 km × 20 km mesh with a 6 km × 3 km × 1 km cavity.

    The cavity center is 1.6 km below the free surface. The dimensions follow
    the written model specification; the box dimensions and mesh sizes are
    setup assumptions for this bounded elastic diagnostic.
    """
    if lc_near <= 0.0 or lc_far <= lc_near:
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
        gmsh.model.add("axial_ellipsoid_bpr")

        occ = gmsh.model.occ
        box = occ.addBox(-20_000.0, -20_000.0, -20_000.0, 40_000.0, 40_000.0, 20_000.0)
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
            elif abs(zmin + 20_000.0) < tolerance and abs(zmax + 20_000.0) < tolerance:
                name = "bottom"
            elif abs(xmin + 20_000.0) < tolerance and abs(xmax + 20_000.0) < tolerance:
                name = "x_neg"
            elif abs(xmin - 20_000.0) < tolerance and abs(xmax - 20_000.0) < tolerance:
                name = "x_pos"
            elif abs(ymin + 20_000.0) < tolerance and abs(ymax + 20_000.0) < tolerance:
                name = "y_neg"
            elif abs(ymin - 20_000.0) < tolerance and abs(ymax - 20_000.0) < tolerance:
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
        gmsh.model.mesh.field.setAsBackgroundMesh(threshold)
        gmsh.option.setNumber("Mesh.MeshSizeMin", 0.75 * lc_near)
        gmsh.option.setNumber("Mesh.MeshSizeMax", lc_far)
        gmsh.model.mesh.generate(3)
        gmsh.write(str(output))

        _, element_tags, _ = gmsh.model.mesh.getElements(3)
        tetrahedron_count = sum(len(tags) for tags in element_tags)
        if tetrahedron_count > 4_000:
            raise RuntimeError(
                f"mesh has {tetrahedron_count} tetrahedra; increase lc-near or lc-far "
                "to keep this setup below 4,000 elements"
            )
        print(f"Wrote {output}: {tetrahedron_count} tetrahedra")
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
    args = parser.parse_args()
    build_mesh(args.output, args.lc_far, args.lc_near)


if __name__ == "__main__":
    main()
