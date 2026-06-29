"""Generate a mesh from a DXF design.

Reads a DXF file, validates that it contains exactly one outermost (root)
closed polygon (the chip outline), and renders the design as B/W PNGs:

    - White (255) = solid fin
    - Black (0)   = fluid

The script always writes ``design.png`` covering the full fluid bbox. When
``--symmetries`` is active it additionally writes ``split_design.png``, the
sub-rectangle that will actually be meshed.

With ``--png-only`` the script stops after writing the PNGs. Otherwise it
loads a glaciercore meshing-config JSON, hard-errors if its chip_width and
chip_length disagree (beyond ``_DIM_TOLERANCE``) with the DXF-derived fluid
bbox, and dispatches the mesher *directly from shapely contours* (no PNG
round-trip): the solid (root XOR-folded with every inner polygon) is computed
analytically, clipped, and each disjoint piece's CW exterior (plus any holes)
is handed to ``generate_mesh_from_contours`` — the same path that
``script_for_clogging`` uses.

``--symmetries`` exploits chip symmetry by meshing only a sub-rectangle of
the fluid bbox. The split axis runs through the bbox centre. Choices:

    - ``full`` (default): mesh the whole fluid bbox, no split.
    - ``N``: keep the top half (y >= centre_y).
    - ``E``: keep the right half (x >= centre_x).
    - ``NE``: keep the top-right quarter.

The settings JSON ``chip_width`` / ``chip_length`` must equal the *post-split*
extent (so for ``--symmetries NE`` they are half the full bbox in each direction).
"""

from __future__ import annotations

import argparse
import json
import sys
from functools import reduce
from pathlib import Path

import cv2
import numpy as np
from shapely.geometry import MultiPolygon, Point, Polygon, box
from shapely.ops import unary_union
from shapely.validation import make_valid

try:
    import ezdxf
    from ezdxf import path as dxf_path
except ImportError as exc:
    raise ImportError("ezdxf is required. Install with: pip install ezdxf") from exc


# --------------------------------------------------------------------------- #
# DXF parsing
# --------------------------------------------------------------------------- #

# $INSUNITS header value -> meters conversion factor
_INSUNITS_TO_M: dict[int, float] = {
    0: 1e-3,    # unitless -> assume mm
    1: 0.0254,  # inches
    2: 0.3048,  # feet
    4: 1e-3,    # millimetres
    5: 1e-2,    # centimetres
    6: 1.0,     # metres
    8: 1e-6,    # microns
}

# Maximum chord-arc deviation (in DXF units) used when flattening arc segments.
_FLATTEN_TOLERANCE = 0.001

# Relative tolerance for the DXF vs settings chip-dim check.
_DIM_TOLERANCE = 1e-6

# Edge-marker stripe thickness (chip-frame metres) used when annotating PNGs
# with inlet/outlet edges. 50 µm in the split; doubles to ~100 µm at the
# centerlines of the mirrored full image (since both adjacent quarters
# contribute a stripe there).
_IO_EDGE_THICKNESS_M = 5e-5

# Clogging sampling defaults.
# ``_CLOGGING_MIN_SPACING_FACTOR`` enforces a minimum centre-to-centre spacing
# (in multiples of the clogging length) so two cloggings can't kiss in a long
# thin channel. ``_CLOGGING_SAMPLE_SPACING_M`` controls how densely we walk
# fin boundaries when locating thinnest-channel hits (20 µm is fine for
# anything down to ~50 µm channels — smaller designs would want it lowered).
# Cloggings are placed at the full channel width — tangent to both adjacent
# fins. The downstream tagging issue this causes (fluid surface ends up in
# fin tags after gmsh's fragmentation) is fixed by ``_smart_connectivity_check``
# in the meshing call, not by sampling-time tricks.
_CLOGGING_MIN_SPACING_FACTOR = 2.0
_CLOGGING_SAMPLE_SPACING_M = 20e-6
_CLOGGING_PREVIEW_COLOR_BGR = (0, 0, 220)  # red overlay for preview PNGs


def _lwpolyline_to_polygon(entity) -> Polygon | None:
    if not entity.is_closed:
        return None
    try:
        p = dxf_path.make_path(entity)
        pts = [(v.x, v.y) for v in p.flattening(_FLATTEN_TOLERANCE)]
        if len(pts) < 3:
            return None
        poly = Polygon(pts)
        return make_valid(poly) if not poly.is_valid else poly
    except Exception:
        return None


def _circle_to_polygon(entity) -> Polygon | None:
    try:
        cx, cy = entity.dxf.center.x, entity.dxf.center.y
        return Point(cx, cy).buffer(entity.dxf.radius, resolution=64)
    except Exception:
        return None


def _hatch_to_polygons(entity) -> list[Polygon]:
    results: list[Polygon] = []
    try:
        for boundary_path in entity.paths:
            if not hasattr(boundary_path, "vertices"):
                continue
            pts = [(v[0], v[1]) for v in boundary_path.vertices]
            if len(pts) < 3:
                continue
            poly = Polygon(pts)
            if not poly.is_valid:
                poly = make_valid(poly)
            if isinstance(poly, Polygon) and poly.area > 0:
                results.append(poly)
    except Exception:
        pass
    return results


def load_polygons_from_dxf(path: Path) -> tuple[list[Polygon], float]:
    """Load all closed polygons from the DXF model space.

    Returns the polygon list plus the conversion factor from DXF units to
    metres (read from ``$INSUNITS``, defaulting to millimetres).
    """
    doc = ezdxf.readfile(str(path))
    msp = doc.modelspace()
    insunits = doc.header.get("$INSUNITS", 4)
    units_to_m = _INSUNITS_TO_M.get(int(insunits), 1e-3)

    polygons: list[Polygon] = []
    for entity in msp:
        etype = entity.dxftype()
        if etype == "LWPOLYLINE":
            poly = _lwpolyline_to_polygon(entity)
            if poly is not None and poly.area > 0:
                polygons.append(poly)
        elif etype == "CIRCLE":
            poly = _circle_to_polygon(entity)
            if poly is not None and poly.area > 0:
                polygons.append(poly)
        elif etype == "HATCH":
            polygons.extend(_hatch_to_polygons(entity))
    return polygons, units_to_m


