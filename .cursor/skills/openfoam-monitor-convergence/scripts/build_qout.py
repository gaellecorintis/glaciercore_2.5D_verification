#!/usr/bin/env python3
"""Build Qout_history.csv (energy balance % vs iteration) from accumulated
outlet-T postProcessing data.

  Q_out  = mdot * Cp * (T_out - T_in)
  pct    = Q_out / Q_in * 100
"""
import glob
import csv

MDOT = 1.43511709e-2     # kg/s  (from patchFlowRate(outlet), 100% flow)
CP = 4002.0              # J/kg/K
TIN = 316.15             # K
QIN = 499.5              # W (Mi455 TTV quarter)
MCP = MDOT * CP          # W/K

pts = {}
for f in glob.glob("postProcessing/fluid/patchAverage*/*/surfaceFieldValue.dat"):
    with open(f) as fh:
        for line in fh:
            line = line.strip()
            if not line or not line[0].isdigit():
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            try:
                it = int(float(parts[0]))
                t_k = float(parts[1])
            except ValueError:
                continue
            pts[it] = t_k        # dedup by iteration (latest wins)

rows = []
for it in sorted(pts):
    t_k = pts[it]
    dT = t_k - TIN
    qout = MCP * dT
    pct = qout / QIN * 100.0
    rows.append((it, t_k, dT, qout, pct))

with open("Qout_history.csv", "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["iter", "Tout_K", "dT_K", "Qout_W", "pct"])
    w.writerows(rows)

print(f"wrote Qout_history.csv ({len(rows)} points)")
if rows:
    it, t_k, dT, qout, pct = rows[-1]
    print(f"  last: iter {it}  Tout {t_k-273.15:.2f}C  Qout {qout:.1f}W  -> {pct:.1f}%")
