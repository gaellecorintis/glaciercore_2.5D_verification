#!/usr/bin/env bash
# Sweep the inlet pressure drop over a list of values on the straight-channel
# mesh. Override ranks with NPROCS=<n> and the sweep with PRESSURES="100,200,...".
set -euo pipefail
cd "$(dirname "$0")"

NPROCS="${NPROCS:-8}"
PRESSURES="${PRESSURES:-100,200,300,400,500}"
MESH="mesh/straight_channels.msh"
MESH_META="mesh/straight_channels_metadata.json"
POWERMAP="../../powermap/powermap_v3/powermap_example.csv"
SIM_JSON="parameters_simulation.json"
OUTPUT_DIR="pressure_sweep_result"

for f in "$MESH" "$MESH_META" "$POWERMAP" "$SIM_JSON"; do
    [[ -f "$f" ]] || { echo "[pressure-sweep] ERROR: missing input '$f' (did you run generate_mesh.sh?)" >&2; exit 1; }
done
mkdir -p "$OUTPUT_DIR"

echo "[pressure-sweep] pressures : $PRESSURES Pa"
echo "[pressure-sweep] ranks     : $NPROCS"
mpiexec -np "$NPROCS" glaciercore simulate pressure-sweep \
    --json "$SIM_JSON" \
    --powermap "$POWERMAP" \
    --mesh "$MESH" \
    --mesh-metadata "$MESH_META" \
    --output-dir "$OUTPUT_DIR" \
    --pressure-values "$PRESSURES" | tee "$OUTPUT_DIR/output_pressure_sweep.txt"
echo "[pressure-sweep] Done -> $OUTPUT_DIR/"
