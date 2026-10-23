# Independent reproduction workflow

The project replaces COMSOL with PyLith while targeting Cabaniss et al.'s
reported deformation, pressure, stress, failure, and eruption results. The
paper and supplement specify the model and provide numerical comparisons; they
do not supply author code, COMSOL files, or model fields. The reported 12–14 MPa
temperature-dependent eruption overpressure is a comparison target. It is not
used to tune undocumented inputs.

Check the reproduction requirements from the repository root:

```sh
make reproduction-status
```

The complete 1998–2011 and 2011–2015 model cycles are not implemented.
`make reproduce` currently reports unresolved requirements and exits without
generating figures. `make reproduction-status` prints the same requirements
without returning an error. Run `make paper-bpr` to export available processed
Center observations from the cited archives. The source files, field names,
checksums, source rows, times, and gaps are preserved under
`data/processed/paper_center_bpr/`. Historical data and PyLith fields remain
local and untracked.

The current event-window fits include observed eruption deflation. They
diagnose Center response but cannot independently predict eruption timing.
The candidate processed observations are not yet tied to one deployment
datum, and their exact correspondence to the paper's channel selection is
unverified. A continuous pressure history and converged failure threshold
are still needed.

The numerical checks cover the spherical Mogi response, domain and mesh
sensitivity, elastic and Maxwell PyLith solves, thermal-to-material transfer,
basal spring mechanics, and saved-stress failure connectivity. They establish
implementation behavior, not agreement with the paper. Each comparison with a
published result must record its source panel or text value, project output,
units, mesh and time resolution, and discrepancy.

Current barriers include mesh-sensitive ellipsoid compliance, an unresolved
Winkler solve, synthetic Maxwell branch values, the conflicting printed
modulus law, and path onset that changes with time-step refinement. The
[source audit](source_audit.md) and [`KNOWN_ISSUES.md`](KNOWN_ISSUES.md)
distinguish paper specifications from assumptions and measured results.
