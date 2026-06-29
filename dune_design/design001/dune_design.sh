#!/usr/bin/env bash
# Generate a dune-based fixed-pattern design (the channel topology is prescribed
# up-front rather than discovered by an optimizer).
#
# NOTE: the `dune` CLI ships with the dune design package; install it separately
# if the command is not found on this instance.
set -euo pipefail
cd "$(dirname "$0")"

MESH_JSON="settings_mesh.json"
SIM_JSON="settings_sim.json"
DUNE_JSON="setting_dune.json"
POWERMAP="../../powermap/powermap_v3/powermap_example.csv"
OUTPUT_DIR="dune_design_results"

command -v dune >/dev/null 2>&1 || {
    echo "[dune] ERROR: 'dune' CLI not found — install the dune design package." >&2; exit 1; }
for f in "$MESH_JSON" "$SIM_JSON" "$DUNE_JSON" "$POWERMAP"; do
    [[ -f "$f" ]] || { echo "[dune] ERROR: missing input '$f'" >&2; exit 1; }
done

echo "[dune] meshing  : $MESH_JSON"
echo "[dune] sim      : $SIM_JSON"
echo "[dune] dune     : $DUNE_JSON"
echo "[dune] powermap : $POWERMAP"
dune design \
    --powermap "$POWERMAP" \
    --mesh-json "$MESH_JSON" \
    --sim-json "$SIM_JSON" \
    --dune-json "$DUNE_JSON" \
    --output-dir "$OUTPUT_DIR"
echo "[dune] Done -> $OUTPUT_DIR/"
