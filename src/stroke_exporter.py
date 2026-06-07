from __future__ import annotations

from pathlib import Path

from .models import DrawingStrategy, ImageAnalysisResult, Stroke
from .utils import write_json


def export_strokes_json(
    strokes: list[Stroke],
    analysis: ImageAnalysisResult,
    strategy: DrawingStrategy,
    output_path: str | Path,
) -> None:
    data = {
        "analysis": analysis.to_dict(),
        "strategy": strategy.to_dict(),
        "stroke_count": len(strokes),
        "strokes": [stroke.to_dict() for stroke in strokes],
    }
    write_json(output_path, data)

