#!/usr/bin/env bash
# Remove ParaView / VTK time-series outputs: every .pvd file together with the
# companion data folder that shares its basename (e.g. results.pvd + results/).
set -euo pipefail
cd "$(dirname "$0")"

echo "[clean-paraview] Removing .pvd files and their data folders under $(pwd) ..."
find . -type f -name "*.pvd" | while read -r pvd; do
    data_dir="${pvd%.pvd}"
    if [[ -d "$data_dir" ]]; then
        echo "[clean-paraview]   rm -r $data_dir"
        rm -rf "$data_dir"
    fi
    echo "[clean-paraview]   rm $pvd"
    rm -f "$pvd"
done
echo "[clean-paraview] Done."
