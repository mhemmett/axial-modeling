# Method-consistent PyLith reconstruction

Axial's bottom-pressure-recorder (BPR) record constrains seafloor uplift, but
the subsurface pressure and stress are model results. **The project will infer
reservoir loading from Center BPR observations and calculate a conditional
failure threshold from converged PyLith stress fields.** Cabaniss et al.
([2020](https://doi.org/10.1038/s41598-020-67043-0)) provide the geometry,
four rheology classes, thermal laws, and tensile plus through-going
Mohr–Coulomb failure sequence. Their numerical pressure and failure curves
serve only as comparisons. The reconstruction may use stated assumptions where
their input specification is incomplete. Every such assumption must accompany
the output it affects. The first completed step fits a post-2011 pressure
history to processed Center observations without joining unknown instrument
datums. It uses a measured PyLith surface response and records the sensitivity
of unobserved intervals to pressure smoothing. The next step is a mechanics
solution with the paper's cavity load and gravity reference, followed by
thermal and viscoelastic cases. The present elastic result constrains
deployment-relative pressure changes but cannot establish a failure pressure.
A stable threshold requires both reservoir tensile failure and a connected
Mohr–Coulomb path in the modeled stress field. If those conditions remain
sensitive to observation gaps or unresolved material properties, the result
will be a bounded conditional estimate rather than a single eruption value.

## Observation-to-pressure baseline

`make paper-bpr` exports candidate processed Center channels from the two
[cited archives](source_audit.md#observation-handling). `make
method-reconstruction` selects the original on-hour observations at seven-day
UTC grid points from 13 April 2011 through 22 April 2015. The chosen start
follows the 2011 eruption deflation maximum in the processed Center record:
1513.092 m at 12:00 UTC on 11 April 2011, within the 14 days after the
eruption. The next observed eruption was on 24 April 2015. The grid stops
before that event. The exported BPR values have already been filtered by their
archives; the script does not create new observations or interpolate gaps.

Each deployment has an unknown absolute depth datum. The inverse problem
therefore fits the change in depth from that deployment's first selected
sample. Depth decreases correspond to uplift. A one-megapascal elastic PyLith
solve gives the surface displacement at each recorded instrument coordinate.
The pressure-to-uplift operator uses that response. The first pressure change
is set to zero on 13 April 2011. A squared second-difference penalty fills
pressure values that the observation differences cannot identify. The nominal
dimensionless penalty is 1; 0.1 and 10 expose sensitivity. These are project
choices, not parameters reported by Cabaniss et al. Neither their predicted
pressure nor their failure pressure enters the fit.

The local output under `data/processed/method_reconstruction_2011_2015/`
contains the source digests, pressure history, and observation-level residuals.
With the currently exported files and the existing coarse elastic PyLith
response, the three deployment-relative uplift changes are 0.606, 0.608, and
1.133 m. Their static elastic pressure equivalents are 21.9, 21.9, and
39.8 MPa. The nominal fit has 0.0222 m root-mean-square residual. Five of
210 pressure parameters lack independent constraints in the observation
design. The last pre-eruption pressure changes are 61.8, 73.4, and 83.3 MPa
for penalties 0.1, 1, and 10. This range measures sensitivity to one
regularization choice; it is neither an uncertainty interval nor a tested
eruption threshold. The pressure values also depend on the zero-change
baseline and fixed-base, coarse-mesh elastic response. A finer mechanics
solution and source-channel review may change them.

## Route to a failure threshold

First, retain deployment-specific observations and quantify pressure
sensitivity to the unobserved intervals and initial state. A fit with large
gap sensitivity cannot identify a unique pressure at the 2015 event. Second,
run the paper's four rheology classes in PyLith using the documented
temperature, geometry, gravity, cavity loading, lateral rollers, and basal
spring prescription. Inputs absent or contradictory in the paper must be
fixed before looking at its model outputs and varied over stated ranges.
Third, recompute the Center pressure operator for each rheology and forward
run its fitted loading. Inspect saved cavity-wall displacement for volume
change and saved cell stress for tensile failure at the reservoir and a
connected Mohr–Coulomb path to the seafloor. Report the first time both
conditions hold and the corresponding fitted pressure, with mesh, timestep,
initial-state, datum-gap, and strength sensitivity. Do not label a threshold
stable until those numerical and assumption sensitivities are resolved.

A threshold near the published value would support this set of PyLith
assumptions. A different stable threshold would identify a model difference
worth explaining. If gap or material sensitivity remains broad, the BPR
record alone does not support a single stress-failure pressure. These outcomes
all clarify how far BPR data can constrain volcanic failure at Axial.
