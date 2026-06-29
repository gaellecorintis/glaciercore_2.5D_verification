#!/usr/bin/env python3
"""Waterfall stack-up comparison across an ordered list of designs.

The script renders **two** complementary plots:

1. **Waterfall** (``<output>``): full stack-up bars + delta callouts in each gap.
2. **Trend line** (``<output>_trend.png``): a simple junction-temperature
   progression with nodes per design and curved green delta arrows between
   consecutive nodes.

Every design is drawn as a **full** stack-up bar (same orientation/style as
``plot_stackup_camparison_designs.py``):

  * y = 0 corresponds to the junction temperature; y = total_dT corresponds
    to the inlet temperature. Heat flows from the bottom up.
  * Each bar has a purple "fixed" block (Die Substrate + TIM, stacked from
    junction up with a dashed internal separator) and a colored "modifiable"
    block (Cold Plate Base + Channel Convection + Fluid Heating combined,
    with a dashed Cold Plate Base sub-separator).
  * The modifiable block is colored on a red → green progression so the eye
    immediately reads "worst → best" left-to-right.

Between every pair of consecutive bars, a "delta callout" makes the
incremental change visually unmissable:

  * A translucent colored band fills the exact "saved" (or "added") ΔT range
    in the gap between the previous bar's top and the new one's top.
  * Dashed horizontal guide lines mark the previous and new top heights.
  * A bold arrow drops from the previous top down to the new top.
  * A bubble-styled label calls out "−X.XX °C (−Y.Y % vs ref)".

Inputs are ``per_component_stackup.json`` files produced by
``scripts/generate_per_component_stackup.py``.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
import sys

from attrs import frozen
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch
import numpy as np


DIE_SUBSTRATE = "Die Substrate"
TIM = "TIM"
COLD_PLATE_SUBSTRATE = "Cold Plate Substrate"
CHANNEL_CONVECTION = "Channel Convection"
FLUID_HEATING = "Fluid Heating"

DIE_COLOR = "#6b3fa0"
TIM_COLOR = "#6b3fa0"
IMPROVEMENT_COLOR = "#2ECC71"
DEGRADATION_COLOR = "#E74C3C"

# Curated red → green progression for the modifiable block of each bar.
# For N bars, we evenly subsample the palette.
PALETTE_BY_N: dict[int, list[str]] = {
    1: ["#E03C3F"],
    2: ["#E03C3F", "#27AE60"],
    3: ["#E03C3F", "#3498DB", "#27AE60"],
    4: ["#E03C3F", "#F39C12", "#3498DB", "#27AE60"],
    5: ["#E03C3F", "#F39C12", "#3498DB", "#1ABC9C", "#27AE60"],
}

BAR_WIDTH = 0.70
LABEL_FONTSIZE = 12
TEMP_FONTSIZE = 11
BIG_LABEL_FONTSIZE = 14
CALLOUT_FONTSIZE = 14


@frozen
class Component:
    name: str
    delta_temperature_celsius: float


@frozen
class Design:
    label: str
    components: list[Component]
    junction_temperature_celsius: float
    inlet_temperature_celsius: float
    total_delta_temperature_celsius: float

    def get_dt(self, name: str) -> float:
        for c in self.components:
            if c.name == name:
                return c.delta_temperature_celsius
        return 0.0


def load_design(path: Path, label: str) -> Design:
    raw = json.loads(path.read_text())
    components = [
        Component(name=c["name"], delta_temperature_celsius=float(c["delta_T_C"]))
        for c in raw["components"]
    ]
    total_dt = float(raw.get("total_delta_T_C", sum(c.delta_temperature_celsius for c in components)))
    junction = float(raw["junction_temperature_C"])
    inlet = float(raw["inlet_temperature_C"])
    return Design(
        label=label,
        components=components,
        junction_temperature_celsius=junction,
        inlet_temperature_celsius=inlet,
        total_delta_temperature_celsius=total_dt,
    )


@frozen
class BarStyle:
    text_color: str
    sublabel_color: str
    separator_color: str
    on_block_text_color: str


def get_palette(n: int) -> list[str]:
    if n in PALETTE_BY_N:
        return PALETTE_BY_N[n]
    cmap = plt.get_cmap("RdYlGn")
    return [mcolors.to_hex(cmap((i + 0.5) / n)) for i in range(n)]


def _draw_anchor_bar(
    ax: plt.Axes,
    x: float,
    design: Design,
    *,
    mod_color: str,
    is_reference: bool,
    ref_mod_dt: float,
    style: BarStyle,
) -> None:
    """Full stack-up bar: purple fixed block + colored modifiable block."""
    junction = design.junction_temperature_celsius
    hw = BAR_WIDTH / 2

    die_dt = design.get_dt(DIE_SUBSTRATE)
    tim_dt = design.get_dt(TIM)
    cp_dt = design.get_dt(COLD_PLATE_SUBSTRATE)
    channel_dt = design.get_dt(CHANNEL_CONVECTION)
    fluid_dt = design.get_dt(FLUID_HEATING)

    fixed_dt = die_dt + tim_dt
    mod_dt = cp_dt + channel_dt + fluid_dt
    total_dt = fixed_dt + mod_dt

    ax.bar(x, die_dt, BAR_WIDTH, bottom=0.0,
           color=DIE_COLOR, edgecolor="none", alpha=0.92, zorder=3)
    if die_dt >= 2.5:
        ax.text(x, die_dt / 2, "Die Substrate",
                ha="center", va="center", fontsize=LABEL_FONTSIZE,
                color=style.on_block_text_color, zorder=5)

    if die_dt > 0:
        ax.plot([x - hw + 0.02, x + hw - 0.02], [die_dt, die_dt],
                color=style.separator_color, linestyle="--",
                linewidth=0.8, alpha=0.6, zorder=4)

    ax.bar(x, tim_dt, BAR_WIDTH, bottom=die_dt,
           color=TIM_COLOR, edgecolor="none", alpha=0.92, zorder=3)
    if tim_dt >= 2.5:
        ax.text(x, die_dt + tim_dt / 2, "TIM",
                ha="center", va="center", fontsize=LABEL_FONTSIZE,
                color=style.on_block_text_color, zorder=5)

    ax.plot([x - hw, x + hw], [fixed_dt, fixed_dt],
            color=style.separator_color, linewidth=2.0, alpha=0.95, zorder=4)

    ax.bar(x, mod_dt, BAR_WIDTH, bottom=fixed_dt,
           color=mod_color, edgecolor="none", alpha=0.92, zorder=3)

    if cp_dt > 0:
        cp_top_y = fixed_dt + cp_dt
        ax.plot([x - hw + 0.02, x + hw - 0.02], [cp_top_y, cp_top_y],
                color=style.separator_color, linestyle="--", linewidth=0.8, alpha=0.6, zorder=4)
        if cp_dt >= 2.5:
            ax.text(x, fixed_dt + cp_dt / 2, "Cold Plate Base",
                    ha="center", va="center", fontsize=LABEL_FONTSIZE,
                    color=style.on_block_text_color, zorder=5)

    if is_reference:
        big_label = f"{mod_dt:.2f} °C\n(ref)"
    else:
        pct = ((mod_dt - ref_mod_dt) / ref_mod_dt * 100.0) if ref_mod_dt > 0 else 0.0
        sign = "−" if pct <= 0 else "+"
        big_label = f"{mod_dt:.2f} °C\n({sign}{abs(pct):.1f} %)"
    upper_mod_center_y = fixed_dt + cp_dt + (mod_dt - cp_dt) / 2
    ax.text(x, upper_mod_center_y, big_label,
            ha="center", va="center", fontsize=BIG_LABEL_FONTSIZE, fontweight="bold",
            color="#ffffff", zorder=6)

    label_x = x - hw - 0.06
    label_kw = {"ha": "right", "va": "center",
                "fontsize": TEMP_FONTSIZE, "color": style.text_color, "zorder": 6}
    if die_dt > 0:
        ax.text(label_x, die_dt, f"{junction - die_dt:.1f}°C", **label_kw)
    ax.text(label_x, fixed_dt, f"{junction - fixed_dt:.1f}°C", **label_kw)
    if cp_dt > 0:
        cp_top_y = fixed_dt + cp_dt
        ax.text(label_x, cp_top_y, f"{junction - cp_top_y:.1f}°C", **label_kw)
    ax.text(label_x, total_dt, f"{design.inlet_temperature_celsius:.1f}°C", **label_kw)
    ax.text(x, -1.8, f"T_j = {junction:.1f} °C",
            ha="center", va="top", fontsize=TEMP_FONTSIZE + 2,
            color=style.text_color, fontweight="bold", zorder=6)


def _draw_gap_delta(
    ax: plt.Axes,
    x_left_edge: float,
    x_right_edge: float,
    prev_top: float,
    curr_top: float,
    *,
    ref_mod_dt: float,
    style: BarStyle,
) -> None:
    """Impressive delta callout in the gap between two adjacent bars:
    translucent "saved" ribbon + dashed guides + bold arrow + bubble label.
    """
    delta = curr_top - prev_top
    if abs(delta) < 1e-3:
        return
    is_improvement = delta < 0
    color = IMPROVEMENT_COLOR if is_improvement else DEGRADATION_COLOR
    sign = "−" if delta < 0 else "+"

    rad = -0.12 if is_improvement else 0.12
    arrow = FancyArrowPatch(
        (x_left_edge, prev_top), (x_right_edge, curr_top),
        connectionstyle=f"arc3,rad={rad}",
        arrowstyle="-|>", mutation_scale=22, color=color, linewidth=2.4,
        shrinkA=2, shrinkB=2, zorder=5,
    )
    ax.add_patch(arrow)

    x_mid = (x_left_edge + x_right_edge) / 2
    y_top = max(prev_top, curr_top)
    y_bot = min(prev_top, curr_top)
    label_y = (y_top + 5.5) if is_improvement else (y_bot - 5.5)
    ax.text(
        x_mid, label_y,
        f"ΔT = {sign}{abs(delta):.2f} °C",
        ha="center", va="center", fontsize=CALLOUT_FONTSIZE, fontweight="bold",
        color=color, zorder=7,
    )


def plot_waterfall(
    designs: list[Design],
    output_path: Path,
    *,
    white_bg: bool = False,
    title: str | None = None,
) -> None:
    if len(designs) < 2:
        raise ValueError("Need at least 2 designs.")

    n = len(designs)
    if white_bg:
        style = BarStyle(text_color="#1a1a1a", sublabel_color="#555555",
                         separator_color="#333333", on_block_text_color="#ffffff")
    else:
        style = BarStyle(text_color="#e8e8e8", sublabel_color="#aaaaaa",
                         separator_color="#ffffff", on_block_text_color="#f5f5f5")

    palette = get_palette(n)
    x_positions = np.arange(n, dtype=float) * 1.55
    fig, ax = plt.subplots(figsize=(max(8.0, 3.4 * n), 8.0))
    if white_bg:
        fig.patch.set_facecolor("white")
        ax.set_facecolor("white")
    else:
        fig.patch.set_alpha(0)
        ax.set_facecolor("none")

    ref_design = designs[0]
    ref_mod = (ref_design.get_dt(COLD_PLATE_SUBSTRATE)
               + ref_design.get_dt(CHANNEL_CONVECTION)
               + ref_design.get_dt(FLUID_HEATING))

    for i, design in enumerate(designs):
        _draw_anchor_bar(
            ax, x_positions[i], design,
            mod_color=palette[i],
            is_reference=(i == 0),
            ref_mod_dt=ref_mod,
            style=style,
        )

    hw = BAR_WIDTH / 2
    for i in range(n - 1):
        x_left_edge = x_positions[i] + hw
        x_right_edge = x_positions[i + 1] - hw
        _draw_gap_delta(
            ax, x_left_edge, x_right_edge,
            prev_top=designs[i].total_delta_temperature_celsius,
            curr_top=designs[i + 1].total_delta_temperature_celsius,
            ref_mod_dt=ref_mod,
            style=style,
        )

    x_left_lim = x_positions[0] - 0.75
    x_right_lim = x_positions[-1] + 0.75
    ax.plot([x_left_lim, x_right_lim], [0, 0],
            color=style.sublabel_color, linestyle="--", linewidth=1.2, alpha=0.7, zorder=2)
    ax.text(x_right_lim + 0.02, 0, "Junction",
            ha="left", va="center", fontsize=12, fontweight="bold", color=style.sublabel_color)

    ax.set_xticks(x_positions)
    ax.set_xticklabels([d.label for d in designs], fontsize=14, color=style.text_color)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(axis="y", left=False, labelleft=False)
    ax.tick_params(axis="x", colors=style.text_color, length=0)

    y_max = max(d.total_delta_temperature_celsius for d in designs) + 9.0
    ax.set_ylim(-6.0, y_max)
    ax.set_xlim(x_left_lim, x_right_lim + 0.5)

    if title:
        ax.set_title(title, color=style.text_color, fontsize=13, pad=15)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight", transparent=not white_bg)
    plt.close(fig)
    logging.info("Plot saved as: %s", output_path)


def plot_progression(
    designs: list[Design],
    output_path: Path,
    *,
    white_bg: bool = False,
) -> None:
    """Trend plot: junction temperature per design, connected by a blue line,
    with curved green delta arrows + ΔT labels between adjacent nodes."""
    if len(designs) < 2:
        raise ValueError("Need at least 2 designs.")

    if white_bg:
        text_color = "#1a1a1a"
        spine_color = "#333333"
        node_face = "#3498DB"
        node_edge = "#1F6EAB"
        line_color = "#3498DB"
    else:
        text_color = "#e8e8e8"
        spine_color = "#aaaaaa"
        node_face = "#5DADE2"
        node_edge = "#3498DB"
        line_color = "#3498DB"

    delta_color = IMPROVEMENT_COLOR

    n = len(designs)
    x_positions = np.arange(n, dtype=float)
    temps = np.array([d.junction_temperature_celsius for d in designs])

    fig, ax = plt.subplots(figsize=(max(7.0, 2.6 * n), 7.0))
    if white_bg:
        fig.patch.set_facecolor("white")
        ax.set_facecolor("white")
    else:
        fig.patch.set_alpha(0)
        ax.set_facecolor("none")

    ax.plot(x_positions, temps, "-", color=line_color, linewidth=2.4,
            zorder=3, alpha=0.9)
    ax.scatter(x_positions, temps, s=200, facecolor=node_face,
               edgecolor=node_edge, linewidth=2.0, zorder=5)

    for x, t in zip(x_positions, temps):
        ax.text(x, t - 0.50, f"{t:.2f} °C",
                ha="center", va="top", fontsize=13, color=text_color,
                fontweight="bold", zorder=6)

    for i in range(n - 1):
        x1, y1 = x_positions[i], temps[i]
        x2, y2 = x_positions[i + 1], temps[i + 1]
        delta = y2 - y1
        color = delta_color if delta <= 0 else DEGRADATION_COLOR
        rad = -0.15 if delta <= 0 else 0.15
        arrow = FancyArrowPatch(
            (x1, y1), (x2, y2),
            connectionstyle=f"arc3,rad={rad}",
            arrowstyle="-|>", mutation_scale=20, color=color, linewidth=2.2,
            shrinkA=10, shrinkB=10, zorder=4,
        )
        ax.add_patch(arrow)

        sign = "−" if delta < 0 else "+"
        x_mid = (x1 + x2) / 2
        y_top = max(y1, y2)
        y_bot = min(y1, y2)
        y_label = (y_top + 1.5) if delta <= 0 else (y_bot - 1.5)
        ax.text(x_mid, y_label,
                f"ΔT = {sign}{abs(delta):.2f} °C",
                ha="center", va="center", color=color,
                fontsize=12, fontweight="bold", zorder=6)

    ax.set_xticks(x_positions)
    ax.set_xticklabels([d.label for d in designs], fontsize=13, color=text_color)
    ax.tick_params(axis="x", colors=text_color, length=0, pad=10)
    ax.tick_params(axis="y", colors=text_color)
    ax.set_ylabel("Junction temperature [°C]", color=text_color, fontsize=13)

    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(spine_color)
        ax.spines[side].set_linewidth(1.2)

    t_min, t_max = float(temps.min()), float(temps.max())
    span = max(t_max - t_min, 1.0)
    ax.set_ylim(t_min - 0.30 * span - 1.0, t_max + 0.30 * span + 1.0)
    ax.set_xlim(-0.5, n - 0.5)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight", transparent=not white_bg)
    plt.close(fig)
    logging.info("Plot saved as: %s", output_path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--input", nargs=2, action="append", metavar=("STACKUP_JSON", "LABEL"), required=True,
        help="Path to a per_component_stackup.json and a display label. Repeat in order (left to right).",
    )
    parser.add_argument("-o", "--output", type=Path, default=Path("waterfall_stackup.png"), help="Output PNG path.")
    parser.add_argument("--white-bg", action="store_true", help="Render on a white background with dark text.")
    parser.add_argument("--title", type=str, default="", help="Optional plot title (default: none).")
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = parse_args()
    try:
        designs = [load_design(Path(path), label) for path, label in args.input]
        plot_waterfall(designs, args.output, white_bg=args.white_bg, title=args.title or None)
        trend_path = args.output.with_name(args.output.stem + "_trend" + args.output.suffix)
        plot_progression(designs, trend_path, white_bg=args.white_bg)
    except (FileNotFoundError, ValueError, KeyError) as e:
        logging.error("Error: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
