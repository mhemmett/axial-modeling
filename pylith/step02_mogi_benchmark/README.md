# Step 02: synthetic Mogi benchmark

This bounded elastic solve compares a pressurized spherical cavity in PyLith
with the analytical Mogi half-space displacement. The case uses synthetic
properties and geometry; it does not use OOI observations or values from the
paper's reported results.

The cavity radius is 200 m at 2 km depth. The rectangular domain extends 8 km
from the source axis horizontally and 8 km below the free surface. The host
rock has density 2,800 kg/m³, shear modulus 16 GPa, and bulk modulus 26.67 GPa.
The cavity receives a 10 MPa pressure increase, the top is free, the base is
fixed vertically, and the sides use roller constraints.

Run `make mogi-benchmark` from the repository root. The command generates a
mesh with fewer than 3,500 linear tetrahedra, runs PyLith with a 300 s timeout,
and compares the surface displacement vectors with the analytical solution.
The output reports peak uplift and relative errors; generated files remain
under this directory and are ignored by Git.

The coarse mesh produces 0.626 mm nearest-axis uplift, 33.2% below the
analytical value, and a 37.2% surface-vector L2 error. This verifies positive
inflation response and the PyLith comparison path. The mismatch is too large
for quantitative validation, and the finite-domain result has not been shown
to converge under refinement.
