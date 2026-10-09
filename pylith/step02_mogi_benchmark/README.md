# Step 02: synthetic Mogi benchmark

This bounded elastic solve compares a pressurized spherical cavity in PyLith
with the analytical Mogi half-space displacement. It uses the analytical
benchmark radius, depth, and Young's modulus listed in Cabaniss et al. Table
S1, with Poisson ratio `0.25` from later Axial deformation modeling. The
comparison uses no Cabaniss model output or plotted result.

The cavity radius is 700 m at 4 km depth. The domain uses the project-directed
50 km × 50 km × 10 km dimensions. The host rock has density 2,700 kg/m³,
shear modulus 24 GPa, and bulk modulus 40 GPa. The cavity receives a 10 MPa
pressure increase, the top is free, the base is fixed vertically, and the
sides use roller constraints.

Run `make mogi-benchmark` from the repository root. The command generates a
mesh with fewer than 3,500 linear tetrahedra, runs PyLith with a 300 s timeout,
and interpolates surface displacement onto a fixed 41 × 41 grid spanning
±6 km. It checks for finite fields and positive inflation, then reports
analytical errors without applying an error threshold. The paper specifies no
numerical threshold. Generated files remain under this directory and are
ignored by Git.

The current 2,995-element mesh produces 3.49 mm peak sampled uplift, 55.9%
interpolated-axis error, and 44.9% fixed-grid vector L2 error. These errors do
not establish analytical compatibility or mesh convergence. The earlier
synthetic benchmark produced 40.4–40.7% field error and 15.0% peak-uplift
change under a far-field mesh change; those runs used a 200 m source at 2 km
depth rather than the Table S1 benchmark geometry.

At the same 50 km × 50 km × 10 km extent, a 2,103-element mesh with a 100 m
near-source target reports 49.8% field and 59.5% center error; a 3,463-element
mesh with a 65 m target reports 42.7% and 54.2%. Peak uplift changes by 8.5%
between the 75 m and 65 m cases. The meshes are independently generated and
nonnested, so this trend does not establish mesh convergence.
