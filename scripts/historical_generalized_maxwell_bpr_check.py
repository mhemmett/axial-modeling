"""Drive a synthetic three-branch Maxwell model with raw historical BPR checks."""

from __future__ import annotations

import argparse
import csv
import json
import re
import shlex
import shutil
import subprocess
from datetime import date
from pathlib import Path

import h5py
import matplotlib
import numpy as np

matplotlib.use("Agg")

import matplotlib.dates as mdates
import matplotlib.pyplot as plt

from axialstress.bpr_mogi_calibration import local_east_north_offset_m
from axialstress.ellipsoid_bpr_calibration import read_ellipsoid_unit_response
from axialstress.generalized_maxwell import generalized_maxwell_relaxation_times_s
from axialstress.historical_bpr import DEPLOYMENTS, PROCESSED_DIR
from axialstress.historical_generalized_maxwell import (
    SECONDS_PER_YEAR,
    compare_model_history,
    prepare_center_fit_pressure_history,
)
from axialstress.surface_interpolation import interpolate_triangular_surface

ROOT = Path(__file__).resolve().parents[1]
STEP_DIR = ROOT / "pylith" / "step13_historical_generalized_maxwell_bpr"
MATERIAL_STEP_DIR = ROOT / "pylith" / "step12_generalized_maxwell_ellipsoid"
ELASTIC_SURFACE = (
    ROOT
    / "pylith"
    / "step05_ellipsoid_elastic"
    / "output"
    / "ellipsoid-surface.h5"
)
PYLITH_ROOT = ROOT / "pylith" / "pylith-5.0.2-linux-x86_64"
EVENT_PAIRS = {
    "1998": ("wc81_1997", "wc82a_1997"),
    "2011": ("nemo_2010_2011_center", "nemo_2009_2011_south"),
}
ERUPTION_DATES = {"1998": date(1998, 1, 25), "2011": date(2011, 4, 6)}
YOUNGS_MODULUS_PA = 50.0e9
POISSON_RATIO = 0.25
DENSITY_KG_M3 = 2800.0
REFERENCE_VISCOSITY_PA_S_BY_BRANCH = np.asarray([1.0e18, 5.0e17, 2.0e18])
SHEAR_RATIO_BY_BRANCH = np.asarray([0.25, 0.25, 0.25])
INITIAL_DT_S = 7.0 * 86_400.0


def _read_daily_depths(path: Path) -> dict[date, float]:
    """Read daily equivalent depths produced from original raw BPR channels."""
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        required = {"time_utc", "equivalent_depth_m", "relative_uplift_m"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError(f"unexpected daily BPR columns in {path}")
        depths: dict[date, float] = {}
        for row_number, row in enumerate(reader, start=2):
            if not row["relative_uplift_m"]:
                continue
            try:
                day = date.fromisoformat(row["time_utc"][:10])
                depth_m = float(row["equivalent_depth_m"])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"invalid daily BPR row {row_number} in {path}") from exc
            if not np.isfinite(depth_m) or day in depths:
                raise ValueError(
                    f"invalid or duplicate daily BPR date at row {row_number} in {path}"
                )
            depths[day] = depth_m
    if not depths:
        raise ValueError(f"no valid daily BPR depths in {path}")
    return depths


def _write_pressure_history(
    path: Path, elapsed_seconds: np.ndarray, pressure_mpa: np.ndarray
) -> None:
    """Write a daily pressure series in years for PyLith TimeHistory."""
    if (
        elapsed_seconds.ndim != 1
        or elapsed_seconds.shape != pressure_mpa.shape
        or len(elapsed_seconds) < 2
        or not np.all(np.isfinite(elapsed_seconds))
        or not np.all(np.isfinite(pressure_mpa))
        or np.any(np.diff(elapsed_seconds) <= 0.0)
    ):
        raise ValueError("time history requires matched finite increasing arrays")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as stream:
        stream.write("#TIME HISTORY ascii\n")
        stream.write("TimeHistory {\n")
        stream.write(f"  num-points = {len(elapsed_seconds)}\n")
        stream.write("  time-units = year\n")
        stream.write("}\n")
        for elapsed_s, pressure_value_mpa in zip(
            elapsed_seconds, pressure_mpa, strict=True
        ):
            stream.write(
                f"{elapsed_s / SECONDS_PER_YEAR:.12g} "
                f"{pressure_value_mpa:.12g}\n"
            )


