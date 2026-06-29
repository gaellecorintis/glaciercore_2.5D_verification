#!/usr/bin/env bash
# Remove rendered result images (.png, .webp) from this folder and below.
set -euo pipefail
cd "$(dirname "$0")"

echo "[clean-screenshots] Removing .png/.webp files under $(pwd) ..."
find . -type f \( -name "*.png" -o -name "*.webp" \) -print -delete
echo "[clean-screenshots] Done."
