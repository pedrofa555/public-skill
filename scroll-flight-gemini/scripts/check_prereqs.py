#!/usr/bin/env python3
"""Report local prerequisites without printing credential values."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from collections.abc import Mapping


def _pillow_status() -> dict:
    try:
        import PIL
    except ImportError:
        return {"available": False, "version": None}
    return {"available": True, "version": PIL.__version__}


def _command_status(name: str) -> dict:
    path = shutil.which(name)
    return {"available": bool(path), "path": path}


def collect_prerequisites(environ: Mapping[str, str]) -> dict:
    optional_api = bool(
        environ.get("GOOGLE_API_KEY") or environ.get("GEMINI_API_KEY")
    )
    return {
        "python": {
            "available": sys.version_info >= (3, 10),
            "version": ".".join(str(value) for value in sys.version_info[:3]),
        },
        "ffmpeg": _command_status("ffmpeg"),
        "ffprobe": _command_status("ffprobe"),
        "pillow": _pillow_status(),
        "geminiAppAccess": "confirm-manually",
        "optionalApiKeyPresent": optional_api,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check scroll-flight prerequisites.")
    parser.add_argument("--json", action="store_true", dest="as_json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = collect_prerequisites(os.environ)
    if args.as_json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        for key in ("python", "ffmpeg", "ffprobe", "pillow"):
            print(f"{key}: {'ok' if report[key]['available'] else 'missing'}")
        print("Gemini app access: confirm manually")
        print(
            "Optional Google AI Studio API key detected: "
            f"{'yes' if report['optionalApiKeyPresent'] else 'no'}"
        )
    mandatory = ("python", "ffmpeg", "ffprobe", "pillow")
    return 0 if all(report[key]["available"] for key in mandatory) else 1


if __name__ == "__main__":
    raise SystemExit(main())
