"""Report the geometric volume represented by a Gmsh reservoir cavity."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import gmsh

from axialstress.cavity_volume import (
    enclosed_volume_m3,
    orient_closed_cavity,
    read_gmsh_cavity_surface,
)
from axialstress.paper_bpr import file_sha256


def main() -> None:
    """Measure cavity discretization against specified ellipsoid dimensions."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mesh", type=Path, required=True)
    parser.add_argument("--length-m", type=float, default=6000.0)
    parser.add_argument("--width-m", type=float, default=3000.0)
    parser.add_argument("--thickness-m", type=float, default=1000.0)
    parser.add_argument("--output-json", type=Path)
    args = parser.parse_args()
    dimensions_m = (args.length_m, args.width_m, args.thickness_m)
    if any(not math.isfinite(value) or value <= 0 for value in dimensions_m):
        parser.error("ellipsoid dimensions must be finite and positive")

    vertices, faces = read_gmsh_cavity_surface(args.mesh)
    volume_m3 = enclosed_volume_m3(vertices, orient_closed_cavity(vertices, faces))
    ideal_m3 = math.pi * math.prod(dimensions_m) / 6.0

    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.open(str(args.mesh))
        _, element_tags, _ = gmsh.model.mesh.getElements(3)
        tetrahedra = sum(len(tags) for tags in element_tags)
    finally:
        gmsh.finalize()

    report = {
        "mesh": str(args.mesh),
        "mesh_sha256": file_sha256(args.mesh),
        "nominal_ellipsoid_dimensions_m": dimensions_m,
        "ideal_ellipsoid_volume_m3": ideal_m3,
        "polyhedral_cavity_volume_m3": volume_m3,
        "relative_volume_difference": (volume_m3 - ideal_m3) / ideal_m3,
        "tetrahedra": tetrahedra,
        "cavity_faces": len(faces),
        "cavity_vertices": len(vertices),
        "mechanical_convergence_established": False,
    }
    rendered = json.dumps(report, indent=2) + "\n"
    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
