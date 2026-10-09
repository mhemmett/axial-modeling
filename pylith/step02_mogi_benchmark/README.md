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
and interpolates the surface displacement from its triangles onto a fixed
41 × 41 sample grid spanning ±6 km in both horizontal directions. This keeps
the comparison points fixed when the surface mesh changes. Generated files
remain under this directory and are ignored by Git.

The 3,191-tetrahedron mesh produces 0.622 mm peak sampled uplift, a 33.6%
interpolated-axis error, and a 40.4% fixed-grid vector L2 error against the
analytical solution. This verifies positive inflation response and a
mesh-independent comparison grid. The mismatch remains too large for
quantitative validation, and the finite-domain result has not been shown to
converge under refinement.
