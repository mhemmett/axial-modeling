# Meshing

`axial_box_ellipsoid.py` subtracts the paper's 6 km × 3 km × 1 km reservoir
ellipsoid from a prototype 50 km × 50 km × 10 km domain. Coordinates
use x east, y north, and z up; the horizontal major axis strikes N30°W with no
dip. Both ellipsoid mesh generators apply this rotation before cutting the
cavity. They create PyLith physical groups for `1:domain`, `cavity`, `top`,
`bottom`, `x_neg`, `x_pos`, `y_neg`, and `y_pos` in Gmsh 4.x format.

Run from the repository root after creating the `axial-modeling` environment:

```bash
conda run -p envs/axial-modeling python meshing/axial_box_ellipsoid.py \
  --lc-near 1200 --lc-far 10000 --output pylith/step00_elastic_cavity/mesh/axial_box.msh
```

The default sizes are intended for a coarse smoke test with fewer than 10,000
tetrahedra. The mesh count is printed after generation. The paper does not
report numerical box dimensions, so the prototype domain requires a boundary
convergence check before it can support the reproduction.

Report the cavity's geometric representation before using a mesh for reservoir
volume or stress. The default nominal dimensions follow the main paper's
6 km × 3 km × 1 km case; supply different dimensions for its sensitivity cases.

```bash
PYTHONPATH=src envs/axial-modeling/bin/python scripts/resource_guard.py \
  timeout 300 envs/axial-modeling/bin/python scripts/cavity_geometry_report.py \
  --mesh pylith/step05_ellipsoid_elastic/mesh/axial_ellipsoid.msh \
  --output-json data/processed/cavity_geometry.json
```

The report gives tetrahedron and cavity-face counts, polyhedral and nominal
ellipsoid volumes, their signed relative difference, and the mesh checksum.
It does not establish PyLith displacement or stress convergence. A bounded
geometry-only sweep is recorded in [`docs/run_log.md`](../docs/run_log.md).

`mogi_sphere.py` builds a spherical-cavity mesh for the analytical elastic
benchmark using the paper's listed source dimensions and modulus, plus the
Axial-literature Poisson-ratio prior. Run `make mogi-benchmark` to compare
PyLith surface displacement with the independent Mogi field on the
prototype 50 km × 50 km × 10 km box. The bounded run uses fewer than
3,500 tetrahedra; outputs remain ignored under
`pylith/step02_mogi_benchmark/`.
