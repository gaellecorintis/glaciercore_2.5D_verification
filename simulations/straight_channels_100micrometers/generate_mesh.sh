#!/usr/bin/env bash
# Build the straight-channel reference mesh from parameters_mesh.json.
# Produces mesh/straight_channels.msh and mesh/straight_channels_metadata.json.
set -euo pipefail
cd "$(dirname "$0")"

MESH_JSON="parameters_mesh.json"
OUTPUT_DIR="mesh"
THREADS="${THREADS:-4}"

[[ -f "$MESH_JSON" ]] || { echo "[mesh] ERROR: $MESH_JSON not found" >&2; exit 1; }

echo "[mesh] json    : $MESH_JSON"
echo "[mesh] output  : $OUTPUT_DIR/"
echo "[mesh] threads : $THREADS"
glaciercore mesh straight-channels --json "$MESH_JSON" --threads "$THREADS" --output-dir "$OUTPUT_DIR"
echo "[mesh] Done -> $OUTPUT_DIR/straight_channels.msh"
