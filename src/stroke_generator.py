from __future__ import annotations

import math

import cv2
import numpy as np

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
        width = style.line_width * (1.15 if is_subject else 0.92)
        width_variation = float(strategy.global_strategy.get("width_variation", 0.0))
        if width_variation > 0:
            width *= 1.0 + ((_stable_hash(cx, cy, length) % 100) / 100.0 - 0.5) * width_variation
        stroke = Stroke(
            id="",
            layer="layer_01_main_contours" if is_subject or semantic in {"building", "person"} else "layer_02_secondary_edges",
            semantic_region=semantic,
            stroke_type="contour" if is_subject else "edge",
            points=points,
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


def generate_building_structure_strokes(image: np.ndarray, building_mask: np.ndarray) -> list[Stroke]:
    if not building_mask.any():
        return []
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(cv2.GaussianBlur(gray, (3, 3), 0), 55, 140)
    edges[~building_mask.astype(bool)] = 0
    h, w = gray.shape
    min_len = max(24, w // 25)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=35, minLineLength=min_len, maxLineGap=10)
    strokes: list[Stroke] = []
    if lines is None:
        return strokes
    kept: list[tuple[int, int, int, int]] = []
    for line in lines[:, 0, :]:
        x1, y1, x2, y2 = [int(v) for v in line]
        length = math.hypot(x2 - x1, y2 - y1)
        if length < min_len:
            continue
        angle = abs(math.degrees(math.atan2(y2 - y1, x2 - x1)))
        rectilinear = min(angle, abs(angle - 90), abs(angle - 180)) < 15
        if not rectilinear and length < min_len * 1.8:
            continue
        if _is_duplicate_line((x1, y1, x2, y2), kept):
            continue
        kept.append((x1, y1, x2, y2))
        strokes.append(
            Stroke(
                id="",
                layer="layer_01_main_contours",
                semantic_region="building",
                stroke_type="structure_line",
                points=[(float(x1), float(y1)), (float(x2), float(y2))],
                width=1.05,
                opacity=0.86,
                priority=1,
                drawing_order=0,
            )
        )
        if len(strokes) >= 240:
            break
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
