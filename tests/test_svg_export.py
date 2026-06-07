from pathlib import Path

from src.models import Stroke
from src.svg_exporter import export_svg


def test_export_svg_writes_polyline(tmp_path: Path):
    stroke = Stroke(
        id="stroke_000001",
        layer="layer_01_main_contours",
        semantic_region="building",
        stroke_type="structure_line",
        points=[(1, 1), (10, 10)],
        width=0.8,
        opacity=0.7,
        priority=1,
        drawing_order=1,
    )
    out = tmp_path / "drawing.svg"
    export_svg([stroke], out, (20, 20), {"svg": {"scale_to_mm": False}})

    text = out.read_text(encoding="utf-8")
    assert "<polyline" in text
    assert "stroke_000001" in text

