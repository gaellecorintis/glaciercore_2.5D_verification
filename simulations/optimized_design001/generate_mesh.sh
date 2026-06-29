#!/usr/bin/env bash
# Body-fit a mesh to a selected (optimized) design picture.
#
# NOTE: current glaciercore expects the SPLIT (partitioned) design image — the
# computational sub-domain, not a full mirrored picture. If you only have the
# full design, produce the split one first with `glaciercore draw split-design`.
#
# Produces mesh/design.msh and mesh/design_metadata.json.
set -euo pipefail
cd "$(dirname "$0")"

MESH_JSON="parameters_mesh.json"
DESIGN_PNG="../../selected_design_png/design.png"
OUTPUT_DIR="mesh"
THREADS="${THREADS:-4}"

for f in "$MESH_JSON" "$DESIGN_PNG"; do
    [[ -f "$f" ]] || { echo "[mesh] ERROR: '$f' not found" >&2; exit 1; }
done

echo "[mesh] json       : $MESH_JSON"
echo "[mesh] design png : $DESIGN_PNG"
echo "[mesh] output     : $OUTPUT_DIR/"
echo "[mesh] threads    : $THREADS"
glaciercore mesh design \
    --json "$MESH_JSON" \
    --design-png "$DESIGN_PNG" \
    --threads "$THREADS" \
    --output-dir "$OUTPUT_DIR"
echo "[mesh] Done -> $OUTPUT_DIR/design.msh"
