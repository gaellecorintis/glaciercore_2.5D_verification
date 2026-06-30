#!/usr/bin/env python3
"""Plot per-field initial residuals vs iteration in Corintis documentation style.

Style: black background, no grid, no bold text, no top/right spines,
square aspect ratio, English labels. Output: residuals_corintis.png
"""
import re
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import sys
LOG = sys.argv[1] if len(sys.argv) > 1 else "log.foamMultiRun.limited"
OUT = "residuals_corintis.png"

time_re = re.compile(r"^\s*Time = ([0-9.eE+-]+)s")
sol_re = re.compile(
    r"^(\w+)\s+\w+:\s+Solving for (\w+), Initial residual = ([0-9.eE+-]+)")
cont_re = re.compile(
    r"continuity errors : sum local = [0-9.eE+-]+, global = ([0-9.eE+-]+)")

fluid_fields = ["Ux", "Uy", "Uz", "p_rgh", "h", "k", "omega"]
series = {f: [] for f in fluid_fields}
solid_e = {"cold_plate": [], "tim": [], "die": []}
cont = []

cur_t = None
seen = set()
with open(LOG) as fh:
    for line in fh:
        m = time_re.match(line)
        if m:
            cur_t = float(m.group(1))
            seen = set()
            continue
        if cur_t is None:
            continue
        m = sol_re.match(line)
        if m:
            region, field, r = m.group(1), m.group(2), float(m.group(3))
            key = (region, field)
            if key in seen:
                continue
            seen.add(key)
            if region == "fluid" and field in series:
                series[field].append((cur_t, r))
            elif field == "e" and region in solid_e:
                solid_e[region].append((cur_t, r))
            continue
        m = cont_re.search(line)
        if m and ("cont", cur_t) not in seen:
            seen.add(("cont", cur_t))
            cont.append((cur_t, abs(float(m.group(1))) + 1e-12))

# ----------------------------------------------------------------------------
# Corintis documentation style
# ----------------------------------------------------------------------------
BG = "black"
FG = "white"
plt.rcParams.update({
    "figure.facecolor": BG,
    "axes.facecolor": BG,
    "savefig.facecolor": BG,
    "text.color": FG,
    "axes.labelcolor": FG,
    "axes.edgecolor": FG,
    "axes.titlecolor": FG,
    "xtick.color": FG,
    "ytick.color": FG,
    "font.weight": "normal",
    "axes.titleweight": "normal",
    "figure.titleweight": "normal",
    "legend.frameon": False,
    "axes.grid": False,
})

# bright palette readable on black
palette = ["#4FC3F7", "#FF8A65", "#81C784", "#E57373",
           "#BA68C8", "#FFD54F", "#F06292"]

fig, ax = plt.subplots(1, 2, figsize=(14, 7))

# --- left: fluid field residuals ---
for i, f in enumerate(fluid_fields):
    if series[f]:
        t, r = zip(*series[f])
        ax[0].semilogy(t, r, marker=".", ms=3, lw=1.2,
                       color=palette[i % len(palette)], label=f)
ax[0].axhline(1e-4, color="#888888", ls="--", lw=1, label="target 1e-4 (U, h)")
ax[0].set_xlabel("Iteration")
ax[0].set_ylabel("Initial residual (log)")
ax[0].set_title("Fluid region")

# --- right: solids energy + continuity ---
solid_palette = {"cold_plate": "#4FC3F7", "tim": "#FF8A65", "die": "#81C784"}
for reg in solid_e:
    if solid_e[reg]:
        t, r = zip(*solid_e[reg])
        ax[1].semilogy(t, r, marker=".", ms=3, lw=1.2,
                       color=solid_palette[reg], label=f"e [{reg}]")
if cont:
    t, r = zip(*cont)
    ax[1].semilogy(t, r, marker=".", ms=3, lw=1.2, color=FG,
                   label="global continuity")
ax[1].set_xlabel("Iteration")
ax[1].set_ylabel("Initial residual (log)")
ax[1].set_title("Solids (energy) + continuity")

# common styling: no top/right spines, square aspect, no grid
for a in ax:
    a.spines["top"].set_visible(False)
    a.spines["right"].set_visible(False)
    a.grid(False)
    a.set_box_aspect(1)
    a.legend(fontsize=9, labelcolor=FG)

last_t = max((s[-1][0] for s in series.values() if s), default=0)
fig.suptitle(f"foamMultiRun convergence - up to iteration {last_t:g}",
             fontsize=13)
fig.tight_layout()
fig.savefig(OUT, dpi=150)
print("wrote", OUT, "| last points:",
      {f: round(series[f][-1][1], 4) for f in fluid_fields if series[f]})
