#!/usr/bin/env bash
# Run a topology optimization, then export the thresholded design snapshot.
# Override MPI ranks with NPROCS=<n>.
set -euo pipefail
cd "$(dirname "$0")"

NPROCS="${NPROCS:-4}"
OPT_JSON="parameters_optimization.json"
MESH_JSON="../mesh/parameters_mesh.json"
MESH="../uniform_mesh/optimization_mesh.msh"
MESH_META="../uniform_mesh/optimization_mesh_metadata.json"
POWERMAP="../../powermap/powermap_v3/powermap_example.csv"
OUTPUT_DIR="result"

for f in "$OPT_JSON" "$MESH" "$MESH_META" "$POWERMAP"; do
    [[ -f "$f" ]] || { echo "[optimization] ERROR: missing input '$f' (run ../generate_uniform_mesh.sh first)" >&2; exit 1; }
done
mkdir -p "$OUTPUT_DIR"

echo "[optimization] mesh     : $MESH"
echo "[optimization] powermap : $POWERMAP"
echo "[optimization] ranks    : $NPROCS"
mpiexec -np "$NPROCS" glaciercore optimize topology \
    --json "$OPT_JSON" \
    --powermap "$POWERMAP" \
    --mesh "$MESH" \
    --mesh-metadata "$MESH_META" \
    --output-dir "$OUTPUT_DIR" | tee "$OUTPUT_DIR/output_optimization.txt"

echo "[optimization] Exporting thresholded design snapshot ..."
glaciercore postprocess design-snapshot \
    --json "$MESH_JSON" \
    --threshold 0.5 \
    --input-pvd "$OUTPUT_DIR/design.pvd"
echo "[optimization] Done -> $OUTPUT_DIR/"
