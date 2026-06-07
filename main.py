from __future__ import annotations

import argparse
from pathlib import Path

from src.image_io import deep_update, load_config
from src.pipeline import render_image_to_output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze a landscape image and render a programmatic pen drawing.")
    parser.add_argument("--input", required=True, help="Input JPG, PNG, or WebP image.")
    parser.add_argument("--output", required=True, help="Output directory.")
    parser.add_argument("--mode", choices=["pure", "enhanced"], default="pure", help="Enhanced is reserved for optional model plugins.")
    parser.add_argument("--effect", choices=["pen", "pencil"], default=None, help="Output effect type.")
    parser.add_argument("--paper", default="A4", help="SVG paper preset, currently A4 by default.")
    parser.add_argument("--detail", type=float, default=None, help="Override drawing.detail_level.")
    parser.add_argument("--stroke-density", type=float, default=None, help="Override drawing.stroke_density.")
    parser.add_argument("--max-size", type=int, default=None, help="Override image.max_size.")
    parser.add_argument("--building-style", default=None, help="Architectural style preset, e.g. learned_reference, architectural_extended_line, modern_facade_grid.")
    parser.add_argument("--style-dir", default=None, help="Reference pen drawing style directory.")
    parser.add_argument("--structure-line-type", default=None, choices=["straight", "slight_curve", "loose_curve", "sketch", "broken", "broken_curve"], help="Building structure line type.")
    parser.add_argument("--facade-line-type", default=None, choices=["straight", "slight_curve", "loose_curve", "sketch", "broken", "broken_curve"], help="Building facade hatch line type.")
    parser.add_argument("--entourage-line-type", default=None, choices=["straight", "slight_curve", "loose_curve", "sketch", "broken", "broken_curve"], help="Non-building entourage line type.")
    parser.add_argument("--pencil-directions", type=int, default=None, help="Pencil stroke direction count.")
    parser.add_argument("--pencil-stroke-darkness", type=float, default=None, help="Pencil stroke darkness exponent.")
    parser.add_argument("--pencil-tone-darkness", type=float, default=None, help="Pencil tone darkness multiplier.")
    parser.add_argument("--pencil-texture-strength", type=float, default=None, help="Pencil texture strength.")
    parser.add_argument("--config", default=str(Path(__file__).with_name("config.yaml")), help="Path to config.yaml.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    overrides: dict = {"svg": {"page_size": args.paper}}
    if args.detail is not None:
        overrides.setdefault("drawing", {})["detail_level"] = args.detail
    if args.stroke_density is not None:
        overrides.setdefault("drawing", {})["stroke_density"] = args.stroke_density
    if args.max_size is not None:
        overrides.setdefault("image", {})["max_size"] = args.max_size
    if args.effect is not None:
        overrides.setdefault("effect", {})["type"] = args.effect
    if args.building_style is not None:
        overrides.setdefault("architectural_style", {})["preset"] = args.building_style
    if args.style_dir is not None:
        overrides.setdefault("architectural_style", {})["style_reference_dir"] = args.style_dir
    if args.structure_line_type is not None:
        overrides.setdefault("architectural_style", {})["structure_line_type"] = args.structure_line_type
    if args.facade_line_type is not None:
        overrides.setdefault("architectural_style", {})["facade_hatch_line_type"] = args.facade_line_type
    if args.entourage_line_type is not None:
        overrides.setdefault("architectural_style", {})["entourage_line_type"] = args.entourage_line_type
    if args.pencil_directions is not None:
        overrides.setdefault("pencil", {})["num_directions"] = args.pencil_directions
    if args.pencil_stroke_darkness is not None:
        overrides.setdefault("pencil", {})["stroke_darkness"] = args.pencil_stroke_darkness
    if args.pencil_tone_darkness is not None:
        overrides.setdefault("pencil", {})["tone_darkness"] = args.pencil_tone_darkness
    if args.pencil_texture_strength is not None:
        overrides.setdefault("pencil", {})["texture_strength"] = args.pencil_texture_strength
    config = deep_update(config, overrides)

    result = render_image_to_output(args.input, args.output, config, args.mode)
    print(f"Generated {result['stroke_count']} strokes in {result['output_dir']}")


if __name__ == "__main__":
    main()
