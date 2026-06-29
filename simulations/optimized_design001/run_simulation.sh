#!/usr/bin/env bash
# Run the conjugate-heat-transfer simulation on the body-fitted optimized mesh.
# Run generate_mesh.sh first. Override MPI ranks with NPROCS=<n>.
set -euo pipefail
cd "$(dirname "$0")"

NPROCS="${NPROCS:-8}"
MESH="mesh/design.msh"
MESH_META="mesh/design_metadata.json"
POWERMAP="../../powermap/powermap_v3/powermap_example.csv"
SIM_JSON="parameters_simulation.json"
OUTPUT_DIR="simulation_result"

for f in "$MESH" "$MESH_META" "$POWERMAP" "$SIM_JSON"; do
    [[ -f "$f" ]] || { echo "[sim] ERROR: missing input '$f' (did you run generate_mesh.sh?)" >&2; exit 1; }
done
mkdir -p "$OUTPUT_DIR"

echo "[sim] mesh     : $MESH"
echo "[sim] metadata : $MESH_META"
echo "[sim] powermap : $POWERMAP"
echo "[sim] ranks    : $NPROCS"
mpiexec -np "$NPROCS" glaciercore simulate run \
    --json "$SIM_JSON" \
    --powermap "$POWERMAP" \
    --mesh "$MESH" \
    --mesh-metadata "$MESH_META" \
    --output-dir "$OUTPUT_DIR" | tee "$OUTPUT_DIR/output_simulation.txt"
echo "[sim] Done -> $OUTPUT_DIR/"
