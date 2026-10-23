# Independent reproduction workflow

The project replaces COMSOL with PyLith while targeting Cabaniss et al.'s
reported deformation, pressure, stress, failure, and eruption results. The
paper and supplement specify the model and provide numerical comparisons; they
do not supply author code, COMSOL files, or model fields. The reported 12–14 MPa
temperature-dependent eruption overpressure is a comparison target. It is not
used to tune undocumented inputs.

Run the bounded reproduction sequence from the repository root:

```sh
make reproduce
```

The target installs the local environment and PyLith binary when needed,
retrieves the historical BPR archives, processes Center records, runs the
implemented model and numerical checks, and builds the report. Set
`REPRODUCE_SKIP_FETCH=1` to use a previously downloaded archive and
`REPRODUCE_SKIP_TESTS=1` to omit pytest from the final validation targets.
Historical data and PyLith fields remain local and untracked.

The historical Center BPR records drive the 1998 and 2011 four-rheology
pressure calibrations. These current event-window fits include the observed
eruption deflation, so they diagnose the Center response and failure fields but
cannot independently predict eruption timing. The model still needs one
continuous Center history and a converged failure threshold before the paper's
eruption prediction is reproduced.

The numerical checks cover the spherical Mogi response, domain and mesh
sensitivity, elastic and Maxwell PyLith solves, thermal-to-material transfer,
basal spring mechanics, and saved-stress failure connectivity. They establish
implementation behavior, not agreement with the paper. Each comparison with a
published result must record its source panel or text value, project output,
units, mesh and time resolution, and discrepancy.

Current barriers include mesh-sensitive ellipsoid compliance, an unresolved
Winkler solve, synthetic Maxwell branch values, conflicting printed modulus
and friction conventions, and path onset that changes with time-step
refinement. The report and [`KNOWN_ISSUES.md`](KNOWN_ISSUES.md) distinguish
these assumptions from paper-specified inputs and measured results.
