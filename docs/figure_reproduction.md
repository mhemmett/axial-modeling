# Figure reproduction record

This inventory tracks the paper's numerical and conceptual figures. Project
plots must be generated from the independent PyLith model and authorized BPR
observations. Published panels and reported values are comparison targets;
they are not inputs to the model calibration. The project uses the Center BPR
history and the reported eruption dates. The pressure history is calibrated
from Center BPR observations alone.

## Comparison rules

Use paper text, tables, captions, and plotted results to establish the target
quantity, range, timing, and presentation. Record whether each comparison uses
a textual value or a value estimated from a published plot. Do not use author
code, COMSOL files, or author-generated model fields. Recreate figure panels
from project outputs and identify any implementation difference from the
paper.

## Main figures

| Figure | Target | Current implementation and next work |
| --- | --- | --- |
| Fig. 1 | Axial map, reservoir setting, and Center BPR location. | Report Fig. 1 uses independent bathymetry, lava-flow, earthquake, and seismic-velocity records. Its 2011–2013 Center marker comes from the archived BPR metadata. Velocity-derived outlines are project proxies; the model cavity is not geolocated independently. The source's 3-D cutaway is not reproduced. |
| Fig. 2 | Center BPR inflation and deflation history with earthquake counts and eruption markers. | Report Fig. 2 shifts actual archived noon observations from 1997–2015 into a display-only history. Paired observations anchor two overlapping handoffs; gap handoffs assume zero net unobserved deformation. The 1998, 2011, and 2015 drops are recorded within deployments. Earthquake counts are omitted because a compatible full daily series is unavailable. |
| Fig. 3 | Spatial material properties for four rheologies. | A new 4 × 4 property section uses the source's uniform viscosity, literal thermal laws, and local PyLith inputs. Its elastic reference and uniform modulus remain documented choices; the printed thermal modulus conflicts with the source's labels. |
| Fig. 4a | Reservoir overpressure required to reproduce the Center BPR deformation history. | A new 2011–2015 panel shows three Maxwell pressures fitted to actual Center BPR deployments. Their unresolved datums and smoothing-dependent gap values prevent a complete paper-interval reconstruction. |
| Fig. 4b | Reservoir volume change required to reproduce the Center BPR history. | A matching panel integrates PyLith cavity displacement for the same three fitted histories. The 400 m mesh has a 4.32% volume deficit; mesh convergence, the elastic and 1998–2011 histories remain open. |
| Fig. 5 | Tensile and Mohr–Coulomb failure fields at predicted and observed eruption times. | Report Fig. 5 includes the elastic first-joint screen on 7 November 2012 and actual 22 April 2015 PyLith stress fields for three fitted Maxwell cases. The elastic path occurs too early; none of the Maxwell fits fails jointly. The 1998–2011 cycle remains unavailable. |
| Fig. 6 | Conceptual eruption mechanism. | Omitted from this report because the elastic screen fails early and the fitted Maxwell cases do not fail by the 2015 eruption. A pathway diagram would assert a mechanism that the current PyLith results do not establish. |

## Supplementary figures

| Figure | Target | Current implementation and next work |
| --- | --- | --- |
| S1 | Temperature, Young's modulus, viscosity, and thermal conductivity for all four rheologies. | One hydrothermal property slice exists. Reproduce all fields with the resolved modulus law and reported thermal boundaries. |
| S2 | Hydrothermal effect on brittle–ductile transition location. | Not reproduced. Calculate transition location for the paper's baseline and hydrothermal cases. |
| S3 | Mogi, Del Negro, two-dimensional FEM, and three-dimensional FEM compatibility, including base conditions. | PyLith benchmarks remain incomplete. Rebuild the specified responses and compare against the reported curves and ranges. |
| S4 | Surface displacement across the Winkler spring-weakening sweep. | Not reproduced. Implement the spring sweep and compare the transition from equivalent to observably different response. |
| S5 | Model geometry, thermal and mechanical boundaries, and tectonic loading. | A project schematic exists. Update it to the model configuration used for the final reproduced runs. |
| S6 | Center BPR pressure for reservoir geometries and rheologies. | Not reproduced. Run the reported geometries and compare Center-fit pressures with the published panels. |

