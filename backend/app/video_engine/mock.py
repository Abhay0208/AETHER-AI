"""Mock video adapter for testing and development.

Generates real short video clips using FFmpeg test patterns so the full
scene-based pipeline can be verified without an external video provider.
In production, replace with real provider adapters (Runway, Pika, etc.).
"""
from __future__ import annotations

import os
import subprocess
import uuid
from typing import Any

from .base import VideoAdapter, VideoError, ClipResult

try:
    from ..config import VIDEOS_DIR
except Exception:  # pragma: no cover
    VIDEOS_DIR = None


class MockVideoAdapter(VideoAdapter):
    def __init__(self, provider: dict, api_key: str | None = None):
        super().__init__(provider, api_key)
        self._dir = VIDEOS_DIR or os.path.join(
            os.path.dirname(__file__), "..", "..", "data", "storage", "videos"
        )
        os.makedirs(self._dir, exist_ok=True)

    # ------------------------------------------------------------------
    # Model discovery
    # ------------------------------------------------------------------
    def list_models(self) -> list[dict[str, Any]]:
        return [
            {
                "id": "mock-video-model",
                "display_name": "Mock Video Model (FFmpeg test pattern)",
                "capabilities": ["text-to-video"],
                "max_duration": 60,
                "supports_image_to_video": False,
                "supports_audio": False,
                "default_resolution": "1280x720",
            }
        ]

    # ------------------------------------------------------------------
    # Generate clip
    # ------------------------------------------------------------------
    def generate_clip(
        self,
        model: str,
        prompt: str,
        *,
        duration: float = 5.0,
        aspect_ratio: str | None = None,
        resolution: str = "1280x720",
        image: str | None = None,
        **kwargs: Any,
    ) -> ClipResult:
        # Honest duration cap for a single mock clip.
        duration = max(1.0, min(float(duration), 10.0))
        width, height = self._parse_resolution(resolution)
        out = os.path.join(self._dir, f"clip_{uuid.uuid4().hex}.mp4")

        # Generate a color-bar style clip with the prompt drawn as text.
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"testsrc2=size={width}x{height}:rate=24:duration={duration}",
            "-vf", f"drawtext=text='{prompt}':fontcolor=white:fontsize={max(20, height//20)}:"
                   f"x=(w-text_w)/2:y=(h-text_h)/2",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-t", str(duration),
            out,
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=120)
        except subprocess.CalledProcessError as exc:
            raise VideoError(
                f"Mock clip generation failed: {exc.stderr or exc}",
                status_code=502,
                provider=self.name,
            )
        except subprocess.TimeoutExpired:
            raise VideoError("Mock clip generation timed out.", status_code=504, provider=self.name)

        return ClipResult(
            clip_id=str(uuid.uuid4()),
            provider=self.name,
            model=model,
            file_path=out,
            duration=duration,
            width=width,
            height=height,
        )

    @staticmethod
    def _parse_resolution(resolution: str) -> tuple[int, int]:
        try:
            w, h = resolution.split("x")
            return int(w), int(h)
        except Exception:
            return 1280, 720
