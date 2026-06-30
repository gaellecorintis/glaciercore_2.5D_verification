# glaciercore k-omega SST — cp substrate 0.5 mm

Same case as `gc_komega_cp1mm/`, with **`cold_plate_substrate_thickness = 0.5 mm`** (aligned with ANSA/Fidelity geometry). No remesh — quadruple-layer thermal parameter only.

| Parameter | Value |
|---|---|
| `cold_plate_substrate_thickness` | 0.5 mm |
| Turbulence | k-omega SST |
| Powermap | `powermap/apollo_pmap/powermap_ttv_quarter_for_hm27_mesh.csv` |
| Warm-start | flow field from `gc_komega_cp1mm` run |

**Key results:** Tj max **85.49 °C**, ΔP **187.6 mbar**, Q **3.401 LPM** (ΔTj vs 1 mm: **−0.21 °C**).

Warm-start source: [`../gc_komega_cp1mm/`](../gc_komega_cp1mm/) (flow field at cp 1 mm)

Large field files (`.h5`, VTK) are not stored in git — see `.gitignore`.
