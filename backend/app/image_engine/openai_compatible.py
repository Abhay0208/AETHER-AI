"""OpenAI-compatible image generation adapter.

Covers OpenAI DALL-E (via POST /images/generations) and any other provider
that exposes the standard OpenAI image generation API shape.
"""
from __future__ import annotations

import base64
import json
import logging
from typing import Any

import httpx

from .base import ImageAdapter, ImageError, ImageResult

log = logging.getLogger("aether.image.openai_compatible")


class OpenAICompatibleImageAdapter(ImageAdapter):
    def __init__(self, provider: dict, api_key: str | None = None):
        super().__init__(provider, api_key)
        base = (self.base_url or "https://api.openai.com").rstrip("/")
        self.images_url = f"{base}/images/generations"
        self.models_url = f"{base}/models"
        self.client = httpx.Client(timeout=300.0)  # image gen can be slow

    # ------------------------------------------------------------------
    # Model discovery
    # ------------------------------------------------------------------
    def list_models(self) -> list[dict[str, Any]]:
        # OpenAI does not require a key to list models, but image models
        # specifically are a subset. Return curated defaults.
        return [
            {
                "id": "dall-e-3",
                "display_name": "DALL·E 3",
                "capabilities": ["text-to-image"],
                "sizes": ["1024x1024", "1024x1792", "1792x1024"],
                "default_size": "1024x1024",
                "supports_aspect_ratio": True,
            },
            {
                "id": "dall-e-2",
                "display_name": "DALL·E 2",
                "capabilities": ["text-to-image"],
                "sizes": ["256x256", "512x512", "1024x1024"],
                "default_size": "1024x1024",
                "supports_aspect_ratio": False,
            },
        ]

    # ------------------------------------------------------------------
    # Generate
    # ------------------------------------------------------------------
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
        image: str | None = None,
        **kwargs: Any,
    ) -> ImageResult:
        if not self.api_key:
            raise ImageError(
                f"No API key configured for provider {self.name}.",
                status_code=403,
                provider=self.name,
            )

        resolved_size = size or self._default_size(model)
        body: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "n": n,
            "size": resolved_size,
        }

        try:
            resp = self.client.post(
                self.images_url, headers=self._headers(), json=body
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = self._extract_error(exc)
            raise ImageError(
                f"{self.name} error: {detail}",
                status_code=exc.response.status_code,
                provider=self.name,
            )
        except httpx.HTTPError as exc:
            raise ImageError(
                f"{self.name} request failed: {exc}",
                status_code=502,
                provider=self.name,
            )

        data = resp.json()
        items = data.get("data", [])
        if not items:
            raise ImageError(
                f"{self.name} returned no images.",
                status_code=502,
                provider=self.name,
            )
        first = items[0]
        return ImageResult(
            image_id=data.get("created", "") and str(data.get("created")) or "",
            provider=self.name,
            model=model,
            url=first.get("url"),
            file_path=None,
            width=None,
            height=None,
            raw=data,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _default_size(self, model: str) -> str:
        for m in self.list_models():
            if m["id"] == model:
                return m.get("default_size", "1024x1024")
        return "1024x1024"

    @staticmethod
    def _extract_error(exc: httpx.HTTPStatusError) -> str:
        try:
            data = exc.response.json()
            err = data.get("error", {})
            if isinstance(err, dict):
                return err.get("message") or str(err)
            return str(err)
        except Exception:
            return exc.response.text or str(exc)
