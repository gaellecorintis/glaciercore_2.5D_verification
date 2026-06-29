Usage
=====

This page walks through the end-to-end workflow the template supports, from a
fresh instance to documented results. Every command uses the **current**
glaciercore CLI (Python 3.14 workspace, glaciercore v0.22+).

.. contents::
   :local:
   :depth: 2


Create a project from the template
-----------------------------------

On GitHub, open the `project template repo <https://github.com/Corintis/project_template>`_
and click :guilabel:`Use this template` to create a new project. The new repo
inherits this documentation, which you edit under :guilabel:`doc/`; pushes to
``main`` rebuild the GitHub Pages site automatically.


Set up the compute instance
---------------------------

glaciercore (which now bundles ``zebraflow`` and the meshing / design / drawing
CLIs) is a **Python 3.14** ``uv`` workspace. On a fresh GCP instance, run the
one-command setup script:

.. code:: bash

   ./utils/gcp_setup/basic_setup_gcp.sh            # base setup
   ./utils/gcp_setup/basic_setup_gcp.sh ale        # + a named profile's aliases
   ./utils/gcp_setup/basic_setup_gcp.sh --list-profiles

It installs system packages, creates the ``~/venv-glaciercore`` virtualenv,
clones and installs glaciercore + ``Notion_API``, and sets up aliases (``fire``
activates the venv, ``glock`` jumps to glaciercore). User aliases live in
``utils/gcp_setup/profiles.json``. For the Notion upload, copy ``.env.example``
to ``.env`` and fill in your credentials (the script bootstraps this for you).


Power maps
----------

Power maps drive both simulation and optimization. Organize them by format
version under :guilabel:`powermap/`:

* :guilabel:`powermap/original_powermap/` — the raw map as delivered by the customer.
* :guilabel:`powermap/powermap_v1/`, :guilabel:`powermap_v2/` — legacy formats, kept for reference.
* :guilabel:`powermap/powermap_v3/` — the **current** physical format that the run
  scripts consume: the first row holds the *x* cell-centre coordinates and the
  first column the *y* cell-centre coordinates, with the origin at the bottom-left.

The example ``powermap_v3/powermap_example.csv`` spans **3.0 mm × 4.0 mm** to match
the chip footprint shared by every example case. glaciercore checks the power-map
extent against the mesh heating region, so if you change a chip's ``chip_width`` /
``chip_length`` you must rescale or regenerate the map to match.

Manipulating power maps
^^^^^^^^^^^^^^^^^^^^^^^^^

Power-map utilities ship with glaciercore under
``glaciercore_scripts/powermap_utils/`` — use them rather than maintaining local
copies:

.. list-table::
   :widths: 35 65
   :header-rows: 1

   * - Task
     - Tool (``glaciercore_scripts/powermap_utils/...``)
   * - Split into halves / quarters
     - ``powermap_manipulators/split.py``
   * - Worst-case (element-wise max)
     - ``powermap_manipulators/create_worst_case_powermap.py``
   * - Apply an HBM power profile
     - ``powermap_manipulators/apply_hbm.py``
   * - Convert v1 → v3
     - ``powermap_converters/from_v1_to_v3.py``
   * - Visualize
     - ``powermap_visualizers/powermap_visualizer.py -v v3``

.. note::

   The former ``generate_sub_powermaps.py`` scripts were removed — their
   splitting and worst-case functionality is fully covered by the tools above,
   which track the current power-map API.


Straight-channel simulation
----------------------------

A straight-channel run is the usual first check of a chip's thermal performance.
Each case lives in its own folder under :guilabel:`simulations/`:

.. code:: bash

   cd simulations/straight_channels_100micrometers

Case folder contents
^^^^^^^^^^^^^^^^^^^^^^

.. list-table:: Files in :guilabel:`simulations/straight_channels_100micrometers`
   :widths: 34 66
   :header-rows: 1
   :stub-columns: 1

   * - File
     - Description
   * - ``parameters_mesh.json``
     - Meshing configuration (geometry, boundary markers, orthotropic regions).
   * - ``parameters_simulation.json``
     - Simulation configuration (fluid/thermal settings, problem data, BCs).
   * - ``generate_mesh.sh``
     - Build the mesh: ``glaciercore mesh straight-channels`` → ``mesh/straight_channels.msh`` (+ ``_metadata.json``).
   * - ``run_simulation.sh``
     - Run the CHT solver: ``glaciercore simulate run`` (override ranks with ``NPROCS=<n>``).
   * - ``run_pressure_sweep.sh``
     - Sweep the inlet pressure drop: ``glaciercore simulate pressure-sweep`` (override with ``PRESSURES="..."``).
   * - ``run_single_snapshot.sh``
     - Render result screenshots from a PVD: ``glaciercore postprocess results-snapshots``.
   * - ``generate_all_snapshots.sh``
     - Walk a folder and render screenshots for every ``simulation_results_dim.pvd``.
   * - ``clean_*.sh``
     - Reset helpers that delete generated artifacts (mesh, ``.h5``, ParaView, screenshots) while preserving the JSON configs.

Run it
^^^^^^^

