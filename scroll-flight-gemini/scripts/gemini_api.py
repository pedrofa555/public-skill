#!/usr/bin/env python3
"""Small, dependency-free Gemini API adapter for scroll-flight assets."""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen


DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/"
DEFAULT_IMAGE_MODEL = "gemini-3.1-flash-image"
DEFAULT_VIDEO_MODEL = "veo-3.1-generate-preview"


class GeminiApiError(RuntimeError):
    """Raised for safe, actionable API failures."""


Transport = Callable[[str, str, dict[str, str], bytes | None], tuple[int, bytes]]


def _redact(value: object, secret: str) -> str:
    text = str(value)
    return text.replace(secret, "[REDACTED]") if secret else text


def _default_transport(
    method: str,
    url: str,
    headers: dict[str, str],
    body: bytes | None = None,
) -> tuple[int, bytes]:
    request = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=120) as response:
            return int(response.status), response.read()
    except HTTPError as exc:
        return int(exc.code), exc.read()
    except URLError as exc:
        raise GeminiApiError(f"Gemini API network error: {exc.reason}") from exc


def _nested(data: dict[str, Any], *paths: tuple[str, ...]) -> Any:
    for path in paths:
        current: Any = data
        for key in path:
            if not isinstance(current, dict) or key not in current:
                current = None
                break
            current = current[key]
        if current is not None:
            return current
    return None


def _mime_type(path: Path) -> str:
    return mimetypes.guess_type(path.name)[0] or "image/png"


def _inline_data(path: Path) -> dict[str, dict[str, str]]:
    if not path.is_file():
        raise GeminiApiError(f"reference file not found: {path}")
    return {
        "inlineData": {
            "mimeType": _mime_type(path),
            "data": base64.b64encode(path.read_bytes()).decode("ascii"),
        }
    }


