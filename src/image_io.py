from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2
import numpy as np
import yaml

from .utils import resize_max


def load_config(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def deep_update(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_update(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_image(path: str | Path, max_size: int | None = None) -> tuple[np.ndarray, float]:
    image_path = Path(path)
    if not image_path.exists():
        raise FileNotFoundError(f"Input image does not exist: {image_path}")
    data = np.fromfile(str(image_path), dtype=np.uint8)
    bgr = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if bgr is None:
        raise ValueError(f"Unsupported or unreadable image: {image_path}")
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    if max_size:
        rgb, scale = resize_max(rgb, max_size)
        return rgb, scale
    return rgb, 1.0


def save_png(path: str | Path, image: np.ndarray) -> None:
    path = Path(path)
    if image.ndim == 3 and image.shape[2] == 3:
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    ok = cv2.imwrite(str(path), image)
    if not ok:
        raise OSError(f"Failed to save image: {path}")

