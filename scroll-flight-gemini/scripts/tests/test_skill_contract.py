import os
import unittest
from pathlib import Path


ROOT = Path(
    os.environ.get(
        "SCROLL_FLIGHT_SKILL_ROOT",
        Path(__file__).resolve().parents[2],
    )
)


class SkillScaffoldContract(unittest.TestCase):
    def test_required_scaffold_exists(self):
        required = [
            ROOT / "SKILL.md",
            ROOT / "agents" / "openai.yaml",
            ROOT / "scripts",
            ROOT / "references",
            ROOT / "assets",
        ]
        missing = [str(path) for path in required if not path.exists()]
        self.assertEqual(missing, [], f"Missing scaffold paths: {missing}")

    def test_runtime_contains_fluency_and_fallback_contracts(self):
        runtime = ROOT / "assets" / "runtime"
        js = (runtime / "scroll-flight.js").read_text(encoding="utf-8")
        css = (runtime / "scroll-flight.css").read_text(encoding="utf-8")
        html = (runtime / "scroll-flight.html").read_text(encoding="utf-8")
        self.assertIn("requestAnimationFrame", js)
        self.assertIn("IntersectionObserver", js)
        self.assertIn("createImageBitmap", js)
        self.assertIn("prefers-reduced-motion", js)
        self.assertIn("class ScrollFlight", js)
        self.assertIn("position: sticky", css)
        self.assertIn("<canvas", html)
        self.assertIn("data-scroll-flight-fallback", html)

    def test_skill_content_covers_triggers_and_manual_gates(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        parts = skill.split("---", 2)
        self.assertEqual(len(parts), 3)
        frontmatter = parts[1].strip().splitlines()
        keys = {
            line.split(":", 1)[0].strip()
            for line in frontmatter
            if ":" in line and not line.startswith(" ")
        }
        self.assertEqual(keys, {"name", "description"})
        description = next(
            line.split(":", 1)[1].strip()
            for line in frontmatter
            if line.startswith("description:")
        )
        self.assertTrue(description.startswith("Use when"))
        lowered = skill.lower()
        for trigger in (
            "cinematic scroll",
            "scroll flight",
            "scroll world",
            "scroll-driven video",
        ):
            self.assertIn(trigger, lowered)
        for contract in (
            "produto ou marca",
            "público-alvo",
            "3–4 cenas",
            "n-1",
            "confirme que salvou os stills",
            "confirme que salvou os clipes",
            "frame-lock",
            "fallback estático",
            "google ai pro",
            "google ai studio",
            "gemini_api.py",
            "api-adapter.md",
        ):
            self.assertIn(contract, lowered)

    def test_references_exist_and_do_not_depend_on_higgsfield(self):
        references = [
            ROOT / "references" / "gemini-checklist.md",
            ROOT / "references" / "prompt-templates.md",
            ROOT / "references" / "runtime-integration.md",
        ]
        combined = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        for path in references:
            combined += "\n" + path.read_text(encoding="utf-8")
        lowered = combined.lower()
        self.assertNotIn("higgsfield auth", lowered)
        self.assertNotIn("higgsfield generate", lowered)
        self.assertNotIn("print(os.environ", lowered)
        self.assertIn("style key", lowered)
        self.assertIn("save as", lowered)

    def test_api_adapter_is_bundled_and_does_not_log_credentials(self):
        adapter = ROOT / "scripts" / "gemini_api.py"
        reference = ROOT / "references" / "api-adapter.md"
        self.assertTrue(adapter.is_file())
        self.assertTrue(reference.is_file())
        source = adapter.read_text(encoding="utf-8").lower()
        self.assertIn("x-goog-api-key", source)
        self.assertIn("redact", source)
        self.assertNotIn("print(self.api_key", source)


if __name__ == "__main__":
    unittest.main()
