# Cabaniss method audit

The method reconstruction follows Cabaniss et al. (2020) in PyLith. Center
bottom-pressure-recorder (BPR) observations constrain reservoir loading;
pressure, volume, stress, and failure are calculated from the new model.
The study explicitly hindcasts the 2011 and 2015 eruptions. Retrospective
calibration is part of that method. The reconstruction uses the reported
inflation cycles, constitutive laws, boundaries, and failure criterion where
specified. It documents assumptions for unresolved inputs without calibrating
them to the reported failure pressure or eruption dates. This audit compares
the published specification with the implementation and identifies unresolved
inputs. It also corrects
two earlier restrictions: processed observations from the cited archives are
eligible inputs, and the manuscript footer on the supplement does not
establish that a newer version exists. Source equations and tables define
the experiment. Published numerical curves remain comparison results and
never provide model forcing.

## Sources inspected on 23 October 2026

The article's publisher page links to these PDFs. SHA-256 digests identify
the inspected bytes; the downloads remain untracked.

| Source | SHA-256 |
| --- | --- |
| [Published article](https://www.nature.com/articles/s41598-020-67043-0.pdf) | `cf74b1f37f71e63468e5c193a0cad7e31037eb2613f599214b129fa1dba42abf` |
| [Publisher-linked supplement](https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41598-020-67043-0/MediaObjects/41598_2020_67043_MOESM1_ESM.pdf) | `bd460be233f7faeacddc776a3d30ba5ac868984617002da64451078281fa5de8` |

The publisher-linked supplement is a 20-page PDF created on 13 May 2020.
It retains the manuscript footer. Visual inspection confirms the existing
transcription of Eqs. 16, 22, 23, and 24. The footer alone supplies no evidence
of a replacement supplement. The contradictions below remain in that source.

## Method and implementation

| Requirement and source | Existing implementation | Remaining action |
| --- | --- | --- |
| Center BPR calibration; main article and Figs. 4–5 | Separate 1998 and 2011 deployment windows | Prepare the 1998–2011 and 2011–2015 cycles, with documented observation gaps and deployment datums. |
| Processed observations; article references 55–56 | Nine candidate processed Center files are exported separately | Establish the channel, offsets, and sampling used by Cabaniss before fitting cycles. |
| Ellipsoid 6 × 3 × 1 km, center 1.6 km deep; main article | Geometry and N30°W orientation implemented | Establish the reservoir position relative to Center and recover or document the unreported domain dimensions. |
| Four rheologies; Fig. 3, supplement Eqs. 9–21 | Fig. 3 labels the non-TD viscoelastic map at 10^16 Pa s; the new one-branch PyLith case uses it. Its uniform 60 GPa modulus is inferred from the color scale. Synthetic generalized-Maxwell branches remain in the legacy comparison only. | Resolve the unpublished branch fractions and FEM modulus assignment before claiming the generalized Maxwell implementation. |
| Absolute Arrhenius viscosity; Eq. 15 and Table S1 | Both 2011–2015 thermal Maxwell cases use the absolute law in their one PyLith branch; legacy generalized-branch writing uses synthetic reference viscosities. | Establish the unpublished branch mapping before extending the absolute law to a generalized Maxwell model. |
| Young's modulus; Eq. 16 and Table S1 | The 2011–2015 thermal Maxwell cases implement literal Eq. 16; a separate legacy map uses a 50-to-20 GPa project law. | Resolve the printed law against the source's labels and map. Table S1 lists 25 GPa for the ductile modulus. |
| Steady heat conduction; Eq. 14, Table S1, and Fig. S5 | Prescribed geotherm on all outer faces | Retain the specified 0 °C surface, 1200 °C reservoir, 30 °C/km background, 3 W/(m K) reference conductivity, and zero heat production. Establish the outer thermal boundaries. |
| Hydrothermal conductivity; Eq. 22 | Printed expression implemented | Resolve the prose's shallow/cool restriction versus the unbounded exponential before selecting a production field. |
| Winkler foundation; Eq. 23 | Fixed production base; separate regional finite-spring calculation | Implement the Cabaniss spring prescription and equilibrium. The regional 32,373 Pa/m coefficient is not the Eq. 23 calibration. |
| Cavity load ΔP + ρgz; Eq. 24 | The 2011–2015 Maxwell stress screen adds pressure-driven PyLith increments to a gravity-equilibrated reference on the same mesh. | Verify the absolute cavity-traction and initial-state equivalence to Eq. 24; density remains homogenized. |
| Tectonic case; main text and Fig. S5 | Static east–west displacement comparisons | Apply ridge-normal loading through the modeled cycles; resolve the 60 mm/year full rate against Table S1's −20 to 20 mm/year range. |
| Reservoir volume and flux; text following Eq. 24 | The 2011–2015 PyLith cavity displacements now yield three complete first-order volume histories on the 400 m mesh. | Derive interval volume rates, refine the cavity mesh, and confirm the paper's integration convention if recoverable. |
| Tensile plus through-going Mohr–Coulomb failure; Eq. 25 and Fig. 5 | All three 2011–2015 Maxwell stress histories are screened; none has joint failure at its BPR-fitted pressure. | Establish the tensile convention and total stress, refine time and mesh resolution, and calculate matching failure slices. |

Table S1 specifies a 25° friction angle. The equivalent dimensionless
coefficient is `tan(25°)` in Eq. 25. A literal coefficient of 25 does not
preserve the tabulated units and is not a paper case. The symbol `f` is
inconsistent between the equation and table; retain that notation issue.

## Observation handling

The cited datasets are [Chadwick and Nooner](https://doi.org/10.1594/IEDA/322282)
and [Fox](https://doi.org/10.1594/IEDA/322344). Their detided, drift-corrected,
and low-pass depth fields are processed observations and eligible inputs.
Their exact use in Cabaniss's calibration still requires confirmation.

The [Chadwick/Nooner format notes](https://api.marine-geo.org/services/download/Document_Accept.php?client=DataLink&doc_uid=3151&entry_id=JdF%3AAxial_Deformation)
specify meters, GMT dates, SPOTL detiding, and a three-day low-pass cutoff.
The [Fox format notes](https://api.marine-geo.org/services/download/Document_Accept.php?client=DataLink&doc_uid=3152&entry_id=JdF%3AAxial_Deformation)
specify a 40-hour filter, hourly LPF samples, and zero placeholders between
samples. Fox's 1997–1998 Center record has no drift correction.

`make paper-bpr` exports existing on-hour observations from nine available
cited Center files. It preserves source fields, digests, UTC times, row
numbers, and gaps. Hourly export is a project storage choice, not a claim
about the paper's timestep. No additional filtering, interpolation, or
vertical offset is applied. Deployment records remain separate until their
common datum is supported by observations. The processed 2000–2002 Center
file is [MGDS UID 896872](https://www.marine-geo.org/tools/search/Files.php?data_set_uid=22282)
in the cited Chadwick/Nooner archive. Its 17,590 valid on-hour values end on
9 July 2002. The following 239 on-hour low-pass fields are zero while raw
depth remains near 1,515 m. The export treats those zero fields as missing
and records the trailing interval through 19 July 2002. Across the nine
files, 150,739 valid on-hour observations are available before datum work.
There are 703 days and 8 hours between the last exported 1998 Center value
and the first 2000 Center value. The model loading across that interval still
requires a documented choice.

The first volume reader combines the original Gmsh cavity faces with the
matching PyLith displacement vertices. The saved PyLith cavity output from
the coarse elastic prototype contains 142 triangles, including eight edges
shared by three faces, so that output topology is unsuitable for a closed
volume integral. The Gmsh physical cavity group contains 138 triangles and
207 edges, with every edge shared by exactly two faces. Its polyhedral
reference volume is 6.13530618 × 10⁹ m³; the ideal 6 × 3 × 1 km ellipsoid is
9.42477796 × 10⁹ m³. The coarse mesh underestimates geometric volume by
34.90%. A one-step model field yields 270,384.46 m³ geometric volume change
and 270,383.17 m³ from the first-order surface integral. These numbers check
the reader but cannot support the paper's volume curve. Mesh refinement is
necessary before using cavity-volume output quantitatively.

A geometry-only sweep of the 6 × 3 × 1 km cavity lowers the polyhedral
volume deficit to 1.72% with 15,423 tetrahedra. No PyLith solve has been run
on that refined mesh, so neither surface compliance nor stress convergence
has been established. `scripts/cavity_geometry_report.py` records a mesh
checksum and the signed difference from the stated ellipsoid dimensions;
the paper provides no numerical acceptance threshold.

Figure 2 displays observations beyond 2015 toward 2019. Its 22-year record
must not be mistaken for a 1993–2015 calibration. The modeled cycles in
Figs. 4–5 are 1998–2011 and 2011–2015. The source explicitly marks data gaps;
missing observations and unknown offsets must not be hidden to make a
continuous-looking curve.

## Delivery sequence

1. Record observation-datum handling, constitutive choices, and
   initialization assumptions.
2. Implement the four rheologies and tectonic case with the source boundaries.
3. Fit pressure to Center observations and save PyLith fields for both cycles.
4. Derive volume, stress, failure paths, and event times from those fields.
5. Compare the numerical panels and supplementary experiments quantitatively.

Supplementary Figs. S3–S4 are published benchmark results and remain in scope.
Separate-station holdouts and project-only diagnostic experiments are outside
the reproduction workflow. Mesh and time resolution must support stable
results; the paper supplies no percentage error tolerance.
