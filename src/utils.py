from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import cv2
import numpy as np


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def normalize01(arr: np.ndarray, eps: float = 1e-8) -> np.ndarray:
    arr = arr.astype(np.float32)
    lo = float(np.nanmin(arr))
    hi = float(np.nanmax(arr))
    if hi - lo < eps:
        return np.zeros_like(arr, dtype=np.float32)
    return (arr - lo) / (hi - lo)


def to_uint8(arr: np.ndarray) -> np.ndarray:
    if arr.dtype == np.uint8:
        return arr
    return np.clip(arr * 255.0 if arr.max() <= 1.5 else arr, 0, 255).astype(np.uint8)


def resize_max(image: np.ndarray, max_size: int) -> tuple[np.ndarray, float]:
    h, w = image.shape[:2]
    longest = max(h, w)
    if longest <= max_size:
        return image, 1.0
    scale = max_size / float(longest)
    resized = cv2.resize(image, (int(round(w * scale)), int(round(h * scale))), interpolation=cv2.INTER_AREA)
    return resized, scale


def local_std(gray: np.ndarray, ksize: int = 31) -> np.ndarray:
    gray_f = gray.astype(np.float32) / 255.0 if gray.dtype == np.uint8 else gray.astype(np.float32)
    mean = cv2.blur(gray_f, (ksize, ksize))
    mean_sq = cv2.blur(gray_f * gray_f, (ksize, ksize))
    return np.sqrt(np.maximum(mean_sq - mean * mean, 0.0))


def clean_mask(mask: np.ndarray, open_size: int = 3, close_size: int = 7) -> np.ndarray:
    mask_u8 = (mask.astype(np.uint8) * 255) if mask.dtype != np.uint8 else mask
    if open_size > 0:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (open_size, open_size))
        mask_u8 = cv2.morphologyEx(mask_u8, cv2.MORPH_OPEN, k)
    if close_size > 0:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (close_size, close_size))
        mask_u8 = cv2.morphologyEx(mask_u8, cv2.MORPH_CLOSE, k)
    return mask_u8 > 0


def write_json(path: str | Path, data: dict[str, Any]) -> None:
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def save_gray(path: str | Path, arr: np.ndarray) -> None:
    cv2.imwrite(str(path), to_uint8(arr))


def save_rgb(path: str | Path, arr: np.ndarray) -> None:
    cv2.imwrite(str(path), cv2.cvtColor(to_uint8(arr), cv2.COLOR_RGB2BGR))


def mask_color_overlay(labels: np.ndarray, label_names: dict[int, str]) -> np.ndarray:
    palette = {
        "unknown": (220, 220, 220),
        "sky": (174, 210, 245),
        "vegetation": (77, 145, 82),
        "water": (74, 146, 190),
        "building": (178, 151, 122),
        "road": (156, 150, 140),
        "mountain": (136, 149, 132),
        "person": (214, 91, 83),
        "ground": (177, 162, 118),
    }
    out = np.zeros((*labels.shape, 3), dtype=np.uint8)
    for label, name in label_names.items():
        out[labels == label] = palette.get(name, palette["unknown"])
    return out

