#!/usr/bin/env python3
"""
Compare monitor region temperatures between two simulation designs.

Parses the "Monitor Region Temperatures" markdown table from two glaciercore
simulation reports and generates an overlaid lollipop chart. Design 1
(baseline) is rendered in a faded style behind Design 2 (new) so that
improvements are immediately visible.

Zones (groups of monitor regions sharing a target temperature) are user-supplied
on the command line via ``--zone NAME TARGET``. Monitor region rows whose name
starts with NAME are attached to that zone and plotted against its target line.
Regions that match no declared zone are skipped.
"""

import argparse
import re
import sys
from dataclasses import dataclass
from itertools import cycle
from pathlib import Path

from colorama import Fore


_DEFAULT_PALETTE = [
    "#1a3a5c",
    "#5c3a1a",
    "#3a1a5c",
    "#1a5c3a",
    "#5c1a3a",
    "#3a5c1a",
]


@dataclass(frozen=True)
class ZoneSpec:
    """A zone groups monitor regions that share a target temperature."""

    name: str       # matched as a prefix against monitor region names
    target: float   # target temperature in °C
    label: str      # display label
    bg_color: str   # background panel color


def parse_zone_specs(
    zone_args: list[list[str]] | None,
    label_overrides: list[list[str]] | None,
    color_overrides: list[list[str]] | None,
) -> list[ZoneSpec]:
    if not zone_args:
        return []
    label_map = dict(label_overrides or [])
    color_map = dict(color_overrides or [])
    palette = cycle(_DEFAULT_PALETTE)
    specs: list[ZoneSpec] = []
    for name, target_str in zone_args:
        try:
            target = float(target_str)
        except ValueError:
            print(f"{Fore.RED}Error: invalid target '{target_str}' for zone '{name}' "
                  f"(must be a number){Fore.RESET}")
            sys.exit(1)
        specs.append(ZoneSpec(
            name=name,
            target=target,
            label=label_map.get(name, name),
            bg_color=color_map.get(name, next(palette)),
        ))
    return specs


def _match_zone(region_name: str, zones: list[ZoneSpec]) -> ZoneSpec | None:
    """Return the longest-matching zone whose name is a prefix of region_name."""
    matches = [z for z in zones if region_name.startswith(z.name)]
    if not matches:
        return None
    return max(matches, key=lambda z: len(z.name))


def _zone_sort_key(name: str, zones: list[ZoneSpec]) -> tuple[int, str]:
    zone = _match_zone(name, zones)
    if zone is None:
        return (len(zones), name)
    return (zones.index(zone), name[len(zone.name):])


def parse_monitor_regions(report_path: Path) -> list[tuple[str, float]]:
    """Parse monitor region names and Cold Plate Base temperatures from a report."""
    text = report_path.read_text()

    section_match = re.search(r"### Monitor Region Temperatures\s*\n", text)
    if not section_match:
        print(f"{Fore.RED}Error: 'Monitor Region Temperatures' section not found in {report_path}{Fore.RESET}")
        sys.exit(1)

    section_text = text[section_match.end():]
    lines = section_text.split("\n")

    header_line = None
    data_start = 0
    for i, line in enumerate(lines):
        if line.strip().startswith("|") and "Region" in line:
            header_line = line
            data_start = i + 2
            break

    if header_line is None:
        print(f"{Fore.RED}Error: Could not find table header in Monitor Region Temperatures{Fore.RESET}")
        sys.exit(1)

    columns = [c.strip() for c in header_line.split("|")]
    columns = [c for c in columns if c]

    try:
        region_idx = next(i for i, c in enumerate(columns) if "Region" in c)
        cp_base_idx = next(i for i, c in enumerate(columns) if "Cold Plate Base" in c)
    except StopIteration:
        print(f"{Fore.RED}Error: Required columns ('Region', 'Cold Plate Base') not found in table header{Fore.RESET}")
        print(f"  Found columns: {columns}")
        sys.exit(1)

    regions: list[tuple[str, float]] = []
    for line in lines[data_start:]:
        line = line.strip()
        if not line.startswith("|"):
            break
        cells = [c.strip() for c in line.split("|")]
        cells = [c for c in cells if c]
        if len(cells) <= max(region_idx, cp_base_idx):
            continue
        try:
            name = cells[region_idx]
            temp = float(cells[cp_base_idx])
            regions.append((name, temp))
        except (ValueError, IndexError):
            continue

    if not regions:
        print(f"{Fore.YELLOW}Warning: No monitor region data found in {report_path}{Fore.RESET}")

    return regions