def _write_cavity_database(path: Path) -> None:
    """Write a one-megapascal normalized cavity traction amplitude."""
    names = (
        "initial_amplitude_normal",
        "initial_amplitude_tangential_1",
        "initial_amplitude_tangential_2",
        "time_history_amplitude_normal",
        "time_history_amplitude_tangential_1",
        "time_history_amplitude_tangential_2",
        "time_history_start_time",
    )
    lines = [
        "#SPATIAL.ascii 1",
        "SimpleDB {",
        "  num-values = 7",
        f"  value-names = {' '.join(names)}",
        "  value-units = Pa Pa Pa Pa Pa Pa s",
        "  num-locs = 1",
        "  data-dim = 0",
        "  space-dim = 3",
        "  cs-data = cartesian {",
        "    to-meters = 1.0",
        "    space-dim = 3",
        "  }",
        "}",
        "0.0 0.0 0.0 0.0 0.0 0.0 -1.0e6 0.0 0.0 0.0",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _configure_run(
    run_dir: Path,
    mesh_path: Path,
    material_database: Path,
    elapsed_seconds: np.ndarray,
    pressure_mpa: np.ndarray,
) -> None:
    """Create a local generalized Maxwell case with raw BPR pressure forcing."""
    (run_dir / "mesh").mkdir(parents=True, exist_ok=True)
    (run_dir / "output").mkdir(parents=True, exist_ok=True)
    shutil.copy2(mesh_path, run_dir / "mesh" / "axial_ellipsoid.msh")
    shutil.copy2(material_database, run_dir / "output" / "genmaxwell-material.spatialdb")
    shutil.copy2(
        ROOT / "pylith" / "step06_maxwell_ellipsoid" / "bc_zero.spatialdb",
        run_dir / "output" / "bc_zero.spatialdb",
    )
    _write_cavity_database(run_dir / "output" / "bc_cavity.spatialdb")
    _write_pressure_history(
        run_dir / "output" / "pressure.timedb", elapsed_seconds, pressure_mpa
    )

    step_config = (MATERIAL_STEP_DIR / "generalized_maxwell.cfg").read_text(
        encoding="utf-8"
    )
    duration_s = float(elapsed_seconds[-1])
    step_config, end_count = re.subn(
        r"(?m)^end_time\s*=.*$", f"end_time = {duration_s:.12g}*s", step_config
    )
    step_config, dt_count = re.subn(
        r"(?m)^initial_dt\s*=.*$",
        f"initial_dt = {min(INITIAL_DT_S, duration_s):.12g}*s",
        step_config,
    )
    cavity_path = (
        "db_auxiliary_field.iohandler.filename = "
        "../step06_maxwell_ellipsoid/bc_cavity.spatialdb"
    )
    if step_config.count(cavity_path) != 1 or end_count != 1 or dt_count != 1:
        raise ValueError("could not configure generalized Maxwell time-history input")
    step_config = step_config.replace(
        cavity_path,
        "use_time_history = True\n"
        f"{cavity_path.split(' = ')[0]} = output/bc_cavity.spatialdb\n"
        "time_history = spatialdata.spatialdb.TimeHistory\n"
        "time_history.description = Raw Center BPR pressure inferred with "
        "static elastic compliance\n"
        "time_history.filename = output/pressure.timedb",
    )
    zero_path = (
        "db_auxiliary_field.iohandler.filename = "
        "../step06_maxwell_ellipsoid/bc_zero.spatialdb"
    )
    if step_config.count(zero_path) != 5:
        raise ValueError("could not configure generalized Maxwell boundary databases")
    step_config = step_config.replace(
        zero_path, "db_auxiliary_field.iohandler.filename = output/bc_zero.spatialdb"
    )
    (run_dir / "generalized_maxwell.cfg").write_text(step_config, encoding="utf-8")
    pylith_config = (MATERIAL_STEP_DIR / "pylithapp.cfg").read_text(encoding="utf-8")
    (run_dir / "pylithapp.cfg").write_text(pylith_config, encoding="utf-8")


def _run_pylith(run_dir: Path) -> None:
    """Run one event window with a five-minute wall-clock limit."""
    log_path = run_dir / "output" / "pylith.log"
    command = (
        f"cd {shlex.quote(str(PYLITH_ROOT))} && source setup.sh && "
        f"cd {shlex.quote(str(run_dir))} && "
        "timeout 300 pylith generalized_maxwell.cfg"
    )
    with log_path.open("w", encoding="utf-8") as log:
        completed = subprocess.run(
            ["bash", "-lc", command],
            cwd=ROOT,
            stdout=log,
            stderr=subprocess.STDOUT,
            check=False,
        )
    if completed.returncode:
        tail = "\n".join(log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-50:])
        raise RuntimeError(f"historical generalized Maxwell PyLith run failed:\n{tail}")


