from __future__ import annotations

import cv2
import numpy as np

from .models import DrawingStrategy, RegionMap
from .utils import normalize01, to_uint8


def extract_multiscale_edges(gray: np.ndarray) -> np.ndarray:
    if gray.dtype != np.uint8:
        gray_u8 = to_uint8(gray)
    else:
        gray_u8 = gray
    denoised = cv2.bilateralFilter(gray_u8, 7, 45, 45)
    edges_1 = cv2.Canny(denoised, 45, 110)
    edges_2 = cv2.Canny(cv2.GaussianBlur(denoised, (0, 0), 1.5), 35, 95)
    edges_3 = cv2.Canny(cv2.GaussianBlur(denoised, (0, 0), 3.0), 25, 75)
    combined = cv2.bitwise_or(edges_1, cv2.bitwise_or(edges_2, edges_3))
    return cv2.morphologyEx(combined, cv2.MORPH_CLOSE, np.ones((2, 2), np.uint8))


def extract_xdog_edges(gray: np.ndarray) -> np.ndarray:
    gray_f = gray.astype(np.float32) / 255.0 if gray.dtype == np.uint8 else gray.astype(np.float32)
    g1 = cv2.GaussianBlur(gray_f, (0, 0), 0.8)
    g2 = cv2.GaussianBlur(gray_f, (0, 0), 2.4)
    dog = g1 - 0.96 * g2
    xdog = 1.0 + np.tanh(18.0 * (dog - 0.03))
    return (normalize01(xdog) < 0.48).astype(np.uint8) * 255


def enhance_edges_by_region(edges: np.ndarray, regions: RegionMap, strategy: DrawingStrategy) -> np.ndarray:
    edges_f = (edges > 0).astype(np.float32)
    weighted = np.zeros_like(edges_f)
    entourage_keep = float(strategy.global_strategy.get("entourage_edge_keep", 1.0))
    building_boost = float(strategy.global_strategy.get("architectural_structure_boost", 1.0))
    for label, name in regions.label_names.items():
        mask = regions.labels == label
        if not mask.any():
            continue
        # Use depth-specific style by dominant vertical location.
        ys = np.where(mask)[0]
        depth = "midground"
        if ys.size:
            y_mean = float(np.mean(ys) / max(edges.shape[0] - 1, 1))
            depth = "foreground" if y_mean > 0.62 else "background" if y_mean < 0.38 else "midground"
        style = strategy.style_for(name, depth, False)
        multiplier = style.edge_strength
        if name == "building":
            multiplier *= building_boost
        elif name in {"vegetation", "mountain", "ground", "road", "water"}:
            multiplier *= max(0.18, entourage_keep)
        weighted[mask] = edges_f[mask] * multiplier

    weighted[regions.subject_mask] *= 1.35
    sky = regions.semantic_masks.get("sky")
    if sky is not None:
        weighted[sky] *= 0.08
    vegetation = regions.semantic_masks.get("vegetation")
    if vegetation is not None:
        # Plant texture is handled by dedicated loose strokes, so reduce fragmented Canny noise.
        weighted[vegetation] *= 0.45

    thresh = np.percentile(weighted[weighted > 0], 45) if np.any(weighted > 0) else 1.0
    enhanced = (weighted >= max(0.25, thresh)).astype(np.uint8) * 255
    return cv2.morphologyEx(enhanced, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
