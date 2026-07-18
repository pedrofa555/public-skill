import json
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image


SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

from verify_assets import load_manifest, validate_image, verify_assets


class VerifyAssetsTests(unittest.TestCase):
    def test_rejects_small_image(self):
        with tempfile.TemporaryDirectory() as temp:
            image_path = Path(temp) / "still.png"
            Image.new("RGB", (640, 360), "black").save(image_path)
            self.assertIn(
                "minimum dimensions",
                " ".join(validate_image(image_path)),
            )

    def test_stills_phase_accepts_valid_images(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "scroll-assets"
            (root / "scene-01").mkdir(parents=True)
            (root / "scene-02").mkdir(parents=True)
            Image.new("RGB", (1280, 720), "black").save(
                root / "scene-01" / "still.png"
            )
            Image.new("RGB", (1280, 720), "white").save(
                root / "scene-02" / "still.png"
            )
            manifest = {
                "version": 1,
                "scenes": [
                    {"id": "scene-01", "still": "scene-01/still.png"},
                    {"id": "scene-02", "still": "scene-02/still.png"},
                ],
                "transitions": [
                    {
                        "id": "scene-01-to-02",
                        "video": "transitions/scene-01-to-02.mp4",
                    }
                ],
            }
            manifest_path = root / "manifest.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            self.assertTrue(verify_assets(manifest_path, "stills")["valid"])

    def test_invalid_phase_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "phase"):
            verify_assets(Path("manifest.json"), "images")

    def test_manifest_rejects_path_traversal(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = {
                "version": 1,
                "scenes": [{"id": "scene-01", "still": "../outside.png"}],
                "transitions": [],
            }
            path = root / "manifest.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            report = verify_assets(path, "stills")
            self.assertFalse(report["valid"])
            self.assertIn("outside scroll-assets", " ".join(report["issues"]))

    def test_load_manifest_requires_core_keys(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "manifest.json"
            path.write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "missing keys"):
                load_manifest(path)


if __name__ == "__main__":
    unittest.main()
