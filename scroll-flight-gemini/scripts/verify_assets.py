#!/usr/bin/env python3
"""Validate scroll-flight source assets without modifying them."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from fractions import Fraction
from pathlib import Path

try:
    from PIL import Image
except ImportError:  # Reported as an actionable validation issue.
    Image = None


PHASES = {"stills", "clips", "all"}


def load_manifest(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("manifest must contain a JSON object")
    required = {"version", "scenes", "transitions"}
    missing = sorted(required - data.keys())
    if missing:
        raise ValueError(f"manifest missing keys: {', '.join(missing)}")
    if not isinstance(data["scenes"], list) or not isinstance(
        data["transitions"], list
    ):
        raise ValueError("manifest scenes and transitions must be arrays")
    return data


def _resolve_source(asset_root: Path, relative_value: str) -> Path:
    relative = Path(relative_value)
    if relative.is_absolute():
        raise ValueError(f"absolute source path is not allowed: {relative_value}")
    resolved_root = asset_root.resolve()
    resolved = (resolved_root / relative).resolve()
    if not resolved.is_relative_to(resolved_root):
        raise ValueError(f"source path is outside scroll-assets: {relative_value}")
    return resolved


def validate_image(
    path: Path,
    min_width: int = 1280,
    min_height: int = 720,
) -> list[str]:
    if Image is None:
        return ["Pillow is not installed"]
    if not path.exists():
        return [f"missing image: {path}"]
    try:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            width, height = image.size
    except Exception as exc:  # Pillow exposes format-specific exception types.
        return [f"unreadable image {path}: {exc}"]
    if width < min_width or height < min_height:
        return [
            f"image {path} is {width}x{height}; minimum dimensions are "
            f"{min_width}x{min_height}"
        ]
    return []


def probe_video(path: Path) -> dict:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise RuntimeError("ffprobe is not installed or not available on PATH")
    command = [
        ffprobe,
        "-v",
        "error",
        "-show_entries",
        "stream=codec_type,codec_name,width,height,r_frame_rate:format=duration",
        "-of",
        "json",
        str(path),
    ]
    completed = subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(completed.stdout)
    streams = [
        stream
        for stream in data.get("streams", [])
        if stream.get("codec_type") == "video"
    ]
    if not streams:
        raise ValueError(f"no video stream found: {path}")
    stream = streams[0]
    duration = float(data.get("format", {}).get("duration", 0) or 0)
    frame_rate = float(Fraction(stream.get("r_frame_rate", "0/1")))
    width = int(stream.get("width", 0) or 0)
    height = int(stream.get("height", 0) or 0)
    issues = []
    if duration <= 0:
        issues.append("duration must be positive")
    if width < 720 or height < 720:
        issues.append(f"video dimensions {width}x{height} must be at least 720x720")
    if frame_rate <= 0:
        issues.append("frame rate must be positive")
    return {
        "path": str(path),
        "codec": stream.get("codec_name"),
        "width": width,
        "height": height,
        "duration": duration,
        "frameRate": frame_rate,
        "issues": issues,
    }


def verify_assets(manifest_path: Path, phase: str) -> dict:
    if phase not in PHASES:
        raise ValueError(f"phase must be one of: {', '.join(sorted(PHASES))}")
    manifest = load_manifest(manifest_path)
    asset_root = manifest_path.resolve().parent
    issues: list[str] = []
    files: list[dict] = []

    if phase in {"stills", "all"}:
        for scene in manifest["scenes"]:
            try:
                path = _resolve_source(asset_root, scene["still"])
                image_issues = validate_image(path)
            except (KeyError, TypeError, ValueError) as exc:
                path = asset_root
                image_issues = [str(exc)]
            files.append(
                {
                    "id": scene.get("id", "unknown"),
                    "kind": "still",
                    "path": str(path),
                    "valid": not image_issues,
                }
            )
            issues.extend(image_issues)

    if phase in {"clips", "all"}:
        for transition in manifest["transitions"]:
            path = asset_root
            try:
                path = _resolve_source(asset_root, transition["video"])
                if not path.exists():
                    raise FileNotFoundError(f"missing video: {path}")
                probe = probe_video(path)
                video_issues = [
                    f"video {path}: {issue}" for issue in probe["issues"]
                ]
            except (KeyError, TypeError, ValueError, RuntimeError, OSError, subprocess.SubprocessError) as exc:
                probe = {}
                video_issues = [str(exc)]
            files.append(
                {
                    "id": transition.get("id", "unknown"),
                    "kind": "clip",
                    "path": str(path),
                    "valid": not video_issues,
                    "probe": probe,
                }
            )
            issues.extend(video_issues)

    return {
        "valid": not issues,
        "phase": phase,
        "issues": issues,
        "files": files,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate scroll-flight assets.")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--phase", choices=sorted(PHASES), default="all")
    parser.add_argument("--json", action="store_true", dest="as_json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = verify_assets(args.manifest, args.phase)
    if args.as_json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"Phase: {report['phase']}")
        print(f"Valid: {'yes' if report['valid'] else 'no'}")
        for issue in report["issues"]:
            print(f"- {issue}")
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
