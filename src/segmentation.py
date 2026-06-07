from __future__ import annotations

import cv2
import numpy as np

from .models import ImageAnalysisResult, RegionMap
from .utils import clean_mask, local_std, normalize01


LABELS = {
    "unknown": 0,
    "sky": 1,
    "vegetation": 2,
    "water": 3,
    "building": 4,
    "road": 5,
    "mountain": 6,
    "person": 7,
    "ground": 8,
}


def segment_regions(image: np.ndarray, analysis: ImageAnalysisResult) -> RegionMap:
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    edges = analysis.maps.get("edge_map")
    if edges is None:
        edges = cv2.Canny(gray, 70, 160)

    sky = detect_sky_mask(image)
    vegetation = detect_vegetation_mask(image)
    water = detect_water_mask(image, sky | vegetation)
    building = detect_building_candidates(image, edges) & ~sky & ~vegetation & ~water
    road = detect_road_mask(image, sky | vegetation | water | building)
    person = detect_person_candidates(image, edges) & ~(sky | water)
    mountain = detect_mountain_background(image, sky | vegetation | water | building | road | person)

    h, w = gray.shape
    labels = np.zeros((h, w), dtype=np.uint8)
    for name, mask in [
        ("sky", sky),
        ("mountain", mountain),
        ("water", water),
        ("vegetation", vegetation),
        ("road", road),
        ("building", building),
        ("person", person),
    ]:
        labels[mask] = LABELS[name]
    labels[labels == 0] = LABELS["ground"]

    semantic_masks = {
        name: labels == label
        for name, label in LABELS.items()
        if name != "unknown"
    }
    depth_masks = estimate_depth_layers(image, labels)
    region_map = RegionMap(
        labels=labels,
        label_names={v: k for k, v in LABELS.items()},
        semantic_masks=semantic_masks,
        depth_masks=depth_masks,
        subject_mask=np.zeros((h, w), dtype=bool),
        main_subject="unknown",
    )

    detected = [
        name
        for name, mask in semantic_masks.items()
        if name not in {"unknown"} and float(np.mean(mask)) > 0.005
    ]
    analysis.content["detected_regions"] = detected
    analysis.content["foreground"] = _regions_in_depth(semantic_masks, depth_masks["foreground"])
    analysis.content["midground"] = _regions_in_depth(semantic_masks, depth_masks["midground"])
    analysis.content["background"] = _regions_in_depth(semantic_masks, depth_masks["background"])
    return region_map


def classify_region(region_features: dict) -> str:
    if region_features.get("sky_score", 0) > 0.6:
        return "sky"
    if region_features.get("green_ratio", 0) > 0.35:
        return "vegetation"
    if region_features.get("line_density", 0) > 0.2 and region_features.get("rectilinear_score", 0) > 0.45:
        return "building"
    if region_features.get("blue_ratio", 0) > 0.25 and region_features.get("horizontal_texture", 0) > 0.45:
        return "water"
    if region_features.get("lower_position", 0) > 0.65 and region_features.get("saturation", 1) < 0.35:
        return "road"
    return "ground"


def detect_sky_mask(image: np.ndarray) -> np.ndarray:
    h, w = image.shape[:2]
    hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
    hue, sat, val = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, 80, 170)
    edge_low = cv2.GaussianBlur((edges > 0).astype(np.float32), (0, 0), 5) < 0.08
    y = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    upper_prior = y < 0.68
    blue = (hue > 85) & (hue < 130) & (sat > 25) & (val > 75)
    pale = (sat < 55) & (val > 135)
    candidate = (blue | pale) & upper_prior & edge_low

    # Keep only components that touch the top or are in the upper band.
    n, comps, stats, _ = cv2.connectedComponentsWithStats(candidate.astype(np.uint8), 8)
    keep = np.zeros_like(candidate, dtype=bool)
    min_area = max(100, int(0.003 * h * w))
    for idx in range(1, n):
        x, y0, ww, hh, area = stats[idx]
        touches_top = y0 < int(0.08 * h)
        upper_large = y0 < int(0.35 * h) and area > min_area
        if area > min_area and (touches_top or upper_large):
            keep[comps == idx] = True
    return clean_mask(keep, 5, 17)


