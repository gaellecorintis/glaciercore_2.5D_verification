# OpenFOAM 3D CHT — cp substrate 1.0 mm

High-fidelity 3D conjugate-heat-transfer reference for the glaciercore 2.5D
verification. HM27 MI455 NE quarter chip, TTV powermap, **T_inlet = 43 °C**,
**3.4 LPM** full chip. Direct counterpart of the glaciercore case
[`../gc_komega_cp1mm`](../gc_komega_cp1mm) (same cp substrate = 1.0 mm).

| Parameter | Value |
|---|---|
| Solver | OpenFOAM multi-region CHT (`foamMultiRun`) |
| Regions | `fluid`, `die`, `tim`, `cold_plate` |
| `cold_plate_substrate_thickness` | 1.0 mm (baked in the mesh) |
| Turbulence | k-omega SST |
| Powermap | `powermap/apollo_pmap/powermap_ttv_quarter_for_hm27_mesh.csv` |
| Mesh | snappyHexMesh body-fit, NE quarter (not stored in git) |
| Converged at | iteration 7000 |

**Key results:** T_die max **78.89 °C**, outlet ΔT **8.85 K**, heat balance
Q_out/Q_in ≈ **101.8 %** (Q_out ≈ 508.5 W on the quarter).

**Comparison vs glaciercore (cp 1.0 mm):** OpenFOAM **78.89 °C** vs glaciercore
**85.70 °C** → glaciercore over-predicts T_die by **~6.8 °C** (conservative).

## Contents (lightweight only)

| Path | What |
|---|---|
| `system/` | OpenFOAM dictionaries (controlDict, fvSchemes, fvSolution, decompose…) |
| `constant/` | Region physical properties (`regionProperties` + per-region), **no mesh** |
| `logs/` | Solver logs: `log.foamMultiRun.ramp_1-5001` (cold-start ramp) + `log.foamMultiRun.final_5001-7000` (final converged run) |
| `Tdie_history.csv` | Die max temperature vs iteration (`iter, T_K, T_C`) |
| `Qout_history.csv` | Heat balance vs iteration (`iter, Tout_K, dT_K, Qout_W, pct`) |
| `figures/` | Curated result figures (T/U fields at 7000, convergence, vs-glaciercore) |

Not in git: the mesh (`polyMesh`, `triSurface`, `geometry`), all time
directories (`0/`, `2525/`…`7000/`), `VTK/`, and `postProcessing/` (~119 GB on
the VM). Only metadata, logs, history CSVs and figures are versioned.
