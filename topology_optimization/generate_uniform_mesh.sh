#!/usr/bin/env bash
# Generate a uniform (rectangular) optimization mesh from mesh/parameters_mesh.json.
# Produces uniform_mesh/optimization_mesh.msh and optimization_mesh_metadata.json.
# Override the element size with ELEMENT_SIZE=<metres> (default 10e-6).
set -euo pipefail
cd "$(dirname "$0")"

MESH_JSON="mesh/parameters_mesh.json"
OUTPUT_DIR="uniform_mesh"
ELEMENT_SIZE="${ELEMENT_SIZE:-10e-6}"

[[ -f "$MESH_JSON" ]] || { echo "[uniform-mesh] ERROR: '$MESH_JSON' not found" >&2; exit 1; }

echo "[uniform-mesh] json         : $MESH_JSON"
echo "[uniform-mesh] element size : $ELEMENT_SIZE m"
echo "[uniform-mesh] output       : $OUTPUT_DIR/"
glaciercore mesh optimization \
    --json "$MESH_JSON" \
    --element-size "$ELEMENT_SIZE" \
    --output-dir "$OUTPUT_DIR"
echo "[uniform-mesh] Done -> $OUTPUT_DIR/optimization_mesh.msh"
