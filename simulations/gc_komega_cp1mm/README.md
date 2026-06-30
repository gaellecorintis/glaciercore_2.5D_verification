# glaciercore k-omega SST — cp substrate 1.0 mm

HM27 MI455 quarter chip, TTV powermap, **T_inlet = 43 °C**, **3.4 LPM** full chip.

| Parameter | Value |
|---|---|
| `cold_plate_substrate_thickness` | 1.0 mm |
| Turbulence | k-omega SST |
| Powermap | `powermap/apollo_pmap/powermap_ttv_quarter_for_hm27_mesh.csv` |
| Mesh | `quarter_chip_HM27.msh` (body-fit, DNS mesh folder) |
| Warm-start | k-omega flow field at T_inlet = 30 °C |

**Key results:** Tj max **85.70 °C**, ΔP **189.4 mbar**, Q **3.401 LPM**.

Powermap in repo: [`../../powermap/apollo_pmap/powermap_ttv_quarter_for_hm27_mesh.csv`](../../powermap/apollo_pmap/powermap_ttv_quarter_for_hm27_mesh.csv)

Large field files (`.h5`, VTK) are not stored in git — see `.gitignore`.
