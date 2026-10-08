# Known issues

- The bounded PyLith 5.0.2 elastic-cavity solve passes with 2,761 tetrahedra.
  The bundled Gmsh command-line interface still lacks `libGLU.so.1`; mesh
  generation uses the Gmsh 4.15.2 Python API from the project Conda environment.
- The ellipsoidal-reservoir surface compliance is not mesh-converged. Four
  global and three local or mixed meshes from 2,761 to 6,772 tetrahedra changed
  Central and Eastern compliance by 21–76% between tested refinements.
  OOI-calibrated pressure and the Eastern spatial comparison remain provisional
  until refinement stabilizes.
- The paper's model-box dimensions, several elastic and viscoelastic constants,
  tensile strength, host-rock density, and parts of the loading convention are
  absent or ambiguous in the allowed written sources. See
  [`parameters.yaml`](parameters.yaml) for source locations and open values.
- The publisher-served supplementary PDF carries a “Confidential manuscript
  submitted” footer. Extracted supplement parameters may reflect a
  pre-publication version and should be treated as source-qualified.
- Independent OOI daily BPR depth records are available for Central and
  Eastern Caldera from 2014 onward. Their aggregate quality flags are marked
  `NOT_EVALUATED`, and the records do not cover the 1998 and 2011 events.
  Earthquake catalogs and datasets supplied with or cited by the paper remain
  excluded. See [`../data/README.md`](../data/README.md).
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
- Supplementary source text reports a deep partial-reservoir depth of 2.6 km in
  prose and 2.8 km in Table S3. It also reports a 60 mm/year full spreading rate
  in the article and a -20 to 20 mm/year prescribed-velocity range in Table S1.
  Neither discrepancy is resolved by the captions or tables.
