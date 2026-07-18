#!/usr/bin/env python3
"""Build responsive scroll-flight assets from validated manual sources."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    Image = None

from verify_assets import load_manifest, verify_assets


RUNTIME_FILES = ("scroll-flight.html", "scroll-flight.css", "scroll-flight.js")


class AssetValidationError(RuntimeError):
    """Raised when mandatory source assets cannot be processed safely."""


def _generated_root(manifest_path: Path) -> Path:
    asset_root = manifest_path.resolve().parent
    generated = (asset_root / "generated").resolve()
    if generated.name != "generated" or not generated.is_relative_to(asset_root):
        raise RuntimeError("refusing unsafe generated output path")
    return generated


def _reset_generated(manifest_path: Path) -> Path:
    generated = _generated_root(manifest_path)
    if generated.exists():
        shutil.rmtree(generated)
    generated.mkdir(parents=True)
    return generated


def _copy_runtime(runtime_source: Path, generated: Path) -> Path:
    runtime_output = generated / "runtime"
    runtime_output.mkdir(parents=True, exist_ok=True)
    for name in RUNTIME_FILES:
        source = runtime_source.resolve() / name
        if not source.is_file():
            raise FileNotFoundError(f"missing runtime template: {source}")
        shutil.copy2(source, runtime_output / name)
    return runtime_output


def select_mode(manifest_path: Path) -> str:
    still_report = verify_assets(manifest_path, "stills")
    if not still_report["valid"]:
        raise AssetValidationError("; ".join(still_report["issues"]))
    manifest = load_manifest(manifest_path)
    asset_root = manifest_path.resolve().parent
    clips_exist = all(
        (asset_root / transition["video"]).is_file()
        for transition in manifest["transitions"]
    )
    if not clips_exist:
        return "static"
    clip_report = verify_assets(manifest_path, "clips")
    return "video" if clip_report["valid"] else "static"


def _save_static_tier(source: Path, destination: Path, width: int, quality: int) -> None:
    if Image is None:
        raise RuntimeError("Pillow is required to build static tiers")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as opened:
        image = opened.convert("RGB")
        if image.width > width:
            height = max(1, round(image.height * width / image.width))
            image = image.resize((width, height), Image.Resampling.LANCZOS)
        image.save(destination, "WEBP", quality=quality, method=6)


def _base_config(manifest: dict, mode: str) -> dict:
    return {
        "version": 1,
        "mode": mode,
        "assetBase": "../",
        "sceneCount": manifest["sceneCount"],
        "scrollScreens": max(3, manifest["requiredClips"] * 2),
        "crossfadeFrames": 6,
        "scenes": [{"id": scene["id"]} for scene in manifest["scenes"]],
        "transitions": [
            {
                "id": transition["id"],
                "from": transition["from"],
                "to": transition["to"],
            }
            for transition in manifest["transitions"]
        ],
        "tiers": [],
    }


def build_static(manifest_path: Path, runtime_source: Path) -> Path:
    manifest = load_manifest(manifest_path)
    asset_root = manifest_path.resolve().parent
    generated = _reset_generated(manifest_path)
    runtime_output = _copy_runtime(runtime_source, generated)
    config = _base_config(manifest, "static")

    for tier in manifest["tiers"]:
        tier_dir = generated / tier["name"]
        scene_entries = []
        for scene in manifest["scenes"]:
            destination = tier_dir / f"{scene['id']}.webp"
            _save_static_tier(
                asset_root / scene["still"],
                destination,
                tier["width"],
                tier["quality"],
            )
            scene_entries.append(
                {"id": scene["id"], "path": f"{tier['name']}/{destination.name}"}
            )
        config["tiers"].append(
            {
                "name": tier["name"],
                "width": tier["width"],
                "scenes": scene_entries,
                "transitions": [],
            }
        )

    config_path = runtime_output / "config.json"
    config_path.write_text(
        json.dumps(config, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return config_path


def extract_transition(
    video: Path,
    output_dir: Path,
    width: int,
    quality: int,
    fps: int = 24,
) -> int:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is not installed or not available on PATH")
    output_dir.mkdir(parents=True, exist_ok=True)
    filter_graph = f"fps={fps},scale=min({width}\\,iw):-2:flags=lanczos"
    command = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(video),
        "-vf",
        filter_graph,
        "-c:v",
        "libwebp",
        "-quality",
        str(quality),
        str(output_dir / "frame-%06d.webp"),
    ]
    subprocess.run(command, check=True, capture_output=True, text=True)
    count = len(list(output_dir.glob("frame-*.webp")))
    if count == 0:
        raise RuntimeError(f"ffmpeg emitted no frames for {video}")
    return count


def build_video(manifest_path: Path, runtime_source: Path) -> Path:
    manifest = load_manifest(manifest_path)
    asset_root = manifest_path.resolve().parent
    generated = _reset_generated(manifest_path)
    runtime_output = _copy_runtime(runtime_source, generated)
    config = _base_config(manifest, "video")

    for tier in manifest["tiers"]:
        transition_entries = []
        for transition in manifest["transitions"]:
            relative_dir = Path(tier["name"]) / transition["id"]
            frame_count = extract_transition(
                asset_root / transition["video"],
                generated / relative_dir,
                tier["width"],
                tier["quality"],
            )
            transition_entries.append(
                {
                    "id": transition["id"],
                    "path": relative_dir.as_posix(),
                    "frameCount": frame_count,
                    "fps": 24,
                }
            )
        config["tiers"].append(
            {
                "name": tier["name"],
                "width": tier["width"],
                "scenes": [],
                "transitions": transition_entries,
            }
        )

    config_path = runtime_output / "config.json"
    config_path.write_text(
        json.dumps(config, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return config_path


def build(manifest_path: Path, runtime_source: Path) -> Path:
    mode = select_mode(manifest_path)
    if mode == "video":
        return build_video(manifest_path, runtime_source)
    return build_static(manifest_path, runtime_source)


def parse_args() -> argparse.Namespace:
    default_runtime = Path(__file__).resolve().parents[1] / "assets" / "runtime"
    parser = argparse.ArgumentParser(description="Build scroll-flight web assets.")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--runtime-source", type=Path, default=default_runtime)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config_path = build(args.manifest, args.runtime_source)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    print(f"Mode: {config['mode']}")
    print(f"Config: {config_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
