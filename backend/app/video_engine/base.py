"""Base classes and normalized data model for video generation adapters.

All video adapters implement :class:`VideoAdapter` and expose:
- :meth:`VideoAdapter.list_models` - available video models
- :meth:`VideoAdapter.generate_clip` - generate a single clip from a scene prompt
"""
from __future__ import annotations

import abc
from typing import Any


class VideoError(Exception):
    """Raised by a video adapter when generation fails."""

    def __init__(self, message: str, status_code: int = 502, provider: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.provider = provider


class ClipResult:
    """Normalized result from a video clip generation."""

    def __init__(
        self,
        clip_id: str,
        provider: str,
        model: str,
        file_path: str | None = None,
        url: str | None = None,
        duration: float | None = None,
        width: int | None = None,
        height: int | None = None,
        raw: dict | None = None,
    ):
        self.clip_id = clip_id
        self.provider = provider
        self.model = model
        self.file_path = file_path
        self.url = url
        self.duration = duration
        self.width = width
        self.height = height
        self.raw = raw or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.clip_id,
            "provider": self.provider,
            "model": self.model,
            "file_path": self.file_path,
            "url": self.url,
            "duration": self.duration,
            "width": self.width,
            "height": self.height,
        }


class VideoAdapter(abc.ABC):
    """Abstract video generation adapter.

    `provider` is a row from the `providers` table (dict-like).
    `api_key` is the decrypted secret key, or None if keyless.
    """

    def __init__(self, provider: dict, api_key: str | None = None):
        self.provider = provider
        self.api_key = api_key
        self.name = provider["name"]
        self.base_url = provider.get("base_url") or ""

    @abc.abstractmethod
    def list_models(self) -> list[dict[str, Any]]:
        """Return video models available from this provider."""

    @abc.abstractmethod
    def generate_clip(
        self,
        model: str,
        prompt: str,
        *,
        duration: float = 5.0,
        aspect_ratio: str | None = None,
        resolution: str | None = None,
        image: str | None = None,  # base64 or path for image-to-video
        **kwargs: Any,
    ) -> ClipResult:
        """Generate a single video clip. Honest about duration limits."""
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers
