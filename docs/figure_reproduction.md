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
| Fig. 1 | Axial map, reservoir setting, and Center BPR location. | Report Fig. 1a uses independent bathymetry, lava-flow, earthquake, and seismic-velocity records. Fig. 1b pairs the same GMRT relief with the actual 150 m PyLith cavity mesh in a cropped perspective view. The model origin is placed at the archived 2011–2013 Center coordinate for display; the mesh does not independently establish its geographic location. The flat model top is separate from observed relief. |
| Fig. 2 | Center BPR inflation and deflation history with earthquake counts and eruption markers. | Report Fig. 2 shifts actual archived noon observations from 1997–2015 into a history with an explicit equal-1998-and-2011-level scenario. Paired observations anchor two overlapping handoffs; short gap handoffs assume zero net unobserved deformation. The 1998–2000 gap uplift is inferred from the stated level assumption and constrained in the historical pressure fits. The 1998, 2011, and 2015 drops are recorded within deployments. Earthquake counts are omitted because a compatible full daily series is unavailable. |
| Fig. 3 | Spatial material properties for four rheologies. | A new 4 × 4 property section uses the source's uniform viscosity, literal thermal laws, and local PyLith inputs. Its elastic reference and uniform modulus remain documented choices; the printed thermal modulus conflicts with the source's labels. |
| Fig. 4a | Reservoir overpressure required to reproduce the Center BPR deformation history. | A new 2011–2015 panel shows three Maxwell pressures fitted to actual Center BPR deployments. Their unresolved datums and smoothing-dependent gap values prevent a complete paper-interval reconstruction. |
| Fig. 4b | Reservoir volume change required to reproduce the Center BPR history. | A matching panel integrates PyLith cavity displacement for the same three fitted histories. The 150 m mesh has a 0.66% volume deficit; the elastic volume curve and a fully resolved Maxwell spectrum remain open. |
| Fig. 5 | Tensile and Mohr–Coulomb failure fields at predicted and observed eruption times. | Five PyLith rows follow the paper's order. Each historical cycle pairs its first sampled joint failure with the observed eruption date; a third column group reports the post-2015 screen. Blank first-failure panels identify cases that never cross jointly. The tectonic row uses a separate ridge-normal loading run and BPR refit. |
| Fig. 6 | Conceptual eruption mechanism. | Omitted from this report. Figure 5 screens stress thresholds and connected yielded cells; it does not simulate fracture growth or magma transport needed to establish an eruption mechanism. |

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

Report Figure 1a is generated by the figure1-map Make target as
figures/figure1_axial_geologic_map.pdf. It uses independent GMRT and MGDS
source records. The updated Center BPR marker is the 2011–2013 deployment
coordinate from MGDS DOI 10.1594/IEDA/322282. The dashed low-velocity
contours are project-derived proxies and do not locate the PyLith cavity.
The colorbar uses GMRT elevations with a warm-shallow, cool-deep bathymetry
ramp from −2,900 to −1,350 m.
Report Figure 1b is generated by report-figure1b as
figures/report_figure1b_pylith_context.pdf. It reads the saved
33,980-tetrahedron PyLith gravity-equilibrium output and extracts all 3,630
meshed cavity faces. A 16 by 16 by 3.5 km crop shows the cavity beneath
resampled GMRT bathymetry. The origin is placed at the archived 2011–2013
Center BPR coordinate solely for visualization. The observed relief is
raised 1.1 km for visibility. The northeast quarter is removed to expose the cavity while retaining the
other three quarters of observed caldera relief. The vertical display scale is exaggerated about 2.2-fold, and the
solved model top remains flat. Source hashes, dimensions,
display transforms, and this coordinate assumption are recorded locally in
data/processed/report_figure1b_pylith_context_summary.json. The panel
does not reproduce the source's temperature or modulus cut planes.

