# Reproduction blockers

The current PyLith implementation has not reproduced the paper's 12–14 MPa
temperature-dependent eruption overpressure or its eruption timing. These are
comparison targets; the present model does not satisfy the necessary numerical
or constitutive checks.

## Numerical stability

- Ellipsoid compliance changes substantially with mesh refinement, so the
  pressure history inferred from surface displacement is not yet stable.
- Production pressure calibrations use a fixed base. The paper prescribes a
  Winkler foundation, but the current finite-spring check accepts an initial
  nonlinear residual of `5.40e3` under a `1.00e4` tolerance. A tighter solve
  previously failed in KSP.
- The Mogi compatibility benchmark remains mesh-sensitive. Its current
  2,995-element case reports 44.9% vector-field error and 55.9% center error;
  the nearest refined case reports 42.7% and 54.2%. The sequence is not nested
  and does not establish convergence.
- Thermal fields also vary near the reservoir. Between two bounded meshes,
  sampled temperatures differ by as much as 324 °C. The mesh sequence is
  nonnested and does not establish a volume-norm convergence rate.
- Failure paths appear and disappear as the time step changes. Current path
  onset is therefore not a stable failure threshold.

## Missing or ambiguous inputs

- The generalized Maxwell branch fractions and relaxation spectrum are
  incomplete. Current branch properties are synthetic.
- Printed Eq. 16 makes Young's modulus rise with temperature, while the text
  describes a lower ductile modulus. The current linear 50-to-20 GPa map is a
  project assumption, not a resolved transcription.
- The failure description labels `f = 25°` as an angle but prints it like a
  coefficient. Tensile strength and pore pressure are also unspecified.
- Model-box dimensions and full-depth density are not reported. Current domain,
  density, and lateral and thermal boundary choices remain documented
  assumptions.
- Current 1998 and 2011 Center BPR fits include the observed eruption
  deflation. They are retrospective pressure diagnostics, not independent
  eruption predictions. A continuous Center history and independently
  reproduced failure threshold remain necessary.

The run records and parameter sources are in [`run_log.md`](run_log.md),
[`parameters.yaml`](parameters.yaml), and
[`iteration_parameters.md`](iteration_parameters.md).
