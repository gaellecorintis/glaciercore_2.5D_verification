#!/usr/bin/env bash
# Render result screenshots from a simulation PVD. Defaults to this case's
# standard simulation output; pass a different PVD as the first argument.
set -euo pipefail
cd "$(dirname "$0")"

PVD="${1:-simulation_result/simulation_results_dim.pvd}"
MESH_JSON="parameters_mesh.json"
MESH_META="mesh/design_metadata.json"

[[ -f "$PVD" ]] || { echo "[snapshot] ERROR: PVD not found: $PVD (run the simulation first, or pass a path)" >&2; exit 1; }

echo "[snapshot] pvd : $PVD"
glaciercore postprocess results-snapshots \
    --input-pvd "$PVD" \
    --mesh-json "$MESH_JSON" \
    --mesh-metadata "$MESH_META" \
    --output-dir "$(dirname "$PVD")"
echo "[snapshot] Done -> $(dirname "$PVD")/"
