# Meshing

`axial_box_ellipsoid.py` subtracts the paper's 6 km × 3 km × 1 km reservoir
ellipsoid from the project-directed 50 km × 50 km × 10 km domain. It creates
PyLith physical groups for `1:domain`, `cavity`, `top`, `bottom`, `x_neg`,
`x_pos`, `y_neg`, and `y_pos` in Gmsh 4.x format.

Run from the repository root after creating the `axial-modeling` environment:

```bash
conda run -p envs/axial-modeling python meshing/axial_box_ellipsoid.py \
  --lc-near 1200 --lc-far 10000 --output pylith/step00_elastic_cavity/mesh/axial_box.msh
```

The default sizes are intended for a coarse smoke test with fewer than 10,000
tetrahedra. The mesh count is printed after generation. The domain size follows
the project owner's instruction; the paper's written extent remains unknown.

`mogi_sphere.py` builds a separate spherical-cavity mesh for the synthetic
elastic benchmark. Run `make mogi-benchmark` to generate its 16 km × 16 km ×
8 km domain and compare PyLith surface displacement with the analytical Mogi
field. The bounded run uses fewer than 3,500 tetrahedra; the mesh and solver
outputs remain ignored under `pylith/step02_mogi_benchmark/`.