Report Figure 2 is generated by the report-figure2 Make target as
figures/report_figure2_center_bpr.pdf. It selects actual noon depth fields
from all nine available archived Center deployments spanning 1997–2015,
removes two noon values at each deployment boundary to reduce transients,
and marks retained sampled days. Thirty paired noons near each of the two
overlap handoffs set the display offset. Seven-noon medians anchor other
handoffs across unobserved gaps, assuming no net deformation during each
gap. The 708-day 1998–2000 gap is assigned 0.767 m of uplift under an equal
pre-1998 and pre-2011 level scenario. This is an
assumption because the cross-gap displacement is unobserved.
The three eruption drops occur within recorded deployments, so none is
inserted by the splice. The source hashes, selected sample counts, shifts,
and gap assumptions are recorded locally in
data/processed/report_figure2_center_bpr_summary.json. The historical
separate-datum pressure fits use the 0.755 m uplift between their sampled
weekly gap endpoints. This includes the 0.767 m unobserved gap assumption
and the observed changes between the sampled endpoints and the display's
seven-noon edge medians. No BPR sample is invented. Its plotted
1998 eruption time is a January month interval, not an invented exact
day. The source's earthquake-count series is omitted because a compatible
complete daily series has not been established.

The Figure 3 analogue is generated by the report-figure3-150m Make target
as figures/source_value_figure3_properties.pdf. Its section is 0–10 km
along the N30°W reservoir axis and 0–4 km deep. Colorbars give GPa,
Pa s, °C, and W/(m K). The thermal fields come from the solved local
temperature archives, and the script checks their hashes against the
model summary. The figure is a method-consistent reconstruction, not an
exact property-map reproduction.

The Figure 4 analogue is generated by the report-figure4-150m Make target
as figures/source_value_figure4_pressure_volume.pdf. Both panels span
13 April 2011 to the observed 24 April 2015 eruption. They show weekly
model states and actual selected BPR samples with separate deployment
datums. Panel a reports MPa relative to the initial modeled state; panel b
reports km³ from PyLith cavity-face integration. The script checks the
pressure, volume, and model-summary hashes. The observed eruption star is
an input date, not a model prediction. No author output was digitized or
used to set the curves. This Figure 4 panel still omits the 1998–2011
pressure curves and elastic case. Unresolved offsets, the fixed base, and
time-step sensitivity prevent claiming a full Figure 4 reproduction.

Report Figure 5 is generated by the report-figure5-150m Make target as
figures/report_figure5_failure.pdf. It intersects actual 150 m PyLith
tetrahedra with a vertical plane selected to expose the saved 3D path at joint
failure. Off-center cuts have smaller visible reservoir sections although
the cavity geometry is fixed. Other states use the central N30°W plane.
Two panel pairs show first
sampled joint failure and the observed 6 April 2011 or 24 April 2015 state.
The final column shows first failure or the latest post-2015 state. Rows follow
the source's order: non-temperature-dependent elastic, uniform Maxwell,
tectonic plus hydrothermal Maxwell, hydrothermal Maxwell, and thermal Maxwell.
Orange denotes Mohr–Coulomb yield with 1 MPa cohesion, 25° friction, and zero
assumed pore pressure. Blue denotes positive principal tension under a zero
tensile-strength screen. One tensile cavity element suffices for the tensile
part of the joint criterion; a cavity-to-surface face-connected shear path is
also required. The paper does not specify its discrete element-connectivity
rule. Black arrows project the first saved tensile cavity cell onto
the section. An arrow does not imply that the element lies in the section.
The magenta line projects the three-dimensional shear path. Magenta polygon
outlines mark path cells that actually intersect the selected section. First
joint panels label the retrospective days before the observed eruption. A panel
without joint failure through the saved observed-date state is left blank.

