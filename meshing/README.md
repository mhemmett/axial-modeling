# Meshing

`axial_box_ellipsoid.py` subtracts the paper's 6 km × 3 km × 1 km reservoir
ellipsoid from the temporary 40 km × 40 km × 20 km fallback domain. It creates
PyLith physical groups for `1:domain`, `cavity`, `top`, `bottom`, `x_neg`,
`x_pos`, `y_neg`, and `y_pos` in Gmsh 4.x format.

Run from the repository root after creating the `axial-modeling` environment:

```bash
conda run -p envs/axial-modeling python meshing/axial_box_ellipsoid.py \
  --lc-near 1200 --lc-far 10000 --output pylith/step00_elastic_cavity/mesh/axial_box.msh
```

The default sizes are intended for a coarse smoke test with fewer than 10,000
tetrahedra. The mesh count is printed after generation. Replace the fallback
domain when its dimensions are recovered from the supplement.
