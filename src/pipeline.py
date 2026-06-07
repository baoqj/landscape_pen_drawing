from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2
import numpy as np

from .edge_extraction import enhance_edges_by_region, extract_multiscale_edges, extract_xdog_edges
from .hatch_generator import create_hatch_density_map, generate_cross_hatching, generate_hatching
from .image_analysis import analyze_image
from .image_io import load_image
from .pen_renderer import render_debug_layers, render_pen_drawing, save_pil_image
from .segmentation import segment_regions
from .stroke_exporter import export_strokes_json
from .stroke_generator import (
    edges_to_strokes,
    generate_building_structure_strokes,
    generate_vegetation_strokes,
    generate_water_strokes,
    sort_strokes_for_plotter,
)
from .style_planner import create_drawing_strategy
from .subject_detection import detect_subject
from .svg_exporter import export_svg
from .utils import ensure_dir, mask_color_overlay, save_rgb, write_json


def render_image_to_output(input_path: str | Path, output_dir: str | Path, config: dict[str, Any], mode: str = "pure") -> dict[str, Any]:
    if mode == "enhanced":
        print("Enhanced mode requested; no optional model plugin is configured, falling back to pure CV mode.")

    output_path = ensure_dir(output_dir)
    debug_dir = ensure_dir(output_path / "debug")
    image, scale = load_image(input_path, int(config.get("image", {}).get("max_size", 1600)))

    analysis = analyze_image(image)
    regions = segment_regions(image, analysis)
    detect_subject(image, analysis, regions)
    strategy = create_drawing_strategy(analysis, regions, config)

    gray = analysis.maps["grayscale"]
    edges = cv2.bitwise_or(extract_multiscale_edges(gray), extract_xdog_edges(gray))
    enhanced_edges = enhance_edges_by_region(edges, regions, strategy)
    hatch_density = create_hatch_density_map(gray, regions, strategy)
    analysis.maps["hatch_density_map"] = hatch_density

    strokes = []
    strokes.extend(edges_to_strokes(enhanced_edges, regions, strategy))
    strokes.extend(generate_building_structure_strokes(image, regions.semantic_masks.get("building", np.zeros_like(gray, dtype=bool))))
    strokes.extend(_generate_semantic_hatching(regions, hatch_density, config))
    strokes.extend(
        generate_vegetation_strokes(
            regions.semantic_masks.get("vegetation", np.zeros_like(gray, dtype=bool)),
            gray,
            density=float(config.get("drawing", {}).get("stroke_density", 0.8)) * max(0.15, float(config.get("drawing", {}).get("texture_strength", 0.65)) / 0.65),
            seed=int(config.get("stroke", {}).get("random_seed", 42)),
        )
    )
    strokes.extend(
        generate_water_strokes(
            regions.semantic_masks.get("water", np.zeros_like(gray, dtype=bool)),
            gray,
            density=float(config.get("drawing", {}).get("stroke_density", 0.8)) * max(0.15, float(config.get("drawing", {}).get("texture_strength", 0.65)) / 0.65),
        )
    )
    strokes.extend(_subject_accent_strokes(enhanced_edges, regions, strategy))
    strokes = sort_strokes_for_plotter(strokes)

    width, height = int(image.shape[1]), int(image.shape[0])
    drawing = render_pen_drawing(strokes, (width, height), config)
    save_pil_image(output_path / "pen_drawing.png", drawing)
    if bool(config.get("svg", {}).get("export", True)):
        export_svg(strokes, output_path / "pen_drawing.svg", (width, height), config)
    export_strokes_json(strokes, analysis, strategy, output_path / "strokes.json")
    write_json(output_path / "analysis.json", analysis.to_dict())
    (output_path / "analysis_report.md").write_text(_analysis_report(analysis, len(strokes), scale), encoding="utf-8")
    render_debug_layers(debug_dir, analysis, regions, hatch_density, enhanced_edges)
    save_rgb(output_path / "region_preview.png", mask_color_overlay(regions.labels, regions.label_names))

    return {
        "input": str(input_path),
        "output_dir": str(output_path),
        "stroke_count": len(strokes),
        "analysis": analysis.to_dict(),
        "pen_drawing": str(output_path / "pen_drawing.png"),
        "svg": str(output_path / "pen_drawing.svg"),
        "strokes_json": str(output_path / "strokes.json"),
    }


