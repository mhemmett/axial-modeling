# Step 09: OOI pressure history and ellipsoid Maxwell response

This diagnostic applies an independently constrained pressure history to the
ellipsoidal reservoir and compares the resulting viscoelastic surface response
with OOI bottom-pressure-recorder (BPR) observations. It extends the static
ellipsoid check through time while retaining the current coarse mesh and
single-branch material assumptions.

Run `make ooi-maxwell-ellipsoid-check` after fetching and processing Central
and Eastern OOI BPR records. The command generates a 1 MPa static elastic
response on a 2,761-tetrahedron mesh, converts Central relative uplift to
pressure using that compliance, and averages the aligned uplift and pressure
series by calendar month. It applies the resulting history to a one-branch
Maxwell PyLith run with `E = 50 GPa`, `nu = 0.25`, and viscosity
`1e18 Pa s`. PyLith linearly interpolates between monthly TimeHistory values;
see the [NeumannTimeDependent boundary condition](https://pylith.readthedocs.io/en/v5.0.2/user/components/bc/NeumannTimeDependent.html)
and [SpatialData TimeHistory format](https://spatialdata.readthedocs.io/en/latest/user/file-formats/time-history.html).

The pressure baseline is zero at the first common finite OOI observation. The
static compliance currently is not mesh-converged, so the inferred pressure
range and both modeled displacement errors are provisional. The OOI aggregate
quality flags are retained without filtering; the current records report
`NOT_EVALUATED`. This 2014–2026 forward check uses no paper-supplied
observations or publication data and does not reproduce the full coupled,
temperature-dependent model.

The same run postprocesses each Cauchy-stress record with the Mohr–Coulomb
criterion and searches for a face-connected path from the cavity to the top
surface. The diagnostic currently uses `C = 1 MPa`, `phi = 25°` directly, and
zero pore pressure; it reports cavity tensile stress without applying an
unspecified tensile cutoff. It reports both the first saved path record and a
linear stress-interpolated onset between the first saved records that bracket
the transition. The interpolation assumes a monotonic path change within the
interval and does not integrate PyLith between records. These assumptions make
the path and candidate tensile threshold provisional. They do not predict an
eruption.

Meshes, time-history inputs, PyLith logs, and HDF5 fields are generated in a
temporary directory. The summary JSON and aligned model/observation CSV remain
under ignored `data/processed/`.
