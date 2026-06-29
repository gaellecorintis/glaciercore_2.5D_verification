#!/usr/bin/env bash
# Remove HDF5 checkpoint / field-data files (.h5) from this folder and below.
set -euo pipefail
cd "$(dirname "$0")"

echo "[clean-h5] Removing .h5 files under $(pwd) ..."
find . -type f -name "*.h5" -print -delete
echo "[clean-h5] Done."