def _generate_semantic_hatching(regions, density_map: np.ndarray, config: dict[str, Any]):
    hatch_cfg = config.get("hatching", {})
    min_spacing = int(hatch_cfg.get("min_spacing_px", 4))
    max_spacing = int(hatch_cfg.get("max_spacing_px", 22))
    mid_luminance_threshold = float(hatch_cfg.get("mid_threshold", 0.65))
    dark_luminance_threshold = float(hatch_cfg.get("dark_threshold", 0.35))
    min_density = max(0.05, min(0.75, 1.0 - mid_luminance_threshold))
    cross_density = max(0.25, min(0.9, 1.0 - dark_luminance_threshold))
    strokes = []
    region_angles = {
        "building": float(hatch_cfg.get("building_angle_deg", 45)),
        "road": 18.0,
        "ground": 28.0,
        "mountain": 8.0,
        "vegetation": 65.0,
        "person": 75.0,
    }
    for name, mask in regions.semantic_masks.items():
        if name in {"sky", "water"} or not mask.any():
            continue
        region_density = float(np.mean(density_map[mask]))
        if region_density < 0.06:
            continue
        angle = region_angles.get(name, 35.0)
        strokes.extend(
            generate_hatching(
                mask,
                density_map,
                angle,
                semantic_region=name,
                min_spacing_px=min_spacing,
                max_spacing_px=max_spacing,
                min_density=max(min_density, 0.20) if name == "vegetation" else min_density,
                width=0.72 if name != "building" else 0.82,
                opacity=0.52 if name != "building" else 0.62,
            )
        )
        if bool(hatch_cfg.get("cross_hatch_dark_regions", True)) and name in {"building", "ground", "road", "person"}:
            strokes.extend(
                generate_cross_hatching(
                    mask,
                    density_map,
                    semantic_region=name,
                    min_spacing_px=min_spacing,
                    max_spacing_px=max_spacing,
                    dark_density_threshold=cross_density,
                )
            )
    return strokes


def _subject_accent_strokes(edges: np.ndarray, regions, strategy):
    subject_edges = np.zeros_like(edges)
    subject_edges[(edges > 0) & regions.subject_mask] = 255
    strokes = edges_to_strokes(subject_edges, regions, strategy)
    for stroke in strokes:
        stroke.layer = "layer_05_accents"
        stroke.stroke_type = "accent_contour"
        stroke.width *= 1.12
        stroke.opacity = min(0.96, stroke.opacity * 1.1)
        stroke.priority = 5
    return strokes[:500]


def _analysis_report(analysis, stroke_count: int, scale: float) -> str:
    content = analysis.content
    tone = analysis.tone
    structure = analysis.structure
    detected = ", ".join(content.get("detected_regions", [])) or "unknown"
    return f"""# Landscape Pen Drawing Analysis Report

## 图像状态

- 尺寸：{analysis.image['width']} x {analysis.image['height']}，缩放系数：{scale:.3f}
- 平均亮度：{tone['mean_luminance']:.3f}
- RMS 对比度：{tone['rms_contrast']:.3f}
- 动态范围：{tone['dynamic_range']:.3f}
- 暗部/中间调/高光比例：{tone['shadow_ratio']:.3f} / {tone['midtone_ratio']:.3f} / {tone['highlight_ratio']:.3f}
- 边缘密度：{structure['edge_density']:.3f}
- 纹理复杂度：{structure['texture_complexity']:.3f}
- 清晰度 Laplacian variance：{structure['sharpness_laplacian_variance']:.2f}

## 内容分隔

- 检测区域：{detected}
- 主体估计：{content.get('main_subject', 'unknown')}
- 前景：{', '.join(content.get('foreground', [])) or 'unknown'}
- 中景：{', '.join(content.get('midground', [])) or 'unknown'}
- 远景：{', '.join(content.get('background', [])) or 'unknown'}

## 钢笔画策略

- 主体：提升轮廓和局部对比度，保留更多结构线和暗部排线。
- 建筑：使用 Hough 直线抽取主结构，阴影用 45 度方向排线和深暗交叉排线。
- 植物：降低碎边比例，用团块轮廓、松散短线和局部点划概括。
- 天空：大面积留白，抑制边缘和排线。
- 水面：以水平短线和稀疏波纹表现，不直接填灰。
- 远景：提高最短线段门槛并降低透明度，避免抢主体。

## 输出

- 生成笔触数：{stroke_count}
- PNG：pen_drawing.png
- SVG：pen_drawing.svg
- 笔触数据：strokes.json
- 调试图：debug/
"""
