import numpy as np

from src.models import RegionMap
from src.style_planner import create_drawing_strategy


class DummyAnalysis:
    content = {"main_subject": "building"}


def test_drawing_strength_parameters_affect_styles():
    labels = np.zeros((20, 20), dtype=np.uint8)
    regions = RegionMap(
        labels=labels,
        label_names={0: "building"},
        semantic_masks={"building": np.ones((20, 20), dtype=bool)},
        depth_masks={
            "foreground": np.zeros((20, 20), dtype=bool),
            "midground": np.ones((20, 20), dtype=bool),
            "background": np.zeros((20, 20), dtype=bool),
        },
        subject_mask=np.zeros((20, 20), dtype=bool),
        main_subject="building",
    )
    low = create_drawing_strategy(DummyAnalysis(), regions, {"drawing": {"detail_level": 0.5, "contour_strength": 0.6, "hatch_strength": 0.5}, "stroke": {}})
    high = create_drawing_strategy(DummyAnalysis(), regions, {"drawing": {"detail_level": 0.5, "contour_strength": 1.4, "hatch_strength": 1.2}, "stroke": {}})

    assert high.style_for("building").edge_strength > low.style_for("building").edge_strength
    assert high.style_for("building").hatch_strength > low.style_for("building").hatch_strength

