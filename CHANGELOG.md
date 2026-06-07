# Changelog

## v0.3.0 - Architectural Pen Styles

- Added reference style analysis for `pics/style` pen drawings using Canny and Hough line statistics.
- Added learned architectural style parameters for line density, dominant hatch angle, line extension, and entourage simplification.
- Added building-specific stroke generation with extended construction lines, mass corner ticks, and straight facade hatching.
- Added architectural presets for extended hand lines, modern facade grids, historic vertical sketches, dense shadows, and light entourage blank space.
- Added CLI and desktop controls for selecting architectural pen styles and reference directories.

## v0.2.0 - Desktop UI

- Added a Tkinter desktop app for browsing image directories and rendering selected or batched images.
- Added style presets for balanced, architecture detail, botanical sketch, minimal whitespace, dense cross-hatching, and waterline scenes.
- Added UI controls for image, drawing, hatching, stroke, and SVG parameters.
- Refactored rendering into a reusable pipeline shared by CLI and desktop UI.

## v0.1.0 - Initial Release

- Added pure OpenCV/NumPy landscape image analysis pipeline.
- Added heuristic semantic segmentation for sky, vegetation, water, building, road, mountain/background, person candidates, and ground.
- Added subject detection using saliency, local contrast, edge energy, center weighting, and semantic weighting.
- Added pen drawing renderer with contour strokes, building structure lines, hatching, cross-hatching, vegetation texture strokes, and water ripples.
- Added SVG and JSON stroke export for plotter-friendly downstream workflows.
- Added CLI, configuration file, README, and unit tests.
