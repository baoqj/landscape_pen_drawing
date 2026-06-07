from pathlib import Path

import cv2
import numpy as np

from src.pencil_renderer import (
    generate_pencil_stroke_map,
    generate_pencil_tone_map,
    generate_procedural_pencil_texture,
    render_pencil_drawing,
)
from src.pipeline import render_image_to_output


def synthetic_building_landscape(width: int = 96, height: int = 72) -> np.ndarray:
    image = np.full((height, width, 3), 230, dtype=np.uint8)
    image[:24] = [190, 215, 235]
    image[24:] = [190, 205, 172]
    cv2.rectangle(image, (24, 20), (74, 58), (150, 145, 134), -1)
    cv2.rectangle(image, (24, 20), (74, 58), (45, 45, 42), 2)
    for x in range(32, 70, 12):
        cv2.line(image, (x, 24), (x, 55), (70, 70, 68), 1)
    cv2.line(image, (24, 40), (74, 40), (70, 70, 68), 1)
    return image


def test_pencil_maps_are_bounded_and_nonblank():
    gray = cv2.cvtColor(synthetic_building_landscape(), cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0

    stroke_map = generate_pencil_stroke_map(gray, kernel_size=4, stroke_width=1, num_directions=8)
    tone_map = generate_pencil_tone_map(gray, tone_group=1, tone_smoothing=1.0)
    texture_map = generate_procedural_pencil_texture(gray.shape, num_directions=8, seed=11)

    for layer in [stroke_map, tone_map, texture_map]:
        assert layer.shape == gray.shape
        assert 0.0 <= float(layer.min()) <= float(layer.max()) <= 1.0
        assert float(layer.std()) > 0.001


def test_render_pencil_drawing_returns_debug_layers():
    image = synthetic_building_landscape()
    result = render_pencil_drawing(
        image,
        {
            "pencil": {
                "auto_kernel": False,
                "kernel_size": 5,
                "num_directions": 8,
                "texture_seed": 12,
            }
        },
    )

    assert result.image.size == (image.shape[1], image.shape[0])
    assert result.params["kernel_size"] == 5
    assert result.combined_map.shape == image.shape[:2]
    assert float(result.combined_map.std()) > 0.001


def test_pipeline_pencil_mode_writes_expected_outputs(tmp_path: Path):
    input_path = tmp_path / "input.png"
    output_dir = tmp_path / "out"
    cv2.imwrite(str(input_path), cv2.cvtColor(synthetic_building_landscape(), cv2.COLOR_RGB2BGR))

    result = render_image_to_output(
        input_path,
        output_dir,
        {
            "effect": {"type": "pencil"},
            "image": {"max_size": 120, "paper_color": [248, 245, 238]},
            "pencil": {
                "auto_kernel": False,
                "kernel_size": 4,
                "num_directions": 6,
                "texture_seed": 5,
            },
            "architectural_style": {"learn_from_reference": False},
        },
    )

    assert result["stroke_count"] == 0
    assert (output_dir / "pencil_drawing.png").exists()
    assert (output_dir / "pen_drawing.png").exists()
    assert (output_dir / "debug" / "pencil_stroke_map.png").exists()
    assert (output_dir / "debug" / "pencil_tone_map.png").exists()
    assert (output_dir / "debug" / "pencil_texture_map.png").exists()
    assert "铅笔画策略" in (output_dir / "analysis_report.md").read_text(encoding="utf-8")
