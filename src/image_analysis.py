from __future__ import annotations

import cv2
import numpy as np

from .models import ImageAnalysisResult
from .utils import local_std, normalize01


def _gray(image: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)


def compute_contrast_metrics(gray: np.ndarray) -> dict[str, float | int]:
    gray_f = gray.astype(np.float32) / 255.0
    p01, p99 = np.percentile(gray_f, [1, 99])
    min_v = float(np.min(gray_f))
    max_v = float(np.max(gray_f))
    rms = float(np.std(gray_f))
    michelson = float((max_v - min_v) / (max_v + min_v + 1e-8))
    return {
        "mean_luminance": float(np.mean(gray_f)),
        "luminance_std": rms,
        "rms_contrast": rms,
        "michelson_contrast": michelson,
        "dynamic_range": float(p99 - p01),
        "shadow_ratio": float(np.mean(gray_f < 0.28)),
        "midtone_ratio": float(np.mean((gray_f >= 0.28) & (gray_f <= 0.72))),
        "highlight_ratio": float(np.mean(gray_f > 0.72)),
    }


def compute_edge_density(gray: np.ndarray) -> float:
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    edges = cv2.Canny(blurred, 70, 160)
    return float(np.mean(edges > 0))


def compute_texture_complexity(gray: np.ndarray) -> float:
    lap = cv2.Laplacian(gray, cv2.CV_32F, ksize=3)
    sobel_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    sobel_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    grad = np.sqrt(sobel_x * sobel_x + sobel_y * sobel_y)
    score = 0.5 * normalize01(np.abs(lap)) + 0.5 * normalize01(grad)
    return float(np.mean(score))


def compute_saliency_map(image: np.ndarray) -> np.ndarray:
    gray = _gray(image)
    gray_f = gray.astype(np.float32) / 255.0
    local_contrast = normalize01(local_std(gray, 35))
    blur = cv2.GaussianBlur(gray_f, (0, 0), 9)
    center_surround = normalize01(np.abs(gray_f - blur))
    edges = cv2.Canny(gray, 60, 150)
    edge_energy = normalize01(cv2.GaussianBlur(edges.astype(np.float32), (0, 0), 3))
    hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
    saturation = hsv[:, :, 1].astype(np.float32) / 255.0

    h, w = gray.shape
    yy, xx = np.mgrid[0:h, 0:w]
    cx, cy = w * 0.5, h * 0.52
    sigma_x, sigma_y = w * 0.38, h * 0.42
    center_weight = np.exp(-(((xx - cx) ** 2) / (2 * sigma_x**2) + ((yy - cy) ** 2) / (2 * sigma_y**2)))

    saliency = (
        0.34 * local_contrast
        + 0.24 * center_surround
        + 0.22 * edge_energy
        + 0.10 * saturation
        + 0.10 * center_weight.astype(np.float32)
    )
    return normalize01(cv2.GaussianBlur(saliency, (0, 0), 5))


def analyze_image(image: np.ndarray) -> ImageAnalysisResult:
    h, w = image.shape[:2]
    gray = _gray(image)
    hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
    tone = compute_contrast_metrics(gray)

    lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    edges = cv2.Canny(cv2.GaussianBlur(gray, (3, 3), 0), 70, 160)
    texture = compute_texture_complexity(gray)
    saturation = hsv[:, :, 1].astype(np.float32) / 255.0
    colorfulness = _colorfulness(image)
    hist = cv2.calcHist([gray], [0], None, [64], [0, 256]).flatten().astype(int).tolist()
    contrast_map = normalize01(local_std(gray, 35))
    saliency = compute_saliency_map(image)

    result = ImageAnalysisResult(
        image={
            "width": int(w),
            "height": int(h),
            "aspect_ratio": round(float(w / max(h, 1)), 4),
        },
        tone=tone,
        structure={
            "edge_density": compute_edge_density(gray),
            "texture_complexity": texture,
            "sharpness_laplacian_variance": lap_var,
            "mean_saturation": float(np.mean(saturation)),
            "colorfulness": colorfulness,
        },
        content={
            "main_subject": "unknown",
            "detected_regions": [],
            "foreground": [],
            "midground": [],
            "background": [],
        },
        drawing_strategy={
            "subject": "increase contrast, strong contour, detailed hatch",
            "building": "straight structural lines, window details, directional hatching",
            "vegetation": "loose grouped strokes, simplified texture",
            "sky": "mostly blank with sparse cloud marks",
            "background": "low detail, sparse lines",
        },
        histogram=hist,
        maps={
            "grayscale": gray,
            "contrast_map": contrast_map,
            "edge_map": edges,
            "saliency_map": saliency,
        },
    )
    return result


def _colorfulness(image: np.ndarray) -> float:
    rgb = image.astype(np.float32)
    rg = np.abs(rgb[:, :, 0] - rgb[:, :, 1])
    yb = np.abs(0.5 * (rgb[:, :, 0] + rgb[:, :, 1]) - rgb[:, :, 2])
    std_root = np.sqrt(np.std(rg) ** 2 + np.std(yb) ** 2)
    mean_root = np.sqrt(np.mean(rg) ** 2 + np.mean(yb) ** 2)
    return float((std_root + 0.3 * mean_root) / 255.0)

