#!/usr/bin/env bash
# Render screenshots for every simulation_results_dim.pvd found under a folder.
# Usage: ./generate_all_snapshots.sh <folder>
set -euo pipefail
cd "$(dirname "$0")"

FOLDER="${1:-}"
[[ -n "$FOLDER" ]] || { echo "Usage: $0 <folder>" >&2; exit 1; }
[[ -d "$FOLDER" ]] || { echo "[snapshots] ERROR: not a directory: $FOLDER" >&2; exit 1; }

found=0
while IFS= read -r pvd; do
    found=1
    echo "[snapshots] === $pvd ==="
    bash run_single_snapshot.sh "$pvd"
done < <(find "$FOLDER" -type f -name "simulation_results_dim.pvd")
[[ $found -eq 1 ]] || echo "[snapshots] No simulation_results_dim.pvd found under $FOLDER"
echo "[snapshots] Done."
