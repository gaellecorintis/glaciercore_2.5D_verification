"""Create a dumbbell-style plot of die vs HBM junction temperatures across designs.

Each design is a glaciercore simulation results JSON file. The script scans the
top-level entries for hotspot regions whose ``region_name`` matches ``--die-region``
or ``--hbm-region``, extracts the maximum junction temperature
(``physical_temperature_junction_statistics.stats.max_value``), and plots them as
a two-marker dumbbell per design (die marker, HBM marker, connector line).

Usage examples
--------------
Pass designs explicitly on the command line. Each ``--design`` takes 2 values:
LABEL and RESULTS_JSON. Use ``\\n`` inside LABEL to insert a line break::

    python create_dumbell_plot.py \\
        --design "Skived Reference\\n200x2000 um" path/to/results_skived.json \\
        --design "B2 Optimized\\n100x1100 um"     path/to/results_b2.json \\
        --die-region die --hbm-region hbm \\
        --output ~/comparison.png

Or load from a JSON manifest with the schema
``[{"label": "...", "results": "<path>"}, ...]``::

    python create_dumbell_plot.py --input designs.json
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


JUNCTION_STATS_KEY = "physical_temperature_junction_statistics"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a dumbbell plot of die vs HBM junction temperatures across designs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-d", "--design",
        action="append",
        nargs=2,
        metavar=("LABEL", "RESULTS_JSON"),
        help=("A design entry: label and path to a glaciercore simulation results JSON. "
              r"Use \n in the label to insert a line break. "
              "Repeat the flag for each design."),
    )
    parser.add_argument(
        "-i", "--input",
        type=Path,
        help=("Path to a JSON manifest listing designs. Schema: "
              '[{"label": "...", "results": "<path-to-results-json>"}, ...]. '
              "Ignored if --design is provided."),
    )
    parser.add_argument(
        "--die-region",
        default="die",
        help="region_name of the die hotspot to extract (default: %(default)s).",
    )
    parser.add_argument(
        "--hbm-region",
        default="hbm",
        help="region_name of the HBM hotspot to extract (default: %(default)s).",
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default="~/design_comparison_plot.png",
        help="Output PNG path (default: %(default)s).",
    )
    parser.add_argument(
        "--title",
        type=str,
        default=r"Junction temperature ($T_{j}$) per Design",
        help="Plot title.",
    )
    parser.add_argument(
        "--xlabel",
        type=str,
        default=r"$T_{j}$  [°C]",
        help="X-axis label.",
    )
    parser.add_argument(
        "--die-label",
        type=str,
        default="Die",
        help="Legend label for the die marker.",
    )
    parser.add_argument(
        "--hbm-label",
        type=str,
        default="HBM",
        help="Legend label for the HBM marker.",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=200,
        help="Output DPI (default: %(default)s).",
    )
    return parser.parse_args()


def _extract_junction_temperature(results: dict[str, Any], region_name: str) -> float:
    """Return the max junction temperature among hotspots whose region_name matches."""
    matches: list[float] = []
    for value in results.values():
        if not isinstance(value, dict):
            continue
        if value.get("region_name") != region_name:
            continue
        stats_entry = value.get(JUNCTION_STATS_KEY)
        if stats_entry is None:
            continue
        matches.append(float(stats_entry["stats"]["max_value"]))
    if not matches:
        raise KeyError(
            f"No hotspot with region_name='{region_name}' and a "
            f"'{JUNCTION_STATS_KEY}' entry found"
        )
    return max(matches)


def load_designs(args: argparse.Namespace) -> list[tuple[str, float, float]]:
    if args.design:
        entries: list[tuple[str, Path]] = [
            (label, Path(path).expanduser()) for label, path in args.design
        ]
    elif args.input:
        with open(args.input, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        entries = [
            (entry["label"], Path(entry["results"]).expanduser()) for entry in manifest
        ]
    else:
        raise SystemExit("No designs provided. Use --design or --input.")

    out: list[tuple[str, float, float]] = []
    for label, results_path in entries:
        with open(results_path, "r", encoding="utf-8") as f:
            results = json.load(f)
        try:
            die_t = _extract_junction_temperature(results, args.die_region)
            hbm_t = _extract_junction_temperature(results, args.hbm_region)
        except KeyError as exc:
            raise SystemExit(f"{results_path}: {exc}") from exc
        out.append((label.replace("\\n", "\n"), die_t, hbm_t))
    return out


def make_plot(designs: list[tuple[str, float, float]],
              output_path: str,
              title: str,
              xlabel: str,
              die_label: str,
              hbm_label: str,
              dpi: int) -> None:
    plt.rcParams.update({
        "figure.facecolor": "none",
        "axes.facecolor": "none",
        "axes.edgecolor": "#444444",
        "text.color": "white",
        "axes.labelcolor": "white",
        "xtick.color": "white",
        "ytick.color": "white",
        "grid.color": "#444444",
        "font.family": "sans-serif",
        "font.size": 16,
    })

    names = [d[0] for d in designs]
    die_temps = [d[1] for d in designs]
    hbm_temps = [d[2] for d in designs]

    y_pos = np.arange(len(designs))[::-1]

    height = max(3.0, 1.1 * len(designs) + 1.5)
    fig, ax = plt.subplots(figsize=(12, height))

    for i in range(len(designs)):
        lo, hi = sorted([die_temps[i], hbm_temps[i]])
        ax.plot([lo, hi], [y_pos[i], y_pos[i]],
                color="#aaaaaa", linewidth=1.2, zorder=1)

    ax.scatter(die_temps, y_pos, s=140, color="#e03030", marker="o",
               label=die_label, zorder=3, edgecolors="white", linewidths=0.5)
    ax.scatter(hbm_temps, y_pos, s=140, color="#d4b06a", marker="s",
               label=hbm_label, zorder=3, edgecolors="white", linewidths=0.5)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(names, fontsize=15)
    ax.set_xlabel(xlabel, fontsize=18, labelpad=10)
    ax.set_ylabel("Design", fontsize=18, labelpad=10)
    ax.set_title(title, fontsize=20, fontweight="normal", pad=14)
    ax.tick_params(axis="x", labelsize=15)

    ax.grid(axis="x", linestyle=":", linewidth=0.5, alpha=0.5)

    legend = ax.legend(loc="lower right", fontsize=15, framealpha=0.3,
                       edgecolor="#666666", fancybox=True)
    legend.get_frame().set_facecolor("#2a2a2a")

    ax.margins(y=0.12)
    plt.tight_layout()

    output_path = os.path.expanduser(output_path)
    plt.savefig(output_path, dpi=dpi, bbox_inches="tight", transparent=True)
    print(f"Plot saved to {output_path}")


def main() -> None:
    args = parse_args()
    designs = load_designs(args)
    make_plot(
        designs=designs,
        output_path=args.output,
        title=args.title,
        xlabel=args.xlabel,
        die_label=args.die_label,
        hbm_label=args.hbm_label,
        dpi=args.dpi,
    )


if __name__ == "__main__":
    main()
