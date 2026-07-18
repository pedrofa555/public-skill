import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

from init_scroll_project import build_manifest, estimate_render, initialize_project


class InitScrollProjectTests(unittest.TestCase):
    def test_four_scenes_need_three_clips_and_one_day(self):
        self.assertEqual(
            estimate_render(4, 3),
            {"requiredClips": 3, "estimatedDays": 1},
        )

    def test_daily_limit_must_be_positive(self):
        with self.assertRaisesRegex(ValueError, "daily clip limit"):
            estimate_render(4, 0)

    def test_scene_count_must_be_at_least_two(self):
        with self.assertRaisesRegex(ValueError, "scene count"):
            estimate_render(1, 3)

    def test_manifest_uses_expected_paths(self):
        manifest = build_manifest(3, "vanilla", 3)
        self.assertEqual(manifest["scenes"][0]["still"], "scene-01/still.png")
        self.assertEqual(
            manifest["transitions"][0]["video"],
            "transitions/scene-01-to-02.mp4",
        )
        self.assertEqual(
            [tier["width"] for tier in manifest["tiers"]],
            [1920, 1280, 768],
        )

    def test_initialization_does_not_overwrite_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = build_manifest(3, "vanilla", 3)
            path = initialize_project(root, manifest)
            original = path.read_text(encoding="utf-8")
            with self.assertRaisesRegex(FileExistsError, "already exists"):
                initialize_project(root, manifest)
            self.assertEqual(path.read_text(encoding="utf-8"), original)
            saved = json.loads(original)
            self.assertEqual(saved["sceneCount"], 3)


if __name__ == "__main__":
    unittest.main()
