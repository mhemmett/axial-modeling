# Step 06: one-branch Maxwell ellipsoid response

This smoke test applies a constant 1 MPa overpressure to the ellipsoidal
reservoir for two years and checks PyLith's viscous-strain state evolution. The
elastic host uses E = 50 GPa, ν = 0.25, the provisional Axial density prior
of 2,700 kg/m³, and a uniform viscosity of 10¹⁸ Pa·s. These properties are
iteration starting values. The written model does not give the
non-temperature-dependent viscosity or the
generalized-Maxwell branch fractions.

For the assumed shear modulus of 20 GPa, the one-branch Maxwell time is
η/G = 5 × 10⁷ s, or about 1.58 years. Run `make maxwell-ellipsoid-smoke` from the
repository root. The 2,761-tetrahedron mesh, HDF5 output, and solver log remain
local and untracked.

This checks a constant-property PyLith Maxwell material, not the paper's
generalized, temperature-dependent thermomechanical model. It uses no OOI
observations or paper-reported results.