def detect_vegetation_mask(image: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
    hue, sat, val = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
    green = (hue >= 30) & (hue <= 95) & (sat > 35) & (val > 35)
    yellow_green = (hue >= 20) & (hue < 30) & (sat > 55) & (val > 45)
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    texture = normalize01(local_std(gray, 17))
    candidate = (green | yellow_green) & (texture > 0.04)
    return clean_mask(candidate, 3, 9)


def detect_water_mask(image: np.ndarray, exclude: np.ndarray) -> np.ndarray:
    h, _ = image.shape[:2]
    hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
    hue, sat, val = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY).astype(np.float32)
    gy = np.abs(cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3))
    gx = np.abs(cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3))
    horizontal_texture = normalize01(gx - gy)
    y = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    blue_gray = ((hue > 80) & (hue < 125) & (sat > 20)) | ((sat < 55) & (val > 65) & (val < 215))
    candidate = blue_gray & (horizontal_texture > 0.35) & (y > 0.25) & ~exclude
    return clean_mask(candidate, 5, 19)


def detect_building_candidates(image: np.ndarray, edges: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
    sat = hsv[:, :, 1]
    h, w = gray.shape
    line_canvas = np.zeros((h, w), dtype=np.uint8)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=max(30, w // 40), minLineLength=max(24, w // 18), maxLineGap=8)
    if lines is not None:
        for line in lines[:, 0, :]:
            x1, y1, x2, y2 = [int(v) for v in line]
            angle = abs(np.degrees(np.arctan2(y2 - y1, x2 - x1)))
            rectilinear = min(angle, abs(angle - 90), abs(angle - 180)) < 18
            if rectilinear:
                cv2.line(line_canvas, (x1, y1), (x2, y2), 255, 7)
    stable_color = sat < 130
    edge_dilated = cv2.dilate(line_canvas, cv2.getStructuringElement(cv2.MORPH_RECT, (17, 17)), iterations=2) > 0
    candidate = edge_dilated & stable_color
    return clean_mask(candidate, 5, 21)


def detect_road_mask(image: np.ndarray, exclude: np.ndarray) -> np.ndarray:
    h, _ = image.shape[:2]
    hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
    hue, sat, val = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
    y = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    low_sat = sat < 85
    earth = ((hue < 25) | (hue > 160)) & (sat < 120) & (val > 45)
    candidate = (low_sat | earth) & (y > 0.45) & ~exclude
    return clean_mask(candidate, 7, 25)


def detect_person_candidates(image: np.ndarray, edges: np.ndarray) -> np.ndarray:
    h, w = edges.shape[:2]
    dense = cv2.dilate(edges, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 9)), iterations=1)
    n, comps, stats, _ = cv2.connectedComponentsWithStats((dense > 0).astype(np.uint8), 8)
    mask = np.zeros_like(edges, dtype=bool)
    for idx in range(1, n):
        x, y, ww, hh, area = stats[idx]
        if area < max(12, h * w * 0.00003) or area > h * w * 0.015:
            continue
        aspect = hh / max(ww, 1)
        if 1.6 <= aspect <= 5.5 and hh < h * 0.45 and ww < w * 0.14 and y > h * 0.25:
            mask[comps == idx] = True
    return clean_mask(mask, 1, 5)


def detect_mountain_background(image: np.ndarray, exclude: np.ndarray) -> np.ndarray:
    h, _ = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    texture = normalize01(local_std(gray, 31))
    y = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    candidate = (y < 0.62) & (texture > 0.03) & (texture < 0.35) & ~exclude
    return clean_mask(candidate, 5, 23)


def estimate_depth_layers(image: np.ndarray, labels: np.ndarray | RegionMap) -> dict[str, np.ndarray]:
    h, w = image.shape[:2]
    yy = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    background = np.repeat(yy < 0.38, w, axis=1)
    midground = np.repeat((yy >= 0.30) & (yy < 0.72), w, axis=1)
    foreground = np.repeat(yy >= 0.62, w, axis=1)

    label_arr = labels.labels if isinstance(labels, RegionMap) else labels
    sky = label_arr == LABELS["sky"]
    mountain = label_arr == LABELS["mountain"]
    road = label_arr == LABELS["road"]
    background |= sky | (mountain & (yy < 0.58))
    foreground |= road & (yy > 0.48)
    midground &= ~sky
    foreground &= ~sky
    return {
        "foreground": foreground.astype(bool),
        "midground": midground.astype(bool) & ~foreground,
        "background": background.astype(bool) & ~foreground,
    }


def _regions_in_depth(semantic_masks: dict[str, np.ndarray], depth_mask: np.ndarray) -> list[str]:
    out = []
    for name, mask in semantic_masks.items():
        if float(np.mean(mask & depth_mask)) > 0.003:
            out.append(name)
    return out