def _read_surface_history(
    path: Path,
    center_station: object,
    south_station: object,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Read surface displacement and sample at Central and South BPR positions."""
    with h5py.File(path, "r") as surface:
        times_s = np.asarray(surface["time"], dtype=float).reshape(-1)
        vertices = np.asarray(surface["geometry/vertices"], dtype=float)
        triangles = np.asarray(surface["viz/topology/cells"], dtype=np.int64)
        displacement = np.asarray(surface["vertex_fields/displacement"], dtype=float)
    if displacement.shape != (len(times_s), *vertices.shape):
        raise ValueError("PyLith surface displacement has an unexpected shape")
    if len(times_s) < 2 or np.any(np.diff(times_s) <= 0.0):
        raise ValueError("PyLith surface output times must be increasing")
    east_m, north_m = local_east_north_offset_m(
        south_station.latitude,
        south_station.longitude,
        origin_latitude_deg=center_station.latitude,
        origin_longitude_deg=center_station.longitude,
    )
    center_uplift_m = np.asarray(
        [
            interpolate_triangular_surface(vertices, triangles, field, (0.0, 0.0))[2]
            for field in displacement
        ],
        dtype=float,
    )
    south_uplift_m = np.asarray(
        [
            interpolate_triangular_surface(vertices, triangles, field, (east_m, north_m))[2]
            for field in displacement
        ],
        dtype=float,
    )
    return times_s, center_uplift_m, south_uplift_m


def _run_event(
    event: str,
    center_slug: str,
    south_slug: str,
    deployments: dict[str, object],
    *,
    mesh_path: Path,
    material_database: Path,
    center_compliance_m_per_mpa: float,
    output_dir: Path,
) -> dict[str, object]:
    """Run and summarize one raw Center/South deployment overlap."""
    center = deployments[center_slug]
    south = deployments[south_slug]
    history = prepare_center_fit_pressure_history(
        _read_daily_depths(PROCESSED_DIR / f"{center_slug}.daily.csv"),
        _read_daily_depths(PROCESSED_DIR / f"{south_slug}.daily.csv"),
        center_compliance_m_per_mpa=center_compliance_m_per_mpa,
    )
    run_dir = STEP_DIR / "output" / event
    if run_dir.exists():
        shutil.rmtree(run_dir)
    _configure_run(
        run_dir,
        mesh_path,
        material_database,
        history.elapsed_seconds,
        history.pressure_change_mpa,
    )
    _run_pylith(run_dir)
    times_s, center_model_m, south_model_m = _read_surface_history(
        run_dir / "output" / "genmaxwell-surface.h5", center, south
    )
    if times_s[0] > history.elapsed_seconds[0]:
        if history.elapsed_seconds[0] != 0.0 or not np.isclose(
            history.pressure_change_mpa[0], 0.0, rtol=0.0, atol=1.0e-12
        ):
            raise ValueError("PyLith output omits a nonzero initial pressure state")
        times_s = np.insert(times_s, 0, 0.0)
        center_model_m = np.insert(center_model_m, 0, 0.0)
        south_model_m = np.insert(south_model_m, 0, 0.0)
    rows, metrics = compare_model_history(
        history,
        times_s,
        center_model_m,
        south_model_m,
    )

    material = np.atleast_2d(np.loadtxt(material_database, comments="#", skiprows=13))
    relaxation_times_s = generalized_maxwell_relaxation_times_s(
        YOUNGS_MODULUS_PA,
        POISSON_RATIO,
        material[:, 6:9].T,
        material[:, 9:12].T,
    )
    maximum_step_s = float(np.max(np.diff(times_s)))
    minimum_relaxation_time_s = float(np.min(relaxation_times_s))
    if maximum_step_s > minimum_relaxation_time_s / 5.0:
        raise ValueError("historical PyLith step exceeds one-fifth of the minimum relaxation time")

    output_dir.mkdir(parents=True, exist_ok=True)
    series_path = output_dir / f"historical_generalized_maxwell_{event}.csv"
    with series_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    summary: dict[str, object] = {
        "method": (
            "three-branch Maxwell forward run driven by Center pressure inferred "
            "from static elastic compliance"
        ),
        "event": event,
        "center_station": center.station,
        "south_station": south.station,
        "center_raw_channel": center.raw_channel,
        "south_raw_channel": south.raw_channel,
        "observation_provenance": "original raw NCEI/MGDS BPR channels",
        "paper_publication_data_used": False,
        "pressure_history_calibration": (
            "daily Center uplift divided by the 1 MPa static PyLith elastic "
            "compliance; first shared daily sample sets zero"
        ),
        "pressure_history_is_viscoelastic_calibration": False,
        "static_center_compliance_m_per_mpa": center_compliance_m_per_mpa,
        "pressure_change_range_mpa": metrics["pressure_change_range_mpa"],
        "overlap_start_utc": metrics["overlap_start_utc"],
        "overlap_end_utc": metrics["overlap_end_utc"],
        "paired_daily_sample_count": metrics["paired_daily_sample_count"],
        "youngs_modulus_pa": YOUNGS_MODULUS_PA,
        "poisson_ratio": POISSON_RATIO,
        "density_kg_m3": DENSITY_KG_M3,
        "branch_reference_viscosity_pa_s": REFERENCE_VISCOSITY_PA_S_BY_BRANCH.tolist(),
        "branch_shear_modulus_fraction": SHEAR_RATIO_BY_BRANCH.tolist(),
        "branch_parameters_are_synthetic": True,
        "branch_temperature_law": "Eq. 15 Arrhenius viscosity on the steady Eq. 14/Eq. 22 field",
        "temperature_feedback": False,
        "initial_timestep_s": min(INITIAL_DT_S, float(history.elapsed_seconds[-1])),
        "maximum_output_step_s": maximum_step_s,
        "minimum_branch_relaxation_time_s": minimum_relaxation_time_s,
        "one_fifth_relaxation_time_limit_passed": True,
        "center": metrics["center"],
        "south": metrics["south"],
        "mesh_tetrahedra": len(material),
        "static_ellipsoid_mesh_converged": False,
        "tide_or_drift_correction_applied": False,
        "limitations": [
            "pressure history uses static elastic compliance, not a viscoelastic inversion",
            "branch viscosities and fractions are synthetic because the written source "
            "does not specify them",
            "the 7-day PyLith step smooths daily pressure changes between output times",
            "raw daily means retain ocean variability and instrument drift",
            "the ellipsoid compliance mesh is not converged",
        ],
    }
    summary_path = output_dir / f"historical_generalized_maxwell_{event}.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"wrote {series_path} and {summary_path}")
    return summary


def _plot_comparisons(output_dir: Path, figure_stem: Path) -> tuple[Path, Path]:
    """Plot observed and modeled Center/South histories for both events."""
    figure, axes = plt.subplots(2, 1, figsize=(11.5, 8.2), sharex=False)
    styles = {
        "center_observed_uplift_m": ("#0072B2", "Center observed", "-"),
        "center_model_uplift_m": ("#0072B2", "Center Maxwell", "--"),
        "south_observed_uplift_m": ("#D55E00", "South observed", "-"),
        "south_model_uplift_m": ("#D55E00", "South Maxwell", "--"),
    }
    deployments = {deployment.slug: deployment for deployment in DEPLOYMENTS}
    for axis, event in zip(axes, EVENT_PAIRS, strict=True):
        series_path = output_dir / f"historical_generalized_maxwell_{event}.csv"
        with series_path.open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        times = [date.fromisoformat(row["time_utc"][:10]) for row in rows]
        center_station = deployments[EVENT_PAIRS[event][0]].station
        south_station = deployments[EVENT_PAIRS[event][1]].station
        for field, (color, label, linestyle) in styles.items():
            axis.plot(
                times,
                [float(row[field]) for row in rows],
                color=color,
                label=label,
                linestyle=linestyle,
                linewidth=1.0 if linestyle == "-" else 1.2,
            )
        axis.axvline(ERUPTION_DATES[event], color="#555555", linewidth=0.9, linestyle=":")
        axis.axhline(0.0, color="#555555", linewidth=0.6)
        axis.set_title(f"{event}: {center_station} forcing; {south_station} held out")
        axis.set_ylabel("Relative elevation (m; up positive)")
        axis.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        axis.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        axis.grid(True, color="#D9D9D9", linewidth=0.55)
        axis.legend(frameon=False, ncol=2, loc="best")
    axes[-1].set_xlabel("Date (UTC)")
    figure.suptitle(
        "Historical three-branch Maxwell forward checks from original raw BPR channels\n"
        "Synthetic branch parameters; center pressure inferred with static compliance"
    )
    figure.autofmt_xdate()
    figure.tight_layout()
    figure_stem.parent.mkdir(parents=True, exist_ok=True)
    png_path = figure_stem.with_suffix(".png")
    pdf_path = figure_stem.with_suffix(".pdf")
    figure.savefig(png_path, dpi=220)
    figure.savefig(pdf_path)
    plt.close(figure)
    return png_path, pdf_path


def main() -> None:
    """Run historical three-branch forward checks for 1998 and 2011."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mesh", type=Path, required=True)
    parser.add_argument("--material-database", type=Path, required=True)
    parser.add_argument(
        "--elastic-surface",
        type=Path,
        default=ELASTIC_SURFACE,
        help="static 1 MPa PyLith surface output used for provisional pressure inference",
    )
    parser.add_argument("--output-dir", type=Path, default=PROCESSED_DIR)
    parser.add_argument(
        "--figure-stem",
        type=Path,
        default=ROOT / "figures" / "historical_generalized_maxwell_bpr_check",
    )
    args = parser.parse_args()
    for required in (args.mesh, args.material_database, args.elastic_surface):
        if not required.is_file():
            raise FileNotFoundError(required)

    deployments = {deployment.slug: deployment for deployment in DEPLOYMENTS}
    center_response, _ = read_ellipsoid_unit_response(args.elastic_surface)
    center_compliance = float(center_response[2])
    for event, pair in EVENT_PAIRS.items():
        _run_event(
            event,
            *pair,
            deployments,
            mesh_path=args.mesh,
            material_database=args.material_database,
            center_compliance_m_per_mpa=center_compliance,
            output_dir=args.output_dir,
        )
    png_path, pdf_path = _plot_comparisons(args.output_dir, args.figure_stem)
    print(f"wrote {png_path} and {pdf_path}")


if __name__ == "__main__":
    main()
