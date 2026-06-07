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
    parser.add_argument("--paper", default="A4", help="SVG paper preset, currently A4 by default.")
    parser.add_argument("--detail", type=float, default=None, help="Override drawing.detail_level.")
    parser.add_argument("--stroke-density", type=float, default=None, help="Override drawing.stroke_density.")
    parser.add_argument("--max-size", type=int, default=None, help="Override image.max_size.")
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
    config = deep_update(config, overrides)

    result = render_image_to_output(args.input, args.output, config, args.mode)
    print(f"Generated {result['stroke_count']} strokes in {result['output_dir']}")


if __name__ == "__main__":
    main()
