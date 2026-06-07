from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image

from .utils import ensure_dir, normalize01, save_gray


@dataclass
class PencilRenderResult:
    image: Image.Image
    stroke_map: np.ndarray
    tone_map: np.ndarray
    texture_map: np.ndarray
    combined_map: np.ndarray
    params: dict[str, Any]


def render_pencil_drawing(image: np.ndarray, config: dict[str, Any]) -> PencilRenderResult:
    pencil_cfg = config.get("pencil", {})
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0
    kernel_size = _kernel_size(gray.shape, pencil_cfg)
    stroke_map = generate_pencil_stroke_map(
        gray,
        kernel_size=kernel_size,
        stroke_width=int(pencil_cfg.get("stroke_width", 1)),
        num_directions=int(pencil_cfg.get("num_directions", 8)),
        smooth_kernel=str(pencil_cfg.get("smooth_kernel", "gauss")),
        gradient_method=str(pencil_cfg.get("gradient_method", "sobel")),
    )
    stroke_darkness = float(pencil_cfg.get("stroke_darkness", 1.65))
    stroke_map = np.power(np.clip(stroke_map, 0.0, 1.0), stroke_darkness)

    tone_map = generate_pencil_tone_map(
        gray,
        tone_group=int(pencil_cfg.get("tone_group", 1)),
        tone_smoothing=float(pencil_cfg.get("tone_smoothing", 1.35)),
    )
    texture_map = generate_procedural_pencil_texture(
        gray.shape,
        num_directions=int(pencil_cfg.get("num_directions", 8)),
        grain_scale=float(pencil_cfg.get("grain_scale", 1.0)),
        paper_grain=float(pencil_cfg.get("paper_grain", 0.18)),
        seed=int(pencil_cfg.get("texture_seed", 37)),
    )

    tone_darkness = float(pencil_cfg.get("tone_darkness", 1.25))
    texture_strength = float(pencil_cfg.get("texture_strength", 0.42))
    tone_texture = 1.0 - np.clip(tone_darkness, 0.0, 4.0) * (1.0 - tone_map) * (
        1.0 - texture_strength * (1.0 - texture_map)
    )
    combined = np.clip(stroke_map * np.clip(tone_texture, 0.0, 1.0), 0.0, 1.0)

    contrast = float(pencil_cfg.get("contrast", 1.08))
    gamma = float(pencil_cfg.get("gamma", 1.0))
    combined = _adjust_contrast_gamma(combined, contrast, gamma)
    if bool(pencil_cfg.get("preserve_color", False)):
        rgb = _apply_luminance_to_color(image, combined)
    else:
        value = np.clip(combined * 255.0, 0, 255).astype(np.uint8)
        rgb = cv2.cvtColor(value, cv2.COLOR_GRAY2RGB)

    return PencilRenderResult(
        image=Image.fromarray(rgb),
        stroke_map=stroke_map,
        tone_map=tone_map,
        texture_map=texture_map,
        combined_map=combined,
        params={
            "kernel_size": kernel_size,
            **pencil_cfg,
        },
    )


def generate_pencil_stroke_map(
    gray: np.ndarray,
    *,
    kernel_size: int,
    stroke_width: int = 1,
    num_directions: int = 8,
    smooth_kernel: str = "gauss",
    gradient_method: str = "sobel",
) -> np.ndarray:
    smooth = _smooth_gray(gray, smooth_kernel)
    gradient = _gradient_magnitude(smooth, gradient_method)
    kernels = [_line_kernel(kernel_size, stroke_width, idx * 180.0 / num_directions) for idx in range(num_directions)]
    responses = np.stack([cv2.filter2D(gradient, cv2.CV_32F, kernel, borderType=cv2.BORDER_REFLECT) for kernel in kernels], axis=-1)
    direction_map = np.argmax(responses, axis=-1)

    directional_sum = np.zeros_like(gray, dtype=np.float32)
    for idx, kernel in enumerate(kernels):
        classified = gradient * (direction_map == idx)
        directional_sum += cv2.filter2D(classified, cv2.CV_32F, kernel, borderType=cv2.BORDER_REFLECT)

    stroke_strength = normalize01(directional_sum)
    return 1.0 - stroke_strength


def generate_pencil_tone_map(gray: np.ndarray, tone_group: int = 1, tone_smoothing: float = 1.35) -> np.ndarray:
    weights = np.array(
        [
            [11, 37, 52],
            [29, 29, 42],
            [2, 22, 76],
        ],
        dtype=np.float32,
    )[int(np.clip(tone_group, 0, 2))]
    weights = weights / max(float(weights.sum()), 1.0)

    values = np.arange(256, dtype=np.float32)
    bright = np.exp(-(255.0 - values) / 9.0) / 9.0
    mid = np.where((105 <= values) & (values <= 225), 1.0 / 120.0, 0.0)
    dark = np.exp(-((values - 90.0) ** 2) / (2 * 11.0**2)) / (np.sqrt(2 * np.pi) * 11.0)
    target_pdf = weights[0] * bright + weights[1] * mid + weights[2] * dark
    target_pdf = target_pdf / np.sum(target_pdf)
    target_cdf = np.cumsum(target_pdf)

    gray_u8 = np.clip(gray * 255.0, 0, 255).astype(np.uint8)
    hist = np.bincount(gray_u8.ravel(), minlength=256).astype(np.float32)
    source_cdf = np.cumsum(hist / max(float(hist.sum()), 1.0))
    lut = np.searchsorted(target_cdf, source_cdf, side="left")
    tone = lut[gray_u8].astype(np.float32) / 255.0
    if tone_smoothing > 0:
        tone = cv2.GaussianBlur(tone, (0, 0), tone_smoothing)
    return np.clip(tone, 0.0, 1.0)


