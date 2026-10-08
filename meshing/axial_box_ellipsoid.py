"""Generate a coarse PyLith mesh with an ellipsoidal magma-reservoir cavity."""

from __future__ import annotations

import argparse
from pathlib import Path


def build_mesh(output: Path, lc_far: float, lc_near: float) -> int:
    """Create a tetrahedral mesh and return the tetrahedron count.

    Parameters
    ----------
    output : pathlib.Path
        Destination for the Gmsh 4.x mesh, in meters-based Cartesian coordinates.
    lc_far : float
        Target edge length away from the reservoir, in meters.
    lc_near : float
        Target edge length near the reservoir, in meters.

    Returns
    -------
    int
        Number of linear tetrahedra written to ``output``.

    Notes
    -----
    The 40 km × 40 km × 20 km box is a documented fallback because the paper's
    supplementary domain dimensions were unavailable. The cavity dimensions and
    centroid depth follow Cabaniss et al. (2020), doi:10.1038/s41598-020-67043-0.
    """
    if lc_near <= 0 or lc_far <= 0 or lc_near >= lc_far:
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
        gmsh.model.add("axial_box_ellipsoid")

        occ = gmsh.model.occ
        box = occ.addBox(-20_000.0, -20_000.0, -20_000.0, 40_000.0, 40_000.0, 20_000.0)
        cavity = occ.addEllipsoid(0.0, 0.0, -1_600.0, 3_000.0, 1_500.0, 500.0)
        result, _ = occ.cut([(3, box)], [(3, cavity)], removeObject=True, removeTool=True)
        occ.synchronize()

        volumes = [tag for dim, tag in result if dim == 3]
        if len(volumes) != 1:
            raise RuntimeError(f"expected one solid volume after cavity cut; found {len(volumes)}")

        tolerance = 1.0e-3
        faces = gmsh.model.getEntities(2)
        groups: dict[str, list[int]] = {
            "top": [],
            "bottom": [],
            "x_neg": [],
            "x_pos": [],
            "y_neg": [],
            "y_pos": [],
            "cavity": [],
        }
        for _, face in faces:
            xmin, ymin, zmin, xmax, ymax, zmax = gmsh.model.getBoundingBox(2, face)
            if abs(zmin) < tolerance and abs(zmax) < tolerance:
                groups["top"].append(face)
            elif abs(zmin + 20_000.0) < tolerance and abs(zmax + 20_000.0) < tolerance:
                groups["bottom"].append(face)
            elif abs(xmin + 20_000.0) < tolerance and abs(xmax + 20_000.0) < tolerance:
                groups["x_neg"].append(face)
            elif abs(xmin - 20_000.0) < tolerance and abs(xmax - 20_000.0) < tolerance:
                groups["x_pos"].append(face)
            elif abs(ymin + 20_000.0) < tolerance and abs(ymax + 20_000.0) < tolerance:
                groups["y_neg"].append(face)
            elif abs(ymin - 20_000.0) < tolerance and abs(ymax - 20_000.0) < tolerance:
                groups["y_pos"].append(face)
            else:
                groups["cavity"].append(face)

        if any(not members for members in groups.values()):
            missing = [name for name, members in groups.items() if not members]
            raise RuntimeError(f"could not classify boundary surfaces: {missing}")

        gmsh.model.addPhysicalGroup(3, volumes, 1)
        gmsh.model.setPhysicalName(3, 1, "1:domain")
        tags = {
            "cavity": 101,
            "top": 102,
            "bottom": 103,
            "x_neg": 104,
            "x_pos": 105,
            "y_neg": 106,
            "y_pos": 107,
        }
        for name, entities in groups.items():
            gmsh.model.addPhysicalGroup(2, entities, tags[name])
            gmsh.model.setPhysicalName(2, tags[name], name)

        distance = gmsh.model.mesh.field.add("Distance")
        gmsh.model.mesh.field.setNumbers(distance, "FacesList", groups["cavity"])
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
        tet_count = sum(len(tags_for_type) for tags_for_type in element_tags)
        print(f"Wrote {output}: {tet_count} tetrahedra")
        if tet_count >= 10_000:
            print("Warning: mesh has 10,000 or more tetrahedra; increase lc-near or lc-far.")
        return tet_count
    finally:
        gmsh.finalize()


def main() -> None:
    """Parse command-line arguments and generate the mesh."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("mesh/axial_box.msh"))
    parser.add_argument("--lc-far", type=float, default=10_000.0, help="far-field size in m")
    parser.add_argument("--lc-near", type=float, default=1_200.0, help="cavity size in m")
    args = parser.parse_args()
    build_mesh(args.output, args.lc_far, args.lc_near)


if __name__ == "__main__":
    main()
