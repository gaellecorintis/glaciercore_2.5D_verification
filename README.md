# glaciercore 2.5D verification

Verification of the glaciercore 2.5D thermal model against high-fidelity 3D CHT
simulations (ANSA/Fidelity) on **HM27 MI455** — aligned BCs, powermap, and cp
substrate thickness sensitivity.

## Repository layout

| Path | Content |
| --- | --- |
| [`simulations/`](simulations/) | Simulation cases and results |
| [`powermap/`](powermap/) | Powermap CSV files used in the study |
| [`scripts/`](scripts/) | Plotting and utility scripts |
| [`.cursor/rules/`](.cursor/rules/) | Cursor rules |

Large field files (`.h5`, VTK, meshes) are excluded — see [`.gitignore`](.gitignore).

## Glaciercore cases (HM27 MI455, T_inlet 43 °C, 3.4 LPM full chip)

| Folder | cp substrate | Tj max | Notes |
| --- | --- | --- | --- |
| [`simulations/gc_komega_cp1mm/`](simulations/gc_komega_cp1mm/) | 1.0 mm | 85.70 °C | Reference k-ω SST run |
| [`simulations/gc_komega_cp05mm/`](simulations/gc_komega_cp05mm/) | 0.5 mm | 85.49 °C | ANSA-aligned substrate thickness |

OpenFOAM and ANSA/Fidelity cases will be added under `simulations/` when available.

## Operating conditions (common to glaciercore cases)

- Geometry: HM27 quarter chip (symmetry)
- Powermap: [`powermap/apollo_pmap/powermap_ttv_quarter_for_hm27_mesh.csv`](powermap/apollo_pmap/powermap_ttv_quarter_for_hm27_mesh.csv)
- Coolant: PGW25
- Target flow rate: 3.4 LPM (full chip)
- Inlet temperature: 43 °C