def create_comparison_chart(
    regions_1: list[tuple[str, float]],
    regions_2: list[tuple[str, float]],
    zones: list[ZoneSpec],
    output_path: Path,
    label_1: str = "Design 1",
    label_2: str = "Design 2",
    title: str | None = None,
    exclude_zones: list[str] | None = None,
) -> None:
    """Create an overlaid lollipop chart comparing two designs against zone targets."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.lines as mlines

    excluded = set(exclude_zones or [])

    def _keep(region_name: str) -> bool:
        zone = _match_zone(region_name, zones)
        return zone is not None and zone.name not in excluded

    regions_1 = sorted([r for r in regions_1 if _keep(r[0])],
                       key=lambda r: _zone_sort_key(r[0], zones))
    regions_2 = sorted([r for r in regions_2 if _keep(r[0])],
                       key=lambda r: _zone_sort_key(r[0], zones))

    names_1 = [r[0] for r in regions_1]
    temps_1 = dict(regions_1)
    names_2 = [r[0] for r in regions_2]
    temps_2 = dict(regions_2)

    all_names_set: dict[str, None] = {}
    for n in names_1:
        all_names_set[n] = None
    for n in names_2:
        all_names_set[n] = None
    all_names = sorted(all_names_set.keys(), key=lambda n: _zone_sort_key(n, zones))

    if not all_names:
        print(f"{Fore.RED}Error: no monitor regions matched any declared zone{Fore.RESET}")
        sys.exit(1)

    _FG = "#e0e0e0"

    cm = 1 / 2.54
    fig, ax = plt.subplots(figsize=(18 * cm, 15 * cm))
    fig.patch.set_alpha(0)
    ax.set_facecolor("none")

    x = list(range(len(all_names)))

    targets = [z.target for z in zones]
    all_temps = list(temps_1.values()) + list(temps_2.values()) + targets
    y_min = min(all_temps) - 3.0
    y_max = max(all_temps) + 6.0
    ax.set_ylim(y_min, y_max)

    zone_indices: dict[str, list[int]] = {}
    for i, name in enumerate(all_names):
        zone = _match_zone(name, zones)
        if zone is None:
            continue
        zone_indices.setdefault(zone.name, []).append(i)

    zone_by_name = {z.name: z for z in zones}

    for zone_name, indices in zone_indices.items():
        zone = zone_by_name[zone_name]
        ax.axvspan(indices[0] - 0.5, indices[-1] + 0.5,
                   color=zone.bg_color, alpha=0.4, zorder=0)
        ax.hlines(
            zone.target, indices[0] - 0.5, indices[-1] + 0.5,
            colors=_FG, linestyles="--", linewidth=1.0, alpha=0.5, zorder=2,
        )

    dx = 0.12
    baseline_color = "#888888"
    baseline_alpha = 0.60
    new_color = "#4fc3f7"

    for i, name in enumerate(all_names):
        zone = _match_zone(name, zones)
        target = zone.target if zone is not None else 0.0

        t1 = temps_1.get(name)
        if t1 is not None:
            ax.vlines(i - dx, target, t1, color=baseline_color, linewidth=1.5,
                      alpha=baseline_alpha, zorder=2)
            ax.plot(i - dx, t1, "o", color=baseline_color, markersize=7,
                    alpha=baseline_alpha, zorder=3)
            ax.text(
                i - dx, t1 + (0.4 if t1 >= target else -0.4), f"{t1:.1f}",
                ha="center", va="bottom" if t1 >= target else "top",
                fontsize=12, color=baseline_color, alpha=0.8,
            )

        t2 = temps_2.get(name)
        if t2 is not None:
            ax.vlines(i + dx, target, t2, color=new_color, linewidth=1.8, zorder=4)
            ax.plot(i + dx, t2, "o", color=new_color, markersize=7, zorder=5)
            ax.text(
                i + dx, t2 + (0.4 if t2 >= target else -0.4), f"{t2:.1f}",
                ha="center", va="bottom" if t2 >= target else "top",
                fontsize=12, color=new_color,
            )

    for zone_name, indices in zone_indices.items():
        zone = zone_by_name[zone_name]
        x_center = (indices[0] + indices[-1]) / 2.0
        label = f"{zone.label}\n(target {zone.target:.0f} °C)"
        ax.text(
            x_center, y_max - 0.3, label,
            ha="center", va="top", fontsize=13, color=_FG, zorder=7,
        )

    ax.set_xticks(x)
    ax.set_xticklabels(all_names)
    ax.set_ylabel("Cold Plate Base Temperature (°C)", fontsize=14, color=_FG)
    ax.set_xlabel("Monitor Locations", fontsize=14, color=_FG)
    ax.tick_params(axis="x", rotation=45, labelsize=12, colors=_FG)
    plt.setp(ax.get_xticklabels(), ha="right")
    ax.tick_params(axis="y", labelsize=12, colors=_FG)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_linewidth(0.5)
    ax.spines["bottom"].set_linewidth(0.5)
    ax.spines["left"].set_color(_FG)
    ax.spines["bottom"].set_color(_FG)

    legend_handles = [
        mlines.Line2D([], [], color=baseline_color, marker="o", linewidth=1.5,
                      markersize=7, alpha=baseline_alpha, label=label_1),
        mlines.Line2D([], [], color=new_color, marker="o", linewidth=1.8,
                      markersize=7, label=label_2),
    ]
    legend = ax.legend(handles=legend_handles, loc="lower center", fontsize=12,
                       framealpha=0.9, ncol=2, bbox_to_anchor=(0.5, 1.01))
    legend.get_frame().set_facecolor((0.16, 0.16, 0.16, 0.7))
    legend.get_frame().set_edgecolor("#555555")
    for text in legend.get_texts():
        text.set_color(_FG)

    if title:
        fig.suptitle(title, fontsize=16, fontweight="bold", y=0.99, color=_FG)

    fig.tight_layout()
    fig.savefig(output_path, dpi=300, bbox_inches="tight", transparent=True)
    plt.close(fig)
    print(f"Comparison chart saved: {output_path}")


def _derive_label(report_path: Path) -> str:
    """Walk up from the report file to find a distinctive directory name."""
    resolved = report_path.resolve()
    generic = {"simulation_result", "simulation_result_hbm", "simulation", "simulation_results"}
    for part in reversed(resolved.parent.parts):
        if part not in generic:
            return part
    return resolved.parent.name


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare monitor region temperatures between two simulation designs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
example:
  python create_lollipop_plot.py report1.md report2.md \\
      --zone Z1 55.0 --zone Z2 48.0 --zone Z3 55.0 \\
      --zone-label Z1 "Zone 1" --zone-label Z2 "Zone 2" --zone-label Z3 "Zone 3"
""",
    )
    parser.add_argument(
        "report_design_1",
        type=Path,
        help="Path to the simulation_results_report.md for design 1 (baseline)",
    )
    parser.add_argument(
        "report_design_2",
        type=Path,
        help="Path to the simulation_results_report.md for design 2 (new)",
    )
    parser.add_argument(
        "--zone",
        action="append",
        nargs=2,
        metavar=("NAME", "TARGET"),
        required=True,
        help="A zone definition: NAME (matched as a prefix of monitor region names) "
             "and TARGET temperature in °C. Repeat for each zone.",
    )
    parser.add_argument(
        "--zone-label",
        action="append",
        nargs=2,
        metavar=("NAME", "LABEL"),
        default=None,
        help="Override the display label for zone NAME (default: NAME). Repeatable.",
    )
    parser.add_argument(
        "--zone-color",
        action="append",
        nargs=2,
        metavar=("NAME", "COLOR"),
        default=None,
        help="Override the background panel color for zone NAME "
             "(default: cycled palette). Repeatable.",
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        help="Output PNG file path (default: comparison_cold_plate_base.png next to design 2 report)",
    )
    parser.add_argument(
        "--label-1",
        default=None,
        help="Legend label for design 1 (default: parent directory name)",
    )
    parser.add_argument(
        "--label-2",
        default=None,
        help="Legend label for design 2 (default: parent directory name)",
    )
    parser.add_argument(
        "--title",
        default=None,
        help="Plot title (e.g. 'GFX Powermap' or 'HBM Powermap')",
    )
    parser.add_argument(
        "--exclude-zone",
        action="append",
        default=None,
        help="Zone NAME to exclude. Repeatable.",
    )
    parser.add_argument(
        "--extra-report-1",
        type=Path,
        action="append",
        default=None,
        help="Additional report file(s) whose monitor regions are merged into design 1 "
             "(useful when zones are split across passes). Repeatable.",
    )
    parser.add_argument(
        "--extra-report-2",
        type=Path,
        action="append",
        default=None,
        help="Additional report file(s) whose monitor regions are merged into design 2 "
             "(useful when zones are split across passes). Repeatable.",
    )
    args = parser.parse_args()

    zones = parse_zone_specs(args.zone, args.zone_label, args.zone_color)

    report_paths = [args.report_design_1, args.report_design_2]
    report_paths.extend(args.extra_report_1 or [])
    report_paths.extend(args.extra_report_2 or [])
    for p in report_paths:
        if not p.exists():
            print(f"{Fore.RED}Error: Report file {p} does not exist{Fore.RESET}")
            sys.exit(1)

    label_1 = args.label_1 or _derive_label(args.report_design_1)
    label_2 = args.label_2 or _derive_label(args.report_design_2)

    def _merge_regions(
        base: list[tuple[str, float]],
        extras: list[Path] | None,
    ) -> list[tuple[str, float]]:
        if not extras:
            return base
        seen = {name for name, _ in base}
        merged = list(base)
        for extra in extras:
            for name, temp in parse_monitor_regions(extra):
                if name in seen:
                    continue
                seen.add(name)
                merged.append((name, temp))
        return merged

    regions_1 = _merge_regions(parse_monitor_regions(args.report_design_1), args.extra_report_1)
    regions_2 = _merge_regions(parse_monitor_regions(args.report_design_2), args.extra_report_2)
    if not regions_1 and not regions_2:
        sys.exit(1)

    output_path = args.output or args.report_design_2.parent / "comparison_cold_plate_base.png"
    create_comparison_chart(
        regions_1, regions_2, zones, output_path, label_1, label_2,
        title=args.title, exclude_zones=args.exclude_zone,
    )


if __name__ == "__main__":
    main()
