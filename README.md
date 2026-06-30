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

## Cases (HM27 MI455, T_inlet 43 °C, 3.4 LPM full chip)

| Folder | Model | cp substrate | Tj max | Notes |
| --- | --- | --- | --- | --- |
| [`simulations/gc_komega_cp1mm/`](simulations/gc_komega_cp1mm/) | glaciercore 2.5D | 1.0 mm | 85.70 °C | Reference k-ω SST run |
| [`simulations/gc_komega_cp05mm/`](simulations/gc_komega_cp05mm/) | glaciercore 2.5D | 0.5 mm | 85.49 °C | ANSA-aligned substrate thickness |
| [`simulations/openfoam_cht_cp1mm/`](simulations/openfoam_cht_cp1mm/) | OpenFOAM 3D CHT | 1.0 mm | 78.89 °C | High-fidelity reference |

**Verification (cp 1.0 mm):** glaciercore 85.70 °C vs OpenFOAM 78.89 °C →
glaciercore over-predicts T_die by **~6.8 °C** (conservative).

ANSA/Fidelity cases will be added under `simulations/` when available.

## Operating conditions (common to glaciercore cases)

- Geometry: HM27 quarter chip (symmetry)
- Powermap: [`powermap/apollo_pmap/powermap_ttv_quarter_for_hm27_mesh.csv`](powermap/apollo_pmap/powermap_ttv_quarter_for_hm27_mesh.csv)
- Coolant: PGW25
- Target flow rate: 3.4 LPM (full chip)
- Inlet temperature: 43 °C
