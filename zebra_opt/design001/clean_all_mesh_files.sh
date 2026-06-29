#!/usr/bin/env bash
# Remove generated mesh / CAD artifacts (.msh, .step, .brep, .geo_unrolled,
# .stl, .ply2) from this folder and below. Deletes generated outputs only —
# it never touches the JSON configuration files.
set -euo pipefail
cd "$(dirname "$0")"

echo "[clean-mesh] Removing mesh/CAD artifacts under $(pwd) ..."
find . -type f \( \
    -name "*.msh" -o -name "*.step" -o -name "*.brep" \
    -o -name "*.geo_unrolled" -o -name "*.stl" -o -name "*.ply2" \
\) -print -delete
echo "[clean-mesh] Done."
