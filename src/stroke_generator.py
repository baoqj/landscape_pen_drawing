from __future__ import annotations

import math

import cv2
import numpy as np

from .hatch_generator import clip_line_to_mask
from .models import DrawingStrategy, RegionMap, Stroke


def edges_to_strokes(edges: np.ndarray, regions: RegionMap, strategy: DrawingStrategy) -> list[Stroke]:
    edge_u8 = (edges > 0).astype(np.uint8) * 255
    contours, _ = cv2.findContours(edge_u8, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
    strokes: list[Stroke] = []
    h, w = edge_u8.shape
    for contour in contours:
        length = float(cv2.arcLength(contour, False))
        if length < 5:
            continue
        pts = contour[:, 0, :].astype(np.float32)
        cx, cy = float(np.mean(pts[:, 0])), float(np.mean(pts[:, 1]))
        semantic = regions.semantic_at(cx, cy)
        depth = regions.depth_at(cx, cy)
        is_subject = bool(regions.subject_mask[int(np.clip(round(cy), 0, h - 1)), int(np.clip(round(cx), 0, w - 1))])
        style = strategy.style_for(semantic, depth, is_subject)
        if style.suppress_edges or length < style.min_stroke_length:
            continue
        if semantic == "vegetation" and not is_subject and _stable_hash(cx, cy, length) % 100 > 55:
            continue
        if depth == "background" and not is_subject and _stable_hash(cx, cy, length) % 100 > 44:
            continue

        eps = max(0.6, style.simplify_tolerance)
        approx = cv2.approxPolyDP(contour, eps, False)[:, 0, :].astype(np.float32)
        if approx.shape[0] < 2:
            continue
        points = [(float(x), float(y)) for x, y in approx]
        line_type = "straight"
        stylized_segments = [points]
        if semantic != "building":
            line_type = str(strategy.global_strategy.get("entourage_line_type", "loose_curve"))
            stylized_segments = _stylize_polyline(points, line_type, style.jitter_px * 0.45, _stable_hash(cx, cy, length))
        width = style.line_width * (1.15 if is_subject else 0.92)
        width_variation = float(strategy.global_strategy.get("width_variation", 0.0))
        if width_variation > 0:
            width *= 1.0 + ((_stable_hash(cx, cy, length) % 100) / 100.0 - 0.5) * width_variation
        for segment_points in stylized_segments:
            if len(segment_points) < 2 or _polyline_length(segment_points) < 4:
                continue
            stroke = Stroke(
                id="",
                layer="layer_01_main_contours" if is_subject or semantic in {"building", "person"} else "layer_02_secondary_edges",
                semantic_region=semantic,
                stroke_type=("contour" if is_subject else "edge") + ("" if line_type == "straight" else f"_{line_type}"),
                points=segment_points,
                width=max(0.1, width),
                opacity=style.opacity,
                priority=1 if is_subject else 2,
                drawing_order=0,
            )
            strokes.append(add_hand_drawn_jitter(stroke, style.jitter_px if semantic != "building" else min(style.jitter_px, 0.25)))
    return strokes


def generate_vegetation_strokes(mask: np.ndarray, gray: np.ndarray, density: float = 0.8, seed: int = 42) -> list[Stroke]:
    mask = mask.astype(bool)
    if not mask.any():
        return []
    rng = np.random.default_rng(seed)
    h, w = mask.shape
    ys, xs = np.where(mask)
    area = len(xs)
    count = int(np.clip(area / 420 * density, 20, 1800))
    gray_f = gray.astype(np.float32) / 255.0 if gray.dtype == np.uint8 else gray
    darkness = 1.0 - gray_f
    weights = darkness[ys, xs] + 0.08
    weights = weights / np.sum(weights)

    strokes: list[Stroke] = []
    for _ in range(count):
        idx = int(rng.choice(len(xs), p=weights))
        x, y = float(xs[idx]), float(ys[idx])
        length = float(rng.uniform(4, 16) * (1.2 if darkness[int(y), int(x)] > 0.55 else 0.8))
        angle = float(rng.uniform(0, 2 * math.pi))
        bend = float(rng.normal(0, 0.55))
        p0 = (x - math.cos(angle) * length * 0.5, y - math.sin(angle) * length * 0.5)
        p1 = (x + math.cos(angle + bend * 0.35) * length * 0.15, y + math.sin(angle + bend * 0.35) * length * 0.15)
        p2 = (x + math.cos(angle + bend) * length * 0.55, y + math.sin(angle + bend) * length * 0.55)
        pts = [p0, p1, p2]
        pts = _clip_points_to_canvas(pts, w, h)
        if _points_inside_fraction(pts, mask) < 0.55:
            continue
        strokes.append(
            Stroke(
                id="",
                layer="layer_04_texture_strokes",
                semantic_region="vegetation",
                stroke_type="loose_leaf_mass",
                points=pts,
                width=float(rng.uniform(0.55, 0.95)),
                opacity=float(rng.uniform(0.35, 0.66)),
                priority=4,
                drawing_order=0,
            )
        )
    return strokes


def generate_water_strokes(mask: np.ndarray, gray: np.ndarray, density: float = 0.8) -> list[Stroke]:
    mask = mask.astype(bool)
    if not mask.any():
        return []
    h, w = mask.shape
    gray_f = gray.astype(np.float32) / 255.0 if gray.dtype == np.uint8 else gray
    strokes: list[Stroke] = []
    ys = np.where(mask)[0]
    y_min, y_max = int(np.min(ys)), int(np.max(ys))
    step = max(5, int(round(18 - 10 * density)))
    for y in range(y_min, y_max + 1, step):
        row = mask[y]
        segments = _row_segments(row)
        for x1, x2 in segments:
            if x2 - x1 < 12:
                continue
            segment_darkness = float(np.mean(1.0 - gray_f[y, x1:x2]))
            if segment_darkness < 0.12:
                continue
            period = max(24, int(80 - segment_darkness * 55))
            for x in range(x1, x2, period):
                length = min(x2 - x, int(18 + segment_darkness * 55))
                if length < 8:
                    continue
                yy = y + math.sin(x * 0.07) * 1.1
                strokes.append(
                    Stroke(
                        id="",
                        layer="layer_04_texture_strokes",
                        semantic_region="water",
                        stroke_type="water_ripple",
                        points=[(float(x), float(yy)), (float(x + length * 0.45), float(yy + 0.7)), (float(x + length), float(yy))],
                        width=0.72,
                        opacity=0.42 + segment_darkness * 0.25,
                        priority=4,
                        drawing_order=0,
                    )
                )
    return strokes


def generate_building_structure_strokes(image: np.ndarray, building_mask: np.ndarray, architectural_style: dict | None = None) -> list[Stroke]:
    if not building_mask.any():
        return []
    architectural_style = architectural_style or {}
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(cv2.GaussianBlur(gray, (3, 3), 0), 55, 140)
    edges[~building_mask.astype(bool)] = 0
    h, w = gray.shape
    min_len = max(24, w // 25)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=35, minLineLength=min_len, maxLineGap=10)
    strokes: list[Stroke] = []
    line_extend = float(architectural_style.get("line_extend_px", 10.0))
    angle_tolerance = float(architectural_style.get("rectilinear_angle_tolerance", 18.0))
    line_width = float(architectural_style.get("structure_line_width", 1.05))
    opacity = float(architectural_style.get("structure_line_opacity", 0.86))
    max_lines = int(architectural_style.get("max_structure_lines", 320))
    structure_line_type = str(architectural_style.get("structure_line_type", "straight"))
    curve_px = float(architectural_style.get("line_curvature_px", 3.0))
    wobble_px = float(architectural_style.get("sketch_wobble_px", 1.0))
    gap_ratio = float(architectural_style.get("broken_gap_ratio", 0.22))
    kept: list[tuple[int, int, int, int]] = []
    if lines is not None:
        sorted_lines = sorted(lines[:, 0, :], key=lambda ln: math.hypot(ln[2] - ln[0], ln[3] - ln[1]), reverse=True)
        for line in sorted_lines:
            x1, y1, x2, y2 = [int(v) for v in line]
            length = math.hypot(x2 - x1, y2 - y1)
            if length < min_len:
                continue
            angle = abs(math.degrees(math.atan2(y2 - y1, x2 - x1)))
            rectilinear = min(angle, abs(angle - 90), abs(angle - 180)) < angle_tolerance
            if not rectilinear and length < min_len * 1.8:
                continue
            if _is_duplicate_line((x1, y1, x2, y2), kept):
                continue
            kept.append((x1, y1, x2, y2))
            extended = _extend_segment((x1, y1), (x2, y2), line_extend if rectilinear else line_extend * 0.55, w, h)
            styled_segments = _stylize_polyline(
                extended,
                structure_line_type,
                curve_px if "curve" in structure_line_type else wobble_px,
                _stable_hash(x1, y1, x2, y2),
                gap_ratio=gap_ratio,
            )
            for styled in styled_segments:
                strokes.append(
                    Stroke(
                        id="",
                        layer="layer_01_main_contours",
                        semantic_region="building",
                        stroke_type=("structure_line_extended" if rectilinear else "structure_line") + f"_{structure_line_type}",
                        points=styled,
                        width=line_width * (1.06 if rectilinear else 0.86),
                        opacity=opacity,
                        priority=1,
                        drawing_order=0,
                    )
                )
            if len(strokes) >= max_lines:
                break
    if bool(architectural_style.get("draw_mass_boxes", True)):
        strokes.extend(_generate_building_mass_box_strokes(building_mask.astype(bool), architectural_style))
    return strokes


def generate_architectural_plane_hatching(
    building_mask: np.ndarray,
    gray: np.ndarray,
    architectural_style: dict | None = None,
) -> list[Stroke]:
    architectural_style = architectural_style or {}
    if not bool(architectural_style.get("draw_facade_hatching", True)) or not building_mask.any():
        return []
    mask = building_mask.astype(bool)
    h, w = mask.shape
    gray_f = gray.astype(np.float32) / 255.0 if gray.dtype == np.uint8 else gray.astype(np.float32)
    darkness = 1.0 - gray_f
    spacing = max(4, int(architectural_style.get("facade_hatch_spacing_px", 16)))
    angle = math.radians(float(architectural_style.get("facade_hatch_angle_deg", 45.0)))
    opacity = float(architectural_style.get("facade_hatch_opacity", 0.36))
    max_lines = int(architectural_style.get("max_facade_hatch_lines", 800))
    hatch_line_type = str(architectural_style.get("facade_hatch_line_type", "straight"))
    curve_px = float(architectural_style.get("line_curvature_px", 3.0))
    wobble_px = float(architectural_style.get("sketch_wobble_px", 1.0))
    gap_ratio = float(architectural_style.get("broken_gap_ratio", 0.22))

    d = np.array([math.cos(angle), math.sin(angle)], dtype=np.float32)
    n = np.array([-math.sin(angle), math.cos(angle)], dtype=np.float32)
    diag = float(math.hypot(w, h) + 4)
    corners = np.array([[0, 0], [w - 1, 0], [0, h - 1], [w - 1, h - 1]], dtype=np.float32)
    projections = corners @ n
    start = int(math.floor(float(projections.min()) - spacing))
    end = int(math.ceil(float(projections.max()) + spacing))

    strokes: list[Stroke] = []
    for b in range(start, end + 1, spacing):
        center = n * b
        p1 = center - d * diag
        p2 = center + d * diag
        for segment in clip_line_to_mask([(float(p1[0]), float(p1[1])), (float(p2[0]), float(p2[1]))], mask):
            if len(segment) < 2 or _polyline_length(segment) < 16:
                continue
            segment_darkness = _segment_darkness(segment, darkness)
            if segment_darkness < 0.16:
                continue
            styled_segments = _stylize_polyline(
                segment,
                hatch_line_type,
                curve_px if "curve" in hatch_line_type else wobble_px,
                _stable_hash(segment[0][0], segment[0][1], segment[-1][0], segment[-1][1]),
                gap_ratio=gap_ratio,
            )
            for styled in styled_segments:
                strokes.append(
                    Stroke(
                        id="",
                        layer="layer_03_hatching",
                        semantic_region="building",
                        stroke_type=f"facade_plane_hatch_{hatch_line_type}",
                        points=styled,
                        width=0.58,
                        opacity=min(0.72, opacity * (0.55 + segment_darkness)),
                        priority=3,
                        drawing_order=0,
                    )
                )
            if len(strokes) >= max_lines:
                return strokes
    return strokes


def add_hand_drawn_jitter(stroke: Stroke, amount: float) -> Stroke:
    if amount <= 0 or len(stroke.points) < 2:
        return stroke
    rng = np.random.default_rng(_stable_hash(len(stroke.points), stroke.points[0][0], stroke.points[-1][1]))
    jittered: list[tuple[float, float]] = []
    for i, (x, y) in enumerate(stroke.points):
        scale = 0.35 if i in {0, len(stroke.points) - 1} else 1.0
        jittered.append((float(x + rng.normal(0, amount * scale)), float(y + rng.normal(0, amount * scale))))
    stroke.points = jittered
    return stroke


def simplify_stroke(stroke: Stroke, tolerance: float) -> Stroke:
    if len(stroke.points) <= 2:
        return stroke
    contour = np.array(stroke.points, dtype=np.float32).reshape((-1, 1, 2))
    approx = cv2.approxPolyDP(contour, tolerance, False)[:, 0, :]
    stroke.points = [(float(x), float(y)) for x, y in approx]
    return stroke


def sort_strokes_for_plotter(strokes: list[Stroke]) -> list[Stroke]:
    layer_order = {
        "layer_01_main_contours": 1,
        "layer_02_secondary_edges": 2,
        "layer_03_hatching": 3,
        "layer_04_texture_strokes": 4,
        "layer_05_accents": 5,
    }
    sorted_strokes = sorted(
        strokes,
        key=lambda s: (
            layer_order.get(s.layer, 99),
            s.priority,
            s.semantic_region,
            s.points[0][1] if s.points else 0,
            s.points[0][0] if s.points else 0,
        ),
    )
    for i, stroke in enumerate(sorted_strokes):
        stroke.id = f"stroke_{i:06d}"
        stroke.drawing_order = i
    return sorted_strokes


def _row_segments(row: np.ndarray) -> list[tuple[int, int]]:
    segments: list[tuple[int, int]] = []
    start: int | None = None
    for i, val in enumerate(row):
        if val and start is None:
            start = i
        elif not val and start is not None:
            segments.append((start, i - 1))
            start = None
    if start is not None:
        segments.append((start, len(row) - 1))
    return segments


def _points_inside_fraction(points: list[tuple[float, float]], mask: np.ndarray) -> float:
    h, w = mask.shape
    inside = 0
    for x, y in points:
        xi = int(np.clip(round(x), 0, w - 1))
        yi = int(np.clip(round(y), 0, h - 1))
        inside += int(mask[yi, xi])
    return inside / max(len(points), 1)


def _clip_points_to_canvas(points: list[tuple[float, float]], w: int, h: int) -> list[tuple[float, float]]:
    return [(float(np.clip(x, 0, w - 1)), float(np.clip(y, 0, h - 1))) for x, y in points]


def _extend_segment(
    p1: tuple[float, float],
    p2: tuple[float, float],
    amount: float,
    width: int,
    height: int,
) -> list[tuple[float, float]]:
    x1, y1 = p1
    x2, y2 = p2
    length = math.hypot(x2 - x1, y2 - y1)
    if length < 1:
        return [(x1, y1), (x2, y2)]
    ux, uy = (x2 - x1) / length, (y2 - y1) / length
    return [
        (float(np.clip(x1 - ux * amount, 0, width - 1)), float(np.clip(y1 - uy * amount, 0, height - 1))),
        (float(np.clip(x2 + ux * amount, 0, width - 1)), float(np.clip(y2 + uy * amount, 0, height - 1))),
    ]


def _generate_building_mass_box_strokes(mask: np.ndarray, architectural_style: dict) -> list[Stroke]:
    h, w = mask.shape
    min_area = max(240, int(h * w * 0.006))
    n, comps, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), 8)
    components = sorted(range(1, n), key=lambda idx: stats[idx, cv2.CC_STAT_AREA], reverse=True)[:8]
    extend = float(architectural_style.get("line_extend_px", 10.0))
    tick = float(architectural_style.get("corner_tick_px", 8.0))
    opacity = float(architectural_style.get("structure_line_opacity", 0.86)) * 0.72
    line_width = float(architectural_style.get("structure_line_width", 1.05)) * 0.86
    structure_line_type = str(architectural_style.get("structure_line_type", "straight"))
    curve_px = float(architectural_style.get("line_curvature_px", 3.0))
    wobble_px = float(architectural_style.get("sketch_wobble_px", 1.0))
    gap_ratio = float(architectural_style.get("broken_gap_ratio", 0.22))
    strokes: list[Stroke] = []
    for idx in components:
        x, y, ww, hh, area = stats[idx]
        if area < min_area or ww < 24 or hh < 24:
            continue
        left, right, top, bottom = float(x), float(x + ww - 1), float(y), float(y + hh - 1)
        box_lines = [
            ((left, top), (right, top)),
            ((right, top), (right, bottom)),
            ((right, bottom), (left, bottom)),
            ((left, bottom), (left, top)),
        ]
        for p1, p2 in box_lines:
            line_points = _extend_segment(p1, p2, extend * 0.45, w, h)
            styled_segments = _stylize_polyline(
                line_points,
                structure_line_type,
                curve_px if "curve" in structure_line_type else wobble_px,
                _stable_hash(p1[0], p1[1], p2[0], p2[1]),
                gap_ratio=gap_ratio,
            )
            for styled in styled_segments:
                strokes.append(
                    Stroke(
                        id="",
                        layer="layer_01_main_contours",
                        semantic_region="building",
                        stroke_type=f"mass_edge_extension_{structure_line_type}",
                        points=styled,
                        width=line_width,
                        opacity=opacity,
                        priority=1,
                        drawing_order=0,
                    )
                )
        if bool(architectural_style.get("draw_corner_extensions", True)):
            corners = [(left, top), (right, top), (right, bottom), (left, bottom)]
            for cx, cy in corners:
                strokes.extend(
                    [
                        Stroke(
                            id="",
                            layer="layer_05_accents",
                            semantic_region="building",
                            stroke_type="corner_tick",
                            points=[(float(np.clip(cx - tick, 0, w - 1)), cy), (float(np.clip(cx + tick, 0, w - 1)), cy)],
                            width=line_width * 0.82,
                            opacity=min(0.88, opacity * 1.08),
                            priority=5,
                            drawing_order=0,
                        ),
                        Stroke(
                            id="",
                            layer="layer_05_accents",
                            semantic_region="building",
                            stroke_type="corner_tick",
                            points=[(cx, float(np.clip(cy - tick, 0, h - 1))), (cx, float(np.clip(cy + tick, 0, h - 1)))],
                            width=line_width * 0.82,
                            opacity=min(0.88, opacity * 1.08),
                            priority=5,
                            drawing_order=0,
                        ),
                    ]
                )
    return strokes


