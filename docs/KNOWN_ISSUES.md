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
  pressure and spatial errors remain provisional.
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
- Under the current failure-proxy assumptions (`C = 1 MPa`, `phi = 25°` used
  directly, zero pore pressure), the OOI Maxwell stress series has a
  cavity-to-top Mohr–Coulomb path in 146 of 147 records, first at 60 days.
  Linear stress interpolation estimates onset at 32.0 days between the 30- and
  60-day records; it assumes monotonic path change and does not integrate
  PyLith between outputs. The maximum cavity tensile stress is 63.97 MPa, but
  tensile strength is unknown and the cutoff is not applied. These outcomes
  depend on the nonconverged compliance and do not constitute an eruption
  prediction.
- Treating printed `f = 25` literally as a dimensionless coefficient gives an
  equivalent friction angle of `87.71°` and a path in all 147 OOI Maxwell
  records, including the first saved record at 30 days. That case has no
  earlier no-path record to bracket. Neither friction interpretation applies a
  tensile cutoff because tensile strength is unspecified. This sensitivity
  exposes the source ambiguity but does not resolve it; both results depend on
  nonconverged compliance and a one-branch Maxwell model.
- The provisional Mohr–Coulomb check on seven three-branch historical stress
  histories finds cavity-to-surface paths within 196 days in every window,
  including all five inter-eruption intervals. The 1998 and 2011 eruption
  windows first have paths by days 7 and 21, respectively; linear stress
  interpolation estimates the 2011 crossing at day 17.61. The zero-pore-
  pressure `1 MPa` cohesion and `25°` friction proxy therefore does not
  distinguish eruptions from non-eruption periods under synthetic branch
  parameters. It is not a calibrated eruption predictor; no tensile cutoff is
  applied and the full branch spectrum remains unknown.
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
  across the 1998 and 2011 eruptions and five additional intervals from 1995
  through 2013. Event-window South RMSE is `0.503 m` and `0.680 m`; deployment
  intervals range from `0.123 m` to `1.242 m`. The 2011–13 correlation is
  `0.991` despite `−1.214 m` bias. Branch fractions and viscosities are
  synthetic, compliance is not mesh-converged, and raw observations retain
  ocean variability and drift. These diagnostics do not calibrate rheology or
  constitute hindcasts.
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
- The steady hydrothermal field converges numerically on 2,761-, 2,941-, and
  3,060-tetrahedron meshes, but temperature remains spatially sensitive. Across
  105 common probes, adjacent-pair RMSE changes are 13.45 and 35.55 °C, with a
  maximum difference of 324.29 °C near the reservoir edge. The meshes are not
  nested, so this is not a formal convergence norm. The lateral and basal
  geotherm boundary conditions also remain assumptions; see
  [`thermal_mesh_sensitivity.md`](thermal_mesh_sensitivity.md).
