import base64
import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

from gemini_api import GeminiApiClient, generate_manifest_assets


class FakeTransport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, method, url, headers, body=None):
        self.calls.append(
            {
                "method": method,
                "url": url,
                "headers": headers,
                "body": body,
            }
        )
        response = self.responses.pop(0)
        if isinstance(response, bytes):
            return 200, response
        if isinstance(response, dict):
            return 200, json.dumps(response).encode("utf-8")
        return response


class GeminiApiTests(unittest.TestCase):
    def test_manifest_dry_run_plans_stills_and_clips_without_network(self):
        manifest = {
            "scenes": [
                {"id": "scene-01", "still": "scene-01/still.png"},
                {"id": "scene-02", "still": "scene-02/still.png"},
            ],
            "transitions": [
                {
                    "id": "scene-01-to-02",
                    "from": "scene-01",
                    "to": "scene-02",
                    "video": "transitions/scene-01-to-02.mp4",
                }
            ],
        }
        prompts = {
            "scenes": {"scene-01": "one", "scene-02": "two"},
            "transitions": {"scene-01-to-02": "connect"},
        }
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest_path = root / "scroll-assets" / "manifest.json"
            prompts_path = root / "prompts.json"
            manifest_path.parent.mkdir(parents=True)
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            prompts_path.write_text(json.dumps(prompts), encoding="utf-8")
            outputs = generate_manifest_assets(
                manifest_path,
                prompts_path,
                dry_run=True,
            )
            self.assertEqual(len(outputs), 3)
            self.assertTrue(all(not path.exists() for path in outputs))

    def test_generate_image_writes_inline_data_without_logging_key(self):
        image = base64.b64encode(b"fake-png").decode("ascii")
        transport = FakeTransport(
            [
                {
                    "candidates": [
                        {
                            "content": {
                                "parts": [{"inlineData": {"data": image}}]
                            }
                        }
                    ]
                }
            ]
        )
        client = GeminiApiClient(api_key="secret-value", transport=transport)
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "scene-01" / "still.png"
            result = client.generate_image("a cinematic scene", output)
            self.assertEqual(result, output)
            self.assertEqual(output.read_bytes(), b"fake-png")
        self.assertEqual(transport.calls[0]["method"], "POST")
        self.assertIn("gemini-3.1-flash-image:generateContent", transport.calls[0]["url"])

    def test_generate_video_polls_operation_and_downloads_uri(self):
        transport = FakeTransport(
            [
                {"name": "models/veo-3.1-generate-preview/operations/123"},
                {"done": False},
                {
                    "done": True,
                    "response": {
                        "generateVideoResponse": {
                            "generatedSamples": [
                                {"video": {"uri": "https://download.test/video.mp4"}}
                            ]
                        }
                    },
                },
                b"fake-mp4",
            ]
        )
        client = GeminiApiClient(
            api_key="secret-value",
            transport=transport,
            sleeper=lambda _: None,
        )
        with tempfile.TemporaryDirectory() as temp:
            (Path(temp) / "from.png").write_bytes(b"from")
            (Path(temp) / "to.png").write_bytes(b"to")
            output = Path(temp) / "transition.mp4"
            result = client.generate_video(
                "connect scene one to scene two",
                output,
                first_frame=Path(temp) / "from.png",
                last_frame=Path(temp) / "to.png",
            )
            self.assertEqual(result, output)
            self.assertEqual(output.read_bytes(), b"fake-mp4")
        self.assertEqual([call["method"] for call in transport.calls], ["POST", "GET", "GET", "GET"])
        self.assertEqual(transport.calls[0]["headers"]["x-goog-api-key"], "secret-value")


if __name__ == "__main__":
    unittest.main()
