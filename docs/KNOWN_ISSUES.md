# Known issues

- The bounded PyLith 5.0.2 elastic-cavity solve passes with 2,761 tetrahedra.
  The bundled Gmsh command-line interface still lacks `libGLU.so.1`; mesh
  generation uses the Gmsh 4.15.2 Python API from the project Conda environment.
- The paper's model-box dimensions, several elastic and viscoelastic constants,
  tensile strength, host-rock density, and parts of the loading convention are
  absent or ambiguous in the allowed written sources. See
  [`parameters.yaml`](parameters.yaml) for source locations and open values.
- The publisher-served supplementary PDF carries a “Confidential manuscript
  submitted” footer. Extracted supplement parameters may reflect a
  pre-publication version and should be treated as source-qualified.
- The article cites BPR and earthquake observations needed for calibration and
  comparison. Project provenance rules prohibit fetching those source records;
  figure panels that need numerical histories cannot be reproduced without
  values in an allowed written source.
- PyLith's documented constitutive models do not provide the paper's coupled
  temperature-dependent elasticity and viscosity. PyLith also does not provide
  the paper's Winkler foundation as a native boundary condition. These gaps
  require a verified coupling implementation and a validated foundation
  treatment before the final model can be called complete. See
  [`comsol_to_pylith.md`](comsol_to_pylith.md).
- Supplementary source text reports a deep partial-reservoir depth of 2.6 km in
  prose and 2.8 km in Table S3. It also reports a 60 mm/year full spreading rate
  in the article and a -20 to 20 mm/year prescribed-velocity range in Table S1.
  Neither discrepancy is resolved by the captions or tables.
