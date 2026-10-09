# Known issues

- The bounded PyLith 5.0.2 elastic-cavity solve passes with 2,761 tetrahedra.
  The bundled Gmsh command-line interface still lacks `libGLU.so.1`; mesh
  generation uses the Gmsh 4.15.2 Python API from the project Conda environment.
- The spherical PyLith/Mogi benchmark has not converged with domain or mesh
  changes. The 3,191-element case with 8 km half-width and bottom depth has
  40.4% fixed-grid vector error; the 2,784-element 12 km case has 58.0% error
  and 61.4% lower peak uplift. Both use the same target sizes, but their
  independently generated tetrahedra are
  not nested, so the difference cannot be attributed to the domain alone.
  Neither case provides quantitative validation.
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
  pressure and spatial errors remain provisional. Localized surface-box meshes
  with 2,586–2,664 tetrahedra reduce the 50-to-25 m compliance change below
  0.1% at both sites, but intervening Eastern changes reach 19.8% and mesh
  counts are not monotone. At the 25 m target, the nearest surface vertices
  remain 139 m from Central and 102 m from Eastern. This pair does not
  establish convergence.
- The fixed-base substitute for the unspecified Winkler foundation also lacks
  a demonstrated domain-converged response. A bounded 20/30/40 km depth sweep
  embeds both BPR coordinates as surface mesh vertices and stays below 2,900
  tetrahedra per mesh. Relative to 20 km, Central compliance changes by
  `+6.54%` at 30 km and `−1.34%` at 40 km; Eastern changes by `−7.30%` and
  `+4.66%`. The independently generated meshes are nonnested, so these
  nonmonotonic changes do not establish convergence or Winkler equivalence.
- The OOI Maxwell forward check applies a monthly pressure history derived from
  static elastic Central compliance to a one-branch Maxwell model. Its
  2,761-tetrahedron compliance implies pressure changes from about −61 to
  +21 MPa, and its observation history includes a 122-day gap interpolated
  linearly. The pressure scale, model errors, and assumed uniform viscosity
  remain provisional; the OOI aggregate flags are `NOT_EVALUATED` and are not
  filtered.
- A separate OOI pressure inversion fits Central uplift with a one-branch
  Maxwell response kernel and holds Eastern out. It reduces Central RMSE to
  `0.00495 m` while Eastern RMSE remains `0.225 m`; the inferred pressure spans
  `−60.4` to `+11.8 MPa`. Direct PyLith histories agree with kernel
  superposition to relative L2 errors below `0.001`, which verifies the
  inversion implementation but not its pressure scale. GCV smoothing, uniform
  Maxwell properties, interpolated monthly observations, and the
  nonconverged mesh remain assumptions; aggregate OOI flags are retained
  without filtering.
- Raw BPR event-window Maxwell-kernel inversions extend the pressure check to
  1998 WC81/WC82A and 2011 NeMO Center/South. Center RMSE is `0.093 m` and
  `0.125 m`; held-out South RMSE is `0.535 m` and `0.713 m`, with positive
  biases of `0.362 m` and `0.385 m`. The inferred pressure reaches `−107 MPa`
  and `−72 MPa`. Direct PyLith responses agree with their kernels within
  `0.13%` relative L2, but these large pressure amplitudes and Southern
  residuals leave the physical source scale unresolved. The weekly grid,
  smoothing prior, one-branch properties, raw ocean variability, and
  nonconverged mesh remain limitations.
- A bounded static PyLith check now uses ten original NCEI raw BPR deployments
  from 1987–1996 and predicts three overlapping spatial holdouts. The 43-day
  WC51/WC61 check has `0.020 m` RMSE and `0.685` correlation. In 1995–96, WC68
  fit holdouts WC69 and WC67 have `0.183 m` and `0.038 m` RMSE, with `0.876`
  and `0.943` correlation. Held-out residuals retain drift and ocean
  variability. Same-station pressure fits reach `+294 MPa`, so these scales
  are not physical estimates; most 1987–93 deployments lack simultaneous
  BPR holdouts. This static, nonconverged check extends raw coverage but does
  not reconstruct the eruption-cycle pressure history.
- Under the current failure-proxy assumptions (`C = 1 MPa`, `phi = 25°` used
  directly, zero pore pressure), the OOI Maxwell stress series has a
  cavity-to-top Mohr–Coulomb path in 146 of 147 records, first at 60 days.
  Linear stress interpolation estimates onset at 32.0 days between the 30- and
  60-day records; it assumes monotonic path change and does not integrate
  PyLith between outputs. The maximum cavity tensile stress is 63.97 MPa, but
  tensile strength is unknown and the cutoff is not applied. These outcomes
  depend on the nonconverged compliance and do not constitute an eruption
  prediction.