.. code:: bash

   bash generate_mesh.sh        # mesh + metadata
   bash run_simulation.sh       # NPROCS=8 bash run_simulation.sh to use 8 ranks
   bash run_single_snapshot.sh  # screenshots next to the PVD

Every run script is written defensively: it checks its inputs exist, logs the
mesh / metadata / power-map / rank count it is about to use, and fails with an
explicit, stage-tagged error if something is missing.

.. note::

   ``glaciercore simulate run`` now **requires** ``--mesh-metadata`` (the
   ``<mesh>_metadata.json`` emitted next to the mesh). The run scripts pass it
   automatically. To converge to a target flow rate, set the inlet boundary
   condition to ``target_flow_rate`` in the simulation JSON — the solver handles
   it natively, so the old external pressure-iteration loop is no longer needed.

Sanity checks
^^^^^^^^^^^^^^

After a simulation converges, verify the terminal output and the result files
before launching a full campaign:

#. the power map (extent matches the chip),
#. the mesh and meshing parameters,
#. the boundary conditions,
#. the range and shape of the velocity and temperature fields,
#. a spot-check of the input JSON.


Topology optimization
----------------------

Two optimization paths are provided.

Zebraflow (recommended)
^^^^^^^^^^^^^^^^^^^^^^^^^

``zebraflow`` discovers the channel layout. Each design under
:guilabel:`zebra_opt/` bundles ``settings_mesh.json``, ``settings_sim.json``,
``settings_opt.json`` and ``run_zebra.sh``:

.. code:: bash

   cd zebra_opt/design001
   bash run_zebra.sh    # NPROCS=<n> to override MPI ranks

``run_zebra.sh`` runs ``glaciercore zebraflow optimize`` and then renders a design picture
for each iteration mesh with ``glaciercore draw design``.

Density-based topology optimization
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The :guilabel:`topology_optimization/` folder drives the ``glaciercore optimize topology``
engine on a precomputed mesh:

.. code:: bash

   cd topology_optimization
   bash generate_uniform_mesh.sh           # glaciercore mesh optimization
   cd case_uniform_001 && bash run_optimization.sh

``run_optimization.sh`` runs ``glaciercore optimize topology`` and then
exports a thresholded design snapshot with ``glaciercore postprocess design-snapshot``.

.. note::

   Power-map-graded meshing (``generate_power_based_mesh.sh``) moved out of
   glaciercore into the separate
   `Corintis/power_based_mesh <https://github.com/Corintis/power_based_mesh>`_
   package (``glaciercore-power-based-mesh``); install it if you need it. The
   script falls back with a clear message otherwise.


Dune fixed-pattern designs
--------------------------

When the channel topology is prescribed up front rather than optimized, use
:guilabel:`dune_design/`. Each design folder holds ``settings_mesh.json``,
``settings_sim.json``, ``setting_dune.json`` and ``dune_design.sh`` (which calls
the external ``dune`` CLI).


Body-fitted simulation of a selected design
--------------------------------------------

A selected design picture (the **split / partitioned** computational sub-domain,
in :guilabel:`selected_design_png/`) is meshed body-fitted and simulated exactly
like the straight-channel case, except the meshing step uses ``mesh design``:

.. code:: bash

   cd simulations/optimized_design001
   bash generate_mesh.sh    # glaciercore mesh design --design-png ... -> mesh/design.msh
   bash run_simulation.sh

To go from an optimization result to a body-fitted picture, threshold the
optimization PVD:

.. code:: bash

   glaciercore postprocess design-snapshot --json parameters_mesh.json \
       --threshold 0.5 --input-pvd result/design.pvd

Meshing directly from a DXF
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``scripts/generate_mesh_from_dxf.py`` meshes a chip straight from a DXF design
(shapely-based, with optional clogging injection). This is the current
**interim** route — the capability is expected to move into glaciercore later.


.. _plotting-section:

Plotting
--------

Prefer the maintained plotting paths over hand-rolled routines:

#. **glaciercore postprocess plot** — built-in comparison plots from sweep results
   (each sweep passed as a repeatable ``--parameter-sweep "NAME=PATH"`` token).
#. **glaciercore_scripts/** — power-map visualizers and manipulators shipped with
   glaciercore.
#. **scripts/** — result plots beyond the CLI: temperature stack-up waterfall
   (``waterfall_plot.py``), die-vs-HBM dumbbell (``create_dumbell_plot.py``),
   monitor-region lollipop (``create_lollipop_plot.py``), and a Customer/Project
   comparison straight from the Notion database (``create_plot_from_notion_db.py``).

The pre-CLI project plotting routines are no longer maintained; they live under
:guilabel:`archive_legacy/plotting/` for reference only.


Document results in Notion
--------------------------

Push a finished design's results to the project's Notion database:

.. code:: bash

   bash notion-database/upload_design_notion.sh   # edit the design metadata block first


Data hygiene
------------

Only light files belong in git: JSON configs, input CSVs, and the occasional
design ``.png``. The ``.gitignore`` already excludes meshes, ``.h5``, ParaView
output and rendered images. Use the per-case ``clean_*.sh`` scripts to reset a
folder before re-running it.
