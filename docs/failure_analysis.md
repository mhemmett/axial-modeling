# Failure threshold calculation

The paper defines an eruptible state by tensile failure at the reservoir and
defines eruption when that failure coincides with a connected Mohr--Coulomb
path to the surface. The project evaluates these conditions from saved PyLith
stress fields; the analysis does not change the mechanical solution.

`axialstress.failure` converts PyLith stress components ordered `xx, yy, zz,
xy, yz, xz` into symmetric tensors with tension positive. The Mohr--Coulomb
criterion uses compression-positive effective principal stresses, cohesion
`C`, and friction angle `phi`:

```text
F = sigma_1 - sigma_3 - (sigma_1 + sigma_3) sin(phi) - 2 C cos(phi)
```

Cells with `F >= 0` count as shear-yield cells. `axialstress.topology` finds
tetrahedra touching the cavity and top boundary, then searches failed cells
that share triangular faces. Edge-only and vertex-only contact do not count as
a connected path.

The source labels `f = 25°` an internal friction angle but prints the criterion
as though `f` were a coefficient. It also does not specify tensile strength
or pore pressure. The current diagnostic uses `C = 1 MPa`, `phi = 25°`, and
zero pore pressure, without applying a tensile cutoff to the shear path. These
choices expose the current implementation path; they do not define an Axial
rock-failure threshold.

Run `make failure-connectivity-smoke` to check stress reading, boundary
extraction, yield calculation, and face connectivity on a synthetic Mogi
case. Run `make historical-failure-time-refinement` to compare failure-path
timing at several time steps under Center BPR forcing. The current path
onset changes with time resolution and repeated paths appear and disappear.
Neither check establishes the paper's 12--14 MPa eruption threshold. The
threshold remains unresolved until the constitutive inputs, basal boundary,
mesh response, and saved path history are stable.
