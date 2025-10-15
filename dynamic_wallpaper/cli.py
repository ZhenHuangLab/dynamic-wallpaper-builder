"""Command line entry point for dynamic wallpaper builder."""

from __future__ import annotations

import argparse
from pathlib import Path

from .builder import build_dynamic_wallpaper, WallpaperBuildError


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create a macOS dynamic wallpaper (HEIC) from time-tagged images.",
    )
    parser.add_argument(
        "--config",
        required=True,
        type=Path,
        help="Path to JSON manifest describing frames and 24-hour schedule.",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Destination HEIC file path (will be created or overwritten).",
    )
    parser.add_argument(
        "--quality",
        type=int,
        default=90,
        help="HEIF encoder quality (1-100). Default: 90",
    )
    parser.add_argument(
        "--resize-mode",
        default="fit",
        choices=["fit", "strict"],
        help="How to handle mismatched image sizes: 'fit' resizes to match the first frame; 'strict' raises an error.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = create_parser()
    args = parser.parse_args(argv)

    if not 1 <= args.quality <= 100:
        parser.error("--quality must be between 1 and 100.")

    try:
        result_path = build_dynamic_wallpaper(
            args.config,
            args.output,
            quality=args.quality,
            resize_mode=args.resize_mode,
        )
    except WallpaperBuildError as exc:
        parser.exit(status=1, message=f"Error: {exc}\n")

    parser.exit(status=0, message=f"Created dynamic wallpaper: {result_path}\n")


if __name__ == "__main__":  # pragma: no cover - CLI entry
    main()
