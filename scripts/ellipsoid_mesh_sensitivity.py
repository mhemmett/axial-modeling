"""Measure mesh sensitivity of the PyLith ellipsoid BPR compliance response."""

from __future__ import annotations

import json
import re
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path
from tempfile import TemporaryDirectory

from axialstress.ellipsoid_bpr_calibration import read_ellipsoid_unit_response

ROOT = Path(__file__).resolve().parents[1]
STEP_DIR = ROOT / "pylith" / "step05_ellipsoid_elastic"
PYLITH_ROOT = ROOT / "pylith" / "pylith-5.0.2-linux-x86_64"
OUTPUT_PATH = ROOT / "data" / "processed" / "ellipsoid_mesh_sensitivity.json"
MESH_VARIANTS = (
    ("coarse", 1_200.0, 10_000.0, None),
    ("local-1100", 1_200.0, 10_000.0, 1_100.0),
    ("local-1000", 1_200.0, 10_000.0, 1_000.0),
    ("local-950", 1_200.0, 10_000.0, 950.0),
    ("local-900", 1_200.0, 10_000.0, 900.0),
)
MAX_TETRAHEDRA = 3_500
COMPLIANCE_RELATIVE_TOLERANCE = 0.05


def _tail(path: Path, lines: int = 20) -> str:
    """Return the last lines of a solver log for actionable failures."""
    return "\n".join(path.read_text(encoding="utf-8", errors="replace").splitlines()[-lines:])


def _run_mesh_variant(
    name: str,
    lc_near: float,
    lc_far: float,
    local_refinement_size: float | None,
) -> dict[str, float | int | str | None]:
    """Build and solve one mesh in a temporary directory."""
    with TemporaryDirectory(prefix=f"axial-ellipsoid-{name}-") as temporary:
        run_dir = Path(temporary)
        (run_dir / "mesh").mkdir()
        (run_dir / "output").mkdir()
        for filename in (
            "step05.cfg",
            "pylithapp.cfg",
            "bc_cavity.spatialdb",
            "bc_zero.spatialdb",
            "mat_elastic.spatialdb",
        ):
            shutil.copy2(STEP_DIR / filename, run_dir / filename)

        mesh_log = run_dir / "output" / "mesh.log"
        mesh_command = [
            sys.executable,
            str(ROOT / "meshing" / "axial_ellipsoid_bpr.py"),
            "--output",
            str(run_dir / "mesh" / "axial_ellipsoid.msh"),
            "--lc-near",
            str(lc_near),
            "--lc-far",
            str(lc_far),
            "--max-tetrahedra",
            str(MAX_TETRAHEDRA),
        ]
        if local_refinement_size is not None:
            mesh_command.extend(
                ["--local-refinement-size", str(local_refinement_size)]
            )
        with mesh_log.open("w", encoding="utf-8") as log:
            subprocess.run(
                mesh_command,
                cwd=ROOT,
                stdout=log,
                stderr=subprocess.STDOUT,
                check=True,
            )
        mesh_output = mesh_log.read_text(encoding="utf-8")
        match = re.search(r"Wrote .*: (\d+) tetrahedra", mesh_output)
        if match is None:
            raise RuntimeError(f"mesh count missing from {mesh_log}")
        tetrahedra = int(match.group(1))

        solver_log = run_dir / "output" / "pylith.log"
        solver_command = (
            f"cd {shlex.quote(str(PYLITH_ROOT))} && source setup.sh && "
            f"cd {shlex.quote(str(run_dir))} && "
            "timeout 300 pylith step05.cfg"
        )
        with solver_log.open("w", encoding="utf-8") as log:
            completed = subprocess.run(
                ["bash", "-lc", solver_command],
                cwd=ROOT,
                stdout=log,
                stderr=subprocess.STDOUT,
                check=False,
            )
        if completed.returncode:
            raise RuntimeError(f"PyLith {name} solve failed:\n{_tail(solver_log)}")

        central, east = read_ellipsoid_unit_response(
            run_dir / "output" / "ellipsoid-surface.h5"
        )
        return {
            "name": name,
            "refinement_mode": "local-box" if local_refinement_size else "global",
            "lc_near_m": lc_near,
            "lc_far_m": lc_far,
            "local_refinement_size_m": local_refinement_size,
            "tetrahedra": tetrahedra,
            "central_compliance_m_per_mpa": float(central[2]),
            "east_compliance_m_per_mpa": float(east[2]),
        }


def main() -> None:
    """Run the bounded station-region mesh check and write JSON."""
    if not (PYLITH_ROOT / "setup.sh").is_file():
        raise SystemExit("PyLith is not installed; run make install-pylith first")
    started = time.perf_counter()
    results = [
        _run_mesh_variant(name, lc_near, lc_far, local_size)
        for name, lc_near, lc_far, local_size in MESH_VARIANTS
    ]
    result_by_name = {str(result["name"]): result for result in results}
    comparison_groups = {
        "station_region_refinement": [
            result_by_name[name]
            for name in (
                "coarse",
                "local-1100",
                "local-1000",
                "local-950",
                "local-900",
            )
        ]
    }
    changes = []
    for group in comparison_groups.values():
        for previous, current in zip(group, group[1:], strict=False):
            for field in (
                "central_compliance_m_per_mpa",
                "east_compliance_m_per_mpa",
            ):
                change = float(current[field]) / float(previous[field]) - 1.0
                current[f"{field}_relative_change"] = change
                changes.append(abs(change))
    summary = {
        "method": "static elastic unit-pressure compliance mesh sensitivity",
        "compliance_relative_tolerance": COMPLIANCE_RELATIVE_TOLERANCE,
        "mesh_convergence_status": (
            "within_tolerance"
            if all(change <= COMPLIANCE_RELATIVE_TOLERANCE for change in changes)
            else "not_established"
        ),
        "comparison_groups": {
            name: [result["name"] for result in group]
            for name, group in comparison_groups.items()
        },
        "runtime_seconds": round(time.perf_counter() - started, 2),
        "variants": results,
        "observations_used": False,
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
