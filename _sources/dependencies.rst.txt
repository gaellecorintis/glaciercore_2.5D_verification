Dependencies
============

Core engine
-----------

The simulation, meshing and optimization commands all come from a single
:guilabel:`glaciercore` entry point, which since v0.21 is a **Python 3.14** ``uv``
workspace that also bundles ``zebraflow``. The former standalone ``glaciercore-mesh``
/ ``glaciercore-design`` / ``glaciercore-drawing`` / ``zebraflow`` console scripts are
gone — everything is now a ``glaciercore <group> <subcommand>`` (e.g. ``glaciercore mesh
straight-channels``, ``glaciercore zebraflow optimize``); run ``glaciercore --help``.

- :guilabel:`glaciercore` — https://github.com/Corintis/glaciercore
  (run the repo from the Firedrake virtualenv in which glaciercore is installed).

On a fresh instance, ``utils/gcp_setup/basic_setup_gcp.sh`` installs it for you
(and clones ``Notion_API``). Two capabilities live in separate, optional repos:

- power-map-graded meshing — `Corintis/power_based_mesh <https://github.com/Corintis/power_based_mesh>`_
  (``glaciercore-power-based-mesh``), used by ``topology_optimization/generate_power_based_mesh.sh``;
- the dune fixed-pattern design CLI (``dune``), used by ``dune_design/``.

Local tooling
-------------

The repo's own scripts (plotting, Notion upload, tests) and this documentation
need a few extra packages, pinned in :guilabel:`requirements.txt` to versions
compatible with the glaciercore v0.22 environment:

.. code-block:: bash

   pip install -r requirements.txt

This brings in ``numpy`` / ``scipy`` / ``matplotlib`` / ``Pint`` (plots),
``requests`` + ``python-dotenv`` (Notion upload), and ``sphinx`` +
``sphinx_rtd_theme`` + ``sphinx-mdinclude`` (this documentation). The Notion
script reads credentials from a ``.env`` file (copy ``.env.example``).
