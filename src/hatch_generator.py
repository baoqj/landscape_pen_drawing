from __future__ import annotations

import math

import cv2
import numpy as np

from .models import DrawingStrategy, RegionMap, Stroke
from .utils import normalize01, to_uint8


def create_hatch_density_map(gray: np.ndarray, regions: RegionMap, strategy: DrawingStrategy) -> np.ndarray:
    gray_f = gray.astype(np.float32) / 255.0 if gray.dtype == np.uint8 else gray.astype(np.float32)
    darkness = np.clip(1.0 - gray_f, 0.0, 1.0)
    contrast_dark = normalize01(cv2.GaussianBlur(darkness, (0, 0), 3))
    density = contrast_dark.copy()

    for label, name in regions.label_names.items():
        mask = regions.labels == label
        if not mask.any():
            continue
        depth = _dominant_depth(mask, regions)
        style = strategy.style_for(name, depth, False)
        density[mask] *= style.hatch_strength

    density[regions.subject_mask] *= 1.25
    if "sky" in regions.semantic_masks:
        density[regions.semantic_masks["sky"]] *= 0.08
    density = cv2.GaussianBlur(np.clip(density, 0, 1), (0, 0), 1.2)
    return np.clip(density, 0, 1).astype(np.float32)


def generate_hatching(
    mask: np.ndarray,
    density_map: np.ndarray,
    angle_deg: float,
    semantic_region: str = "unknown",
    layer: str = "layer_03_hatching",
    min_spacing_px: int = 4,
    max_spacing_px: int = 22,
    min_density: float = 0.08,
    width: float = 0.8,
    opacity: float = 0.62,
    priority: int = 3,
) -> list[Stroke]:
    mask = mask.astype(bool)
    if not mask.any():
        return []
    h, w = mask.shape
    density_mean = float(np.mean(density_map[mask]))
    spacing = int(round(max_spacing_px - density_mean * (max_spacing_px - min_spacing_px)))
    spacing = max(min_spacing_px, min(max_spacing_px, spacing))

    angle = math.radians(angle_deg)
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
        segments = clip_line_to_mask([(float(p1[0]), float(p1[1])), (float(p2[0]), float(p2[1]))], mask)
        for segment in segments:
            if len(segment) < 2:
                continue
            segment_density = _segment_density(segment, density_map)
            if segment_density < min_density:
                continue
            # Shorten very light segments to keep midtones airy.
            if segment_density < 0.22 and _polyline_length(segment) > 60:
                segment = _center_crop(segment, 0.68)
            strokes.append(
                Stroke(
                    id="",
                    layer=layer,
                    semantic_region=semantic_region,
                    stroke_type="hatch",
                    points=segment,
                    width=width,
                    opacity=min(0.95, opacity * (0.65 + segment_density * 0.55)),
                    priority=priority,
                    drawing_order=0,
                )
            )
    return strokes


def generate_cross_hatching(
    mask: np.ndarray,
    density_map: np.ndarray,
    semantic_region: str = "unknown",
    min_spacing_px: int = 4,
    max_spacing_px: int = 22,
) -> list[Stroke]:
    dark_mask = mask.astype(bool) & (density_map > 0.52)
    first = generate_hatching(
        dark_mask,
        density_map,
        45,
        semantic_region=semantic_region,
        min_spacing_px=min_spacing_px,
        max_spacing_px=max_spacing_px,
        min_density=0.28,
        width=0.72,
        opacity=0.55,
        priority=4,
    )
    second = generate_hatching(
        dark_mask,
        density_map,
        -45,
        semantic_region=semantic_region,
        min_spacing_px=max(min_spacing_px + 1, 5),
        max_spacing_px=max_spacing_px + 4,
        min_density=0.38,
        width=0.68,
        opacity=0.48,
        priority=4,
    )
    return first + second


def clip_line_to_mask(line: list[tuple[float, float]], mask: np.ndarray) -> list[list[tuple[float, float]]]:
    if len(line) < 2:
        return []
    h, w = mask.shape[:2]
    (x1, y1), (x2, y2) = line[0], line[-1]
    length = max(2, int(round(math.hypot(x2 - x1, y2 - y1))))
    xs = np.linspace(x1, x2, length)
    ys = np.linspace(y1, y2, length)
    xi = np.rint(xs).astype(int)
    yi = np.rint(ys).astype(int)
    valid = (xi >= 0) & (xi < w) & (yi >= 0) & (yi < h)
    inside = np.zeros(length, dtype=bool)
    inside[valid] = mask[yi[valid], xi[valid]]

    segments: list[list[tuple[float, float]]] = []
    start: int | None = None
    for i, is_inside in enumerate(inside):
        if is_inside and start is None:
            start = i
        elif not is_inside and start is not None:
            if i - start > 5:
                segments.append([(float(xs[start]), float(ys[start])), (float(xs[i - 1]), float(ys[i - 1]))])
            start = None
    if start is not None and length - start > 5:
        segments.append([(float(xs[start]), float(ys[start])), (float(xs[-1]), float(ys[-1]))])
    return segments


def _dominant_depth(mask: np.ndarray, regions: RegionMap) -> str:
    best = ("midground", 0)
    for depth, dmask in regions.depth_masks.items():
        count = int(np.sum(mask & dmask))
        if count > best[1]:
            best = (depth, count)
    return best[0]


def _segment_density(segment: list[tuple[float, float]], density_map: np.ndarray) -> float:
    h, w = density_map.shape[:2]
    (x1, y1), (x2, y2) = segment[0], segment[-1]
    n = max(2, int(round(math.hypot(x2 - x1, y2 - y1))))
    xs = np.clip(np.rint(np.linspace(x1, x2, n)).astype(int), 0, w - 1)
    ys = np.clip(np.rint(np.linspace(y1, y2, n)).astype(int), 0, h - 1)
    return float(np.mean(density_map[ys, xs]))


def _polyline_length(points: list[tuple[float, float]]) -> float:
    if len(points) < 2:
        return 0.0
    return float(sum(math.hypot(x2 - x1, y2 - y1) for (x1, y1), (x2, y2) in zip(points, points[1:])))


def _center_crop(points: list[tuple[float, float]], keep_ratio: float) -> list[tuple[float, float]]:
    if len(points) <= 2:
        (x1, y1), (x2, y2) = points[0], points[-1]
        cx, cy = (x1 + x2) * 0.5, (y1 + y2) * 0.5
        scale = keep_ratio * 0.5
        return [(cx + (x1 - cx) * scale, cy + (y1 - cy) * scale), (cx + (x2 - cx) * scale, cy + (y2 - cy) * scale)]
    n = len(points)
    keep = max(2, int(round(n * keep_ratio)))
    start = max(0, (n - keep) // 2)
    return points[start : start + keep]

