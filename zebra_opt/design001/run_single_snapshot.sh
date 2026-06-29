#!/usr/bin/env bash
# Render result screenshots from a Zebraflow simulation/iteration PVD.
# Usage: ./run_single_snapshot.sh <input-pvd>
set -euo pipefail
cd "$(dirname "$0")"

PVD="${1:-}"
[[ -n "$PVD" ]] || { echo "Usage: $0 <input-pvd>" >&2; exit 1; }
[[ -f "$PVD" ]] || { echo "[snapshot] ERROR: PVD not found: $PVD" >&2; exit 1; }
MESH_JSON="settings_mesh.json"

# Zebra writes a mesh-metadata JSON next to each iteration mesh; use the nearest
# one if present so regions / colour scales render correctly.
META=$(find "$(dirname "$PVD")" -maxdepth 2 -name "*metadata*.json" 2>/dev/null | head -1 || true)

echo "[snapshot] pvd      : $PVD"
echo "[snapshot] metadata : ${META:-<none found, rendering without>}"
if [[ -n "$META" ]]; then
    glaciercore postprocess results-snapshots --input-pvd "$PVD" --mesh-json "$MESH_JSON" \
        --mesh-metadata "$META" --output-dir "$(dirname "$PVD")"
else
    glaciercore postprocess results-snapshots --input-pvd "$PVD" --mesh-json "$MESH_JSON" \
        --output-dir "$(dirname "$PVD")"
fi
echo "[snapshot] Done -> $(dirname "$PVD")/"
