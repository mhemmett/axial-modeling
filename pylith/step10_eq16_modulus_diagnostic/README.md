# Step 10: printed Young's-modulus law diagnostic

Equation 16 defines a temperature-dependent Young's modulus, but its printed
trend conflicts with the brittle and ductile descriptions in the supplement.
This diagnostic applies the equation exactly as printed in PyLith so its
mechanical effect is measurable without silently reversing the formula.

Run `make eq16-maxwell-ellipsoid-smoke` for constant conductivity or
`make eq16-hydrothermal-maxwell-ellipsoid-smoke` with the written Eq. 22
conductivity. Both runs solve the zero-source steady thermal equation, evaluate
Eq. 15 viscosity and Eq. 16 modulus at tetrahedron centroids, and apply a
constant 1 MPa cavity load to a one-branch Maxwell model. The modulus varies
from approximately 25 GPa at the cold end to 33.3 GPa at the 1200 °C cavity;
the source text describes a decrease toward 25 GPa at the magma chamber.

The mesh contains 2,761 tetrahedra, and the imposed thermal boundaries are
0 °C at the surface, 1200 °C at the cavity, and a 30 °C/km extension on the
sides and base. The modulus law remains a source-conflict diagnostic, and the
single Maxwell branch, assumed Poisson ratio, and fixed-base boundaries remain
unresolved setup choices. These runs verify the printed law through PyLith;
they do not establish the intended modulus relation or reproduce a figure.

Meshes, fields, and solver output are removed after each run. Summary JSON
files remain under ignored `data/processed/`.
