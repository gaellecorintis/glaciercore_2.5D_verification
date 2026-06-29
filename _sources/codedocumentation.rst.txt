Scripts and utilities
=====================

A project carries only a small amount of code: a handful of standalone scripts
that complement the glaciercore CLIs. They live in the repo-root
:guilabel:`scripts/` folder and run inside the project virtualenv (``fire``).

Each script is self-documenting — run it with ``--help`` (or read its module
docstring) for the full, up-to-date argument list. This page is a map of *what
exists and when to reach for it*.

Result plotting
---------------

.. list-table::
   :widths: 32 68
   :header-rows: 1

   * - Script
     - Purpose
   * - ``scripts/waterfall_plot.py``
     - Multi-design temperature stack-up (waterfall) comparison with per-component deltas, read from ``per_component_stackup.json`` files.
   * - ``scripts/create_dumbell_plot.py``
     - Dumbbell chart comparing die vs HBM junction temperatures across designs.
   * - ``scripts/create_lollipop_plot.py``
     - Overlaid lollipop chart of monitor-region temperatures, with zone grouping and baseline-vs-new comparison.
   * - ``scripts/create_plot_from_notion_db.py``
     - GPU die vs HBM temperature plots straight from CSV exports or the Notion database (paginated query, ``.env`` credentials).

For standard comparison plots from sweep results, prefer the built-in
``glaciercore postprocess plot``; for power-map plotting use
``glaciercore_scripts/powermap_utils/``.

Meshing and data migration
---------------------------

.. list-table::
   :widths: 32 68
   :header-rows: 1

   * - Script
     - Purpose
   * - ``scripts/generate_mesh_from_dxf.py``
     - Mesh a chip directly from a DXF design (shapely-based, optional clogging injection). The current **interim** route until this lands in glaciercore.
   * - ``scripts/convert_old_quadtrees.py``
     - Migrate legacy zebraflow quadtree CSVs to the current schema, scaling pixel coordinates to metres from ``settings_mesh.json``.

Archived routines
-----------------

The pre-CLI project plotting (``project_plotting_utils.py``,
``generate_plot_results_v1.py``) is kept for reference under
:guilabel:`archive_legacy/plotting/`. It targets the old power-map API and the
pre-CLI plotting workflow; do not build on it.
