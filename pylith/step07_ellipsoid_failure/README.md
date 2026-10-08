# Step 07: failure progression in the ellipsoid Maxwell model

Stress-threshold calculations need the full simulated stress history, not a
single end state. This check runs the two-year ellipsoid Maxwell diagnostic and
evaluates Mohr–Coulomb shear yield in each of its 25 saved stress records. It
also reports the first recorded time with a face-connected shear-yield path
from the reservoir boundary to the top surface and the tensile stress threshold
reached at the reservoir.

The check uses cohesion `C = 1 MPa` from Table S1, applies the reported 25°
friction angle directly as `phi`, and assumes zero pore pressure. The paper does
not specify tensile strength, so tensile failure remains a reported threshold
instead of a selected pass/fail value. The shear-path analysis does not apply a
tensile cutoff. The load, one-branch viscosity, elastic properties, and fixed
base remain explicit solver-smoke assumptions.

Run `make ellipsoid-failure-progression-smoke`. Meshes, HDF5 records, and the
machine-readable summary remain local and untracked. This evaluates model
stress only; it uses no observations or paper-reported results.
