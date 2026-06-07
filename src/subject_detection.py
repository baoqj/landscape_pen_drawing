from __future__ import annotations

import cv2
import numpy as np

from .models import ImageAnalysisResult, RegionMap
from .segmentation import LABELS
from .utils import clean_mask, normalize01


SEMANTIC_WEIGHTS = {
    "person": 1.75,
    "building": 1.45,
    "road": 0.85,
    "vegetation": 0.95,
    "water": 0.80,
    "mountain": 0.72,
    "ground": 0.65,
    "sky": 0.20,
}


def detect_subject(image: np.ndarray, analysis: ImageAnalysisResult, regions: RegionMap) -> np.ndarray:
    h, w = regions.labels.shape
    saliency = analysis.maps["saliency_map"].astype(np.float32)
    contrast = normalize01(analysis.maps["contrast_map"])
    edge = normalize01(cv2.GaussianBlur((analysis.maps["edge_map"] > 0).astype(np.float32), (0, 0), 5))

    yy, xx = np.mgrid[0:h, 0:w]
    center = np.exp(-(((xx - w * 0.5) ** 2) / (2 * (w * 0.34) ** 2) + ((yy - h * 0.54) ** 2) / (2 * (h * 0.34) ** 2)))
    semantic = np.ones((h, w), dtype=np.float32) * 0.65
    for label, name in regions.label_names.items():
        semantic[regions.labels == label] = SEMANTIC_WEIGHTS.get(name, 0.65)

    score = normalize01(0.38 * saliency + 0.25 * contrast + 0.20 * edge + 0.17 * center.astype(np.float32))
    score = normalize01(score * semantic)
    score[regions.semantic_masks.get("sky", np.zeros_like(score, dtype=bool))] *= 0.15

    threshold = max(0.48, float(np.percentile(score, 82)))
    candidate = score >= threshold
    candidate = clean_mask(candidate, 5, 21)
    chosen = _select_best_component(candidate, score, regions)
    if not chosen.any():
        chosen = score >= float(np.percentile(score, 92))
        chosen = clean_mask(chosen, 3, 13)

    regions.subject_mask = chosen
    regions.main_subject = _main_subject_name(regions, chosen)
    analysis.content["main_subject"] = regions.main_subject
    analysis.maps["subject_mask"] = chosen.astype(np.float32)
    return chosen


def _select_best_component(mask: np.ndarray, score: np.ndarray, regions: RegionMap) -> np.ndarray:
    n, comps, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), 8)
    h, w = mask.shape
    best_idx = 0
    best_score = -1.0
    for idx in range(1, n):
        area = stats[idx, cv2.CC_STAT_AREA]
        if area < max(80, int(h * w * 0.003)) or area > h * w * 0.55:
            continue
        comp = comps == idx
        mean_score = float(np.mean(score[comp]))
        semantic_bonus = 1.0
        for label, name in regions.label_names.items():
            if float(np.mean(regions.labels[comp] == label)) > 0.45:
                semantic_bonus = SEMANTIC_WEIGHTS.get(name, 1.0)
                break
        area_bonus = min(1.25, np.sqrt(area / (h * w)) * 4.0)
        final = mean_score * semantic_bonus * area_bonus
        if final > best_score:
            best_idx = idx
            best_score = final
    return comps == best_idx if best_idx else np.zeros_like(mask, dtype=bool)


def _main_subject_name(regions: RegionMap, mask: np.ndarray) -> str:
    if not mask.any():
        return "unknown"
    counts: list[tuple[int, str]] = []
    for label, name in regions.label_names.items():
        if label == LABELS["unknown"]:
            continue
        counts.append((int(np.sum((regions.labels == label) & mask)), name))
    counts.sort(reverse=True)
    return counts[0][1] if counts and counts[0][0] > 0 else "unknown"

