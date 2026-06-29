Project procedure
=================

This page is a flexible framework — not a strict set of rules — for organizing a
project and collaborating across the team.

For a new project, the team typically follows these steps:

1. Acquire a power map and translate it into the current glaciercore (v3) format.
   Keep its physical extent consistent with the chip footprint.

2. Fix the high-level settings: coolant type, cold-plate vs in-chip configuration,
   ``channel_depth``, layer thicknesses and conductivities, and the other inputs of
   the meshing / simulation ``.json`` files. Validate them with
   ``validate-mesh-config`` / ``validate-simulation-config`` before running.

3. Run a quick preliminary study (a pressure sweep on 100 µm straight channels) to
   gauge baseline thermal performance.

4. Choose an optimization path: ``zebraflow`` (the optimizer discovers the channel
   layout — recommended) or density-based ``glaciercore optimize topology``. Study the
   symmetry / split-flow assumptions, and lay out inlets/outlets so they satisfy the
   manufacturing constraints (e.g. the minimum inlet–outlet slit distance).

5. From the optimization result, generate the (split) design picture, build the
   body-fitted mesh, and run a pressure sweep comparable to step 3.

6. Compare and plot the results of steps 5 and 3 — the optimized design should
   improve thermal performance.

7. Discuss, gather feedback from the customer or project management, and address new
   requests.

8. Produce the mask file for the hardware team (2D, ``.STEP`` or ``.GDS``).

9. Attend to any further requests.

All outputs — simulation and optimization results, mask pictures and hardware
files, and a report summarizing the project's evolution and decisions — should be
collected in a single shared drive folder that serves as the project's repository
of record.
