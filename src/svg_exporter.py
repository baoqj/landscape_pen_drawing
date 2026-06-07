from __future__ import annotations

from pathlib import Path

import svgwrite

from .models import Stroke


def export_svg(strokes: list[Stroke], output_path: str | Path, canvas_size: tuple[int, int], config: dict) -> None:
    width, height = canvas_size
    svg_cfg = config.get("svg", {})
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if svg_cfg.get("scale_to_mm", True):
        page_w_mm = 210.0 if svg_cfg.get("page_size", "A4").upper() == "A4" else float(width)
        page_h_mm = page_w_mm * height / max(width, 1)
        dwg = svgwrite.Drawing(str(path), size=(f"{page_w_mm:.2f}mm", f"{page_h_mm:.2f}mm"), viewBox=f"0 0 {width} {height}")
    else:
        dwg = svgwrite.Drawing(str(path), size=(f"{width}px", f"{height}px"), viewBox=f"0 0 {width} {height}")

    dwg.add(dwg.rect(insert=(0, 0), size=(width, height), fill="rgb(248,245,238)"))
    by_layer: dict[str, list[Stroke]] = {}
    for stroke in strokes:
        by_layer.setdefault(stroke.layer, []).append(stroke)

    for layer, layer_strokes in by_layer.items():
        group = dwg.g(id=_safe_id(layer))
        for stroke in layer_strokes:
            if len(stroke.points) < 2:
                continue
            group.add(
                dwg.polyline(
                    points=[(round(x, 2), round(y, 2)) for x, y in stroke.points],
                    fill="none",
                    stroke="#1f1f1d",
                    stroke_width=max(0.1, stroke.width),
                    stroke_opacity=max(0.05, min(1.0, stroke.opacity)),
                    stroke_linecap="round",
                    stroke_linejoin="round",
                    id=stroke.id,
                )
            )
        dwg.add(group)
    dwg.save()


def _safe_id(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "_-" else "_" for ch in value)

