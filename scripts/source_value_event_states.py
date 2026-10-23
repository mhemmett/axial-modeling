"""Continue fitted PyLith pressure to an observed eruption date."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path

import h5py
import numpy as np
import source_value_maxwell_cases as maxwell

from axialstress.failure_analysis import analyze_stress_history
from axialstress.paper_bpr import file_sha256

ROOT = Path(__file__).resolve().parents[1]
CASES = ("constant_maxwell", "thermal_maxwell", "hydrothermal_maxwell")


def main() -> None:
    """Run a bounded PyLith continuation with constant final fitted pressure."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cycle", choices=("1998-2011", "2011-2015"), required=True)
    parser.add_argument("--case", choices=CASES, required=True)
    parser.add_argument("--fit-dir", type=Path)
    parser.add_argument("--source-dir", type=Path)
    parser.add_argument("--basis-dir", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    basis_dir = (args.basis_dir or ROOT / "data/processed/refined_elastic_basis_400m").resolve()
    source_dir = (
        args.source_dir or ROOT / "data/processed/source_value_bpr_failure_2011_2015"
    ).resolve()
    fit_dir = (
        args.fit_dir
        or ROOT / f"data/processed/source_value_bpr_failure_{args.cycle.replace('-', '_')}"
    ).resolve()
    output_dir = (
        args.output_dir
        or ROOT / f"data/processed/source_value_event_states_{args.cycle.replace('-', '_')}"
    ).resolve()
    source_path = source_dir / "summary.json"
    source = json.loads(source_path.read_text(encoding="utf-8"))
    mesh_path = basis_dir / "axial_ellipsoid.msh"
    reference_path = basis_dir / "fixed-base-equilibrium-material.h5"
    if (
        source.get("paper_output_data_used") is not False
        or file_sha256(mesh_path) != source["mesh_sha256"]
        or file_sha256(reference_path) != source["equilibrium_sha256"]
    ):
        raise ValueError("source-value mesh or gravity reference changed")
    material_path = source_dir / "materials" / f"{args.case}.spatialdb"
    if file_sha256(material_path) != source["cases"][args.case]["material_sha256"]:
        raise ValueError("source-value material changed")
    if args.cycle == "2011-2015":
        fit_path = fit_dir / "summary.json"
        fit = json.loads(fit_path.read_text(encoding="utf-8"))
        if fit.get("paper_output_data_used") is not False:
            raise ValueError("pressure fit provenance is incomplete")
        series_path = fit_dir / fit["cases"][args.case]["pressure_failure_csv"]
        start_utc = datetime.fromisoformat(fit["cycle_start_utc"])
        event_utc = datetime.fromisoformat(fit["eruption_utc"])
    else:
        fit_path = fit_dir / args.case / "summary.json"
        fit = json.loads(fit_path.read_text(encoding="utf-8"))
        if fit.get("paper_output_data_used") is not False:
            raise ValueError("pressure fit provenance is incomplete")
        series_path = fit_dir / args.case / "pressure_failure.csv"
        if file_sha256(series_path) != fit["series_sha256"]:
            raise ValueError("historical pressure series changed")
        start_utc = datetime.fromisoformat(fit["cycle_start_utc"])
        event_utc = datetime.fromisoformat(fit["observed_eruption_utc"])
    with series_path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    saved_dates = [datetime.fromisoformat(row["time_utc"]) for row in rows]
    if not rows or saved_dates[-1] >= event_utc:
        raise ValueError("event must follow the last sampled pressure")
    step_s = (saved_dates[0] - start_utc).total_seconds()
    if step_s <= 0.0 or step_s not in (7.0 * 86_400.0, 28.0 * 86_400.0):
        raise ValueError("pressure series begins outside a supported grid")
    if any(
        (later - earlier).total_seconds() != step_s
        for earlier, later in zip(saved_dates, saved_dates[1:], strict=False)
    ):
        raise ValueError("pressure fit has an irregular interior grid")
    dates = [start_utc, *saved_dates, event_utc]
    elapsed_s = np.asarray([(day - start_utc).total_seconds() for day in dates])
    last_pressure_mpa = float(rows[-1]["pressure_change_mpa"])
    pressure_mpa = np.asarray(
        [0.0, *(float(row["pressure_change_mpa"]) for row in rows), last_pressure_mpa]
    )
    run_dir = output_dir / args.case / "held_pressure_to_eruption"
    maxwell._write_run(
        run_dir,
        mesh_path,
        material_path,
        elapsed_seconds=elapsed_s,
        pressure_mpa=pressure_mpa,
        time_step_s=step_s,
    )
    maxwell._run_pylith(run_dir)
    output_path = run_dir / "output/maxwell-material.h5"
    with h5py.File(output_path, "r") as material:
        times_s = np.asarray(material["time"], dtype=float).reshape(-1)
        vertices = np.asarray(material["geometry/vertices"], dtype=float)
        cells = np.asarray(material["viz/topology/cells"], dtype=np.int64)
        increment = np.asarray(material["cell_fields/cauchy_stress"][-1], dtype=float)
    if not np.isclose(times_s[-1], elapsed_s[-1], rtol=0.0, atol=0.01):
        raise ValueError("PyLith did not save stress at the observed eruption date")
    reference = maxwell._reference_stress(reference_path, vertices, cells)
    stress = reference + increment
    failure = analyze_stress_history(
        vertices,
        cells,
        stress[None],
        np.asarray([elapsed_s[-1]]),
        cohesion_pa=1.0e6,
        friction_angle_deg=25.0,
        pore_pressure_pa=0.0,
    )["records"][0]
    result = {
        "method": "held last fitted pressure through observed eruption date",
        "paper_output_data_used": False,
        "case": args.case,
        "cycle": args.cycle,
        "observed_eruption_utc": event_utc.isoformat(),
        "last_fitted_pressure_utc": saved_dates[-1].isoformat(),
        "hold_duration_days": (event_utc - saved_dates[-1]).total_seconds() / 86_400.0,
        "time_step_s": step_s,
        "held_pressure_change_mpa": float(pressure_mpa[-1]),
        "joint_failure_zero_tensile_strength": bool(
            failure["maximum_cavity_principal_stress_pa"] > 0.0
            and failure["cavity_to_surface_shear_path_found"]
        ),
        "maximum_cavity_principal_stress_pa": float(
            failure["maximum_cavity_principal_stress_pa"]
        ),
        "connected_path_cell_indices": list(
            map(int, failure["cavity_to_surface_path_cell_indices"])
        ),
        "source_summary_sha256": file_sha256(source_path),
        "fit_summary_sha256": file_sha256(fit_path),
        "fit_series_sha256": file_sha256(series_path),
        "mesh_sha256": file_sha256(mesh_path),
        "material_sha256": file_sha256(material_path),
        "gravity_reference_sha256": file_sha256(reference_path),
        "event_stress_sha256": file_sha256(output_path),
    }
    result_path = output_dir / args.case / "summary.json"
    result_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(
        args.cycle,
        args.case,
        event_utc.isoformat(),
        result["joint_failure_zero_tensile_strength"],
    )


if __name__ == "__main__":
    main()
