import numpy as np

from src.hatch_generator import clip_line_to_mask, generate_hatching


def test_clip_line_to_mask_splits_to_inside_segments():
    mask = np.zeros((40, 40), dtype=bool)
    mask[10:30, 12:28] = True
    segments = clip_line_to_mask([(0, 20), (39, 20)], mask)

    assert len(segments) == 1
    assert 10 <= segments[0][0][0] <= 14
    assert 26 <= segments[0][-1][0] <= 30


def test_generate_hatching_returns_strokes_inside_mask():
    mask = np.zeros((80, 80), dtype=bool)
    mask[20:60, 20:60] = True
    density = np.zeros((80, 80), dtype=np.float32)
    density[mask] = 0.8

    strokes = generate_hatching(mask, density, 45, semantic_region="building", min_spacing_px=6, max_spacing_px=12)

    assert strokes
    assert all(stroke.semantic_region == "building" for stroke in strokes)
    assert all(len(stroke.points) >= 2 for stroke in strokes)

