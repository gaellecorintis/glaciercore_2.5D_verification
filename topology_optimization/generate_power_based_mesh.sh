#!/usr/bin/env bash
# Generate a power-map-graded optimization mesh (finer where the power is high).
#
# NOTE: power-based meshing was split out of glaciercore into a separate package
# (https://github.com/Corintis/power_based_mesh) and is no longer part of the
# default workspace install. Install that package to get the
# `glaciercore-power-based-mesh` CLI. If you just need a uniform mesh, run
# ./generate_uniform_mesh.sh instead.
set -euo pipefail
cd "$(dirname "$0")"

MESH_JSON="mesh/parameters_mesh.json"
POWERMAP="../powermap/powermap_v3/powermap_example.csv"
OUTPUT_DIR="mesh"
MIN_MESH_SIZE="${MIN_MESH_SIZE:-8e-6}"
MAX_MESH_SIZE="${MAX_MESH_SIZE:-20e-6}"

if ! command -v glaciercore-power-based-mesh >/dev/null 2>&1; then
    echo "[power-mesh] ERROR: 'glaciercore-power-based-mesh' is not installed." >&2
    echo "[power-mesh]   Power-based meshing now lives in a separate package:" >&2
    echo "[power-mesh]     https://github.com/Corintis/power_based_mesh" >&2
    echo "[power-mesh]   Install it, or run ./generate_uniform_mesh.sh for a uniform mesh." >&2
    exit 1
fi
for f in "$MESH_JSON" "$POWERMAP"; do
    [[ -f "$f" ]] || { echo "[power-mesh] ERROR: '$f' not found" >&2; exit 1; }
done

echo "[power-mesh] json     : $MESH_JSON"
echo "[power-mesh] powermap : $POWERMAP"
echo "[power-mesh] mesh size: $MIN_MESH_SIZE .. $MAX_MESH_SIZE m"
glaciercore-power-based-mesh power-based-mesh \
    --json "$MESH_JSON" \
    --powermap "$POWERMAP" \
    --output-dir "$OUTPUT_DIR" \
    --min-mesh-size "$MIN_MESH_SIZE" \
    --max-mesh-size "$MAX_MESH_SIZE"
echo "[power-mesh] Done -> $OUTPUT_DIR/"
