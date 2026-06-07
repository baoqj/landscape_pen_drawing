from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

from .models import ImageAnalysisResult, RegionMap, Stroke
from .utils import ensure_dir, mask_color_overlay, save_gray, save_rgb, to_uint8


def render_pen_drawing(strokes: list[Stroke], canvas_size: tuple[int, int], config: dict) -> Image.Image:
    width, height = canvas_size
    paper = tuple(int(v) for v in config.get("image", {}).get("paper_color", [248, 245, 238]))
    scale = 2
    canvas = Image.new("RGB", (width * scale, height * scale), paper)
    draw = ImageDraw.Draw(canvas, "RGBA")

    for stroke in strokes:
        if len(stroke.points) < 2:
            continue
        pts = [(float(x) * scale, float(y) * scale) for x, y in stroke.points]
        alpha = int(np.clip(stroke.opacity, 0, 1) * 255)
        width_px = max(1, int(round(stroke.width * scale)))
        color = (22, 22, 21, alpha)
        if stroke.semantic_region in {"sky", "mountain"}:
            color = (35, 35, 34, int(alpha * 0.68))
        elif stroke.semantic_region == "vegetation":
            color = (18, 24, 18, int(alpha * 0.88))
        draw.line(pts, fill=color, width=width_px, joint="curve")

    resample = Image.Resampling.LANCZOS if hasattr(Image, "Resampling") else Image.LANCZOS
    return canvas.resize((width, height), resample=resample)


def render_debug_layers(
    output_dir: str | Path,
    analysis: ImageAnalysisResult,
    regions: RegionMap,
    hatch_density_map: np.ndarray,
    enhanced_edges: np.ndarray,
) -> None:
    out = ensure_dir(output_dir)
    save_gray(out / "grayscale.png", analysis.maps["grayscale"])
    save_gray(out / "contrast_map.png", analysis.maps["contrast_map"])
    save_gray(out / "edge_map.png", analysis.maps["edge_map"])
    save_gray(out / "enhanced_edge_map.png", enhanced_edges)
    save_gray(out / "saliency_map.png", analysis.maps["saliency_map"])
    save_gray(out / "subject_mask.png", regions.subject_mask.astype(np.float32))
    save_gray(out / "hatch_density_map.png", hatch_density_map)
    save_rgb(out / "region_map.png", mask_color_overlay(regions.labels, regions.label_names))
    save_rgb(out / "semantic_masks.png", _semantic_mask_contact_sheet(regions))


def save_pil_image(path: str | Path, image: Image.Image) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


def _semantic_mask_contact_sheet(regions: RegionMap) -> np.ndarray:
    masks = [(name, mask) for name, mask in regions.semantic_masks.items() if mask.any()]
    if not masks:
        return np.zeros((*regions.labels.shape, 3), dtype=np.uint8)
    h, w = regions.labels.shape
    thumbs: list[np.ndarray] = []
    for name, mask in masks:
        img = np.full((h, w, 3), 245, dtype=np.uint8)
        color = _color_for_name(name)
        img[mask] = color
        cv2.putText(img, name, (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (20, 20, 20), 2, cv2.LINE_AA)
        thumb_w = 260
        thumb_h = max(1, int(round(h * thumb_w / max(w, 1))))
        thumbs.append(cv2.resize(img, (thumb_w, thumb_h), interpolation=cv2.INTER_AREA))
    cols = min(3, len(thumbs))
    rows = int(np.ceil(len(thumbs) / cols))
    th, tw = thumbs[0].shape[:2]
    sheet = np.full((rows * th, cols * tw, 3), 250, dtype=np.uint8)
    for i, thumb in enumerate(thumbs):
        r, c = divmod(i, cols)
        sheet[r * th : (r + 1) * th, c * tw : (c + 1) * tw] = thumb
    return sheet


def _color_for_name(name: str) -> tuple[int, int, int]:
    return {
        "sky": (174, 210, 245),
        "vegetation": (77, 145, 82),
        "water": (74, 146, 190),
        "building": (178, 151, 122),
        "road": (156, 150, 140),
        "mountain": (136, 149, 132),
        "person": (214, 91, 83),
        "ground": (177, 162, 118),
    }.get(name, (220, 220, 220))

