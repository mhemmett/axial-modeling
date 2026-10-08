# Step 00: elastic pressurized cavity

This single-step linear-elastic solve applies a uniform 10 MPa pressure to the
ellipsoidal cavity. It fixes the base, applies roller constraints to the side
faces, leaves the top free, and writes displacement and Cauchy stress to HDF5.
The fixed base is a Phase 0 substitute for the paper's Winkler foundation.

Run from the repository root with `make smoke`. The generated mesh and output
files remain under this directory and are ignored by Git. The expected surface
uplift above the cavity is positive and lies between 0.01 m and 10 m; this is a
sanity range, not a fit to BPR observations.