def find_root_polygons(polygons: list[Polygon]) -> list[Polygon]:
    """Return polygons not contained in any other polygon in the list."""
    roots: list[Polygon] = []
    for i, p in enumerate(polygons):
        if any(q.contains(p) for j, q in enumerate(polygons) if j != i):
            continue
        roots.append(p)
    return roots


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #


def _fluid_bounds(inner_polygons: list[Polygon]) -> tuple[float, float, float, float]:
    """Return (minx, miny, maxx, maxy) of the union of the inner polygons."""
    if not inner_polygons:
        raise ValueError("DXF must contain at least one inner (fluid) polygon.")
    return unary_union(inner_polygons).bounds


def _apply_symmetries(
    fluid_bbox: tuple[float, float, float, float],
    symmetries: str,
) -> tuple[float, float, float, float]:
    """Return the sub-rectangle of ``fluid_bbox`` selected by ``symmetries``.

    Split axes run through the bbox centre. ``N`` keeps the top half (high
    y), ``E`` the right half (high x), ``NE`` the top-right quarter. ``full``
    returns ``fluid_bbox`` unchanged.
    """
    minx, miny, maxx, maxy = fluid_bbox
    cx = 0.5 * (minx + maxx)
    cy = 0.5 * (miny + maxy)
    if symmetries == "full":
        return fluid_bbox
    if symmetries == "N":
        return (minx, cy, maxx, maxy)
    if symmetries == "E":
        return (cx, miny, maxx, maxy)
    if symmetries == "NE":
        return (cx, cy, maxx, maxy)
    raise ValueError(f"Unknown --symmetries value: {symmetries!r}")


def _flatten_polygons(geom) -> list[Polygon]:
    """Flatten a Shapely geometry into a list of (non-empty, positive-area) Polygons.

    Handles Polygon, MultiPolygon and GeometryCollection results from
    ``intersection``; degenerate outputs (LineString, Point, empty) are dropped.
    """
    if geom.is_empty:
        return []
    gt = geom.geom_type
    if gt == "Polygon":
        return [geom] if geom.area > 0 else []
    if gt in ("MultiPolygon", "GeometryCollection"):
        return [g for g in geom.geoms if g.geom_type == "Polygon" and g.area > 0]
    return []


def _render_image(
    inner_polygons: list[Polygon],
    crop_bbox: tuple[float, float, float, float],
    units_to_m: float,
    px_per_cm: int,
) -> np.ndarray:
    """Render the design as a B/W BGR image cropped to ``crop_bbox``.

    Each inner polygon is geometrically intersected with ``crop_bbox`` so
    polygons straddling a split axis are clipped cleanly. The canvas is
    seeded white (= solid): by construction the crop sits inside the root
    polygon, so the root contributes a uniform parity flip everywhere and is
    folded into the seed. Each clipped inner polygon is then XOR-filled to
    alternate fluid (black) / solid (white) parity as nesting deepens.
    """
    minx, miny, maxx, maxy = crop_bbox
    canvas_w_m = (maxx - minx) * units_to_m
    canvas_h_m = (maxy - miny) * units_to_m
    if canvas_w_m <= 0 or canvas_h_m <= 0:
        raise ValueError("Crop bounding box has zero or negative dimensions.")

    px_per_m = px_per_cm * 100
    n_cols = max(1, round(canvas_w_m * px_per_m))
    n_rows = max(1, round(canvas_h_m * px_per_m))
    span_x = maxx - minx
    span_y = maxy - miny
    crop_box = box(minx, miny, maxx, maxy)

    def _ring_to_px(coords) -> np.ndarray:
        pts = []
        for x, y in coords:
            col = int(round((x - minx) / span_x * (n_cols - 1)))
            row = int(round((maxy - y) / span_y * (n_rows - 1)))
            col = max(0, min(n_cols - 1, col))
            row = max(0, min(n_rows - 1, row))
            pts.append([col, row])
        return np.array(pts, dtype=np.int32)

    img = np.full((n_rows, n_cols), 255, dtype=np.uint8)
    mask = np.empty_like(img)

    for shape in inner_polygons:
        if shape.is_empty:
            continue
        for geom in _flatten_polygons(shape.intersection(crop_box)):
            mask[:] = 0
            cv2.fillPoly(mask, [_ring_to_px(geom.exterior.coords)], 255)
            for interior in geom.interiors:
                cv2.fillPoly(mask, [_ring_to_px(interior.coords)], 0)
            cv2.bitwise_xor(img, mask, dst=img)

    return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)


# --------------------------------------------------------------------------- #
# Cloggings: sampling, rasterisation, preview
# --------------------------------------------------------------------------- #


def _is_on_crop_boundary(
    pt: Point,
    crop_bbox: tuple[float, float, float, float],
    eps_dxf: float,
) -> bool:
    """True if ``pt`` lies on any of the four ``crop_bbox`` edges, within
    ``eps_dxf``. Used to discard cropping-artifact hits — samples whose
    nearest-other point sits on the crop edge are measuring the flat segment
    created by ``solid.intersection(crop_box)``, not a physical channel.
    """
    minx, miny, maxx, maxy = crop_bbox
    return (
        abs(pt.x - minx) < eps_dxf
        or abs(pt.x - maxx) < eps_dxf
        or abs(pt.y - miny) < eps_dxf
        or abs(pt.y - maxy) < eps_dxf
    )


