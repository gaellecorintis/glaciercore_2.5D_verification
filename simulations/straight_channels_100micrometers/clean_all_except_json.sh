#!/usr/bin/env bash
# Convenience wrapper: remove every generated artifact in this case folder
# (mesh, screenshots, HDF5, ParaView outputs) while leaving the JSON configs
# and run scripts intact. Run this to reset a case before re-running it.
set -euo pipefail
cd "$(dirname "$0")"

echo "[clean-all] Resetting $(pwd) (JSON configs are preserved) ..."
bash clean_all_mesh_files.sh
bash clean_all_screenshots.sh
bash clean_h5_files.sh
bash clean_paraview.sh
echo "[clean-all] Done."