- The provisional Mohr–Coulomb check on twelve three-branch historical stress
  histories finds cavity-to-surface paths within 196 days in every window,
  including all ten inter-eruption intervals. The 1998 and 2011 eruption
  windows first have paths by days 7 and 21, respectively; linear stress
  interpolation estimates the 2011 crossing at day 17.61. The zero-pore-
  pressure `1 MPa` cohesion and `25°` friction proxy therefore does not
  distinguish eruptions from non-eruption periods under synthetic branch
  parameters. The written joint tensile-plus-shear condition leaves strength
  unspecified and reports a saved-record envelope: maximum cavity tension at
  a connected-path record is `94.0 MPa` in 1998, `71.1 MPa` in 2011, and at
  most `58.3 MPa` in an inter-eruption window. Using unrounded output values,
  `(58.3221, 71.0951] MPa` separates these windows only for this diagnostic,
  synthetic rheology, and unconverged mesh; it is not a calibrated strength
  range or eruption predictor. The added 2002–04 Center/South window brackets
  a path at day 53.64, another quiet-period path under the same synthetic setup.
  A time-step refinement of the first 80 days moves the interpolated crossing
  from day 17.61 to day 2.29 for 2011 and from day 53.64 to day 26.93 for
  2002–04. Half-day and quarter-day results agree within 0.01 day for each
  first crossing, but the paths appear and disappear repeatedly. The 80-day
  quarter-day runs complete in both windows. These crossings are not persistent
  or resolution-independent eruption times. The full branch spectrum remains
  unknown.
- The paper's model-box dimensions, several elastic and viscoelastic constants,
  tensile strength, host-rock density, and parts of the loading convention are
  absent or ambiguous in the allowed written sources. See
  [`parameters.yaml`](parameters.yaml) for source locations and open values.
- The publisher-served supplementary PDF carries a “Confidential manuscript
  submitted” footer. Extracted supplement parameters may reflect a
  pre-publication version and should be treated as source-qualified.
- Independent OOI daily BPR depth records cover Central and Eastern Caldera
  from 2014 onward; their aggregate quality flags are `NOT_EVALUATED`. Original
  non-OOI raw BPR channels span intermittent deployments from 1987 through 2022,
  including event checks for 1998 and 2011, later deployment overlaps, and a
  1995–96 spatial comparison. Several later records overlap the OOI era.
  Separate deployment baselines do not form a continuous deformation history;
  daily means retain tidal residuals, ocean variability, and instrument drift.
  Earthquake catalogs and paper-produced analysis products remain excluded. See
  [`../data/README.md`](../data/README.md).
- The coarse ellipsoid Maxwell stress diagnostic reaches 8–12 Mohr–Coulomb
  shear-yield cells but no cavity-to-surface path under `C = 1 MPa`, `phi = 25°`,
  and zero pore pressure. Its maximum cavity tensile stress rises from 1.96 to
  2.65 MPa, but tensile strength is unspecified and the mesh is not converged;
  these values are diagnostic thresholds, not an eruption prediction.
- PyLith's documented constitutive models do not evaluate the paper's
  temperature-dependent elasticity and viscosity internally; a driver must
  map the steady thermal solution into material databases and validate each
  case. PyLith also does not provide the paper's Winkler foundation as a native
  boundary condition. Both the four-case model comparison and a validated
  foundation treatment remain incomplete. See
  [`comsol_to_pylith.md`](comsol_to_pylith.md).
- The two-year Maxwell smoke test uses a uniform assumed viscosity of
  `10^18 Pa s` and a single Maxwell branch. The written model leaves the
  non-temperature-dependent viscosity and generalized branch fractions
  unresolved; this test only verifies PyLith's viscous-strain state evolution.
- The separate three-branch PyLith smoke uses synthetic viscosities and shear
  fractions. Its independent stress reconstruction matches all saved PyLith
  Cauchy stresses to relative L2 error `1.99e-16`, and its largest saved time
  interval satisfies the documented one-fifth relaxation-time limit. A
  two-year 30-day versus 15-day refinement changes final stress by 1.82%,
  viscous strain by 8.77%, and displacement by 0.917% in relative L2 norm.
  This pair quantifies temporal sensitivity but does not establish convergence
  or validate the paper's unspecified branch spectrum.
- Three-branch raw-BPR diagnostics use daily Center records to infer pressure
  through static ellipsoid compliance, then check held-out South deployments
  across the 1998 and 2011 eruptions and nine additional intervals from 1995
  through 2022. Event-window South RMSE is `0.503 m` and `0.680 m`; deployment
  intervals range from `0.043 m` to `1.242 m`. The 2013–15 South 2 holdout
  has `0.358 m` RMSE; a separate South 1 holdout has `1.096 m` RMSE and
  `−0.988 m` bias. The 2015–17 South 2 holdout has `0.265 m` RMSE and
  `−0.245 m` bias. The 2018–20 and 2020–22 South holdouts have `0.105 m` and
  `0.043 m` RMSE, and `−0.096 m` and `−0.017 m` bias. Their high correlations
  coexist with fitted pressure ranges
  of `−50.7` to `+26.7 MPa` and `0` to `+20.8 MPa`, respectively. The 2011–13
  correlation is `0.991` despite `−1.214 m` bias. Branch fractions and viscosities are
  synthetic, compliance is not mesh-converged, and raw observations retain
  ocean variability and drift. Continuous event runs now extend the 1998 South
  comparison through May 1999 and the 2011 history through August 2013 by
  holding terminal Center pressure constant. The 1998 follow-up has `0.063 m`
  RMSE but `−0.369` correlation; its assumed load and raw short-period
  variability preclude treating that small residual as predictive skill. These
  diagnostics do not calibrate rheology or constitute hindcasts.
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
