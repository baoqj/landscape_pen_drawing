from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np


BUILTIN_ARCHITECTURAL_STYLES: dict[str, dict[str, Any]] = {
    "learned_reference": {
        "structure_boost": 1.25,
        "entourage_edge_keep": 0.46,
        "line_extend_px": 12.0,
        "corner_tick_px": 9.0,
        "rectilinear_angle_tolerance": 18.0,
        "facade_hatch_spacing_px": 16,
        "facade_hatch_angle_deg": 45.0,
        "facade_hatch_opacity": 0.38,
        "structure_line_width": 1.08,
        "structure_line_opacity": 0.9,
        "structure_line_type": "straight",
        "facade_hatch_line_type": "straight",
        "entourage_line_type": "loose_curve",
        "line_curvature_px": 3.5,
        "sketch_wobble_px": 1.2,
        "broken_gap_ratio": 0.22,
        "draw_corner_extensions": True,
        "draw_mass_boxes": True,
        "draw_facade_hatching": True,
        "max_structure_lines": 360,
        "max_facade_hatch_lines": 900,
        "vegetation_looseness": 1.25,
    },
    "architectural_extended_line": {
        "structure_boost": 1.38,
        "entourage_edge_keep": 0.38,
        "line_extend_px": 18.0,
        "corner_tick_px": 13.0,
        "rectilinear_angle_tolerance": 20.0,
        "facade_hatch_spacing_px": 18,
        "facade_hatch_angle_deg": 42.0,
        "facade_hatch_opacity": 0.34,
        "structure_line_width": 1.12,
        "structure_line_opacity": 0.92,
        "structure_line_type": "sketch",
        "facade_hatch_line_type": "straight",
        "entourage_line_type": "loose_curve",
        "line_curvature_px": 3.0,
        "sketch_wobble_px": 1.45,
        "broken_gap_ratio": 0.18,
        "draw_corner_extensions": True,
        "draw_mass_boxes": True,
        "draw_facade_hatching": True,
        "max_structure_lines": 420,
        "max_facade_hatch_lines": 700,
        "vegetation_looseness": 1.45,
    },
    "modern_facade_grid": {
        "structure_boost": 1.45,
        "entourage_edge_keep": 0.34,
        "line_extend_px": 10.0,
        "corner_tick_px": 8.0,
        "rectilinear_angle_tolerance": 14.0,
        "facade_hatch_spacing_px": 20,
        "facade_hatch_angle_deg": 0.0,
        "facade_hatch_opacity": 0.32,
        "structure_line_width": 1.0,
        "structure_line_opacity": 0.88,
        "structure_line_type": "straight",
        "facade_hatch_line_type": "straight",
        "entourage_line_type": "broken_curve",
        "line_curvature_px": 1.4,
        "sketch_wobble_px": 0.65,
        "broken_gap_ratio": 0.2,
        "draw_corner_extensions": True,
        "draw_mass_boxes": True,
        "draw_facade_hatching": True,
        "max_structure_lines": 520,
        "max_facade_hatch_lines": 620,
        "vegetation_looseness": 1.35,
    },
    "historic_vertical_sketch": {
        "structure_boost": 1.52,
        "entourage_edge_keep": 0.42,
        "line_extend_px": 14.0,
        "corner_tick_px": 10.0,
        "rectilinear_angle_tolerance": 22.0,
        "facade_hatch_spacing_px": 13,
        "facade_hatch_angle_deg": 82.0,
        "facade_hatch_opacity": 0.4,
        "structure_line_width": 1.02,
        "structure_line_opacity": 0.9,
        "structure_line_type": "sketch",
        "facade_hatch_line_type": "slight_curve",
        "entourage_line_type": "loose_curve",
        "line_curvature_px": 4.2,
        "sketch_wobble_px": 1.15,
        "broken_gap_ratio": 0.16,
        "draw_corner_extensions": True,
        "draw_mass_boxes": False,
        "draw_facade_hatching": True,
        "max_structure_lines": 560,
        "max_facade_hatch_lines": 980,
        "vegetation_looseness": 1.2,
    },
    "dense_architectural_shadow": {
        "structure_boost": 1.32,
        "entourage_edge_keep": 0.30,
        "line_extend_px": 9.0,
        "corner_tick_px": 7.0,
        "rectilinear_angle_tolerance": 18.0,
        "facade_hatch_spacing_px": 9,
        "facade_hatch_angle_deg": 45.0,
        "facade_hatch_opacity": 0.48,
        "structure_line_width": 0.92,
        "structure_line_opacity": 0.86,
        "structure_line_type": "straight",
        "facade_hatch_line_type": "broken",
        "entourage_line_type": "broken_curve",
        "line_curvature_px": 2.4,
        "sketch_wobble_px": 0.95,
        "broken_gap_ratio": 0.24,
        "draw_corner_extensions": True,
        "draw_mass_boxes": True,
        "draw_facade_hatching": True,
        "max_structure_lines": 430,
        "max_facade_hatch_lines": 1500,
        "vegetation_looseness": 1.1,
    },
    "light_entourage_blank": {
        "structure_boost": 1.18,
        "entourage_edge_keep": 0.22,
        "line_extend_px": 11.0,
        "corner_tick_px": 8.0,
        "rectilinear_angle_tolerance": 16.0,
        "facade_hatch_spacing_px": 24,
        "facade_hatch_angle_deg": 35.0,
        "facade_hatch_opacity": 0.26,
        "structure_line_width": 1.0,
        "structure_line_opacity": 0.82,
        "structure_line_type": "slight_curve",
        "facade_hatch_line_type": "broken",
        "entourage_line_type": "loose_curve",
        "line_curvature_px": 4.5,
        "sketch_wobble_px": 1.25,
        "broken_gap_ratio": 0.34,
        "draw_corner_extensions": True,
        "draw_mass_boxes": True,
        "draw_facade_hatching": True,
        "max_structure_lines": 280,
        "max_facade_hatch_lines": 420,
        "vegetation_looseness": 1.65,
    },
}


