#!/usr/bin/env python3
"""Create a deterministic scroll-flight asset manifest and source folders."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def estimate_render(scene_count: int, daily_clip_limit: int) -> dict:
    if scene_count < 2:
        raise ValueError("scene count must be at least 2")
    if daily_clip_limit < 1:
        raise ValueError("daily clip limit must be positive")
    required = scene_count - 1
    return {
        "requiredClips": required,
        "estimatedDays": math.ceil(required / daily_clip_limit),
    }


def build_manifest(scene_count: int, stack: str, daily_clip_limit: int) -> dict:
    estimate = estimate_render(scene_count, daily_clip_limit)
    scenes = [
        {
            "id": f"scene-{index:02d}",
            "still": f"scene-{index:02d}/still.png",
        }
        for index in range(1, scene_count + 1)
    ]
    transitions = [
        {
            "id": f"scene-{index:02d}-to-{index + 1:02d}",
            "from": f"scene-{index:02d}",
            "to": f"scene-{index + 1:02d}",
            "video": f"transitions/scene-{index:02d}-to-{index + 1:02d}.mp4",
        }
        for index in range(1, scene_count)
    ]
    return {
        "version": 1,
        "stack": stack,
        "sceneCount": scene_count,
        "dailyClipLimit": daily_clip_limit,
        **estimate,
        "mode": "pending",
        "scenes": scenes,
        "transitions": transitions,
        "tiers": [
            {"name": "desktop", "width": 1920, "quality": 82},
            {"name": "tablet", "width": 1280, "quality": 78},
            {"name": "mobile", "width": 768, "quality": 72},
        ],
    }


def initialize_project(root: Path, manifest: dict) -> Path:
    asset_root = root.resolve() / "scroll-assets"
    manifest_path = asset_root / "manifest.json"
    if manifest_path.exists():
        raise FileExistsError(f"manifest already exists: {manifest_path}")

    for scene in manifest["scenes"]:
        (asset_root / Path(scene["still"]).parent).mkdir(
            parents=True,
            exist_ok=True,
        )
    (asset_root / "transitions").mkdir(parents=True, exist_ok=True)
    (asset_root / "generated").mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return manifest_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create scroll-assets folders and manifest.json.",
    )
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--scenes", type=int, default=4)
    parser.add_argument("--stack", default="vanilla")
    parser.add_argument("--daily-clip-limit", type=int, default=3)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = build_manifest(args.scenes, args.stack, args.daily_clip_limit)
    manifest_path = initialize_project(args.root, manifest)
    print(f"Manifest: {manifest_path}")
    print(f"Required clips: {manifest['requiredClips']}")
    print(f"Estimated minimum days: {manifest['estimatedDays']}")
    print("Save stills as:")
    for scene in manifest["scenes"]:
        print(f"  {manifest_path.parent / scene['still']}")
    print("Save transition clips as:")
    for transition in manifest["transitions"]:
        print(f"  {manifest_path.parent / transition['video']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
