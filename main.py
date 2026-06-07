from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np

from src.edge_extraction import enhance_edges_by_region, extract_multiscale_edges, extract_xdog_edges
from src.hatch_generator import create_hatch_density_map, generate_cross_hatching, generate_hatching
from src.image_analysis import analyze_image
from src.image_io import deep_update, load_config, load_image
from src.pen_renderer import render_debug_layers, render_pen_drawing, save_pil_image
from src.segmentation import segment_regions
from src.stroke_exporter import export_strokes_json
from src.stroke_generator import (
    edges_to_strokes,
    generate_building_structure_strokes,
    generate_vegetation_strokes,
    generate_water_strokes,
    sort_strokes_for_plotter,
)
from src.style_planner import create_drawing_strategy
from src.subject_detection import detect_subject
from src.svg_exporter import export_svg
from src.utils import ensure_dir, mask_color_overlay, save_rgb, write_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze a landscape image and render a programmatic pen drawing.")
    parser.add_argument("--input", required=True, help="Input JPG, PNG, or WebP image.")
    parser.add_argument("--output", required=True, help="Output directory.")
    parser.add_argument("--mode", choices=["pure", "enhanced"], default="pure", help="Enhanced is reserved for optional model plugins.")
    parser.add_argument("--paper", default="A4", help="SVG paper preset, currently A4 by default.")
    parser.add_argument("--detail", type=float, default=None, help="Override drawing.detail_level.")
    parser.add_argument("--stroke-density", type=float, default=None, help="Override drawing.stroke_density.")
    parser.add_argument("--max-size", type=int, default=None, help="Override image.max_size.")
    parser.add_argument("--config", default=str(Path(__file__).with_name("config.yaml")), help="Path to config.yaml.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    overrides: dict = {"svg": {"page_size": args.paper}}
    if args.detail is not None:
        overrides.setdefault("drawing", {})["detail_level"] = args.detail
    if args.stroke_density is not None:
        overrides.setdefault("drawing", {})["stroke_density"] = args.stroke_density
    if args.max_size is not None:
        overrides.setdefault("image", {})["max_size"] = args.max_size
    config = deep_update(config, overrides)

    if args.mode == "enhanced":
        print("Enhanced mode requested; no optional model plugin is configured, falling back to pure CV mode.")

    output_dir = ensure_dir(args.output)
    debug_dir = ensure_dir(output_dir / "debug")
    image, scale = load_image(args.input, int(config.get("image", {}).get("max_size", 1600)))

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
            density=float(config.get("drawing", {}).get("stroke_density", 0.8)),
            seed=int(config.get("stroke", {}).get("random_seed", 42)),
        )
    )
    strokes.extend(generate_water_strokes(regions.semantic_masks.get("water", np.zeros_like(gray, dtype=bool)), gray))
    strokes.extend(_subject_accent_strokes(enhanced_edges, regions, strategy))
    strokes = sort_strokes_for_plotter(strokes)

    width, height = int(image.shape[1]), int(image.shape[0])
    drawing = render_pen_drawing(strokes, (width, height), config)
    save_pil_image(output_dir / "pen_drawing.png", drawing)
    export_svg(strokes, output_dir / "pen_drawing.svg", (width, height), config)
    export_strokes_json(strokes, analysis, strategy, output_dir / "strokes.json")
    write_json(output_dir / "analysis.json", analysis.to_dict())
    (output_dir / "analysis_report.md").write_text(_analysis_report(analysis, regions, len(strokes), scale), encoding="utf-8")
    render_debug_layers(debug_dir, analysis, regions, hatch_density, enhanced_edges)
    save_rgb(output_dir / "region_preview.png", mask_color_overlay(regions.labels, regions.label_names))
    print(f"Generated {len(strokes)} strokes in {output_dir}")


def _generate_semantic_hatching(regions, density_map: np.ndarray, config: dict):
    hatch_cfg = config.get("hatching", {})
    min_spacing = int(hatch_cfg.get("min_spacing_px", 4))
    max_spacing = int(hatch_cfg.get("max_spacing_px", 22))
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
                min_density=0.12 if name != "vegetation" else 0.20,
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


def _analysis_report(analysis, regions, stroke_count: int, scale: float) -> str:
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


if __name__ == "__main__":
    main()