@dataclass
class StyleReferenceMetrics:
    image_count: int
    ink_ratio: float
    edge_density: float
    line_count: int
    median_line_length: float
    horizontal_ratio: float
    vertical_ratio: float
    diagonal_ratio: float
    dominant_angles: list[float]
    suggested_profile: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "image_count": self.image_count,
            "ink_ratio": round(self.ink_ratio, 4),
            "edge_density": round(self.edge_density, 4),
            "line_count": int(self.line_count),
            "median_line_length": round(self.median_line_length, 2),
            "horizontal_ratio": round(self.horizontal_ratio, 4),
            "vertical_ratio": round(self.vertical_ratio, 4),
            "diagonal_ratio": round(self.diagonal_ratio, 4),
            "dominant_angles": [round(v, 1) for v in self.dominant_angles],
            "suggested_profile": self.suggested_profile,
        }


def resolve_architectural_style(config: dict[str, Any], project_root: str | Path | None = None) -> dict[str, Any]:
    arch_cfg = config.get("architectural_style", {})
    preset = str(arch_cfg.get("preset", "learned_reference"))
    preset_defaults = BUILTIN_ARCHITECTURAL_STYLES.get(preset, BUILTIN_ARCHITECTURAL_STYLES["learned_reference"])
    base = dict(preset_defaults)
    base["preset"] = preset
    learned_applied = False

    if bool(arch_cfg.get("learn_from_reference", True)):
        style_dir = _resolve_style_dir(arch_cfg.get("style_reference_dir", "../../pics/style"), project_root)
        metrics = analyze_style_directory(style_dir)
        if metrics is not None:
            learned = style_from_metrics(metrics)
            base.update(learned)
            base["reference_summary"] = metrics.to_dict()
            learned_applied = True
            if preset == "learned_reference":
                base["suggested_profile"] = metrics.suggested_profile
        else:
            base["reference_summary"] = {"image_count": 0, "style_reference_dir": str(style_dir)}

    for key, value in arch_cfg.items():
        if key in {"preset", "learn_from_reference", "style_reference_dir", "resolved"}:
            continue
        if learned_applied and value == preset_defaults.get(key):
            continue
        base[key] = value
    return base


