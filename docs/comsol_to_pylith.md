# Translating the COMSOL workflow to PyLith

## Scope

Cabaniss et al. (2020) use COMSOL Multiphysics 5.4 for a three-dimensional
thermomechanical model. PyLith documents elastic and viscoelastic mechanics,
but its documented constitutive models do not expose the paper's temperature-
dependent elastic and viscous properties as native coupled laws. This table
records that capability gap; it is not a decision to replace the target model
with one-way thermal preprocessing. The project target is a complete coupled
workflow, using an efficient Julia or C++ component or a documented PyLith
extension if required. The coupling architecture must be designed and verified
before it can be called complete. Capability statements are checked against
the PyLith 5.0.2 documentation linked below.

## Feature mapping

| Paper feature | PyLith implementation | Limitation and plan |
| --- | --- | --- |
| Isotropic linear elasticity | `IsotropicLinearElasticity` | Native. Use elastic parameters and a `SimpleDB`/`SimpleGridDB` material database. |
| Linear Maxwell viscoelasticity | `IsotropicLinearMaxwell` | Native. Resolve relaxation times in the loading schedule. |
| Generalized Maxwell viscoelasticity | `IsotropicLinearGenMaxwell` | Native. Requires each Maxwell branch's moduli and viscosity. |
| Power-law viscoelasticity | `IsotropicPowerLaw` | Native. The paper's reported rheologies do not require this option for Phase 0. |
| Temperature-dependent Young's modulus and viscosity | Coupled thermal and mechanical update through a verified solver interface or extension | PyLith's documented constitutive models do not implement coupled `E(T)` or `eta(T)`. A spatial database can represent a prescribed field, but does not alone reproduce two-way thermomechanical feedback. Evaluate whether PyLith can be advanced with updated state each step; otherwise implement the missing coupled component in Julia or C++. |
| Hydrothermal circulation | Represent enhanced brittle-crust thermal conductivity in the coupled heat-transport model | The paper represents circulation through increased conductivity. It changes the evolving temperature field and therefore must feed into temperature-dependent mechanics in the complete target model. |
| Tensile and Mohr–Coulomb failure | `axialstress.failure` evaluates criteria from Cauchy stress | These are failure criteria in the paper, not a plastic constitutive law. PyLith Drucker–Prager plasticity is not introduced unless a later written specification requires inelastic constitutive feedback. |
| Andersonian stress regime | Classify principal stress orientations in postprocessing | Report normal, strike-slip, reverse, or oblique orientation from the principal axes. |
| Winkler elastic-foundation base | Fixed base with an extended domain | PyLith does not list an elastic-foundation boundary condition. The planned substitute is a deeper domain with a fixed base, extended until surface displacement converges. An iterated traction database or a thin compliant layer remains an alternative if convergence is impractical. Record the resulting boundary-condition difference in comparisons. |
| Roller lateral faces | `DirichletTimeDependent` with one constrained displacement component per face | Native. Constrain only the normal component on each of the four lateral faces. |
| Pressurized reservoir cavity | `NeumannTimeDependent` normal traction on the cavity surface | Use a uniform pressure for the smoke test. For an inflation history, supply a `TimeHistory` amplitude through the Neumann condition's auxiliary database. |
| Ridge-perpendicular tectonic loading | `DirichletTimeDependent` velocity on opposite lateral faces | Native. The paper states 60 mm/yr full rate; confirm its exact face convention from the supplement before implementation and state it explicitly. |
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
runs. Third, enlarge the fixed-base domain and check surface displacement
convergence. Lastly, compare model-derived failure indicators, pressure scales,
event timing, and spatial patterns against the written specifications and
published reference figures. Raw BPR records are prohibited project inputs;
data-dependent comparisons can proceed only from numerical observations
reported in allowed written sources.
