from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class ImageAnalysisResult:
    image: dict[str, Any]
    tone: dict[str, Any]
    structure: dict[str, Any]
    content: dict[str, Any]
    drawing_strategy: dict[str, Any]
    histogram: list[int]
    maps: dict[str, np.ndarray] = field(default_factory=dict, repr=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "image": self.image,
            "tone": self.tone,
            "structure": self.structure,
            "content": self.content,
            "drawing_strategy": self.drawing_strategy,
            "histogram": self.histogram,
        }


@dataclass
class RegionMap:
    labels: np.ndarray
    label_names: dict[int, str]
    semantic_masks: dict[str, np.ndarray]
    depth_masks: dict[str, np.ndarray]
    subject_mask: np.ndarray
    main_subject: str

    def semantic_at(self, x: float, y: float) -> str:
        h, w = self.labels.shape[:2]
        xi = int(np.clip(round(x), 0, w - 1))
        yi = int(np.clip(round(y), 0, h - 1))
        return self.label_names.get(int(self.labels[yi, xi]), "unknown")

    def depth_at(self, x: float, y: float) -> str:
        h, w = self.labels.shape[:2]
        xi = int(np.clip(round(x), 0, w - 1))
        yi = int(np.clip(round(y), 0, h - 1))
        for name, mask in self.depth_masks.items():
            if bool(mask[yi, xi]):
                return name
        return "midground"


@dataclass
class RegionStyle:
    semantic_region: str
    depth_layer: str
    is_subject: bool
    edge_strength: float
    hatch_strength: float
    texture_strength: float
    line_width: float
    opacity: float
    jitter_px: float
    simplify_tolerance: float
    min_stroke_length: float
    hatch_angles: tuple[float, ...]
    suppress_edges: bool = False


@dataclass
class DrawingStrategy:
    global_strategy: dict[str, Any]
    region_styles: dict[str, RegionStyle]

    def style_for(self, semantic_region: str, depth_layer: str = "midground", is_subject: bool = False) -> RegionStyle:
        if is_subject and "subject" in self.region_styles:
            return self.region_styles["subject"]
        key = f"{semantic_region}:{depth_layer}"
        if key in self.region_styles:
            return self.region_styles[key]
        return self.region_styles.get(semantic_region, self.region_styles["default"])

    def to_dict(self) -> dict[str, Any]:
        return {
            "global_strategy": self.global_strategy,
            "region_styles": {
                k: {
                    "semantic_region": v.semantic_region,
                    "depth_layer": v.depth_layer,
                    "is_subject": v.is_subject,
                    "edge_strength": v.edge_strength,
                    "hatch_strength": v.hatch_strength,
                    "texture_strength": v.texture_strength,
                    "line_width": v.line_width,
                    "opacity": v.opacity,
                    "jitter_px": v.jitter_px,
                    "simplify_tolerance": v.simplify_tolerance,
                    "min_stroke_length": v.min_stroke_length,
                    "hatch_angles": list(v.hatch_angles),
                    "suppress_edges": v.suppress_edges,
                }
                for k, v in self.region_styles.items()
            },
        }


@dataclass
class Stroke:
    id: str
    layer: str
    semantic_region: str
    stroke_type: str
    points: list[tuple[float, float]]
    width: float
    opacity: float
    priority: int
    drawing_order: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "layer": self.layer,
            "semantic_region": self.semantic_region,
            "stroke_type": self.stroke_type,
            "points": [[round(float(x), 2), round(float(y), 2)] for x, y in self.points],
            "width": round(float(self.width), 3),
            "opacity": round(float(self.opacity), 3),
            "priority": int(self.priority),
            "drawing_order": int(self.drawing_order),
        }