def analyze_style_directory(style_dir: str | Path, max_images: int = 32) -> StyleReferenceMetrics | None:
    path = Path(style_dir)
    if not path.exists():
        return None
    files = [p for p in sorted(path.iterdir()) if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}]
    if not files:
        return None

    ink_ratios: list[float] = []
    edge_densities: list[float] = []
    lengths: list[float] = []
    angles: list[float] = []
    line_count = 0

    for file_path in files[:max_images]:
        data = np.fromfile(str(file_path), dtype=np.uint8)
        gray = cv2.imdecode(data, cv2.IMREAD_GRAYSCALE)
        if gray is None:
            continue
        gray = _resize_for_analysis(gray, 900)
        blur = cv2.GaussianBlur(gray, (3, 3), 0)
        edges = cv2.Canny(blur, 70, 160)
        min_len = max(20, gray.shape[1] // 30)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=35, minLineLength=min_len, maxLineGap=8)

        ink_ratios.append(float(np.mean(gray < 205)))
        edge_densities.append(float(np.mean(edges > 0)))
        if lines is None:
            continue
        line_count += int(lines.shape[0])
        for x1, y1, x2, y2 in lines[:, 0, :]:
            length = float(np.hypot(x2 - x1, y2 - y1))
            if length < min_len:
                continue
            lengths.append(length)
            angles.append(_fold_angle(float(np.degrees(np.arctan2(y2 - y1, x2 - x1)))))

    if not ink_ratios:
        return None

    horizontal = _ratio(angles, lambda a: abs(a) <= 12)
    vertical = _ratio(angles, lambda a: abs(abs(a) - 90) <= 14)
    diagonal = _ratio(angles, lambda a: 18 <= abs(a) <= 72)
    dominant_angles = _dominant_angles(angles)
    ink = float(np.mean(ink_ratios))
    profile = _suggest_profile(ink, horizontal, vertical, diagonal)
    return StyleReferenceMetrics(
        image_count=len(ink_ratios),
        ink_ratio=ink,
        edge_density=float(np.mean(edge_densities)),
        line_count=line_count,
        median_line_length=float(np.median(lengths)) if lengths else 0.0,
        horizontal_ratio=horizontal,
        vertical_ratio=vertical,
        diagonal_ratio=diagonal,
        dominant_angles=dominant_angles,
        suggested_profile=profile,
    )


def style_from_metrics(metrics: StyleReferenceMetrics) -> dict[str, Any]:
    ink = metrics.ink_ratio
    median_len = metrics.median_line_length or 42.0
    line_extend = float(np.clip(median_len * 0.26, 7, 20))
    spacing = int(np.clip(26 - ink * 34, 7, 24))
    angle = _choose_hatch_angle(metrics)
    entourage_keep = float(np.clip(0.62 - ink * 0.72, 0.22, 0.55))
    structure_line_type, hatch_line_type, entourage_line_type = _choose_line_types(metrics)
    return {
        "line_extend_px": line_extend,
        "corner_tick_px": float(np.clip(line_extend * 0.72, 5, 15)),
        "facade_hatch_spacing_px": spacing,
        "facade_hatch_angle_deg": angle,
        "facade_hatch_opacity": float(np.clip(0.24 + ink * 0.45, 0.28, 0.52)),
        "structure_boost": float(np.clip(1.12 + metrics.vertical_ratio * 0.48 + metrics.horizontal_ratio * 0.28, 1.12, 1.62)),
        "entourage_edge_keep": entourage_keep,
        "max_structure_lines": int(np.clip(240 + metrics.line_count / max(metrics.image_count, 1) * 0.12, 260, 620)),
        "max_facade_hatch_lines": int(np.clip(450 + ink * 2100, 520, 1500)),
        "vegetation_looseness": float(np.clip(1.0 + (1.0 - entourage_keep), 1.1, 1.75)),
        "structure_line_type": structure_line_type,
        "facade_hatch_line_type": hatch_line_type,
        "entourage_line_type": entourage_line_type,
    }


def _resize_for_analysis(gray: np.ndarray, max_side: int) -> np.ndarray:
    h, w = gray.shape[:2]
    longest = max(h, w)
    if longest <= max_side:
        return gray
    scale = max_side / float(longest)
    return cv2.resize(gray, (int(round(w * scale)), int(round(h * scale))), interpolation=cv2.INTER_AREA)


def _fold_angle(angle: float) -> float:
    while angle < -90:
        angle += 180
    while angle > 90:
        angle -= 180
    return angle


def _ratio(values: list[float], predicate) -> float:
    if not values:
        return 0.0
    return float(sum(1 for value in values if predicate(value)) / len(values))


def _dominant_angles(angles: list[float]) -> list[float]:
    if not angles:
        return [0.0, 45.0]
    bins = np.linspace(-90, 90, 19)
    hist, edges = np.histogram(angles, bins=bins)
    order = np.argsort(hist)[::-1]
    out: list[float] = []
    for idx in order[:4]:
        center = float((edges[idx] + edges[idx + 1]) * 0.5)
        if all(abs(center - existing) > 12 for existing in out):
            out.append(center)
    return out[:3]


def _suggest_profile(ink: float, horizontal: float, vertical: float, diagonal: float) -> str:
    if ink > 0.34:
        return "dense_architectural_shadow"
    if vertical > 0.34:
        return "historic_vertical_sketch"
    if horizontal > 0.42:
        return "modern_facade_grid"
    if diagonal > 0.42:
        return "architectural_extended_line"
    return "light_entourage_blank"


def _choose_hatch_angle(metrics: StyleReferenceMetrics) -> float:
    candidates = [angle for angle in metrics.dominant_angles if 16 <= abs(angle) <= 74]
    if candidates:
        return float(candidates[0])
    if metrics.vertical_ratio > metrics.horizontal_ratio:
        return 82.0
    if metrics.horizontal_ratio > 0.45:
        return 0.0
    return 45.0


def _choose_line_types(metrics: StyleReferenceMetrics) -> tuple[str, str, str]:
    if metrics.ink_ratio > 0.34:
        return "straight", "broken", "broken_curve"
    if metrics.horizontal_ratio > 0.42:
        return "straight", "straight", "broken_curve"
    if metrics.vertical_ratio > 0.30:
        return "sketch", "slight_curve", "loose_curve"
    if metrics.diagonal_ratio > 0.38:
        return "sketch", "slight_curve", "loose_curve"
    return "slight_curve", "broken", "loose_curve"


def _resolve_style_dir(style_dir: str | Path, project_root: str | Path | None) -> Path:
    path = Path(style_dir).expanduser()
    if path.is_absolute():
        return path
    if project_root is not None:
        return (Path(project_root) / path).resolve()
    return path.resolve()
