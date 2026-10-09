# Step 05: elastic ellipsoidal response at OOI BPR sites

This diagnostic computes the static surface displacement from a 1 MPa
overpressure on the written 6 km × 3 km × 1 km reservoir geometry. A uniform
elastic host uses E = 50 GPa and ν = 0.25; density is 2800 kg/m³. The Poisson
ratio, density, box dimensions, and fixed-base/roller boundaries are explicit
setup assumptions because the written benchmark does not specify all of them.

Run `make ellipsoid-bpr-check` from the repository root. The command generates
a bounded tetrahedral mesh, runs PyLith, interpolates the unit-load response
at both BPR coordinates, calibrates pressure against Central uplift, and
reports the Eastern-site prediction. Derived observations and solver output
remain local under ignored `data/processed/` and `pylith/step05_ellipsoid_elastic/output/`.

Run `make ellipsoid-mesh-sensitivity` to compare Central and Eastern compliance
across four bounded mesh resolutions. It runs four independent PyLith solves
under the same 300 s per-solve limit and writes its summary under ignored
`data/processed/`.

The current four-resolution check does not meet its 5% compliance-change
tolerance. Treat the OOI pressure history and Eastern-site error as provisional
until a refined mesh stabilizes both station responses.

This is a linear-elastic compliance check, not the temperature-dependent
viscoelastic model. Central is fitted by construction; Eastern is a held-out
spatial check. It does not reproduce eruption-cycle memory or use paper
observation datasets, published results, or figure values.
