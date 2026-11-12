"""Base classes and normalized data model for image generation adapters.

All image adapters implement :class:`ImageAdapter` and expose a single method
:meth:`ImageAdapter.generate` that returns an :class:`ImageResult`.
"""
from __future__ import annotations

import abc
from typing import Any


class ImageError(Exception):
    """Raised by an image adapter when generation fails."""

    def __init__(self, message: str, status_code: int = 502, provider: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.provider = provider


class ImageResult:
    """Normalized result from an image generation adapter."""

    def __init__(
        self,
        image_id: str,
        provider: str,
        model: str,
        url: str | None = None,
        file_path: str | None = None,
        width: int | None = None,
        height: int | None = None,
        raw: dict | None = None,
    ):
        self.image_id = image_id
        self.provider = provider
        self.model = model
        self.url = url
        self.file_path = file_path
        self.width = width
        self.height = height
        self.raw = raw or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.image_id,
            "provider": self.provider,
            "model": self.model,
            "url": self.url,
            "file_path": self.file_path,
            "width": self.width,
            "height": self.height,
        }


class ImageAdapter(abc.ABC):
    """Abstract image generation adapter.

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
        """Return image models available from this provider."""

    @abc.abstractmethod
    def generate(
        self,
        model: str,
        prompt: str,
        *,
        n: int = 1,
        size: str | None = None,
        aspect_ratio: str | None = None,
        negative_prompt: str | None = None,
        style: str | None = None,
        image: str | None = None,  # base64 data URL or file path for img2img
        **kwargs: Any,
    ) -> ImageResult:
        """Generate image(s). Returns the first result (multiple handled by caller)."""
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers
