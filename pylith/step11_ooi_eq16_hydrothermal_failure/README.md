# Step 11: OOI hydrothermal Eq. 16 failure diagnostic

This diagnostic applies the independent OOI pressure history to a one-branch
Maxwell ellipsoid with properties transferred from a steady temperature field.
It uses Eq. 22 for hydrothermal conductivity, Eq. 15 for viscosity, and Eq. 16
for Young's modulus exactly as printed. The same cellwise modulus field drives
the static compliance calibration and the Maxwell solve.

Run `make ooi-eq16-hydrothermal-maxwell-check` after fetching and processing
Central and Eastern OOI BPR records. The temperature solve uses Eq. 14 with
zero heat production, 0 °C at the top, 1200 °C at the cavity, and a 30 °C/km
geotherm on the sides and base. Density is 2700 kg/m³ and Poisson's ratio is
assumed to be 0.25. The temperature solution is transferred once; deformation
and viscous heating do not update it.

The 2,761-tetrahedron run converged its nonlinear thermal solve in 10
iterations with relative change `6.421e-10`. Temperature ranges from 0 to
1200 °C, conductivity from 7.214 to 91.098 W/(m K), modulus from 25.00 to
33.33 GPa, and viscosity from `1.805e13` to `9.626e30 Pa s`. Static compliance
is 0.0679954 m/MPa; the inferred pressure ranges from −28.61 to 9.87 MPa. The
147 Maxwell stress records show a cavity-to-top Mohr–Coulomb path in 87 records;
the first saved record with a path occurs at 90 days. Maximum cavity tensile
stress is 52.36 MPa; no tensile cutoff is applied.

This is an OOI-only diagnostic, not a reproduction or eruption prediction.
Eq. 16 makes modulus rise with temperature, contrary to the written brittle
and ductile descriptions. Compliance is not mesh-converged, the generalized
Maxwell spectrum and tensile strength remain unresolved, and the friction angle
is used directly with zero pore pressure. The record begins in 2014, so it
does not cover the 1998 or 2011 cycles. Summary JSON and model/observation CSV
files remain under ignored `data/processed/`; meshes, logs, and HDF5 files are
temporary.
