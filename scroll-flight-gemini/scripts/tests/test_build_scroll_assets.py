import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image


SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

from build_scroll_assets import build, select_mode
from init_scroll_project import build_manifest, initialize_project


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def create_runtime_source(root: Path) -> Path:
    runtime = root / "runtime-source"
    runtime.mkdir()
    for name in ("scroll-flight.html", "scroll-flight.css", "scroll-flight.js"):
        (runtime / name).write_text(name, encoding="utf-8")
    return runtime


class BuildScrollAssetsTests(unittest.TestCase):
    def test_missing_clip_selects_static_for_entire_section(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = build_manifest(3, "vanilla", 3)
            manifest_path = initialize_project(root, manifest)
            for scene in manifest["scenes"]:
                Image.new("RGB", (1280, 720), "black").save(
                    manifest_path.parent / scene["still"]
                )
            self.assertEqual(select_mode(manifest_path), "static")

    def test_static_build_writes_all_three_tiers_without_touching_sources(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            runtime = create_runtime_source(root)
            manifest = build_manifest(2, "vanilla", 3)
            manifest_path = initialize_project(root, manifest)
            sources = []
            for scene in manifest["scenes"]:
                path = manifest_path.parent / scene["still"]
                Image.new("RGB", (1920, 1080), "black").save(path)
                sources.append(path)
            before = {path: sha256(path) for path in sources}
            config_path = build(manifest_path, runtime)
            config = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertEqual(config["mode"], "static")
            self.assertEqual(
                sorted(
                    path.name
                    for path in (manifest_path.parent / "generated").iterdir()
                ),
                ["desktop", "mobile", "runtime", "tablet"],
            )
            self.assertEqual(before, {path: sha256(path) for path in sources})

    @unittest.skipUnless(
        shutil.which("ffmpeg") and shutil.which("ffprobe"),
        "FFmpeg unavailable",
    )
    def test_complete_clip_set_builds_video_tiers(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            runtime = create_runtime_source(root)
            manifest = build_manifest(2, "vanilla", 3)
            manifest_path = initialize_project(root, manifest)
            for index, scene in enumerate(manifest["scenes"]):
                Image.new("RGB", (1280, 720), (index * 120, 0, 0)).save(
                    manifest_path.parent / scene["still"]
                )
            video = manifest_path.parent / manifest["transitions"][0]["video"]
            subprocess.run(
                [
                    "ffmpeg",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    "testsrc=size=1280x720:rate=24",
                    "-t",
                    "1",
                    "-pix_fmt",
                    "yuv420p",
                    str(video),
                ],
                check=True,
            )
            config_path = build(manifest_path, runtime)
            config = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertEqual(config["mode"], "video")
            for tier in config["tiers"]:
                transition = tier["transitions"][0]
                self.assertGreater(transition["frameCount"], 0)
                frames = list(
                    (
                        manifest_path.parent
                        / "generated"
                        / transition["path"]
                    ).glob("frame-*.webp")
                )
                self.assertEqual(len(frames), transition["frameCount"])


if __name__ == "__main__":
    unittest.main()
