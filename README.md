# Dynamic Wallpaper Builder

Create macOS dynamic wallpapers (HEIC) from time-tagged images.

English | [中文版](README_zh.md)

This project provides a Python CLI that converts a list of time-tagged images into a macOS dynamic wallpaper (`.heic`) file. Each frame is assigned to a specific time of day, so macOS can automatically switch between them as the day progresses.

## Features

- Accepts PNG, JPEG, and other formats supported by Pillow.
- Generates HEIC sequences with embedded `apple_desktop:h24` metadata for 24‑hour timelines.
- Optional light/dark appearance mapping for macOS appearance switching.
- Automatic resizing to match the first frame (configurable).

## Prerequisites

- macOS 11 or later with Python 3.10+.
- `libheif` is bundled with the [`pillow-heif`](https://pypi.org/project/pillow-heif/) wheels on macOS; no extra system packages are required.

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

dynamic-wallpaper --config examples/schedule.json --output MyDynamicWall.heic
```

The command creates `MyDynamicWall.heic` containing the frames defined in `examples/schedule.json`.

## Manifest Format

The CLI expects a JSON file with an array of frames ordered by time. Each entry requires:

- `file`: Path to the image (relative paths are resolved from the manifest directory).
- `time`: Time in `HH:MM` or `HH:MM:SS` (24-hour clock).
- Optional `appearance`: Set to `light` or `dark` to mark the frame for macOS appearance switching.

Example (`examples/schedule.json`):

```json
{
  "frames": [
    {"file": "sunrise.png", "time": "05:30", "appearance": "light"},
    {"file": "midday.png", "time": "12:00"},
    {"file": "sunset.png", "time": "18:30"},
    {"file": "night.png", "time": "23:00", "appearance": "dark"}
  ]
}
```

## CLI Options

- `--config`: Path to the manifest file (required).
- `--output`: Destination HEIC file (required).
- `--quality`: HEVC quality between 1 and 100 (default 90).
- `--resize-mode`: `fit` (default) rescales frames to match the first frame; `strict` raises an error if dimensions differ.

## Using the Wallpaper on macOS

1. Copy the generated `.heic` file to a location such as `~/Pictures/Wallpapers/`.
2. Open **System Settings → Wallpaper**.
3. Click the `+` button and pick the generated file. macOS will inspect the embedded timeline metadata and switch frames automatically according to the assigned times.

## Sample Assets

The `examples/` folder contains four placeholder PNG images and the manifest shown above. You can replace them with your own imagery while keeping the same filenames, or point the manifest to different paths.

## Development Notes

- Run `pip install -e .[dev]` to install optional linting tools (`black`, `ruff`).
- The core build logic lives in `dynamic_wallpaper/builder.py`; the CLI entry point is `dynamic_wallpaper/cli.py`.
- Tests are not included yet; consider adding integration tests that open the generated HEIC and verify the XMP payload if you extend the project.
