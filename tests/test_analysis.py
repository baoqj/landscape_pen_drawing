import numpy as np

from src.image_analysis import analyze_image
from src.segmentation import segment_regions
from src.subject_detection import detect_subject


def test_analysis_and_segmentation_on_synthetic_landscape():
    image = np.zeros((120, 180, 3), dtype=np.uint8)
    image[:50] = [170, 205, 235]
    image[50:90] = [90, 145, 80]
    image[90:] = [145, 135, 120]
    image[42:88, 70:125] = [170, 150, 125]
    image[55:70, 88:105] = [50, 50, 48]

    analysis = analyze_image(image)
    regions = segment_regions(image, analysis)
    subject = detect_subject(image, analysis, regions)

    assert analysis.image["width"] == 180
    assert 0 <= analysis.tone["mean_luminance"] <= 1
    assert "sky" in analysis.content["detected_regions"]
    assert subject.shape == image.shape[:2]
    assert regions.labels.shape == image.shape[:2]

