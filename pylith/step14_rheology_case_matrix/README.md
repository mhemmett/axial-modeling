# Four-case rheology solver matrix

This bounded integration run passes four rheology configurations through the
same PyLith geometry and cavity load. Its thermal fields and material database
properties supply the project-generated 4 × 4 Figure 3-style property matrix.

Run the model and save its outputs with make rheology-case-matrix.
Generate the model and property figure with make figure3-rheology-properties.

The model uses a 50 km × 50 km horizontal domain from the seafloor to 10 km
depth. The 2,269-tetrahedron mesh contains a 6 km × 3 km × 1 km ellipsoidal
void centered 1.6 km below the seafloor. PyLith applies normal pressure traction
to the void boundary. The four cases use a shared constant 1 MPa load over two
years and save 25 stress records.

Non-temperature-dependent elastic and viscoelastic cases use a uniform
50 GPa modulus. The two temperature-dependent cases interpolate linearly from
50 GPa at 0 °C to 20 GPa at 1200 °C, clipped at those limits, following the
project owner's direction. This interpolation is an explicit project
assumption; Eq. 16 remains a separate diagnostic because its printed trend
conflicts with the stated brittle and ductile modulus labels.

The three generalized Maxwell branches use synthetic reference viscosities of
1e18, 5e17, and 2e18 Pa s, with branch fractions of 0.25. The figure shows
their geometric-mean viscosity and labels the field as synthetic. Thermal
boundaries use 0 °C at the surface, 1200 °C at the reservoir, and an assumed
30 °C/km at the sides and base. The hydrothermal case solves the enhanced
conductivity field; the other two temperature-dependent properties use the
baseline thermal field.

All four cases reached the two-year endpoint. The Maxwell stress
reconstruction relative L2 errors were 1.98e-16, 2.67e-16, and 2.73e-16.
The minimum relaxation times were 1e8 s for the uniform case and 2.5e8 s
for the temperature-dependent cases; the monthly output step was below one
fifth of each. No case formed a cavity-to-surface shear path under this common
load. All solves retain a fixed base with lateral roller boundaries. A
regional finite-spring prior and lithostatic reference traction are now
documented; this matrix still awaits a PyLith gravity/prestress equilibrium
before it can use the basal condition in absolute stress comparisons.

The summary is written to ignored
data/processed/rheology_case_matrix_summary.json. The thermal mesh fields
used by the plotting script are saved to ignored
data/processed/rheology_case_matrix_model_data.npz. The tracked project
figure is figures/figure3_rheology_property_matrix.png and its PDF version.
The fields represent project model inputs, not Cabaniss output data, and do not
calibrate pressure or eruption timing.