def _polyline_length(points: list[tuple[float, float]]) -> float:
    if len(points) < 2:
        return 0.0
    return float(sum(math.hypot(x2 - x1, y2 - y1) for (x1, y1), (x2, y2) in zip(points, points[1:])))


def _segment_darkness(segment: list[tuple[float, float]], darkness: np.ndarray) -> float:
    h, w = darkness.shape
    (x1, y1), (x2, y2) = segment[0], segment[-1]
    n = max(2, int(round(math.hypot(x2 - x1, y2 - y1))))
    xs = np.clip(np.rint(np.linspace(x1, x2, n)).astype(int), 0, w - 1)
    ys = np.clip(np.rint(np.linspace(y1, y2, n)).astype(int), 0, h - 1)
    return float(np.mean(darkness[ys, xs]))


def _stylize_polyline(
    points: list[tuple[float, float]],
    line_type: str,
    amount: float,
    seed: int,
    gap_ratio: float = 0.22,
) -> list[list[tuple[float, float]]]:
    if len(points) < 2:
        return [points]
    normalized = line_type.lower().strip()
    if normalized == "straight":
        return [points]
    if normalized in {"slight_curve", "curve", "curved", "loose_curve"}:
        strength = amount * (1.45 if normalized == "loose_curve" else 1.0)
        return [_curve_polyline(points, strength, seed)]
    if normalized == "sketch":
        return [_sketch_polyline(points, amount, seed)]
    if normalized == "broken":
        return _break_polyline(points, gap_ratio)
    if normalized == "broken_curve":
        curved = _curve_polyline(points, amount, seed)
        return _break_polyline(curved, gap_ratio)
    return [points]


