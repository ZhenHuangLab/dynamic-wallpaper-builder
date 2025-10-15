"""Core logic for building macOS dynamic wallpaper HEIC files."""

from __future__ import annotations

import base64
import json
import plistlib
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import List, Optional

from PIL import Image, ImageOps
from pillow_heif import register_heif_opener


class WallpaperBuildError(Exception):
    """Raised when the dynamic wallpaper build fails."""


@dataclass(slots=True)
class FrameSpec:
    """Represents a single frame in the dynamic wallpaper."""

    file_path: Path
    normalized_time: float
    appearance: Optional[str] = None


XMP_TEMPLATE = """<?xpacket begin='\ufeff' id='W5M0MpCehiHzreSzNTczkc9d'?>\n<x:xmpmeta xmlns:x='adobe:ns:meta/'>\n  <rdf:RDF xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#'>\n    <rdf:Description xmlns:apple_desktop='http://ns.apple.com/namespace/1.0/' apple_desktop:h24='{payload}'/>\n  </rdf:RDF>\n</x:xmpmeta>\n<?xpacket end='w'?>\n"""


def build_dynamic_wallpaper(
    config_path: Path,
    output_path: Path,
    *,
    quality: int = 90,
    resize_mode: str = "fit",
) -> Path:
    """Build a dynamic wallpaper HEIC file from the manifest at ``config_path``.

    Parameters
    ----------
    config_path:
        Path to the JSON manifest file describing frames and schedule.
    output_path:
        Destination path for the resulting HEIC file.
    quality:
        Encoder quality (0-100). Higher is better quality but larger files.
    resize_mode:
        Behaviour when frame dimensions differ. ``"fit"`` resizes every frame to
        match the first frame. ``"strict"`` raises an error if sizes differ.

    Returns
    -------
    Path
        The path to the generated HEIC file.
    """

    frames, light_index, dark_index = _load_manifest(config_path)
    if len(frames) < 2:
        raise WallpaperBuildError("Dynamic wallpaper requires at least two frames.")

    output_path = output_path.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    register_heif_opener(quality=quality)

    pil_frames: List[Image.Image] = []
    target_size = None

    for frame in frames:
        if not frame.file_path.exists():
            raise WallpaperBuildError(f"Image file not found: {frame.file_path}")

        with Image.open(frame.file_path) as src:
            src = ImageOps.exif_transpose(src)
            converted = src.convert("RGB")
            converted.load()

        if target_size is None:
            target_size = converted.size
        elif converted.size != target_size:
            if resize_mode == "fit":
                converted = converted.resize(target_size, Image.Resampling.LANCZOS)
            elif resize_mode == "strict":
                raise WallpaperBuildError(
                    "All images must share the same dimensions when resize_mode='strict'."
                )
            else:
                raise WallpaperBuildError(f"Unknown resize_mode '{resize_mode}'.")

        pil_frames.append(converted)

    plist_dict: dict[str, object] = {
        "ti": [
            {"t": round(frame.normalized_time, 6), "i": index}
            for index, frame in enumerate(frames)
        ]
    }

    appearance_dict: dict[str, int] = {}
    if light_index is not None:
        appearance_dict["l"] = light_index
    if dark_index is not None:
        appearance_dict["d"] = dark_index
    if appearance_dict:
        plist_dict["ap"] = appearance_dict

    plist_bytes = plistlib.dumps(plist_dict, fmt=plistlib.FMT_BINARY)
    payload = base64.b64encode(plist_bytes).decode("ascii")
    xmp_bytes = XMP_TEMPLATE.format(payload=payload).encode("utf-8")

    primary = pil_frames[0]
    primary.info["xmp"] = xmp_bytes

    append_images = pil_frames[1:]
    primary.save(
        output_path,
        format="HEIF",
        save_all=True,
        append_images=append_images,
        quality=quality,
        primary_index=0,
    )

    for image in pil_frames:
        image.close()

    return output_path


def _load_manifest(config_path: Path) -> tuple[list[FrameSpec], Optional[int], Optional[int]]:
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise WallpaperBuildError(f"Manifest not found: {config_path}") from exc
    except json.JSONDecodeError as exc:
        raise WallpaperBuildError(f"Failed to parse JSON manifest: {exc}") from exc

    if not isinstance(data, dict) or "frames" not in data:
        raise WallpaperBuildError("Manifest must be a JSON object with a 'frames' array.")

    frames_data = data["frames"]
    if not isinstance(frames_data, list) or not frames_data:
        raise WallpaperBuildError("Manifest 'frames' must be a non-empty list.")

    base_dir = config_path.parent
    frames: List[FrameSpec] = []

    for raw in frames_data:
        if not isinstance(raw, dict):
            raise WallpaperBuildError("Each frame entry must be a JSON object.")

        path_value = raw.get("file") or raw.get("image")
        time_value = raw.get("time")
        if path_value is None or time_value is None:
            raise WallpaperBuildError("Frame entries require 'file' and 'time' fields.")

        file_path = Path(path_value)
        if not file_path.is_absolute():
            file_path = (base_dir / file_path).resolve()

        normalized_time = _parse_time_fraction(str(time_value))

        appearance = _parse_appearance(raw)

        frames.append(FrameSpec(file_path=file_path, normalized_time=normalized_time, appearance=appearance))

    frames.sort(key=lambda f: f.normalized_time)

    for earlier, later in zip(frames, frames[1:]):
        if later.normalized_time <= earlier.normalized_time:
            raise WallpaperBuildError("Frame times must be strictly increasing within the 24h cycle.")

    light_index = _first_index_with(frames, "light")
    dark_index = _first_index_with(frames, "dark")

    return frames, light_index, dark_index


def _parse_time_fraction(time_value: str) -> float:
    parts = time_value.split(":")
    if len(parts) not in (2, 3):
        raise WallpaperBuildError(f"Time '{time_value}' must use HH:MM or HH:MM:SS format.")

    try:
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = int(parts[2]) if len(parts) == 3 else 0
    except ValueError as exc:
        raise WallpaperBuildError(f"Time '{time_value}' contains invalid numbers.") from exc

    if hours == 24 and minutes == 0 and seconds == 0:
        return 1.0

    if not (0 <= hours < 24):
        raise WallpaperBuildError(f"Hour out of range in '{time_value}'.")
    if not (0 <= minutes < 60) or not (0 <= seconds < 60):
        raise WallpaperBuildError(f"Minute/second out of range in '{time_value}'.")

    total_seconds = hours * 3600 + minutes * 60 + seconds
    day_seconds = timedelta(days=1).total_seconds()
    return total_seconds / day_seconds


def _parse_appearance(raw: dict) -> Optional[str]:
    appearance = raw.get("appearance")
    if isinstance(appearance, str):
        appearance = appearance.strip().lower()
    elif raw.get("light") is True:
        appearance = "light"
    elif raw.get("dark") is True:
        appearance = "dark"
    else:
        appearance = None

    if appearance not in {None, "light", "dark"}:
        raise WallpaperBuildError(
            "Appearance must be one of 'light', 'dark', or omitted."
        )

    return appearance


def _first_index_with(frames: List[FrameSpec], appearance: str) -> Optional[int]:
    for index, frame in enumerate(frames):
        if frame.appearance == appearance:
            return index
    return None
