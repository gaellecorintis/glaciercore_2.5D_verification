#!/usr/bin/env bash
# Generate comparison plots from pressure-sweep result folders using the
# built-in glaciercore plotting. Edit the `-ps "<label>" <folder>` pairs below
# to point at the cases you want to compare.
set -euo pipefail
cd "$(dirname "$0")"

OUTPUT_DIR="plot_001"
echo "[plot] output : $OUTPUT_DIR/"
glaciercore plot \
    -ps "straight channels" ../simulations/straight_channels_100micrometers/pressure_sweep_result \
    -ps "optimized design"  ../simulations/optimized_design001/pressure_sweep_result \
    -ps "straight_channel_point" ../simulations/straight_channels_100micrometers \
    --output-dir "$OUTPUT_DIR"
echo "[plot] Done -> $OUTPUT_DIR/"
