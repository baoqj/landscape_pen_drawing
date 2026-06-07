from __future__ import annotations

from .models import DrawingStrategy, ImageAnalysisResult, RegionMap, RegionStyle


def create_drawing_strategy(analysis: ImageAnalysisResult, regions: RegionMap, config: dict | None = None) -> DrawingStrategy:
    config = config or {}
    drawing_cfg = config.get("drawing", {})
    stroke_cfg = config.get("stroke", {})
    detail = float(drawing_cfg.get("detail_level", 0.75))
    density = float(drawing_cfg.get("stroke_density", 0.8))
    base_width = float(stroke_cfg.get("base_width_px", 1.1))

    region_styles: dict[str, RegionStyle] = {
        "default": RegionStyle("ground", "midground", False, 0.75, 0.65, 0.45, base_width, 0.62, 0.7, 1.8, 12, (35.0,)),
        "subject": RegionStyle(regions.main_subject, "midground", True, 1.45, 1.2, 0.9, base_width * 1.12, 0.92, 0.45, 0.9, 6, (45.0, -45.0)),
    }

    for semantic in ["sky", "vegetation", "water", "building", "road", "mountain", "person", "ground"]:
        for depth in ["foreground", "midground", "background"]:
            region_styles[f"{semantic}:{depth}"] = assign_region_style(
                semantic,
                depth,
                False,
                detail=detail,
                density=density,
                base_width=base_width,
                stroke_cfg=stroke_cfg,
            )
        region_styles[semantic] = assign_region_style(
            semantic,
            "midground",
            False,
            detail=detail,
            density=density,
            base_width=base_width,
            stroke_cfg=stroke_cfg,
        )

    global_strategy = {
        "subject": "主体系数提高：保留更多轮廓、结构线和交叉排线。",
        "building": "建筑使用较长、较直的结构线，暗面使用规则排线。",
        "vegetation": "植物用团块轮廓、短曲线和点状笔触概括，不逐叶描绘。",
        "sky": "天空大面积留白，只在暗云或明显渐变处轻描。",
        "water": "水面使用水平短线和稀疏波纹，保留高光空白。",
        "background": "远景降低对比度和线条密度，避免抢主体。",
        "detail_level": detail,
        "stroke_density": density,
    }
    return DrawingStrategy(global_strategy=global_strategy, region_styles=region_styles)


def assign_region_style(
    region_type: str,
    depth_layer: str,
    is_subject: bool,
    *,
    detail: float = 0.75,
    density: float = 0.8,
    base_width: float = 1.1,
    stroke_cfg: dict | None = None,
) -> RegionStyle:
    stroke_cfg = stroke_cfg or {}
    jitter = float(stroke_cfg.get("jitter_px", 0.7))
    building_jitter = float(stroke_cfg.get("building_jitter_px", 0.25))
    vegetation_jitter = float(stroke_cfg.get("vegetation_jitter_px", 1.4))
    opacity = 0.65
    edge = 0.8 * detail
    hatch = 0.65 * density
    texture = 0.55 * density
    simplify = 1.6
    min_len = 10.0
    angles: tuple[float, ...] = (35.0,)
    suppress = False

    if region_type == "sky":
        edge, hatch, texture, opacity, simplify, min_len, angles, suppress = 0.10, 0.08, 0.05, 0.35, 3.0, 22.0, (5.0,), True
    elif region_type == "building":
        edge, hatch, texture, opacity, simplify, min_len, angles = 1.18 * detail, 0.95 * density, 0.35, 0.88, 0.9, 14.0, (45.0, -45.0)
        jitter = building_jitter
    elif region_type == "person":
        edge, hatch, texture, opacity, simplify, min_len, angles = 1.25 * detail, 0.55 * density, 0.25, 0.9, 0.8, 5.0, (65.0,)
    elif region_type == "vegetation":
        edge, hatch, texture, opacity, simplify, min_len, angles = 0.62 * detail, 0.62 * density, 1.15 * density, 0.58, 2.3, 7.0, (25.0, 115.0)
        jitter = vegetation_jitter
    elif region_type == "water":
        edge, hatch, texture, opacity, simplify, min_len, angles = 0.45 * detail, 0.45 * density, 0.75 * density, 0.52, 2.0, 13.0, (0.0,)
    elif region_type == "road":
        edge, hatch, texture, opacity, simplify, min_len, angles = 0.7 * detail, 0.78 * density, 0.45, 0.62, 1.8, 13.0, (18.0,)
    elif region_type == "mountain":
        edge, hatch, texture, opacity, simplify, min_len, angles = 0.36 * detail, 0.35 * density, 0.28, 0.45, 2.8, 20.0, (10.0,)

    if depth_layer == "background":
        edge *= 0.50
        hatch *= 0.48
        texture *= 0.48
        opacity *= 0.72
        min_len *= 1.55
        simplify *= 1.45
    elif depth_layer == "foreground":
        edge *= 1.06
        hatch *= 1.08
        texture *= 1.05

    if is_subject:
        edge *= 1.35
        hatch *= 1.20
        opacity = min(0.95, opacity * 1.25)
        min_len *= 0.75
        simplify *= 0.7

    return RegionStyle(
        semantic_region=region_type,
        depth_layer=depth_layer,
        is_subject=is_subject,
        edge_strength=edge,
        hatch_strength=hatch,
        texture_strength=texture,
        line_width=base_width,
        opacity=opacity,
        jitter_px=jitter,
        simplify_tolerance=simplify,
        min_stroke_length=min_len,
        hatch_angles=angles,
        suppress_edges=suppress,
    )