Separate PyLith continuations hold the last BPR-fitted pressure for one day
through 6 April 2011 and two days through 24 April 2015. The tectonic row
applies the paper's 60 mm/year full spreading rate along a project N60°E
normal to the N30°W model reservoir axis. This azimuth is an explicit
approximation because the paper does not tabulate the local ridge-normal
azimuth. The 50 by 50 km box spans 68.3 km along that project direction;
the imposed affine velocity differs by 60 mm/year across the full span.
The run removes the modeled tectonic
displacement before refitting reservoir pressure. Supplementary Table S1
instead lists velocities from −20 to 20 mm/year; the row therefore follows
the main-text full rate and states this discrepancy. PyLith shifts one
penultimate saved time when matching a partial final step; the plot uses the
actual saved timestamps and interpolates only the fitted pressure at those
times. Generated stress hashes, projected arrow locations, and whole-mesh
failure flags are saved in
data/processed/report_figure5_failure_summary.json. The 1998–2000 BPR gap,
separate deployment datums, one Maxwell branch, fixed base, and seven-day
time step limit any eruption-timing inference. No published stress image or
pressure output supplies a plotted field.

The 150 m gravity reference and some fitted runs use eight MPI ranks; later
runs use 16. PyLith changes HDF5 vertex and cell numbering with the rank
count. The resource guard binds each 16-rank solve to 16 distinct allowed CPUs.
Before adding gravity stress or comparing Figure 5 panels, the code
matches every vertex by its exact coordinates and every tetrahedron by its
four vertices. It rejects any changed or missing geometry. This remaps
saved fields without interpolating stress or altering the mesh.
For the uniform 1998–2011 history, the eight-rank fitted run and 16-rank
eruption-date continuation have the same loads through their shared weekly
states. At saved indices 100 and 500, their aligned Cauchy stress differs by
0.118 and 0.132 Pa RMS, with maximum cell-component differences of 2.55 and
1.74 Pa. The corresponding eight-rank stress RMS values are 13.8 and
2.35 MPa. These values check MPI partition consistency at two shared times;
they do not establish temporal or mesh convergence.

The 150 m historical uniform Maxwell fit first meets the joint screen on
19 January 1999 at a fitted pressure change of −14.78 MPa. Its first
positive-pressure joint state is on 4 January 2000 at 12.56 MPa. Both lie
in the unobserved 1998–2000 gap. The final pre-2011 state has no joint
failure, so these crossings do not establish a useful eruption forecast.
The thermal historical fit has no joint crossing in its weekly history.
Its 6 April 2011 continuation holds the last fitted 3.31 MPa pressure change
for one day and still has no joint failure; the cavity maximum principal
stress is −20.47 MPa.
The historical hydrothermal fit has no tensile cavity state or connected
shear path in its weekly history. Its final fitted pressure change is
6.49 MPa, with a cavity maximum principal stress of −25.62 MPa. Holding
that pressure for one day to 6 April 2011 also leaves no joint failure;
the cavity maximum principal stress is −25.63 MPa.
The separate historical spreading-plus-hydrothermal refit has no tensile
cavity state or connected shear path through 6 April 2011. Its event-date
pressure change is 6.62 MPa and cavity maximum principal stress is
−25.30 MPa under the stated 60 mm/year full spreading rate.

Across the saved post-2015 weekly states through 12 October 2026, the
uniform, thermal, hydrothermal, and spreading-plus-hydrothermal Maxwell fits
have neither cavity tension nor a connected shear path. Their maximum cavity
principal stresses are −23.13, −23.29, −27.94, and −27.93 MPa, respectively.
The spreading sensitivity refits BPR pressure after subtracting modeled
tectonic uplift; its last pressure change is 4.81 MPa. These are calculated
PyLith stresses under separately fitted pressure histories; they are not
measured failure thresholds.

At the observed 24 April 2015 eruption date, separate two-day PyLith
continuations of the three source Maxwell fits also have no joint failure.
Their cavity maximum principal stresses are −26.34, −25.85, and −30.16 MPa
for uniform, thermal, and hydrothermal rheology, respectively.
The spreading-plus-hydrothermal refit also has no cavity tension or connected
shear path by 24 April 2015. Its event-date pressure change is 4.33 MPa and
its cavity maximum principal stress is −30.13 MPa.
