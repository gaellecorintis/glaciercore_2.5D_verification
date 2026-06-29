# Power maps

This folder holds the example power maps used by the simulation and
optimization cases. Power maps are organized by format version:

- **`original_powermap/`** — the raw power map as delivered by the client.
- **`powermap_v1/`**, **`powermap_v2/`** — legacy glaciercore formats, kept for
  reference. `v1` carries the chip dimensions in the first row; `v2` is the bare
  power array.
- **`powermap_v3/`** — the **current** physical format consumed by glaciercore:
  the first row holds the x cell-centre coordinates and the first column holds
  the y cell-centre coordinates (origin at the bottom-left). This is the file the
  run scripts reference (`powermap_v3/powermap_example.csv`).

The example `powermap_v3` map spans **3.0 mm × 4.0 mm** to match the chip
footprint used across the `simulations/`, `zebra_opt/`, and `topology_optimization/`
examples. If you change a chip's `chip_width` / `chip_length`, regenerate or
rescale the power map so its physical extent matches — glaciercore checks the
power map extent against the mesh heating region.

## Manipulating power maps

The power-map utilities that used to live here (splitting into cardinal /
half sub-maps, building a worst-case map, format conversion, HBM application)
now ship with glaciercore in **`glaciercore_scripts/powermap_utils/`**. Use those
instead of maintaining local copies:

| Task | Tool (`~/glaciercore/glaciercore_scripts/powermap_utils/...`) |
| --- | --- |
| Split into halves / quarters | `powermap_manipulators/split.py --powermap <csv> ...` |
| Worst-case (element-wise max) | `powermap_manipulators/create_worst_case_powermap.py --powermap <a.csv> <b.csv> ... --output worst.csv` |
| Apply HBM power profile | `powermap_manipulators/apply_hbm.py --powermap <csv> ...` (uses `orthotropic_material_regions_list` from the mesh JSON) |
| Convert v1 → v3 | `powermap_converters/from_v1_to_v3.py ...` |
| Visualize | `powermap_visualizers/powermap_visualizer.py -v v3` |

> Migration note: the former `powermap_v1/generate_sub_powermaps.py` and
> `powermap_v2/generate_sub_powermaps.py` were removed — their splitting and
> worst-case functionality is fully covered by the `glaciercore_scripts`
> tools above, which track the current power-map API.