def _sample_boundary_min_other_distance(
    solid_pieces: list[Polygon],
    threshold_dxf: float,
    sample_spacing_dxf: float,
    crop_bbox: tuple[float, float, float, float] | None = None,
    crop_eps_dxf: float = 1e-6,
) -> list[tuple[float, Point, Point]]:
    """Walk each solid piece's exterior at uniform arc-length spacing; for
    every sample, find the nearest OTHER piece and the nearest-point on it.
    Return only samples whose distance ≤ ``threshold_dxf`` — these mark the
    *full extent* of every region where the channel is at-or-near minimum
    width, not just per-pair closest-point midpoints.

    If ``crop_bbox`` is supplied, samples or nearest-other-points sitting on
    the crop edges (within ``crop_eps_dxf``) are dropped. These are
    cropping artifacts: ``solid.intersection(crop_box)`` adds flat segments
    along the crop edges, and the closest-point routine then measures
    1 µm-scale gaps between adjacent fins' clipped top edges that don't
    correspond to physical channels.

    Returns ``(d_dxf, point_on_self, point_on_other)`` tuples in DXF units.
    """
    from shapely.ops import nearest_points
    from shapely.strtree import STRtree

    tree = STRtree(solid_pieces)
    out: list[tuple[float, Point, Point]] = []
    for i, piece in enumerate(solid_pieces):
        boundary = piece.exterior
        length = boundary.length
        if length <= 0:
            continue
        n_samples = max(2, int(length / sample_spacing_dxf))
        for k in range(n_samples):
            sample = boundary.interpolate(k * length / n_samples)
            if crop_bbox is not None and _is_on_crop_boundary(sample, crop_bbox, crop_eps_dxf):
                continue
            search_box = box(
                sample.x - threshold_dxf, sample.y - threshold_dxf,
                sample.x + threshold_dxf, sample.y + threshold_dxf,
            )
            best_d = float("inf")
            best_pt: Point | None = None
            for j_raw in tree.query(search_box):
                j = int(j_raw)
                if j == i:
                    continue
                q = solid_pieces[j]
                d = sample.distance(q)
                if d < best_d:
                    _, near = nearest_points(sample, q)
                    best_d = d
                    best_pt = near
            if best_pt is None or best_d > threshold_dxf:
                continue
            if crop_bbox is not None and _is_on_crop_boundary(best_pt, crop_bbox, crop_eps_dxf):
                continue
            out.append((best_d, sample, best_pt))
    return out


def sample_cloggings_in_thinnest_channels(
    root: Polygon,
    inner_polygons: list[Polygon],
    crop_bbox: tuple[float, float, float, float],
    units_to_m: float,
    n_cloggings: int,
    clogging_length_m: float,
    seed: int,
    width_tolerance: float,
    sample_spacing_m: float,
) -> tuple[list[Polygon], list[dict], dict]:
    """Sample ``n_cloggings`` cloggings spread along the thinnest-channel
    regions of the design — pure shapely, no rasterisation.

    Pipeline:

    - ``find_thinnest_channel_hits`` returns a dense set of boundary samples
      ``(d, p_self, p_other)`` covering every thinnest-channel stretch.
    - Pick ``n_cloggings`` of them uniformly at random subject to a centre-to-
      centre spacing constraint (``_CLOGGING_MIN_SPACING_FACTOR`` × the
      streamwise length).
    - For each pick, build a rectangle:
        - **spanwise** (perpendicular to the local flow, across the channel):
          oriented from ``p_self`` to ``p_other``, extent = ``d`` (no oversize).
        - **streamwise** (along the local flow): ``clogging_length_m``.
        - clipped to the fluid region so it never overlaps a fin; the
          connected piece containing the centre is kept (the rectangle can
          pick up a stray neighbouring-channel piece across a thin fin).

    Channel direction is per-sample, set from the (p_self → p_other) vector,
    so curved or oblique channels behave the same as axis-aligned ones.

    Returns the clipped cloggings (DXF units), a metadata list (chip-frame
    metres), and a diagnostic dict (``hits``, ``min_channel_width_m``,
    ``threshold_width_m``) for the highlight PNG.
    """
    if n_cloggings <= 0:
        return [], [], {"hits": [], "min_channel_width_m": 0.0, "threshold_width_m": 0.0}

    # Parity-fold the DXF to recover the solid region; the fluid is the
    # complement inside the crop. Solid pieces (chip wall + each fin pillar)
    # are the connected components of the solid region — these are what we
    # measure channel widths between.
    crop_box_shapely = box(*crop_bbox)
    solid_region = reduce(
        lambda acc, p: acc.symmetric_difference(p),
        inner_polygons,
        root,
    ).intersection(crop_box_shapely)
    fluid_region = crop_box_shapely.difference(solid_region)
    solid_pieces = _flatten_polygons(solid_region)
    if len(solid_pieces) < 2:
        raise RuntimeError(
            f"Need ≥ 2 disjoint solid pieces to detect channels; got {len(solid_pieces)}."
        )

    # Single-pass thinnest-channel detector: walk every boundary sample with a
    # generous search radius (5 % of the chip diagonal), then derive the
    # global min and filter to hits within ``(1 + width_tolerance) × min``.
    minx, miny, maxx, maxy = crop_bbox
    chip_diag_dxf = ((maxx - minx) ** 2 + (maxy - miny) ** 2) ** 0.5
    sample_spacing_dxf = sample_spacing_m / units_to_m
    raw_hits = _sample_boundary_min_other_distance(
        solid_pieces,
        threshold_dxf=0.05 * chip_diag_dxf,
        sample_spacing_dxf=sample_spacing_dxf,
        crop_bbox=crop_bbox,
        crop_eps_dxf=1e-3 * sample_spacing_dxf,
    )
    if not raw_hits:
        raise RuntimeError("No boundary samples near any other solid piece — design has no channels?")
    min_d_dxf = min(d for d, _a, _b in raw_hits)
    # Float-arithmetic safety: gives ``width_tolerance=0`` a tiny epsilon
    # so samples that round to clean min don't get rejected by float drift.
    threshold_d_dxf = min_d_dxf * (1.0 + width_tolerance) + max(min_d_dxf * 1e-9, 1e-12)
    hits = [h for h in raw_hits if h[0] <= threshold_d_dxf]
    min_m = min_d_dxf * units_to_m
    threshold_m = threshold_d_dxf * units_to_m
    print(
        f"Cloggings: {len(hits)} thinnest-channel boundary samples at "
        f"min channel width {min_m * 1e6:.1f} um "
        f"(threshold {threshold_m * 1e6:.1f} um)."
    )

    minx, miny, _maxx, _maxy = crop_bbox
    rng = np.random.default_rng(seed)
    min_spacing_m = _CLOGGING_MIN_SPACING_FACTOR * clogging_length_m
    cloggings: list[Polygon] = []
    meta: list[dict] = []
    max_attempts = max(10_000, 1000 * n_cloggings)

    for _ in range(max_attempts):
        if len(cloggings) >= n_cloggings:
            break
        idx = int(rng.integers(len(hits)))
        d_dxf, p_self, p_other = hits[idx]
        if d_dxf <= 0:
            continue
        cx, cy = 0.5 * (p_self.x + p_other.x), 0.5 * (p_self.y + p_other.y)
        center_m = ((cx - minx) * units_to_m, (cy - miny) * units_to_m)

        if any(
            (center_m[0] - m["center_m"][0]) ** 2 + (center_m[1] - m["center_m"][1]) ** 2
            < min_spacing_m ** 2
            for m in meta
        ):
            continue

        # Spanwise unit vector: from p_self → p_other (across the channel).
        sx, sy = (p_other.x - p_self.x) / d_dxf, (p_other.y - p_self.y) / d_dxf
        # Streamwise unit vector: CCW perpendicular to spanwise (along flow).
        tx, ty = -sy, sx

        half_s = 0.5 * d_dxf
        half_t = 0.5 * clogging_length_m / units_to_m
        corners = [
            (cx + sx * half_s + tx * half_t, cy + sy * half_s + ty * half_t),
            (cx - sx * half_s + tx * half_t, cy - sy * half_s + ty * half_t),
            (cx - sx * half_s - tx * half_t, cy - sy * half_s - ty * half_t),
            (cx + sx * half_s - tx * half_t, cy + sy * half_s - ty * half_t),
        ]
        rect = Polygon(corners)
        if not rect.is_valid:
            rect = make_valid(rect)
        if rect.is_empty:
            continue

        clog = rect.intersection(fluid_region)
        if clog.is_empty or clog.area <= 0:
            continue

        # Keep the connected piece containing the centre — the rectangle may
        # straddle a thin fin and pick up a stray neighbouring-channel piece.
        center_point = Point(cx, cy)
        if clog.geom_type == "MultiPolygon":
            picked = None
            for piece in clog.geoms:
                if piece.contains(center_point) or piece.distance(center_point) < 1e-9:
                    picked = piece
                    break
            clog = picked if picked is not None else max(clog.geoms, key=lambda g: g.area)

        cloggings.append(clog)
        meta.append({
            "center_m": list(center_m),
            "spanwise_unit": [sx, sy],
            "streamwise_unit": [tx, ty],
            "channel_width_m": d_dxf * units_to_m,
            "clogging_length_m": clogging_length_m,
        })

    if len(cloggings) < n_cloggings:
        raise RuntimeError(
            f"Could not place {n_cloggings} cloggings after {max_attempts} attempts "
            f"(placed {len(cloggings)}). Decrease --clogging-length, increase "
            f"--clogging-width-tolerance, or lower --n-cloggings."
        )

    diagnostic = {
        "hits": hits,
        "min_channel_width_m": min_m,
        "threshold_width_m": threshold_m,
    }
    return cloggings, meta, diagnostic