## Required comparison record

For every numerical panel, record the project command, output file, case
configuration, units, time or spatial domain, corresponding published target,
comparison method, validation checks, and remaining discrepancy. Keep
numerical reproduction results separate from parameter calibration so that a
reported value cannot be forced by tuning an undocumented input.

Report Figure 1 is generated by the figure1-map Make target as
figures/figure1_axial_geologic_map.pdf. It uses independent GMRT and MGDS
source records. The updated Center BPR marker is the 2011–2013 deployment
coordinate from MGDS DOI 10.1594/IEDA/322282. The dashed low-velocity
contours are project-derived proxies and do not locate the PyLith cavity.
The 3-D model cutaway in the source's Figure 1 is not reconstructed.

Report Figure 2 is generated by the report-figure2 Make target as
figures/report_figure2_center_bpr.pdf. It selects actual noon depth fields
from all nine available archived Center deployments spanning 1997–2015,
removes two noon values at each deployment boundary to reduce transients,
and marks retained sampled days. Thirty paired noons near each of the two
overlap handoffs set the display offset. Seven-noon medians anchor other
handoffs across unobserved gaps, assuming no net deformation during each
gap. The 708-day 1998–2000 gap leaves its vertical alignment uncertain.
The three eruption drops occur within recorded deployments, so none is
inserted by the splice. The source hashes, selected sample counts, shifts,
and gap assumptions are recorded locally in
data/processed/report_figure2_center_bpr_summary.json. The visual splice
is not used by the separate-datum pressure fit. Its plotted
1998 eruption time is a January month interval, not an invented exact
day. The source's earthquake-count series is omitted because a compatible
complete daily series has not been established.

The Figure 3 analogue is generated by the method-source-figure3 Make target
as figures/source_value_figure3_properties.pdf. Its section is 0–10 km
along the N30°W reservoir axis and 0–4 km deep. Colorbars give GPa,
Pa s, °C, and W/(m K). The thermal fields come from the solved local
temperature archives, and the script checks their hashes against the
model summary. The figure is a method-consistent reconstruction, not an
exact property-map reproduction.

The Figure 4 analogue is generated by the method-source-figure4 Make target
as figures/source_value_figure4_pressure_volume.pdf. Both panels span
13 April 2011 to the observed 24 April 2015 eruption. They show weekly
model states and actual selected BPR samples with separate deployment
datums. Panel a reports MPa relative to the initial modeled state; panel b
reports km³ from PyLith cavity-face integration. The script checks the
pressure, volume, and model-summary hashes. The observed eruption star is
an input date, not a model prediction. No author output was digitized or
used to set the curves. The missing 1998–2011 cycle, elastic case,
unresolved offsets, fixed base, and time-step sensitivity preclude claiming
Figure 4 has been reproduced.

Report Figure 5 is generated by the report-figure5 Make target as
figures/report_figure5_failure.pdf. It intersects the actual 400 m PyLith
tetrahedra with vertical N30°W planes and colors cells by the stress screens
used in the 2011–2015 fits. Orange denotes
Mohr–Coulomb yield for 1 MPa cohesion, 25° friction, and zero assumed pore
pressure; blue denotes positive principal tension for zero assumed tensile
strength. The elastic panel uses the nominal first-joint state on 7 November
2012 at 13.09 MPa. Its section is 1.2 km off the model axis; a magenta line
projects the seven-cell three-dimensional path onto that section. The three
Maxwell panels use the last saved state, 22 April 2015, before the observed
24 April eruption. Source-output hashes, whole-mesh and section cell counts,
and path flags are saved in
data/processed/report_figure5_failure_summary.json. The elastic screen
reaches joint failure about 2.5 years early, and no fitted Maxwell case has a
connected cavity-to-surface path or cavity tension. This is a partial
analogue of the source's Figure 5 rather than an eruption prediction.
