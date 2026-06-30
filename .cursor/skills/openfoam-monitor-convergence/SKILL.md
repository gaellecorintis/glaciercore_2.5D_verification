---
name: openfoam-monitor-convergence
description: Monitor convergence of an OpenFOAM CHT (conjugate heat transfer) run by tracking fluid and solid residuals, computing the energy balance (Q_out/Q_in), and following the peak junction temperature (Tjmax). Use when watching/diagnosing an OpenFOAM multi-region run, plotting residuals, checking whether a CHT case is converged, or building Tjmax / energy-balance history plots.
---

# Monitor an OpenFOAM CHT run (residuals + energy balance + Tjmax)

Three things decide whether a CHT run is converged:
1. **Residuals** drop and flatten — fluid (U, p_rgh, h, k, omega) AND solids (e).
2. **Energy balance** Q_out/Q_in → 100 % (heat removed by coolant = heat in).
3. **Tjmax** (die hotspot) stops drifting.

Helper scripts live in `scripts/` next to this file. They are working
templates — adjust the case-specific constants (marked below) before use.

## 1. Residuals (fluid + solid)

Plot per-field initial residuals straight from the solver log:

```bash
python3 scripts/plot_residuals_corintis.py        # reads log.foamMultiRun*, writes residuals.png
```

Left panel = fluid region (U, p_rgh, h, k, omega + continuity), right panel =
solids (energy `e` for each solid region). Converged = all curves below ~1e-4
and flat. Early spikes are normal at warm-start / flow-rate-ramp steps.

> Point the script at the **current** run's log (e.g. `log.foamMultiRun.limited`),
> not an old one.

## 2. Energy balance Q_out/Q_in

Physics: `Q_out = mdot * Cp * (T_out - T_in)`, then `pct = Q_out / Q_in * 100`.

Extract the outlet temperature from a **decomposed** (parallel) case, then build
the history CSV:

```bash
source /opt/openfoam13/etc/bashrc
mpirun -np 24 foamPostProcess -region fluid -parallel -time <iters> \
  -func "patchAverage(patch=outlet, field=T)"
python3 scripts/build_qout.py                      # writes Qout_history.csv
```

Edit these constants at the top of `build_qout.py` for your case:
`MDOT` (kg/s, from `patchFlowRate(outlet)`), `CP`, `TIN` (K), `QIN` (W).

## 3. Tjmax (die hotspot)

Extract the die max temperature via the `cellMax(T)` function object:

```bash
mpirun -np 24 foamPostProcess -region die -parallel -time <iters> -func 'cellMax(T)'
```

## 4. Combined live watcher (read-only, safe on a running job)

`scripts/watch_Tdie.sh` polls for new written time steps and, **before they are
purged** (`purgeWrite`), extracts Tjmax (die) and T_out (fluid outlet), then
rebuilds `Tdie_history.csv` and `Qout_history.csv`. It never modifies the run.

```bash
bash scripts/watch_Tdie.sh        # set case path + POLL inside the script
```

Then plot Tjmax + energy balance on twin axes (with an asymptote estimate):

```bash
python3 scripts/plot_Tdie.py Tdie_latest.png
```

## Convergence checklist

```
- [ ] fluid residuals (U, p_rgh, h, k, omega) flat below ~1e-4
- [ ] solid energy residuals (e) flat and low
- [ ] Q_out/Q_in ≈ 100 % (energy balance closed)
- [ ] Tjmax drift < ~0.1 °C over the last few hundred iterations
```

## Notes

- Use `purgeWrite` small (e.g. 3) to save disk, but then an **external watcher**
  is required to capture Tjmax/T_out before each time step is deleted.
- For a converged check, all four boxes above must hold — energy balance at
  100 % alone is necessary but not sufficient (Tjmax can still be drifting).