def _write_thinnest_channels_diagnostic_png(
    inner_polygons: list[Polygon],
    crop_bbox: tuple[float, float, float, float],
    units_to_m: float,
    px_per_cm: int,
    hits: list[tuple[float, Point, Point]],
    min_channel_width_m: float,
    threshold_width_m: float,
    output_path: Path,
    line_thickness: int = 2,
) -> None:
    """Render the design B/W and overlay every thinnest-channel boundary
    sample in red — one short segment per sample, from the sample point on a
    solid piece to its closest point on the nearest neighbour. A long parallel
    thin channel becomes a continuous red ladder along its full streamwise
    extent. A legend in the bottom-left tags red as "thinnest channels".
    """
    img = _render_image(inner_polygons, crop_bbox, units_to_m, px_per_cm)
    minx, miny, maxx, maxy = crop_bbox
    n_rows, n_cols = img.shape[:2]
    span_x, span_y = maxx - minx, maxy - miny

    def to_px(x: float, y: float) -> tuple[int, int]:
        col = int(round((x - minx) / span_x * (n_cols - 1)))
        row = int(round((maxy - y) / span_y * (n_rows - 1)))
        return max(0, min(n_cols - 1, col)), max(0, min(n_rows - 1, row))

    red = _CLOGGING_PREVIEW_COLOR_BGR
    for _d, p_self, p_other in hits:
        cv2.line(img, to_px(p_self.x, p_self.y), to_px(p_other.x, p_other.y), red, thickness=line_thickness)

    # Matplotlib-style legend in the top-right: white box with a thin grey
    # border, short colour swatch on the left, label text on the right. No
    # mention of the colour name in the label — the swatch carries that.
    threshold_um = threshold_width_m * 1e6
    min_um = min_channel_width_m * 1e6
    # Hide the sub-2%% numerical buffer from the label (it exists only to
    # absorb vertex-discretisation scatter, not as a meaningful spec). Show
    # both numbers only when the user intentionally opens up the tolerance.
    if threshold_width_m <= min_channel_width_m * 1.02:
        legend_text = f"channel width = {min_um:.0f} um"
    else:
        legend_text = f"channel width <= {threshold_um:.0f} um  (min {min_um:.0f} um)"

    # Matplotlib-style legend top-right: white box, thin black border, a
    # short red swatch line, then the label text.
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale, thickness = 1.1, 2
    (tw, th), bl = cv2.getTextSize(legend_text, font, scale, thickness)
    swatch_w, gap, pad = 56, 16, 12
    box_w = swatch_w + gap + tw + 2 * pad
    box_h = th + bl + 2 * pad
    x0 = n_cols - 18 - box_w
    y0 = 18
    cv2.rectangle(img, (x0, y0), (x0 + box_w, y0 + box_h), (255, 255, 255), -1)
    cv2.rectangle(img, (x0, y0), (x0 + box_w, y0 + box_h), (0, 0, 0), 2)
    cy = y0 + box_h // 2
    cv2.line(img, (x0 + pad, cy), (x0 + pad + swatch_w, cy), red, 5, cv2.LINE_AA)
    cv2.putText(img, legend_text, (x0 + pad + swatch_w + gap, cy + th // 2), font, scale, (0, 0, 0), thickness, cv2.LINE_AA)

    if not cv2.imwrite(str(output_path), img):
        raise RuntimeError(f"Failed to write thinnest-channels diagnostic to {output_path}")


def _write_clogging_preview_png(
    inner_polygons_without_cloggings: list[Polygon],
    cloggings_dxf: list[Polygon],
    crop_bbox: tuple[float, float, float, float],
    units_to_m: float,
    px_per_cm: int,
    output_path: Path,
) -> None:
    """Render the pre-clogging design (white = solid, black = fluid) and
    overlay each clogging in red so the user can sight-check placement.
    """
    img = _render_image(inner_polygons_without_cloggings, crop_bbox, units_to_m, px_per_cm)
    minx, miny, maxx, maxy = crop_bbox
    n_rows, n_cols = img.shape[:2]
    span_x = maxx - minx
    span_y = maxy - miny

    def _ring_to_px(coords) -> np.ndarray:
        pts = []
        for x, y in coords:
            col = int(round((x - minx) / span_x * (n_cols - 1)))
            row = int(round((maxy - y) / span_y * (n_rows - 1)))
            col = max(0, min(n_cols - 1, col))
            row = max(0, min(n_rows - 1, row))
            pts.append([col, row])
        return np.array(pts, dtype=np.int32)

    for clog in cloggings_dxf:
        pieces = list(clog.geoms) if clog.geom_type == "MultiPolygon" else [clog]
        for piece in pieces:
            cv2.fillPoly(img, [_ring_to_px(piece.exterior.coords)], _CLOGGING_PREVIEW_COLOR_BGR)
            for interior in piece.interiors:
                cv2.fillPoly(img, [_ring_to_px(interior.coords)], (0, 0, 0))

    if not cv2.imwrite(str(output_path), img):
        raise RuntimeError(f"Failed to write clogging preview to {output_path}")


# --------------------------------------------------------------------------- #
# Settings validation
# --------------------------------------------------------------------------- #


def _validate_chip_dimensions(
    settings_chip_width: float,
    settings_chip_length: float,
    chip_width_dxf: float,
    chip_length_dxf: float,
    tol: float,
) -> None:
    def _close(a: float, b: float) -> bool:
        return abs(a - b) <= tol * max(abs(b), 1e-12)

    if _close(chip_width_dxf, settings_chip_width) and _close(chip_length_dxf, settings_chip_length):
        return
    raise ValueError(
        f"DXF chip dimensions ({chip_width_dxf * 1e3:.4f} x {chip_length_dxf * 1e3:.4f} mm) "
        f"do not match settings_mesh.json "
        f"({settings_chip_width * 1e3:.4f} x {settings_chip_length * 1e3:.4f} mm). "
        f"Update one of them so they agree within tolerance ({tol})."
    )


# --------------------------------------------------------------------------- #
# Shapely -> contour pipeline (no PNG round-trip)
# --------------------------------------------------------------------------- #


def _build_solid_contours(
    root: Polygon,
    inner_polygons: list[Polygon],
    crop_bbox: tuple[float, float, float, float],
    units_to_m: float,
) -> list[tuple[np.ndarray, np.ndarray]]:
    """Compute the solid geometry by even-odd parity (XOR-fold of root with
    every inner polygon), clip to ``crop_bbox``, and return the CW exterior +
    interior contours of each disjoint solid piece in chip-frame metres
    (origin at ``crop_bbox`` bottom-left).

    The XOR fold matches the rendering convention in ``_render_image`` and
    handles arbitrary nesting: a fin pillar sitting inside a fluid manifold
    (depth 3) ends up as solid, the manifold itself (depth 2) as fluid, the
    chip wall (depth 1) as solid. This is the same result you'd get from
    ``cv2.findContours`` on the rendered PNG, but computed analytically with
    no raster round-trip.
    """
    from functools import reduce

    from shapely.geometry.polygon import orient

    crop_minx, crop_miny, _, _ = crop_bbox
    crop_box_shapely = box(*crop_bbox)
    solid = reduce(
        lambda acc, p: acc.symmetric_difference(p),
        inner_polygons,
        root,
    ).intersection(crop_box_shapely)

    contours: list[tuple[np.ndarray, np.ndarray]] = []
    # gmsh's default boolean tolerance is ~1e-8 m; vertices closer than this in
    # the chip frame collapse into a zero-length line in ``addLine``. Drop any
    # consecutive duplicates above that threshold so the XOR-fold's
    # floating-point near-misses don't crash the mesher.
    _min_edge_length_m = 1e-7

    def _ring_to_xy(ring) -> tuple[np.ndarray, np.ndarray] | None:
        coords = np.asarray(ring.coords)[:-1]
        x = (coords[:, 0] - crop_minx) * units_to_m
        y = (coords[:, 1] - crop_miny) * units_to_m
        if len(x) < 3:
            return None
        prev_x = np.concatenate([x[-1:], x[:-1]])
        prev_y = np.concatenate([y[-1:], y[:-1]])
        keep = np.hypot(x - prev_x, y - prev_y) > _min_edge_length_m
        x, y = x[keep], y[keep]
        return (x, y) if len(x) >= 3 else None

    for piece in _flatten_polygons(solid):
        oriented_piece = orient(piece, sign=-1.0)
        ring = _ring_to_xy(oriented_piece.exterior)
        if ring is not None:
            contours.append(ring)
        for interior in oriented_piece.interiors:
            ring = _ring_to_xy(interior)
            if ring is not None:
                contours.append(ring)
    return contours


def _smart_connectivity_check(
    self, buffers, fins, full_inlet_tags, outlet_tags, sim_domain_coordinator,
):
    """Monkey-patch replacement for
    ``GmshEntityMarkerCoordinator.convert_disconnected_fluid_surfaces_to_fins``.

    The default glaciercore check has two problems for our DXF + clogging
    geometry:

    1. It only iterates surfaces *not* already in ``fins`` and adds the
       disconnected ones. It can't *remove* a surface that should be fluid
       but was wrongly classified as fin upstream — which is what happens
       to HM27's main fluid surface after gmsh fragments the chip with
       full-width cloggings touching the chip wall.
    2. It marks every disconnected fluid pocket as solid, which is wrong
       for clogging dead-zones (they're physically real fluid).

    This replacement:
    - Walks *all* 2D surfaces, including those currently in ``fins``.
    - A surface whose boundary touches both an inlet line and an outlet
      line is "main fluid" — keep it out of fins (or remove it if upstream
      put it there).
    - A surface that's disconnected (touches neither, or only one) is
      preserved as fluid (clogging dead-zone case).

    Net effect: the giant chip-fluid face — wherever upstream put it — ends
    up in pure_fluid_entities → ``FLOW``. Dead-zones likewise. Real fins
    stay in fins.
    """
    import gmsh
    from glaciercore_meshing.gmsh_operations.boundaries import (
        get_boundary_line_tags,
        get_gmsh_external_line_tags,
    )

    full_inlet_entities = self._get_set_of_entities_from_dim_tags(full_inlet_tags)
    outlet_entities = self._get_set_of_entities_from_dim_tags(outlet_tags)
    boundary_lines = get_boundary_line_tags(domain=sim_domain_coordinator.chip_domain_bounds)
    bm = sim_domain_coordinator.boundary_markers
    inlet_line_tags = list(get_gmsh_external_line_tags(boundary_lines, bm.inlet))
    outlet_line_tags = list(get_gmsh_external_line_tags(boundary_lines, bm.outlet))
    for tag in full_inlet_entities:
        for _, line_tag in gmsh.model.getBoundary([(2, tag)], oriented=False):
            inlet_line_tags.append(abs(line_tag))
    for tag in outlet_entities:
        for _, line_tag in gmsh.model.getBoundary([(2, tag)], oriented=False):
            outlet_line_tags.append(abs(line_tag))
    inlet_set = set(inlet_line_tags)
    outlet_set = set(outlet_line_tags)

    # Re-classify every fin currently in ``fins``: if its boundary touches
    # both inlet and outlet, it isn't really a fin — drop it. This is the
    # rescue path for the giant fluid surface that the upstream fragmenter
    # mis-routes into fin tags when cloggings are present.
    new_fins: list = []
    rescued = 0
    for dim, tag in fins:
        if dim != 2:
            new_fins.append((dim, tag))
            continue
        surface_lines = {
            abs(t) for _, t in gmsh.model.getBoundary([(dim, tag)], oriented=False)
        }
        if (surface_lines & inlet_set) and (surface_lines & outlet_set):
            rescued += 1
            continue  # drop from fins
        new_fins.append((dim, tag))
    if rescued:
        print(
            f"[smart-connectivity] rescued {rescued} mis-tagged fluid surface(s) "
            f"from fin pool back into fluid"
        )

    # Disconnected pure-fluid pockets (the original function's target) are
    # *not* added to fins here — they stay as fluid so the clogging dead
    # zones keep their physical role as stagnant-fluid regions for heat.
    return new_fins


def _mesh_from_solid_contours(
    contours: list[tuple[np.ndarray, np.ndarray]],
    mesh_input,
    output_dir: Path,
    preserve_dead_zones: bool = False,
) -> None:
    """Drive ``generate_mesh_from_contours`` from a pre-cleaned contour list.

    Mirrors the ``script_for_clogging`` path: takes shapely-derived contours
    that are already valid (correct orientation, no duplicate vertices,
    positive area, no self-intersections) and skips glaciercore's raster-era
    ``clean_contours`` step entirely — that step is designed to repair
    ``cv2.findContours`` artefacts (boundary snapping, smoothing, downsampling)
    and is both unnecessary and actively harmful on analytically-clean
    polygons (where the smoothing introduces self-intersections that crash
    downstream).

    ``preserve_dead_zones`` (True when --n-cloggings > 0): wrap the meshing
    call in a monkey-patch that prevents glaciercore from reclassifying
    cloggings' stagnant fluid pockets as copper. See
    ``_smart_connectivity_check`` for the rationale.
    """
    from glaciercore_config.data_handling.geometry import TopOptGeometry
    from glaciercore_meshing.body_fitted.meshing import (
        generate_mesh_from_contours,
        get_mesh_size_coordinator,
    )
    from glaciercore_meshing.gmsh_operations.markers import GmshEntityMarkerCoordinator
    from glaciercore_meshing.gmsh_operations.surfaces import SimDomainCoordinator

    geometry = mesh_input.geometry
    if not isinstance(geometry, TopOptGeometry):
        raise TypeError(
            "settings_mesh.json must declare geometry.type == 'top_opt' for the "
            f"shapely-direct meshing path; got {type(geometry).__name__}."
        )
    boundary_markers = mesh_input.boundary_markers

    sim_domain_coordinator = SimDomainCoordinator(
        chip_width=geometry.dimensions.chip_width,
        chip_length=geometry.dimensions.chip_length,
        boundary_markers=boundary_markers,
    )
    mesh_sizes_coordinator = get_mesh_size_coordinator(
        rescaled_contours=contours,
        geometry=geometry,
        chip_domain_bounds=sim_domain_coordinator.chip_domain_bounds,
    )

    def _run_mesh() -> None:
        generate_mesh_from_contours(
            cleaned_contours=contours,
            geometry=geometry,
            mesh_sizes_coordinator=mesh_sizes_coordinator,
            sim_domain_coordinator=sim_domain_coordinator,
            output_dir=output_dir,
            mesh_file_path=Path("design.msh"),
        )

    if preserve_dead_zones:
        from unittest.mock import patch

        with patch.object(
            GmshEntityMarkerCoordinator,
            "convert_disconnected_fluid_surfaces_to_fins",
            new=_smart_connectivity_check,
        ):
            _run_mesh()
    else:
        _run_mesh()


# --------------------------------------------------------------------------- #
# Driver
# --------------------------------------------------------------------------- #


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Mesh a chip from a DXF design by feeding shapely contours straight to glaciercore."
    )
    parser.add_argument("--dxf", type=Path, required=True, help="[required] DXF design path.")
    parser.add_argument(
        "--settings", type=Path, required=True, help="[required] glaciercore settings_mesh.json path."
    )
    parser.add_argument("--output-dir", type=Path, required=True, help="[required] Output directory.")
    parser.add_argument(
        "--px-per-cm",
        type=int,
        default=500,
        help="[default: 500] PNG resolution (pixels/cm).",
    )
    parser.add_argument(
        "--png-only",
        action="store_true",
        help="[default: off] Stop after writing PNG(s); skip meshing.",
    )
    parser.add_argument(
        "--symmetries",
        choices=["full", "N", "E", "NE"],
        default="full",
        help="[default: full] Mesh only a sub-rectangle of the fluid bbox: full, N (top), E (right), NE (top-right).",
    )
    parser.add_argument(
        "--n-cloggings",
        type=int,
        default=0,
        help="[default: 0] Number of cloggings to inject into the design. "
        "Each clogging is placed in a thinnest-channel region (see --clogging-width-tolerance) "
        "and spans the full channel width.",
    )
    parser.add_argument(
        "--clogging-length",
        type=float,
        default=200e-6,
        help="[default: 200e-6 m] Streamwise length of each clogging (along the local flow direction).",
    )
    parser.add_argument(
        "--clogging-seed",
        type=int,
        default=0,
        help="[default: 0] RNG seed for clogging placement.",
    )
    parser.add_argument(
        "--clogging-width-tolerance",
        type=float,
        default=0.01,
        help="[default: 0.01 = 1%%] Width buffer above the global minimum: channels with "
        "width <= (1 + tol) * global_min_width count as 'thinnest'. 1%% absorbs the ~1 µm "
        "of vertex-discretisation scatter typically seen in DXF designs where channels of "
        "the same nominal width measure as 99.95-100.95 µm. Set lower if your design's "
        "next-thicker class is closer than 1%% to the minimum; set higher to also catch "
        "near-minimum classes.",
    )
    args = parser.parse_args()

    if not args.dxf.exists():
        sys.exit(f"DXF file not found: {args.dxf}")
    if not args.settings.exists():
        sys.exit(f"Settings file not found: {args.settings}")

    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Load mesh settings up front so PNGs can be annotated with the configured
    # inlet/outlet surfaces and edge markers in --png-only mode too. These
    # imports are lightweight (no gmsh/firedrake dependency).
    from glaciercore_config.loader import load_mesh_input
    from glaciercore_drawing.inlet_outlet import draw_inlet_outlet_surfaces_on_picture_from_file

    mesh_input = load_mesh_input(args.settings)
    boundary_markers = mesh_input.boundary_markers
    chip_dimensions = mesh_input.geometry.dimensions.get_chip_dimensions()

    polygons, units_to_m = load_polygons_from_dxf(args.dxf)
    if not polygons:
        sys.exit("No closed polygons found in DXF.")

    roots = find_root_polygons(polygons)
    if len(roots) != 1:
        sys.exit(
            f"Expected exactly one outermost (root) polygon defining the chip outline, "
            f"found {len(roots)}."
        )
    root = roots[0]
    inner_polygons = [p for p in polygons if p is not root]
    if not inner_polygons:
        sys.exit("DXF must contain at least one inner (fluid) polygon inside the chip outline.")

    fluid_bbox = _fluid_bounds(inner_polygons)
    crop_bbox = _apply_symmetries(fluid_bbox, args.symmetries)
    cminx, cminy, cmaxx, cmaxy = crop_bbox
    chip_width_dxf = (cmaxx - cminx) * units_to_m
    chip_length_dxf = (cmaxy - cminy) * units_to_m

    # Cloggings (optional). Sampling shrinks each clogging spanwise by
    # ``_CLOGGING_GAP_M`` so it leaves a 1 µm fluid sliver on each side of
    # the channel — see the constant's docstring for why.
    cloggings_dxf: list[Polygon] = []
    if args.n_cloggings > 0:
        cloggings_dxf, cloggings_meta, clogging_diag = sample_cloggings_in_thinnest_channels(
            root=root,
            inner_polygons=inner_polygons,
            crop_bbox=crop_bbox,
            units_to_m=units_to_m,
            n_cloggings=args.n_cloggings,
            clogging_length_m=args.clogging_length,
            seed=args.clogging_seed,
            width_tolerance=args.clogging_width_tolerance,
            sample_spacing_m=_CLOGGING_SAMPLE_SPACING_M,
        )
        # The thinnest-channels diagnostic PNG is heavy to render and only
        # useful as a sight-check before committing to a mesh — emit it only
        # in --png-only mode.
        if args.png_only:
            diag_png_path = args.output_dir / "thinnest_channels_highlight.png"
            _write_thinnest_channels_diagnostic_png(
                inner_polygons=inner_polygons,
                crop_bbox=crop_bbox,
                units_to_m=units_to_m,
                px_per_cm=args.px_per_cm,
                hits=clogging_diag["hits"],
                min_channel_width_m=clogging_diag["min_channel_width_m"],
                threshold_width_m=clogging_diag["threshold_width_m"],
                output_path=diag_png_path,
            )
            print(f"PNG: {diag_png_path}  (thinnest channels highlighted in red)")
        (args.output_dir / "cloggings.json").write_text(json.dumps({
            "n_cloggings": args.n_cloggings,
            "seed": args.clogging_seed,
            "clogging_length_m": args.clogging_length,
            "min_channel_width_m": clogging_diag["min_channel_width_m"],
            "threshold_width_m": clogging_diag["threshold_width_m"],
            "cloggings": cloggings_meta,
        }, indent=2) + "\n")
        _write_clogging_preview_png(
            inner_polygons_without_cloggings=inner_polygons,
            cloggings_dxf=cloggings_dxf,
            crop_bbox=crop_bbox,
            units_to_m=units_to_m,
            px_per_cm=args.px_per_cm,
            output_path=args.output_dir / "cloggings_preview.png",
        )
        print(
            f"Cloggings: placed {len(cloggings_dxf)} at "
            f"{args.clogging_length * 1e6:.0f} um length, "
            f"channel widths "
            f"{min(m['channel_width_m'] for m in cloggings_meta) * 1e6:.0f}"
            f"-{max(m['channel_width_m'] for m in cloggings_meta) * 1e6:.0f} um."
        )
        # Fold cloggings into the inner-polygons list so the XOR parity-
        # fold turns them solid in the PNG renderer and in the meshing
        # contour build.
        inner_polygons = inner_polygons + cloggings_dxf

    # Render the design (with cloggings folded in, if any) but treat the raw
    # B/W PNGs as scratch — the annotation helper takes a file path, so we
    # write them, annotate, and delete the raw copy. Only the annotated
    # outputs (and the clogging diagnostics, gated above) land in output_dir.
    full_img = _render_image(inner_polygons, fluid_bbox, units_to_m, args.px_per_cm)
    full_path = args.output_dir / "design.png"
    if not cv2.imwrite(str(full_path), full_img):
        sys.exit(f"Failed to write PNG to {full_path}")
    split_path: Path | None = None
    if args.symmetries != "full":
        split_img = _render_image(inner_polygons, crop_bbox, units_to_m, args.px_per_cm)
        split_path = args.output_dir / "split_design.png"
        if not cv2.imwrite(str(split_path), split_img):
            sys.exit(f"Failed to write split PNG to {split_path}")

    # Annotate the PNG whose coordinate frame matches the post-split chip extent
    # (the same frame that ``boundary_markers`` is defined in). For ``full`` that
    # is ``design.png``; otherwise it is ``split_design.png``. Uses the same
    # helper zebraflow uses so colour conventions stay in sync (blue = inlet,
    # red = outlet); ``edge_thickness`` makes the BoundaryLines (LEFT/RIGHT/TOP/
    # BOTTOM) listed under ``inlet`` / ``outlet`` visible as a chip-edge stripe.
    if args.symmetries == "full":
        annotated_src = full_path
        annotated_dst = args.output_dir / "design_inlets_outlets.png"
    else:
        annotated_src = split_path
        annotated_dst = args.output_dir / "split_design_inlets_outlets.png"
    draw_inlet_outlet_surfaces_on_picture_from_file(
        picture_path=annotated_src,
        boundary_markers=boundary_markers,
        chip_dimensions=chip_dimensions,
        output_path=annotated_dst,
        color=True,
        edge_thickness=_IO_EDGE_THICKNESS_M,
    )
    print(f"PNG: {annotated_dst}  (inlet/outlet overlay; blue = inlet, red = outlet)")

    # Mirror the annotated split back out to the full chip frame so the user
    # gets a single picture covering the whole chip with the (symmetric) inlet/
    # outlet pattern overlaid. Mirrors zebraflow's ``full_design_inlets_outlets``
    # output. Skipped when ``--symmetries full`` since the annotated PNG already
    # covers the full chip.
    if args.symmetries != "full":
        from PIL import Image

        full_io_path = args.output_dir / "full_design_inlets_outlets.png"
        with Image.open(annotated_dst) as im:
            quarter = im.copy()
        qw, qh = quarter.size
        if args.symmetries == "N":
            full_io = Image.new(quarter.mode, (qw, 2 * qh))
            full_io.paste(quarter, (0, 0))
            full_io.paste(quarter.transpose(Image.FLIP_TOP_BOTTOM), (0, qh))
        elif args.symmetries == "E":
            full_io = Image.new(quarter.mode, (2 * qw, qh))
            full_io.paste(quarter.transpose(Image.FLIP_LEFT_RIGHT), (0, 0))
            full_io.paste(quarter, (qw, 0))
        else:  # NE
            full_io = Image.new(quarter.mode, (2 * qw, 2 * qh))
            full_io.paste(quarter.transpose(Image.FLIP_LEFT_RIGHT), (0, 0))
            full_io.paste(quarter, (qw, 0))
            full_io.paste(quarter.transpose(Image.ROTATE_180), (0, qh))
            full_io.paste(quarter.transpose(Image.FLIP_TOP_BOTTOM), (qw, qh))
        full_io.save(full_io_path)
        print(f"PNG: {full_io_path}  (full chip, mirrored from split annotation)")

    # Remove the un-annotated B/W renders: they're only needed as scratch input
    # to ``draw_inlet_outlet_surfaces_on_picture_from_file`` (which takes a file
    # path). Final outputs are the annotated *_inlets_outlets.png variants plus,
    # when --n-cloggings > 0, the clogging diagnostic + preview.
    full_path.unlink(missing_ok=True)
    if split_path is not None:
        split_path.unlink(missing_ok=True)

    if args.png_only:
        return

    _validate_chip_dimensions(
        settings_chip_width=mesh_input.geometry.dimensions.chip_width,
        settings_chip_length=mesh_input.geometry.dimensions.chip_length,
        chip_width_dxf=chip_width_dxf,
        chip_length_dxf=chip_length_dxf,
        tol=_DIM_TOLERANCE,
    )

    contours = _build_solid_contours(root, inner_polygons, crop_bbox, units_to_m)
    mesh_dir = args.output_dir / "mesh"
    mesh_dir.mkdir(parents=True, exist_ok=True)
    print(f"Meshing from {len(contours)} shapely-derived contours (no PNG round-trip)...")
    _mesh_from_solid_contours(
        contours,
        mesh_input,
        mesh_dir,
        preserve_dead_zones=(args.n_cloggings > 0),
    )
    print(f"Mesh files written under {mesh_dir}")


if __name__ == "__main__":
    main()
