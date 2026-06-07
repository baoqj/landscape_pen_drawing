import cv2
import numpy as np

from src.stroke_generator import generate_architectural_plane_hatching, generate_building_structure_strokes


def test_building_structure_strokes_extend_lines():
    image = np.full((120, 160, 3), 240, dtype=np.uint8)
    mask = np.zeros((120, 160), dtype=bool)
    mask[30:95, 35:130] = True
    cv2.rectangle(image, (35, 30), (130, 95), (40, 40, 40), 2)
    cv2.line(image, (42, 60), (124, 60), (20, 20, 20), 2)

    strokes = generate_building_structure_strokes(
        image,
        mask,
        {"line_extend_px": 14, "draw_mass_boxes": True, "max_structure_lines": 20},
    )

    assert strokes
    assert any(stroke.stroke_type in {"structure_line_extended", "mass_edge_extension", "corner_tick"} for stroke in strokes)


def test_building_structure_strokes_can_use_curved_line_type():
    image = np.full((120, 160, 3), 240, dtype=np.uint8)
    mask = np.zeros((120, 160), dtype=bool)
    mask[30:95, 35:130] = True
    cv2.rectangle(image, (35, 30), (130, 95), (40, 40, 40), 2)
    cv2.line(image, (42, 60), (124, 60), (20, 20, 20), 2)

    strokes = generate_building_structure_strokes(
        image,
        mask,
        {
            "line_extend_px": 14,
            "structure_line_type": "slight_curve",
            "line_curvature_px": 5,
            "draw_mass_boxes": False,
            "max_structure_lines": 20,
        },
    )

    assert strokes
    assert any("slight_curve" in stroke.stroke_type for stroke in strokes)
    assert any(len(stroke.points) > 2 for stroke in strokes)


def test_architectural_plane_hatching_generates_straight_building_lines():
    gray = np.full((100, 140), 120, dtype=np.uint8)
    mask = np.zeros((100, 140), dtype=bool)
    mask[20:82, 30:115] = True

    strokes = generate_architectural_plane_hatching(
        mask,
        gray,
        {"facade_hatch_spacing_px": 12, "facade_hatch_angle_deg": 45, "max_facade_hatch_lines": 30},
    )

    assert strokes
    assert all(stroke.semantic_region == "building" for stroke in strokes)
    assert all(stroke.stroke_type == "facade_plane_hatch_straight" for stroke in strokes)


def test_architectural_plane_hatching_can_use_broken_lines():
    gray = np.full((100, 140), 120, dtype=np.uint8)
    mask = np.zeros((100, 140), dtype=bool)
    mask[20:82, 30:115] = True

    strokes = generate_architectural_plane_hatching(
        mask,
        gray,
        {
            "facade_hatch_spacing_px": 14,
            "facade_hatch_angle_deg": 0,
            "facade_hatch_line_type": "broken",
            "broken_gap_ratio": 0.35,
            "max_facade_hatch_lines": 40,
        },
    )

    assert strokes
    assert all(stroke.stroke_type == "facade_plane_hatch_broken" for stroke in strokes)
