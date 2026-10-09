"""Draw the documented Axial model geometry and boundary-condition schematic."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse, Rectangle

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_STEM = ROOT / "figures/model_setup_schematic"


def _draw_pressure_arrows(axis: plt.Axes, *, center_depth_km: float) -> None:
    """Draw arrows normal to the two-dimensional reservoir boundary."""
    arrow = {"arrowstyle": "-|>", "color": "#B33A3A", "linewidth": 1.0}
    axis.annotate("", xy=(-3.9, center_depth_km), xytext=(-2.9, center_depth_km), arrowprops=arrow)
    axis.annotate("", xy=(3.9, center_depth_km), xytext=(2.9, center_depth_km), arrowprops=arrow)
    axis.annotate(
        "", xy=(0.0, center_depth_km - 0.9), xytext=(0.0, center_depth_km - 0.4), arrowprops=arrow
    )
    axis.annotate(
        "", xy=(0.0, center_depth_km + 0.9), xytext=(0.0, center_depth_km + 0.4), arrowprops=arrow
    )


def plot_model_setup_schematic(output_stem: Path) -> tuple[Path, Path]:
    """Write PNG and PDF diagrams of model geometry and written boundaries."""
    output_stem.parent.mkdir(parents=True, exist_ok=True)
    figure, (section, plan) = plt.subplots(1, 2, figsize=(12.0, 6.8), constrained_layout=True)

    section.add_patch(Rectangle((-25.0, 0.0), 50.0, 10.0, facecolor="#F7F8FA", edgecolor="none"))
    section.plot([-25.0, 25.0], [0.0, 0.0], color="#333333", linewidth=2.0)
    section.plot([-25.0, -25.0], [0.0, 10.0], color="#2878A0", linestyle="--", linewidth=1.6)
    section.plot([25.0, 25.0], [0.0, 10.0], color="#2878A0", linestyle="--", linewidth=1.6)
    section.plot([-25.0, 25.0], [10.0, 10.0], color="#6A8F3A", linewidth=2.0)
    section.add_patch(
        Ellipse(
            (0.0, 1.6),
            width=6.0,
            height=1.0,
            facecolor="#F3B7A8",
            edgecolor="#8F3025",
            linewidth=1.5,
            zorder=3,
        )
    )
    _draw_pressure_arrows(section, center_depth_km=1.6)
    section.annotate(
        "Reservoir center 1.6 km\n6 × 3 × 1 km · 1200 °C",
        xy=(0.0, 1.6),
        xytext=(8.0, 2.7),
        ha="center",
        va="center",
        fontsize=8,
        arrowprops={"arrowstyle": "-", "color": "#555555", "linewidth": 0.8},
    )
    section.text(0.0, 0.25, "Free top · 0 °C", ha="center", va="top", fontsize=9)
    section.text(
        -23.5, 5.0, "Roller side\n30 °C/km*", rotation=90, ha="center", va="center", fontsize=8
    )
    section.text(
        23.5, 5.0, "Roller side\n30 °C/km*", rotation=270, ha="center", va="center", fontsize=8
    )
    section.text(0.0, 9.6, "Target Winkler base · 30 °C/km*", ha="center", va="center", fontsize=8)
    section.text(
        0.0, 4.1, "Outward pressure load", ha="center", va="center", color="#8F3025", fontsize=8
    )
    section.set_xlim(-28.0, 28.0)
    section.set_ylim(11.5, -1.4)
    section.set_aspect("equal", adjustable="box")
    section.set_xlabel("Distance across ridge (km)")
    section.set_ylabel("Depth below seafloor (km)")
    section.set_title("Vertical cross-section")
    section.grid(color="#D8DDE3", linewidth=0.5, alpha=0.7)

    plan.add_patch(Rectangle((-25.0, -25.0), 50.0, 50.0, facecolor="#F7F8FA", edgecolor="none"))
    plan.add_patch(
        Ellipse(
            (0.0, 0.0),
            width=6.0,
            height=3.0,
            facecolor="#F3B7A8",
            edgecolor="#8F3025",
            linewidth=1.5,
        )
    )
    plan.plot(
        [-25.0, 25.0, 25.0, -25.0, -25.0],
        [-25.0, -25.0, 25.0, 25.0, -25.0],
        color="#2878A0",
        linestyle="--",
        linewidth=1.6,
    )
    for x0, x1 in ((-25.0, -28.0), (25.0, 28.0)):
        plan.annotate(
            "",
            xy=(x1, 0.0),
            xytext=(x0, 0.0),
            arrowprops={"arrowstyle": "-|>", "color": "#C38122", "linewidth": 1.7},
        )
    plan.text(0.0, 0.0, "6 km × 3 km", ha="center", va="center", fontsize=9)
    plan.text(
        0.0,
        26.5,
        "60 mm/year full spreading rate;\nper-face split unresolved",
        ha="center",
        va="bottom",
        color="#8B5A12",
        fontsize=9,
    )
    plan.text(
        0.0,
        -26.0,
        "Dashed perimeter: roller lateral boundaries",
        ha="center",
        va="top",
        color="#245F7D",
        fontsize=9,
    )
    plan.set_xlim(-30.0, 30.0)
    plan.set_ylim(-30.0, 30.0)
    plan.set_aspect("equal", adjustable="box")
    plan.set_xlabel("Distance across ridge (km)")
    plan.set_ylabel("Distance along ridge (km)")
    plan.set_title("Plan view")
    plan.grid(color="#D8DDE3", linewidth=0.5, alpha=0.7)

    figure.suptitle("Axial thermomechanical model setup — schematic")
    figure.text(
        0.5,
        -0.015,
        "The domain follows the project setup direction: 50 km × 50 km by 10 km depth. "
        "*The side and basal 30 °C/km geotherm is an explicit thermal assumption.\n"
        "The target Winkler base is not represented in current PyLith runs; its Axial "
        "density contrast and prestress are unresolved. The tectonic face-rate split is unresolved.",
        ha="center",
        va="top",
        fontsize=8.5,
    )
    png_path = output_stem.with_suffix(".png")
    pdf_path = output_stem.with_suffix(".pdf")
    figure.savefig(png_path, dpi=220, bbox_inches="tight")
    figure.savefig(pdf_path, bbox_inches="tight")
    plt.close(figure)
    return png_path, pdf_path


def main() -> None:
    """Parse output path and write the model setup schematic."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-stem", type=Path, default=DEFAULT_OUTPUT_STEM)
    args = parser.parse_args()
    png_path, pdf_path = plot_model_setup_schematic(args.output_stem)
    print(f"wrote {png_path} and {pdf_path}")


if __name__ == "__main__":
    main()
