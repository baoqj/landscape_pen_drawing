from __future__ import annotations

from .models import DrawingStrategy, ImageAnalysisResult, RegionMap, RegionStyle


def create_drawing_strategy(analysis: ImageAnalysisResult, regions: RegionMap, config: dict | None = None) -> DrawingStrategy:
    config = config or {}
    drawing_cfg = config.get("drawing", {})
    stroke_cfg = config.get("stroke", {})
    arch_cfg = config.get("architectural_style", {}).get("resolved", config.get("architectural_style", {}))

    detail = float(drawing_cfg.get("detail_level", 0.75))
    density = float(drawing_cfg.get("stroke_density", 0.8))
    contour_strength = float(drawing_cfg.get("contour_strength", 1.0))
    hatch_strength = float(drawing_cfg.get("hatch_strength", 0.85))
    texture_strength = float(drawing_cfg.get("texture_strength", 0.65))
    sky_suppression = float(drawing_cfg.get("sky_suppression", 0.9))
    background_simplification = float(drawing_cfg.get("background_simplification", 0.7))
    subject_boost = float(drawing_cfg.get("subject_boost", 1.3))

    base_width = float(stroke_cfg.get("base_width_px", 1.1))
    opacity_min = float(stroke_cfg.get("opacity_min", 0.45))
    opacity_max = float(stroke_cfg.get("opacity_max", 0.95))
    width_variation = float(stroke_cfg.get("width_variation", 0.25))
    architectural_structure_boost = float(arch_cfg.get("structure_boost", 1.0))
    entourage_edge_keep = float(arch_cfg.get("entourage_edge_keep", 1.0))
    vegetation_looseness = float(arch_cfg.get("vegetation_looseness", 1.0))
    entourage_line_type = str(arch_cfg.get("entourage_line_type", "loose_curve"))

    style_kwargs = {
        "detail": detail,
        "density": density,
        "base_width": base_width,
        "stroke_cfg": stroke_cfg,
        "contour_strength": contour_strength,
        "hatch_strength": hatch_strength,
        "texture_strength": texture_strength,
        "sky_suppression": sky_suppression,
        "background_simplification": background_simplification,
        "subject_boost": subject_boost,
        "opacity_min": opacity_min,
        "opacity_max": opacity_max,
        "architectural_structure_boost": architectural_structure_boost,
        "entourage_edge_keep": entourage_edge_keep,
        "vegetation_looseness": vegetation_looseness,
        "entourage_line_type": entourage_line_type,
    }

    region_styles: dict[str, RegionStyle] = {
        "default": assign_region_style("ground", "midground", False, **style_kwargs),
        "subject": assign_region_style(regions.main_subject, "midground", True, **style_kwargs),
    }

    for semantic in ["sky", "vegetation", "water", "building", "road", "mountain", "person", "ground"]:
        for depth in ["foreground", "midground", "background"]:
            region_styles[f"{semantic}:{depth}"] = assign_region_style(semantic, depth, False, **style_kwargs)
        region_styles[semantic] = assign_region_style(semantic, "midground", False, **style_kwargs)

    global_strategy = {
        "subject": "主体系数提高：保留更多轮廓、结构线和交叉排线。",
        "building": "建筑使用较长、较直的结构线，暗面使用规则排线。",
        "vegetation": "植物用团块轮廓、短曲线和点状笔触概括，不逐叶描绘。",
        "sky": "天空大面积留白，只在暗云或明显渐变处轻描。",
        "water": "水面使用水平短线和稀疏波纹，保留高光空白。",
        "background": "远景降低对比度和线条密度，避免抢主体。",
        "detail_level": detail,
        "stroke_density": density,
        "contour_strength": contour_strength,
        "hatch_strength": hatch_strength,
        "texture_strength": texture_strength,
        "sky_suppression": sky_suppression,
        "background_simplification": background_simplification,
        "subject_boost": subject_boost,
        "opacity_min": opacity_min,
        "opacity_max": opacity_max,
        "width_variation": width_variation,
        "architectural_structure_boost": architectural_structure_boost,
        "entourage_edge_keep": entourage_edge_keep,
        "vegetation_looseness": vegetation_looseness,
        "entourage_line_type": entourage_line_type,
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
    contour_strength: float = 1.0,
    hatch_strength: float = 0.85,
    texture_strength: float = 0.65,
    sky_suppression: float = 0.9,
    background_simplification: float = 0.7,
    subject_boost: float = 1.3,
    opacity_min: float = 0.45,
    opacity_max: float = 0.95,
    architectural_structure_boost: float = 1.0,
    entourage_edge_keep: float = 1.0,
    vegetation_looseness: float = 1.0,
    entourage_line_type: str = "loose_curve",
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
        keep = max(0.02, 1.0 - sky_suppression)
        edge, hatch, texture, opacity, simplify, min_len, angles, suppress = 0.30 * keep, 0.20 * keep, 0.12 * keep, 0.35, 3.0, 22.0, (5.0,), True
    elif region_type == "building":
        edge, hatch, texture, opacity, simplify, min_len, angles = 1.18 * detail, 0.95 * density, 0.35, 0.88, 0.9, 14.0, (45.0, -45.0)
        edge *= architectural_structure_boost
        hatch *= min(1.45, architectural_structure_boost)
        min_len *= max(0.72, 1.0 / max(architectural_structure_boost, 0.1))
        jitter = building_jitter
    elif region_type == "person":
        edge, hatch, texture, opacity, simplify, min_len, angles = 1.25 * detail, 0.55 * density, 0.25, 0.9, 0.8, 5.0, (65.0,)
    elif region_type == "vegetation":
        edge, hatch, texture, opacity, simplify, min_len, angles = 0.62 * detail, 0.62 * density, 1.15 * density, 0.58, 2.3, 7.0, (25.0, 115.0)
        edge *= entourage_edge_keep
        hatch *= max(0.28, entourage_edge_keep)
        texture *= vegetation_looseness
        opacity *= max(0.62, entourage_edge_keep)
        simplify *= vegetation_looseness
        jitter = vegetation_jitter
    elif region_type == "water":
        edge, hatch, texture, opacity, simplify, min_len, angles = 0.45 * detail, 0.45 * density, 0.75 * density, 0.52, 2.0, 13.0, (0.0,)
        edge *= max(0.38, entourage_edge_keep)
    elif region_type == "road":
        edge, hatch, texture, opacity, simplify, min_len, angles = 0.7 * detail, 0.78 * density, 0.45, 0.62, 1.8, 13.0, (18.0,)
        edge *= max(0.45, entourage_edge_keep)
    elif region_type == "mountain":
        edge, hatch, texture, opacity, simplify, min_len, angles = 0.36 * detail, 0.35 * density, 0.28, 0.45, 2.8, 20.0, (10.0,)
        edge *= entourage_edge_keep
        hatch *= entourage_edge_keep

    if depth_layer == "background":
        keep = max(0.12, 1.0 - 0.72 * background_simplification)
        edge *= keep
        hatch *= keep
        texture *= keep
        opacity *= 0.72
        min_len *= 1.0 + background_simplification
        simplify *= 1.0 + background_simplification * 0.65
    elif depth_layer == "foreground":
        edge *= 1.06
        hatch *= 1.08
        texture *= 1.05

    if is_subject:
        edge *= subject_boost
        hatch *= 0.85 + subject_boost * 0.25
        texture *= 0.85 + subject_boost * 0.18
        opacity = min(0.98, opacity * 1.25)
        min_len *= 0.75
        simplify *= 0.7

    edge *= contour_strength
    hatch *= hatch_strength
    texture *= texture_strength
    opacity = max(opacity_min, min(opacity_max, opacity))

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
