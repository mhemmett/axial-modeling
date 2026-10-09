# Translating the COMSOL workflow to PyLith

## Scope

Cabaniss et al. (2020) use COMSOL Multiphysics 5.4 for a three-dimensional
thermomechanical model. PyLith documents elastic and viscoelastic mechanics,
but its constitutive models do not evaluate the paper's temperature-dependent
elastic and viscous properties internally. The written method solves steady
heat conduction, then assigns the resulting temperature-dependent properties
to mechanics; it specifies no feedback from mechanics to heat. A verified
driver can coordinate that property handoff and the PyLith solve without
runtime material updates. Capability statements are checked against the
PyLith 5.0.2 documentation linked below.

## Feature mapping

| Paper feature | PyLith implementation | Limitation and plan |
| --- | --- | --- |
| Isotropic linear elasticity | `IsotropicLinearElasticity` | Native. Use elastic parameters and a `SimpleDB`/`SimpleGridDB` material database. |
| Linear Maxwell viscoelasticity | `IsotropicLinearMaxwell` | Native. Resolve relaxation times in the loading schedule. |
| Generalized Maxwell viscoelasticity | `IsotropicLinearGenMaxwell` | Native. Requires each Maxwell branch's moduli and viscosity. |
| Power-law viscoelasticity | `IsotropicPowerLaw` | Native. The paper's reported rheologies do not require this option for Phase 0. |
| Temperature-dependent Young's modulus and viscosity | Map the steady thermal solution into the PyLith material database | PyLith's documented constitutive models do not evaluate `E(T)` or `eta(T)` internally. The driver computes the temperature field and cellwise properties before mechanics, matching the written steady-state method. |
| Hydrothermal circulation | Represent enhanced brittle-crust thermal conductivity in the heat-transport solve | The paper represents circulation through increased conductivity. The resulting steady temperature field feeds temperature-dependent mechanical properties. |
| Tensile and Mohr–Coulomb failure | `axialstress.failure` evaluates criteria from Cauchy stress | These are failure criteria in the paper, not a plastic constitutive law. PyLith Drucker–Prager plasticity is not introduced unless a later written specification requires inelastic constitutive feedback. |
| Andersonian stress regime | Classify principal stress orientations in postprocessing | Report normal, strike-slip, reverse, or oblique orientation from the principal axes. |
| Winkler elastic-foundation base | Fixed base with an extended domain | PyLith does not list an elastic-foundation boundary condition. A bounded 20/30/40 km depth sweep with embedded BPR surface points produces nonmonotonic compliance changes on independently generated, nonnested meshes; it does not show domain convergence or Winkler equivalence. Continue domain and mesh refinement, or validate an iterated traction database or thin compliant layer. Record the resulting boundary-condition difference in comparisons. |
| Roller lateral faces | `DirichletTimeDependent` with one constrained displacement component per face | Native. Constrain only the normal component on each of the four lateral faces. |
| Pressurized reservoir cavity | `NeumannTimeDependent` normal traction on the cavity surface | Use a uniform pressure for the smoke test. For an inflation history, supply a `TimeHistory` amplitude through the Neumann condition's auxiliary database. |
| Ridge-perpendicular tectonic loading | `DirichletTimeDependent` velocity on opposite lateral faces | Native. The article states 60 mm/year full rate; Supplementary Table S1 lists `Pv` from -20 to 20 mm/year, and Fig. S5 does not specify the per-face split. Resolve this conflict before applying tectonic loading. |
| COMSOL mesh | Gmsh Python API and PyLith `MeshIOPetsc` | Generate first-order tetrahedra and physical groups; save Gmsh 4.x. PyLith 5.x reads Gmsh meshes and supports surface groups for boundary conditions. |
| Surface displacement and stress output | HDF5 solution output plus material physics output | Read displacement from the solution observer and Cauchy stress from the material observer. Keep output basis order consistent with the stress interpolation. |

## PyLith documentation

- [Component implementations, PyLith 5.0.2](https://pylith.readthedocs.io/en/v5.0.2/user/components/implementations.html):
  lists the elastic, Maxwell, generalized Maxwell, power-law, Neumann, and
  Dirichlet implementations.
- [Time-dependent boundary conditions](https://pylith.readthedocs.io/en/v5.0.2/user/physics/bc/time-dependent.html):
  documents normal and tangential Neumann amplitudes and optional time histories.
- [Gmsh utilities](https://pylith.readthedocs.io/en/v5.0.2/user/meshing/gmsh-utils.html)
  and [Gmsh mesh import](https://pylith.readthedocs.io/en/v5.0.2/user/meshing/gmsh.html):
  describe physical groups and `MeshIOPetsc` compatibility.
- [OutputPhysics](https://pylith.readthedocs.io/en/v5.0.2/user/components/meshio/OutputPhysics.html)
  documents output of derived material fields such as Cauchy stress.

## Validation sequence

First, verify the Phase 0 elastic cavity against an analytical limiting case.
Second, verify heat transport, temperature-dependent properties, and the
coupling scheme with manufactured or limiting cases before full historical
runs. Third, continue enlarging the fixed-base domain while refining the mesh
and check surface displacement convergence against a verified Winkler
implementation or another justified reference. Lastly, compare model-derived
failure indicators, pressure scales, event timing, and spatial patterns against
the written specifications,
independent OOI BPR records, and original NCEI/MGDS channels from historical
Axial deployments. Paper-produced data products remain excluded even when an
archive cites the paper. Earthquake, bathymetry, and lava-flow records remain
outside the authorized inputs.
