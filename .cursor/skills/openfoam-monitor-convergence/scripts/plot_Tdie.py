import csv
import sys
import math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def read_csv(path, xcol, ycol, xcast=int, ycast=float):
    xs, ys = [], []
    try:
        with open(path) as f:
            for row in csv.DictReader(f):
                xs.append(xcast(row[xcol]))
                ys.append(ycast(row[ycol]))
    except FileNotFoundError:
        pass
    return xs, ys


def estimate_Tinf(q_it, q_pct, iters, T_C):
    """Estimate the asymptotic Tjmax by exponential charge-up fit.
    tau is taken from the (cleaner) energy-balance curve:
        100 - Q = 100*exp(-(n-n0)/tau)  ->  ln(100-Q) linear in n.
    Then Tjmax = Tinf - B*exp(-n/tau) is linear in (Tinf, B) for fixed tau.

    Only the RECENT window is used: the relaxation-factor boost (~iter 2100)
    changed the effective time constant, so mixing pre/post-boost data biases
    the asymptote low. We fit on the last ~14 energy-balance points, which
    reflect the current numerical regime."""
    try:
        # recent window: keep data at/after the 14th-from-last Q sample
        nmin = q_it[max(0, len(q_it) - 14)] if q_it else 0
        # --- tau from Q (recent) ---
        xs = [n for n, q in zip(q_it, q_pct) if q < 99.5 and n >= nmin]
        ys = [math.log(100.0 - q) for n, q in zip(q_it, q_pct)
              if q < 99.5 and n >= nmin]
        if len(xs) < 3:
            return None
        n = len(xs)
        mx = sum(xs) / n
        my = sum(ys) / n
        sxx = sum((x - mx) ** 2 for x in xs)
        sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
        slope = sxy / sxx
        if slope >= 0:
            return None
        tau = -1.0 / slope
        # --- Tinf from Tjmax (recent), fixed tau: T = a + b*E, E=exp(-x/tau) ---
        it_r = [n for n in iters if n >= nmin]
        T_r = [t for n, t in zip(iters, T_C) if n >= nmin]
        if len(it_r) < 3:
            it_r, T_r = iters, T_C
        E = [math.exp(-x / tau) for x in it_r]
        m = len(it_r)
        mE = sum(E) / m
        mT = sum(T_r) / m
        see = sum((e - mE) ** 2 for e in E)
        seT = sum((e - mE) * (t - mT) for e, t in zip(E, T_r))
        b = seT / see
        a = mT - b * mE          # a = Tinf
        return a
    except Exception:
        return None


iters, T_C = read_csv("Tdie_history.csv", "iter", "T_C")
q_it, q_pct = read_csv("Qout_history.csv", "iter", "pct")

fig, ax = plt.subplots(figsize=(7, 6))
fig.patch.set_facecolor("black")
ax.set_facecolor("black")

# ---- left axis: Tjmax ----
TC = "#e8552d"
l1, = ax.plot(iters, T_C, "o-", color=TC, markersize=5, linewidth=1.6,
              label="Tjmax (die hotspot)")
if iters:
    ax.annotate(f"{T_C[-1]:.2f} C", (iters[-1], T_C[-1]),
                textcoords="offset points", xytext=(0, -32), ha="center",
                color=TC, fontsize=9,
                arrowprops=dict(arrowstyle="-", color=TC, lw=0.8, alpha=0.7))

ax.set_xlabel("Iteration", color="white", fontsize=12)
ax.set_ylabel("Die max temperature [C]", color=TC, fontsize=12)
ax.tick_params(axis="y", colors=TC)
ax.tick_params(axis="x", colors="white")
ax.set_title("Tjmax & energy balance vs iteration", color="white", fontsize=13)

# ---- right axis: energy balance % ----
QC = "#33c4d6"
ax2 = ax.twinx()
ax2.set_facecolor("none")
l2, = ax2.plot(q_it, q_pct, "s-", color=QC, markersize=5, linewidth=1.6,
               label="Q_out / Q_in (energy balance)")
l3 = ax2.axhline(100, color="#888888", ls="--", lw=1.2,
                 label="100% = thermal equilibrium")
if q_it:
    ax2.annotate(f"{q_pct[-1]:.1f}%", (q_it[-1], q_pct[-1]),
                 textcoords="offset points", xytext=(-8, 8), ha="right",
                 color=QC, fontsize=9)
ax2.set_ylabel("Energy balance  Q_out / Q_in  [%]", color=QC, fontsize=12)
ax2.tick_params(axis="y", colors=QC)
Q_TOP = 110.0
ax2.set_ylim(0, Q_TOP)

# ---- align left (Tjmax) axis so converged Tjmax sits on the Q=100% line ----
# fraction of the axis height where the 100% line lives:
f = 100.0 / Q_TOP
Tinf = estimate_Tinf(q_it, q_pct, iters, T_C)
if Tinf and T_C and Tinf > max(T_C):
    lo = min(T_C) - 0.4
    hi = lo + (Tinf - lo) / f          # Tinf maps exactly onto the 100% line
    ax.set_ylim(lo, hi)
    # label the predicted converged Tjmax (sits on the 100% line by construction)
    ax.annotate(f"Tjmax converge ~ {Tinf:.1f} C", (iters[-1], Tinf),
                textcoords="offset points", xytext=(-6, -14), ha="right",
                color=TC, fontsize=9)
elif T_C:
    ax.set_ylim(min(T_C) - 0.4, max(T_C) + 0.6)

# ---- styling ----
ax.spines["top"].set_visible(False)
ax2.spines["top"].set_visible(False)
ax.spines["bottom"].set_color("white")
ax.spines["left"].set_color(TC)
ax2.spines["right"].set_color(QC)
ax2.spines["left"].set_visible(False)
ax.grid(False)
ax2.grid(False)

lines = [l1, l2, l3]
ax.legend(lines, [ln.get_label() for ln in lines],
          loc="upper left", fontsize=9, labelcolor="white",
          facecolor="black", edgecolor="none")

out = sys.argv[1] if len(sys.argv) > 1 else "Tdie_latest.png"
plt.tight_layout()
plt.savefig(out, dpi=150, facecolor="black")
print(f"saved {out} (Tjmax {len(iters)}pts, Qout {len(q_it)}pts, "
      f"last {iters[-1] if iters else '-'} / {q_pct[-1] if q_pct else '-':.1f}%)")
