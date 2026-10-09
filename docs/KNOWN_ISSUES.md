# Known issues

- The bounded PyLith 5.0.2 elastic-cavity solve passes with 2,761 tetrahedra.
  The bundled Gmsh command-line interface still lacks `libGLU.so.1`; mesh
  generation uses the Gmsh 4.15.2 Python API from the project Conda environment.
- The ellipsoidal-reservoir surface compliance is not mesh-converged. The
  reproducible seven-case suite changes Central and Eastern compliance by
  21–76% between tested refinements. Exploratory mixed meshes up to 13,412
  tetrahedra also change both station responses by 11–19% when cavity spacing
  is refined from 600 to 300 m. OOI-calibrated pressure and spatial errors
  remain provisional.
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
- Independent OOI daily BPR depth records are available for Central and
  Eastern Caldera from 2014 onward. Their aggregate quality flags are marked
  `NOT_EVALUATED`. The user also authorized raw-depth channels from independent
  uncabled BPR deployments spanning the 1998 and 2011 eruptions. Those checks
  read no detided or drift-corrected channel. Earthquake catalogs and source
  datasets other than the authorized raw BPR archives remain excluded. See
  [`../data/README.md`](../data/README.md).
- The raw-depth historical BPR series show five-day median subsidence of
  3.13 m and 1.00 m at the 1998 center and south stations, and 2.19 m and
  1.71 m at the corresponding 2011 stations. A homogeneous elastic Mogi source
  fit at each center reproduces the south-site event-window shape with
  correlations 0.982 and 0.997, but south-site relative L2 errors remain 0.548
  and 0.213. Across the full shared deployment records, the south-site
  correlations are 0.994 (309 daily pairs, 1997–1998) and 0.992 (324 pairs,
  2010–2011), with relative L2 errors 0.612 and 0.197. These longer comparisons
  retain raw instrument drift and tides; the point source is only a spatial
  reference, not a calibrated deformation history or eruption hindcast.
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
