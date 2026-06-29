# Corintis Project Template

The standard structure and common scripts shared across Corintis projects. It is
kept in sync with the latest `main` of
[glaciercore](https://github.com/Corintis/glaciercore).

> **Environment:** glaciercore is now a **Python 3.14** uv workspace that bundles
> `zebraflow` and the meshing / design / drawing tooling under a single unified
> `glaciercore` CLI (the old `glaciercore-mesh`, `glaciercore-design`,
> `glaciercore-drawing` and `zebraflow` console scripts are gone — everything is a
> `glaciercore <group> <subcommand>`). The configs and scripts in this template
> target that version (glaciercore v0.22+). All example JSON configs validate
> against the current `glaciercore_config` schemas.

## Getting started on a GCP instance

On a fresh instance, run the one-command setup script. It installs system
packages, creates a `~/venv-glaciercore` virtualenv, clones and installs
glaciercore (with `zebraflow`) and `Notion_API`, and configures handy aliases.

```bash
./utils/gcp_setup/basic_setup_gcp.sh            # base setup
./utils/gcp_setup/basic_setup_gcp.sh ale        # + a named profile's aliases
./utils/gcp_setup/basic_setup_gcp.sh --list-profiles
```

After setup: `fire` activates the venv, `glock` jumps to glaciercore and activates
it. Profiles live in `utils/gcp_setup/profiles.json`.

For the Notion upload, copy `.env.example` to `.env` and fill in your Notion
credentials (the setup script bootstraps this for you). `.env` is gitignored —
never commit it.

## Repository layout

- **`simulations/`** — Conjugate-heat-transfer simulations, one folder per design
  (`straight_channels_100micrometers/`, `optimized_design001/`, …). Each holds
  `parameters_mesh.json`, `parameters_simulation.json`, and the run scripts
  (`generate_mesh.sh`, `run_simulation.sh`, `run_pressure_sweep.sh`,
  `run_single_snapshot.sh`) plus `clean_*.sh` reset helpers.
- **`zebra_opt/`** — Zebraflow topology-optimization runs (the optimizer discovers
  the channel layout). Each design folder bundles `settings_mesh.json`,
  `settings_sim.json`, `settings_opt.json`, and `run_zebra.sh`.
- **`topology_optimization/`** — Density-based topology optimization
  (`glaciercore optimize topology`). Holds the shared `mesh/` config,
  `generate_uniform_mesh.sh` / `generate_power_based_mesh.sh`, and the `case_*`
  optimization runs (each with `run_optimization.sh`).
- **`dune_design/`** — Dune-based fixed-pattern designs (channel topology
  prescribed up-front). Each design folder holds `settings_mesh.json`,
  `settings_sim.json`, `setting_dune.json`, and `dune_design.sh` (needs the
  external `dune` CLI).
- **`scripts/`** — Standalone utility scripts (run with the project venv):
  result plots (`waterfall_plot.py`, `create_dumbell_plot.py`,
  `create_lollipop_plot.py`), Notion-DB plotting (`create_plot_from_notion_db.py`,
  uses `.env`), quadtree migration (`convert_old_quadtrees.py`), and
  `generate_mesh_from_dxf.py`. The DXF mesher is the current **interim** way to
  mesh a chip directly from a DXF design — this capability is expected to move
  into glaciercore later.
- **`powermap/`** — Versioned power maps. The run scripts use the current physical
  format in `powermap_v3/`. See [`powermap/README.md`](powermap/README.md).
- **`selected_design_png/`** — Selected (split / partitioned) design pictures used
  for body-fitted simulations after post-processing.
- **`notion-database/`** — Push design results into the project's Notion database.
- **`utils/`** — Shared assets: `gcp_setup/` (instance bootstrap + profiles) and
  `plotting_styles/` (`Corintis.mplstyle`, `Corintisblack.mplstyle`).
- **`archive_legacy/`** — Legacy material kept for reference only, not part of the
  current workflow: `plotting/` (pre-CLI project plotting) and
  `design_gds_mask_from_png/` (GDS-mask-from-picture scripts).
- **`doc/`** — Sphinx documentation source. Build locally with
  `sphinx-build doc _build` and open `_build/index.html`. Pushes to `main` publish
  it to GitHub Pages via `.github/workflows/documentation.yaml`.

## Typical workflow

1. **Set up** the instance: `./utils/gcp_setup/basic_setup_gcp.sh`.
2. **Pick / copy a design folder** and edit its `*_*.json` for the customer's
   geometry and operating conditions.
3. **Run** — for a fixed / body-fitted design:
   ```bash
   cd simulations/straight_channels_100micrometers   # or optimized_design001
   bash generate_mesh.sh        # -> mesh/<name>.msh (+ <name>_metadata.json)
   bash run_simulation.sh       # NPROCS=<n> to override MPI ranks
   bash run_single_snapshot.sh  # render result screenshots
   ```
   …or let the optimizer find the layout: `bash zebra_opt/design001/run_zebra.sh`.
4. **Plot / sweep** — `bash run_pressure_sweep.sh`, then `glaciercore postprocess plot` (see the Plotting section).
5. **Document** — upload results with `notion-database/upload_design_notion.sh`.

## glaciercore CLI reference (current command names)

The CLI was unified under a single `glaciercore` entry point — every task is now
a `glaciercore <group> <subcommand>`. The scripts here already use the current
names:

| Task | Command |
| --- | --- |
| Canonical / fixed mesh | `glaciercore mesh straight-channels` |
| Uniform optimization mesh | `glaciercore mesh optimization` |
| Body-fitted mesh | `glaciercore mesh design` |
| Simulation | `glaciercore simulate run` (`--mesh-metadata` now required) |
| Pressure / flow-rate sweep | `glaciercore simulate pressure-sweep` · `glaciercore simulate flow-rate-sweep` |
| Density-based topology optimization | `glaciercore optimize topology` |
| Zebraflow optimization | `glaciercore zebraflow optimize` |
| Design picture / CAD | `glaciercore draw design` · `glaciercore cad design` |
| Result screenshots | `glaciercore postprocess results-snapshots` |
| Validate a config | `validate-mesh-config` · `validate-simulation-config` · `validate-optimization-config` |

> Power-based meshing moved out of glaciercore into the separate
> [`Corintis/power_based_mesh`](https://github.com/Corintis/power_based_mesh)
> package (`glaciercore-power-based-mesh`); install it if you need
> `generate_power_based_mesh.sh`.

## Plotting

There are three complementary sources of plots — prefer them over hand-rolled
routines:

1. **`glaciercore postprocess plot`** — built-in comparison plots from
   pressure/flow-rate sweep results. Each sweep is passed as a repeatable
   `--parameter-sweep "NAME=PATH"` token (alias `-ps`), e.g.
   `glaciercore postprocess plot -ps "Optimized=optimized_sweep/" -ps "Straight 100 um=straight_100um_sweep/"`.
2. **`glaciercore_scripts/`** (shipped with glaciercore) — power-map visualizers,
   splitters and converters under `powermap_utils/`.
3. **`scripts/`** (this repo) — result plots beyond the CLI: temperature stack-up
   waterfall (`waterfall_plot.py`), die-vs-HBM dumbbell (`create_dumbell_plot.py`),
   monitor-region lollipop (`create_lollipop_plot.py`), and Customer/Project
   comparison straight from the Notion database (`create_plot_from_notion_db.py`).

The pre-CLI project plotting is no longer maintained; it lives under
`archive_legacy/plotting/` for reference only.

## Conventions worth knowing

- **Chip footprint:** the example chips use a common **3.0 mm × 4.0 mm** footprint
  so the single `powermap_v3` example matches every case. glaciercore checks the
  power-map extent against the mesh heating region — if you resize a chip,
  rescale/regenerate the power map to match.
- **Manufacturing constraints:** glaciercore enforces a minimum inlet-outlet slit
  distance (default 2.5 mm edge-to-edge). Lay out inlets/outlets far enough apart
  rather than disabling the check.
- **HBM / orthotropic regions:** defined as `orthotropic_material_regions_list`
  (geometry markers) in the mesh JSON, with matching `orthotropic_material_conductivity_list`
  (`k_x/k_y/k_z` + `marker`) in the simulation JSON. Use markers `≥ 300` to avoid
  colliding with glaciercore's default markers.

If this is your first project, build and read the `doc/` documentation to learn
the end-to-end workflow.
