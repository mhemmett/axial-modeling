# Known issues

- The bounded PyLith 5.0.2 elastic-cavity solve passes with 2,761 tetrahedra.
  The bundled Gmsh command-line interface still lacks `libGLU.so.1`; mesh
  generation uses the Gmsh 4.15.2 Python API from the project Conda environment.
- The ellipsoidal-reservoir surface compliance is not mesh-converged. Five
  bounded station-region cases stay below 3,500 tetrahedra, but independently
  generated meshes are not guaranteed to be nested and response does not vary
  smoothly with target size.
  The 950 m case has fewer elements than the 1,000 m case (3,053 versus 3,124)
  and changes Central/Eastern compliance by +59.8%/+58.1%; the next 900 m case
  changes them by −35.1%/−31.5%. Repeating all five solves reproduced the
  results exactly, but no adjacent local-refinement pair meets the 5% criterion
  at both stations. Earlier seven-case results vary by 21–76%; exploratory
  mixed meshes up to 13,412 tetrahedra also change both station responses by
  11–19% when cavity spacing is refined from 600 to 300 m. OOI-calibrated
  pressure and spatial errors remain provisional.
- The OOI Maxwell forward check applies a monthly pressure history derived from
  static elastic Central compliance to a one-branch Maxwell model. Its
  2,761-tetrahedron compliance implies pressure changes from about −61 to
  +21 MPa, and its observation history includes a 122-day gap interpolated
  linearly. The pressure scale, model errors, and assumed uniform viscosity
  remain provisional; the OOI aggregate flags are `NOT_EVALUATED` and are not
  filtered.
- Under the current failure-proxy assumptions (`C = 1 MPa`, `phi = 25°` used
  directly, zero pore pressure), the OOI Maxwell stress series has a
  cavity-to-top Mohr–Coulomb path in 146 of 147 records, first at 60 days. The
  maximum cavity tensile stress is 63.97 MPa, but tensile strength is unknown
  and the cutoff is not applied. These outcomes depend on the nonconverged
  compliance and do not constitute an eruption prediction.
- The paper's model-box dimensions, several elastic and viscoelastic constants,
  tensile strength, host-rock density, and parts of the loading convention are
  absent or ambiguous in the allowed written sources. See
  [`parameters.yaml`](parameters.yaml) for source locations and open values.
- The publisher-served supplementary PDF carries a “Confidential manuscript
  submitted” footer. Extracted supplement parameters may reflect a
  pre-publication version and should be treated as source-qualified.
- Independent OOI daily BPR depth records cover Central and Eastern Caldera
  from 2014 onward; their aggregate quality flags are `NOT_EVALUATED`. Original
  non-OOI raw BPR channels span intermittent deployments from 1987 through 2013,
  including event checks for 1998 and 2011 and a 1995–96 spatial comparison.
  Separate deployment baselines do not form a continuous deformation history;
  daily means retain tidal residuals, ocean variability, and instrument drift.
  Earthquake catalogs and paper-produced analysis products remain excluded. See
  [`../data/README.md`](../data/README.md).
- The coarse ellipsoid Maxwell stress diagnostic reaches 8–12 Mohr–Coulomb
  shear-yield cells but no cavity-to-surface path under `C = 1 MPa`, `phi = 25°`,
  and zero pore pressure. Its maximum cavity tensile stress rises from 1.96 to
  2.65 MPa, but tensile strength is unspecified and the mesh is not converged;
  these values are diagnostic thresholds, not an eruption prediction.
- PyLith's documented constitutive models do not provide the paper's coupled
  temperature-dependent elasticity and viscosity. PyLith also does not provide
  the paper's Winkler foundation as a native boundary condition. These gaps
  require a verified coupling implementation and a validated foundation
  treatment before the final model can be called complete. See
  [`comsol_to_pylith.md`](comsol_to_pylith.md).
- The two-year Maxwell smoke test uses a uniform assumed viscosity of
  `10^18 Pa s` and a single Maxwell branch. The written model leaves the
  non-temperature-dependent viscosity and generalized branch fractions
  unresolved; this test only verifies PyLith's viscous-strain state evolution.
- The thermal-Maxwell smokes transfer the written Arrhenius viscosity law into
  PyLith once from a steady field; the hydrothermal variant also uses Eq. 22 in
  the heat solve. Both hold Young's modulus constant because Eq. 16 conflicts
  with the brittle and ductile descriptions. A separate diagnostic applies
  Eq. 16 as printed: over its 0–1200 °C field it produces about 25–33.3 GPa,
  rising with temperature instead of approaching 25 GPa at the magma chamber.
  The OOI hydrothermal diagnostic now uses this cellwise modulus in both the
  static pressure calibration and Maxwell run; it also applies Eq. 15 viscosity.
  Its cold-cell viscosity reaches about `9.6e30 Pa s`. These one-way runs do not
  update temperature from deformation or viscous heating, and the Eq. 16
  inconsistency remains unresolved.
- Supplementary source text reports a deep partial-reservoir depth of 2.6 km in
  prose and 2.8 km in Table S3. It also reports a 60 mm/year full spreading rate
  in the article and a -20 to 20 mm/year prescribed-velocity range in Table S1.
  Neither discrepancy is resolved by the captions or tables.