def generate_procedural_pencil_texture(
    shape: tuple[int, int],
    *,
    num_directions: int = 8,
    grain_scale: float = 1.0,
    paper_grain: float = 0.18,
    seed: int = 37,
) -> np.ndarray:
    h, w = shape
    rng = np.random.default_rng(seed)
    base = rng.normal(0.0, 1.0, (h, w)).astype(np.float32)
    base = cv2.GaussianBlur(base, (0, 0), max(0.4, 0.8 * grain_scale))

    directional = np.zeros((h, w), dtype=np.float32)
    for idx in range(max(1, min(num_directions, 12))):
        angle = idx * 180.0 / max(num_directions, 1)
        kernel = _line_kernel(max(3, int(7 * grain_scale)), 0, angle)
        directional += cv2.filter2D(base, cv2.CV_32F, kernel, borderType=cv2.BORDER_REFLECT)
    directional = normalize01(np.abs(directional))

    paper = rng.normal(0.0, 1.0, (h, w)).astype(np.float32)
    paper = normalize01(cv2.GaussianBlur(paper, (0, 0), max(1.0, 2.2 * grain_scale)))
    texture = 1.0 - 0.35 * directional - float(np.clip(paper_grain, 0.0, 1.0)) * 0.25 * paper
    return np.clip(texture, 0.0, 1.0)


def render_pencil_debug_layers(output_dir: str | Path, result: PencilRenderResult) -> None:
    out = ensure_dir(output_dir)
    save_gray(out / "pencil_stroke_map.png", result.stroke_map)
    save_gray(out / "pencil_tone_map.png", result.tone_map)
    save_gray(out / "pencil_texture_map.png", result.texture_map)
    save_gray(out / "pencil_combined_map.png", result.combined_map)


def _kernel_size(shape: tuple[int, int], pencil_cfg: dict[str, Any]) -> int:
    if bool(pencil_cfg.get("auto_kernel", True)):
        value = int(round(min(shape) / max(float(pencil_cfg.get("kernel_scale", 30.0)), 8.0)))
    else:
        value = int(pencil_cfg.get("kernel_size", 8))
    return max(2, min(32, value))


def _smooth_gray(gray: np.ndarray, smooth_kernel: str) -> np.ndarray:
    if smooth_kernel == "median":
        return cv2.medianBlur(np.clip(gray * 255, 0, 255).astype(np.uint8), 3).astype(np.float32) / 255.0
    if smooth_kernel == "bilateral":
        return cv2.bilateralFilter(np.clip(gray * 255, 0, 255).astype(np.uint8), 7, 40, 40).astype(np.float32) / 255.0
    return cv2.GaussianBlur(gray.astype(np.float32), (0, 0), np.sqrt(2.0))


def _gradient_magnitude(gray: np.ndarray, gradient_method: str) -> np.ndarray:
    if gradient_method == "forward":
        gx = np.zeros_like(gray, dtype=np.float32)
        gy = np.zeros_like(gray, dtype=np.float32)
        gx[:, :-1] = gray[:, 1:] - gray[:, :-1]
        gy[:-1, :] = gray[1:, :] - gray[:-1, :]
    elif gradient_method == "scharr":
        gx = cv2.Scharr(gray, cv2.CV_32F, 1, 0)
        gy = cv2.Scharr(gray, cv2.CV_32F, 0, 1)
    else:
        gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=5)
        gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=5)
    return normalize01(np.sqrt(gx * gx + gy * gy))


def _line_kernel(kernel_size: int, stroke_width: int, angle_deg: float) -> np.ndarray:
    size = kernel_size * 2 + 1
    kernel = np.zeros((size, size), dtype=np.float32)
    center = kernel_size
    half_width = max(0, int(stroke_width))
    kernel[max(0, center - half_width) : min(size, center + half_width + 1), :] = 1.0
    matrix = cv2.getRotationMatrix2D((center, center), angle_deg, 1.0)
    rotated = cv2.warpAffine(kernel, matrix, (size, size), flags=cv2.INTER_LINEAR)
    total = float(rotated.sum())
    return rotated / total if total > 0 else rotated


def _adjust_contrast_gamma(values: np.ndarray, contrast: float, gamma: float) -> np.ndarray:
    adjusted = (values - 0.5) * contrast + 0.5
    adjusted = np.clip(adjusted, 0.0, 1.0)
    if gamma > 0:
        adjusted = np.power(adjusted, 1.0 / gamma)
    return np.clip(adjusted, 0.0, 1.0)


def _apply_luminance_to_color(image: np.ndarray, luminance: np.ndarray) -> np.ndarray:
    yuv = cv2.cvtColor(image, cv2.COLOR_RGB2YUV).astype(np.float32) / 255.0
    yuv[:, :, 0] = luminance
    rgb = cv2.cvtColor(np.clip(yuv * 255.0, 0, 255).astype(np.uint8), cv2.COLOR_YUV2RGB)
    return rgb