def _curve_polyline(points: list[tuple[float, float]], amount: float, seed: int) -> list[tuple[float, float]]:
    if len(points) < 2 or amount <= 0:
        return points
    rng = np.random.default_rng(seed)
    curved: list[tuple[float, float]] = [points[0]]
    for idx, (p1, p2) in enumerate(zip(points, points[1:])):
        x1, y1 = p1
        x2, y2 = p2
        length = math.hypot(x2 - x1, y2 - y1)
        if length < 4:
            curved.append(p2)
            continue
        nx, ny = -(y2 - y1) / length, (x2 - x1) / length
        bow = float(rng.normal(0, amount)) * (0.55 + min(length / 80.0, 1.2))
        mx = (x1 + x2) * 0.5 + nx * bow
        my = (y1 + y2) * 0.5 + ny * bow
        curved.append((float(mx), float(my)))
        curved.append(p2)
    return curved


def _sketch_polyline(points: list[tuple[float, float]], amount: float, seed: int) -> list[tuple[float, float]]:
    if len(points) < 2 or amount <= 0:
        return points
    rng = np.random.default_rng(seed)
    out: list[tuple[float, float]] = [points[0]]
    for p1, p2 in zip(points, points[1:]):
        x1, y1 = p1
        x2, y2 = p2
        length = math.hypot(x2 - x1, y2 - y1)
        steps = max(2, min(9, int(length // 18) + 2))
        for step in range(1, steps + 1):
            t = step / steps
            x = x1 + (x2 - x1) * t + rng.normal(0, amount)
            y = y1 + (y2 - y1) * t + rng.normal(0, amount)
            out.append((float(x), float(y)))
    return out


def _break_polyline(points: list[tuple[float, float]], gap_ratio: float) -> list[list[tuple[float, float]]]:
    if len(points) < 2:
        return [points]
    ratio = float(np.clip(gap_ratio, 0.05, 0.65))
    segments: list[list[tuple[float, float]]] = []
    for p1, p2 in zip(points, points[1:]):
        x1, y1 = p1
        x2, y2 = p2
        length = math.hypot(x2 - x1, y2 - y1)
        if length < 12:
            segments.append([p1, p2])
            continue
        keep = (1.0 - ratio) * 0.5
        segments.append([(x1, y1), (x1 + (x2 - x1) * keep, y1 + (y2 - y1) * keep)])
        segments.append([(x2 - (x2 - x1) * keep, y2 - (y2 - y1) * keep), (x2, y2)])
    return [segment for segment in segments if _polyline_length(segment) >= 4]


def _is_duplicate_line(line: tuple[int, int, int, int], kept: list[tuple[int, int, int, int]]) -> bool:
    x1, y1, x2, y2 = line
    for a1, b1, a2, b2 in kept[-60:]:
        if min(math.hypot(x1 - a1, y1 - b1) + math.hypot(x2 - a2, y2 - b2), math.hypot(x1 - a2, y1 - b2) + math.hypot(x2 - a1, y2 - b1)) < 18:
            return True
    return False


def _stable_hash(*values: float) -> int:
    acc = 2166136261
    for value in values:
        iv = int(round(float(value) * 1000))
        acc ^= iv & 0xFFFFFFFF
        acc = (acc * 16777619) & 0xFFFFFFFF
    return acc
