# PyLith reconstruction workflow

The project uses Center BPR observations to infer reservoir loading and PyLith
stress to evaluate a conditional failure threshold. The method follows
Cabaniss et al. where their paper specifies inputs. A documented assumption
fills each remaining input gap. Their reported 12–14 MPa eruption overpressure
is a comparison target and does not tune the model. The current
[method reconstruction](method_reconstruction.md) establishes the first
deployment-aware pressure input; it does not calculate a failure threshold.

Check the reproduction requirements from the repository root:

```sh
make reproduction-status
```

`make reproduce` still checks the stricter exact-reproduction requirements and
exits on unresolved source details. `make reproduction-status` prints those
requirements. For the method reconstruction, run `make paper-bpr` and `make
ellipsoid-unit-response`, then `make method-reconstruction`. The first command
exports cited observations and provenance; the second solves the existing
elastic PyLith case; the third saves a conditional 2011–2015 pressure fit.
Historical data and PyLith fields remain local and untracked.

The current event-window fits include observed eruption deflation. They
diagnose Center response but cannot independently predict eruption timing.
The candidate processed observations are not tied to one deployment datum,
and their exact correspondence to the paper's channel selection is unverified.
The deployment-relative fit does not assign those offsets. A converged
stress-based threshold remains to be calculated.

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