def _write_atomic(path: Path, data: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(data)
        Path(temporary).replace(path)
    finally:
        temporary_path = Path(temporary)
        if temporary_path.exists():
            temporary_path.unlink()
    return path


class GeminiApiClient:
    """Call Gemini image and Veo generation without exposing the API key."""

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str = DEFAULT_BASE_URL,
        transport: Transport | None = None,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get(
            "GOOGLE_API_KEY"
        )
        if not self.api_key:
            raise GeminiApiError(
                "GEMINI_API_KEY or GOOGLE_API_KEY is not configured"
            )
        self.base_url = base_url.rstrip("/") + "/"
        self.transport = transport or _default_transport
        self.sleeper = sleeper

    def _request(
        self,
        method: str,
        url: str,
        payload: dict[str, Any] | None = None,
    ) -> tuple[int, bytes]:
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key,
        }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload else None
        try:
            status, response = self.transport(method, url, headers, body)
        except GeminiApiError:
            raise
        except Exception as exc:  # Keep transport-specific details actionable.
            raise GeminiApiError(_redact(f"Gemini API transport error: {exc}", self.api_key)) from exc
        if status >= 400:
            detail = response.decode("utf-8", errors="replace")[:1000]
            raise GeminiApiError(
                _redact(f"Gemini API HTTP {status}: {detail}", self.api_key)
            )
        return status, response

    def _json_request(
        self,
        method: str,
        url: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        _, response = self._request(method, url, payload)
        try:
            parsed = json.loads(response.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise GeminiApiError("Gemini API returned invalid JSON") from exc
        if not isinstance(parsed, dict):
            raise GeminiApiError("Gemini API returned an unexpected response")
        return parsed

    def generate_image(
        self,
        prompt: str,
        output: Path,
        *,
        model: str = DEFAULT_IMAGE_MODEL,
        aspect_ratio: str = "16:9",
        image_size: str = "2K",
        references: list[Path] | None = None,
    ) -> Path:
        parts: list[dict[str, Any]] = [{"text": prompt}]
        parts.extend(_inline_data(path) for path in references or [])
        payload = {
            "contents": [{"parts": parts}],
            "generationConfig": {
                "responseModalities": ["IMAGE"],
                "responseFormat": {
                    "image": {"aspectRatio": aspect_ratio, "imageSize": image_size}
                },
            },
        }
        response = self._json_request(
            "POST", urljoin(self.base_url, f"models/{model}:generateContent"), payload
        )
        image_data = _nested(
            response,
            ("candidates",),
        )
        if isinstance(image_data, list):
            for candidate in image_data:
                parts_data = candidate.get("content", {}).get("parts", [])
                for part in parts_data:
                    encoded = _nested(part, ("inlineData", "data"), ("inline_data", "data"))
                    if encoded:
                        try:
                            return _write_atomic(output, base64.b64decode(encoded))
                        except (ValueError, base64.binascii.Error) as exc:
                            raise GeminiApiError("Gemini API returned invalid image data") from exc
        raise GeminiApiError("Gemini API response did not contain an image")

    def generate_video(
        self,
        prompt: str,
        output: Path,
        *,
        model: str = DEFAULT_VIDEO_MODEL,
        first_frame: Path | None = None,
        last_frame: Path | None = None,
        references: list[Path] | None = None,
        aspect_ratio: str = "16:9",
        resolution: str = "720p",
        poll_seconds: float = 10,
        timeout_seconds: float = 1800,
    ) -> Path:
        instance: dict[str, Any] = {"prompt": prompt}
        if first_frame:
            instance["image"] = _inline_data(first_frame)
        if last_frame:
            instance["lastFrame"] = _inline_data(last_frame)
        if references:
            instance["referenceImages"] = [
                {"image": _inline_data(path), "referenceType": "asset"}
                for path in references
            ]
        payload = {
            "instances": [instance],
            "parameters": {
                "numberOfVideos": 1,
                "aspectRatio": aspect_ratio,
                "resolution": resolution,
            },
        }
        response = self._json_request(
            "POST", urljoin(self.base_url, f"models/{model}:predictLongRunning"), payload
        )
        operation_name = response.get("name")
        if not isinstance(operation_name, str) or not operation_name:
            raise GeminiApiError("Gemini API did not return a video operation")
        deadline = time.monotonic() + timeout_seconds
        while True:
            operation_url = operation_name if operation_name.startswith("http") else urljoin(
                self.base_url, operation_name.lstrip("/")
            )
            operation = self._json_request("GET", operation_url)
            if operation.get("done") is True:
                if operation.get("error"):
                    raise GeminiApiError(
                        _redact(f"Gemini video operation failed: {operation['error']}", self.api_key)
                    )
                video_uri = _nested(
                    operation,
                    ("response", "generateVideoResponse", "generatedSamples",),
                )
                if isinstance(video_uri, list) and video_uri:
                    video_uri = _nested(video_uri[0], ("video", "uri"), ("video", "gcsUri"))
                if not isinstance(video_uri, str) or not video_uri:
                    raise GeminiApiError("Gemini video operation returned no download URI")
                _, video_bytes = self._request("GET", video_uri)
                return _write_atomic(output, video_bytes)
            if time.monotonic() >= deadline:
                raise GeminiApiError("Gemini video operation timed out")
            self.sleeper(poll_seconds)


def _prompt_for(data: dict[str, Any], group: str, identifier: str) -> str:
    group_data = data.get(group, {})
    if isinstance(group_data, dict):
        prompt = group_data.get(identifier)
    else:
        prompt = None
    if not isinstance(prompt, str) or not prompt.strip():
        raise GeminiApiError(f"missing prompt for {group}.{identifier}")
    return prompt.strip()


def generate_manifest_assets(
    manifest_path: Path,
    prompts_path: Path,
    *,
    phase: str = "all",
    image_model: str = DEFAULT_IMAGE_MODEL,
    video_model: str = DEFAULT_VIDEO_MODEL,
    base_url: str = DEFAULT_BASE_URL,
    poll_seconds: float = 10,
    timeout_seconds: float = 1800,
    dry_run: bool = False,
) -> list[Path]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    prompt_data = json.loads(prompts_path.read_text(encoding="utf-8"))
    asset_root = manifest_path.resolve().parent
    client = None if dry_run else GeminiApiClient(base_url=base_url)
    generated: list[Path] = []
    if phase in {"stills", "all"}:
        for scene in manifest["scenes"]:
            output = asset_root / scene["still"]
            prompt = _prompt_for(prompt_data, "scenes", scene["id"])
            if client:
                client.generate_image(prompt, output, model=image_model)
            generated.append(output)
    if phase in {"clips", "all"}:
        scenes = {scene["id"]: scene for scene in manifest["scenes"]}
        for transition in manifest["transitions"]:
            output = asset_root / transition["video"]
            prompt = _prompt_for(prompt_data, "transitions", transition["id"])
            if client:
                client.generate_video(
                    prompt,
                    output,
                    model=video_model,
                    first_frame=asset_root / scenes[transition["from"]]["still"],
                    last_frame=asset_root / scenes[transition["to"]]["still"],
                    poll_seconds=poll_seconds,
                    timeout_seconds=timeout_seconds,
                )
            generated.append(output)
    return generated


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate scroll-flight assets with Gemini API.")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("prompts", type=Path)
    parser.add_argument("--phase", choices=("stills", "clips", "all"), default="all")
    parser.add_argument("--image-model", default=DEFAULT_IMAGE_MODEL)
    parser.add_argument("--video-model", default=DEFAULT_VIDEO_MODEL)
    parser.add_argument("--base-url", default=os.environ.get("GEMINI_API_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--poll-seconds", type=float, default=10)
    parser.add_argument("--timeout-seconds", type=float, default=1800)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    outputs = generate_manifest_assets(
        args.manifest,
        args.prompts,
        phase=args.phase,
        image_model=args.image_model,
        video_model=args.video_model,
        base_url=args.base_url,
        poll_seconds=args.poll_seconds,
        timeout_seconds=args.timeout_seconds,
        dry_run=args.dry_run,
    )
    prefix = "Would generate" if args.dry_run else "Generated"
    for output in outputs:
        print(f"{prefix}: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
