#!/usr/bin/env bash
# Run a Zebraflow topology optimization (the optimizer discovers the channel
# layout), then render a design picture for each iteration mesh.
# Override MPI ranks with NPROCS=<n>.
set -euo pipefail
cd "$(dirname "$0")"

NPROCS="${NPROCS:-4}"
MESH_JSON="settings_mesh.json"
SIM_JSON="settings_sim.json"
OPT_JSON="settings_opt.json"
POWERMAP="../../powermap/powermap_v3/powermap_example.csv"
OUTPUT_DIR="optimization_results"

for f in "$MESH_JSON" "$SIM_JSON" "$OPT_JSON" "$POWERMAP"; do
    [[ -f "$f" ]] || { echo "[zebra] ERROR: missing input '$f'" >&2; exit 1; }
done

echo "[zebra] meshing      : $MESH_JSON"
echo "[zebra] simulation   : $SIM_JSON"
echo "[zebra] optimization : $OPT_JSON"
echo "[zebra] powermap     : $POWERMAP"
echo "[zebra] ranks        : $NPROCS"
mpiexec -np "$NPROCS" glaciercore zebraflow optimize \
    --meshing-json "$MESH_JSON" \
    --simulation-json "$SIM_JSON" \
    --optimization-json "$OPT_JSON" \
    --powermap "$POWERMAP" \
    --output-dir "$OUTPUT_DIR"

echo "[zebra] === Rendering a design picture per iteration ==="
shopt -s nullglob
for mesh in "$OUTPUT_DIR"/zebra_flow_iteration_*/zebra.msh; do
    echo "[zebra]   $mesh"
    glaciercore draw design --mesh-file "$mesh" --json "$MESH_JSON"
done
shopt -u nullglob
echo "[zebra] Done -> $OUTPUT_DIR/"
