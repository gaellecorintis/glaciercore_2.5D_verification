#!/usr/bin/env python3
"""Convert old-format zebraflow quadtree CSV files to the current format.

Old format differences:
  - Metadata line has 5 fields (missing flow_orientation, edge fins info)
  - Header uses old column names (startx/starty/endx/endy, is_overrefined, max_temperature)
  - Coordinates are in pixel units (need scaling to meters)

This script:
  1. Updates the metadata line from 5 fields to 9 fields (adding defaults)
  2. Renames header columns to current names
  3. Scales all coordinate and width values from pixels to meters
"""

import argparse
import json
from pathlib import Path


OLD_HEADER = "is_leaf,startx,starty,endx,endy,channel_width,refinement_level,is_overrefined,max_temperature"
NEW_HEADER = "is_leaf,point1_x,point1_y,point2_x,point2_y,channel_width,refinement_level,is_at_max_refinement,cost_function_value"

METADATA_INDICES_TO_SCALE = [0, 1, 3, 4]
DATA_INDICES_TO_SCALE = [1, 2, 3, 4, 5]


def detect_format(meta_fields: list[str], header_line: str) -> tuple[bool, bool]:
    """Return (needs_metadata_upgrade, needs_header_rename)."""
    needs_metadata = len(meta_fields) <= 6
    needs_header = "startx" in header_line or "is_overrefined" in header_line
    return needs_metadata, needs_header


def compute_scale(quadtree_dir: Path, chip_width: float, chip_length: float) -> float:
    """Compute the pixel-to-meter scale factor from all quadtree files.

    Determines the total pixel extent of all quadtrees and derives
    an isotropic scale factor from the chip dimensions.
    """
    max_x = 0.0
    max_y = 0.0

    for csv_file in sorted(quadtree_dir.glob("quadtree_*.csv")):
        with open(csv_file) as f:
            lines = f.readlines()
        meta = lines[0].strip().split(",")
        root_data = lines[2].strip().split(",")
        p2x = float(root_data[3])
        p2y = float(root_data[4])
        max_x = max(max_x, p2x)
        max_y = max(max_y, p2y)

    if max_x == 0 or max_y == 0:
        raise ValueError(f"Could not determine pixel extents (max_x={max_x}, max_y={max_y})")

    scale_x = chip_length / max_x
    scale_y = chip_width / max_y

    if abs(scale_x - scale_y) / max(scale_x, scale_y) > 0.01:
        raise ValueError(
            f"Anisotropic scaling detected: scale_x={scale_x:.6e}, scale_y={scale_y:.6e}. "
            f"Pixel extents ({max_x}, {max_y}) don't match chip dimensions "
            f"({chip_length}, {chip_width}) with isotropic scaling."
        )

    return (scale_x + scale_y) / 2


def convert_file(
    filepath: Path,
    scale: float | None,
    flow_orientation: str,
) -> None:
    with open(filepath) as f:
        lines = f.readlines()

    meta = lines[0].strip().split(",")
    header = lines[1].strip()

    needs_metadata, needs_header = detect_format(meta, header)

    if not needs_metadata and not needs_header and scale is None:
        print(f"  {filepath.name}: already in new format, skipping")
        return

    if needs_metadata:
        if len(meta) == 5:
            meta_width = float(meta[0])
            meta_height = float(meta[1])
            if scale is not None:
                meta[0] = str(float(meta[0]) * scale)
                meta[1] = str(float(meta[1]) * scale)
                meta[3] = str(float(meta[3]) * scale)
                meta[4] = str(float(meta[4]) * scale)
                original_region_height = str(float(meta_height) * scale)
            else:
                original_region_height = meta[1]
            meta.extend([
                flow_orientation,
                "0.0",
                "0.0",
                original_region_height,
            ])
        elif len(meta) == 6:
            if scale is not None:
                meta[0] = str(float(meta[0]) * scale)
                meta[1] = str(float(meta[1]) * scale)
                meta[3] = str(float(meta[3]) * scale)
                meta[4] = str(float(meta[4]) * scale)
                original_region_height = str(float(meta[1]))
            else:
                original_region_height = meta[1]
            meta.extend([
                "0.0",
                "0.0",
                original_region_height,
            ])
    elif scale is not None:
        for i in METADATA_INDICES_TO_SCALE:
            if i < len(meta):
                meta[i] = str(float(meta[i]) * scale)
        if len(meta) > 8:
            meta[8] = str(float(meta[8]) * scale)

    lines[0] = ",".join(meta) + "\n"

    if needs_header:
        lines[1] = NEW_HEADER + "\n"

    if scale is not None:
        for line_idx in range(2, len(lines)):
            parts = lines[line_idx].strip().split(",")
            if len(parts) < 6:
                continue
            for i in DATA_INDICES_TO_SCALE:
                parts[i] = f"{float(parts[i]) * scale:f}"
            lines[line_idx] = ",".join(parts) + "\n"

    with open(filepath, "w") as f:
        f.writelines(lines)

    actions = []
    if needs_metadata:
        actions.append("metadata upgraded")
    if needs_header:
        actions.append("header renamed")
    if scale is not None:
        actions.append(f"coordinates scaled by {scale:.6e}")
    print(f"  {filepath.name}: {', '.join(actions)}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert old-format zebraflow quadtree CSV files to the current format.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
examples:
  # Convert with coordinate scaling from mesh JSON (recommended)
  python convert_old_quadtrees.py quadtree/ --mesh-json settings_mesh.json

  # Only update metadata and header (no coordinate scaling)
  python convert_old_quadtrees.py quadtree/
""",
    )
    parser.add_argument(
        "quadtree_dir",
        type=Path,
        help="Directory containing quadtree_*.csv files",
    )
    parser.add_argument(
        "--mesh-json",
        type=Path,
        default=None,
        help="Path to the meshing JSON file (settings_mesh.json). "
        "Reads chip_width and chip_length from geometry.dimensions.",
    )
    args = parser.parse_args()

    if not args.quadtree_dir.is_dir():
        parser.error(f"Not a directory: {args.quadtree_dir}")

    csv_files = sorted(args.quadtree_dir.glob("quadtree_*.csv"))
    if not csv_files:
        parser.error(f"No quadtree_*.csv files found in {args.quadtree_dir}")

    scale = None
    if args.mesh_json is not None:
        if not args.mesh_json.is_file():
            parser.error(f"Mesh JSON file not found: {args.mesh_json}")
        with open(args.mesh_json) as f:
            mesh_config = json.load(f)
        dims = mesh_config["geometry"]["dimensions"]
        chip_width = dims["chip_width"]
        chip_length = dims["chip_length"]
        print(f"Read from {args.mesh_json}: chip_width={chip_width}, chip_length={chip_length}")
        scale = compute_scale(args.quadtree_dir, chip_width, chip_length)
        print(f"Auto-computed scale: {scale:.6e} m/pixel")

    print(f"Processing {len(csv_files)} file(s) in {args.quadtree_dir}/")
    for csv_file in csv_files:
        convert_file(csv_file, scale, flow_orientation="left_to_right")

    print("Done.")


if __name__ == "__main__":
    main()