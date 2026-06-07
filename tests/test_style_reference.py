from pathlib import Path

import cv2
import numpy as np

from src.style_reference import analyze_style_directory, resolve_architectural_style


def test_style_reference_extracts_line_metrics(tmp_path: Path):
    image = np.full((220, 260), 245, dtype=np.uint8)
    for x in range(40, 220, 32):
        cv2.line(image, (x, 25), (x, 195), 20, 2)
    for y in range(50, 180, 34):
        cv2.line(image, (25, y), (235, y), 20, 2)
    cv2.imwrite(str(tmp_path / "style.jpg"), image)

    metrics = analyze_style_directory(tmp_path)

    assert metrics is not None
    assert metrics.image_count == 1
    assert metrics.line_count > 5
    assert metrics.horizontal_ratio + metrics.vertical_ratio > 0.4


def test_resolve_architectural_style_merges_learned_reference(tmp_path: Path):
    image = np.full((180, 220), 245, dtype=np.uint8)
    for offset in range(20, 160, 28):
        cv2.line(image, (20, offset), (200, offset + 50), 20, 2)
    cv2.imwrite(str(tmp_path / "style.jpg"), image)

    style = resolve_architectural_style(
        {
            "architectural_style": {
                "preset": "learned_reference",
                "learn_from_reference": True,
                "style_reference_dir": str(tmp_path),
            }
        }
    )

    assert style["reference_summary"]["image_count"] == 1
    assert style["line_extend_px"] >= 7
    assert "facade_hatch_angle_deg" in style
    assert style["structure_line_type"] in {"straight", "slight_curve", "loose_curve", "sketch", "broken", "broken_curve"}
    assert style["facade_hatch_line_type"] in {"straight", "slight_curve", "loose_curve", "sketch", "broken", "broken_curve"}
