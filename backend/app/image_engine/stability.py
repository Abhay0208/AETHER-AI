"""Stability AI image generation adapter.

Uses Stability AI's API (POST /v1/generation/{model}/text-to-image). Supports
text-to-image, image-to-image, inpainting, outpainting, upscaling, and more.
"""
from __future__ import annotations

import base64
import json
import logging
import os
from typing import Any

import httpx

from .base import ImageAdapter, ImageError, ImageResult

log = logging.getLogger("aether.image.stability")


class StabilityAdapter(ImageAdapter):
    def __init__(self, provider: dict, api_key: str | None = None):
        super().__init__(provider, api_key)
        base = (self.base_url or "https://api.stability.ai").rstrip("/")
        self.base = base
        self.client = httpx.Client(timeout=300.0)

    # ------------------------------------------------------------------
    # Model discovery
    # ------------------------------------------------------------------
    def list_models(self) -> list[dict[str, Any]]:
        return [
            {
                "id": "stable-diffusion-xl-1024-v1-0",
                "display_name": "Stable Diffusion XL 1.0",
                "capabilities": ["text-to-image", "image-to-image", "inpainting", "outpainting", "upscaling"],
                "sizes": ["1024x1024"],
                "default_size": "1024x1024",
                "supports_aspect_ratio": True,
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

        # Stability uses multipart/form-data for most endpoints.
        resolved_size = size or "1024x1024"
        width, height = self._parse_size(resolved_size)

        body: dict[str, Any] = {
            "prompt": prompt,
            "width": width,
            "height": height,
            "samples": n,
        }
        if negative_prompt:
            body["negative_prompt"] = negative_prompt
        if style:
            body["style_preset"] = style

        # Build multipart body manually to support both text and image fields.
        fields = []
        for key, value in body.items():
            fields.append((key, str(value)))
        if image:
            fields.append(("init_image", image))

        try:
            resp = self.client.post(
                f"{self.base}/v1/generation/{model}/text-to-image",
                headers={"Authorization": f"Bearer {self.api_key}"},
                data=fields,
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
        artifacts = data.get("artifacts", [])
        if not artifacts:
            raise ImageError(
                f"{self.name} returned no images.",
                status_code=502,
                provider=self.name,
            )
        first = artifacts[0]
        image_b64 = first.get("base64", "")
        file_path = None
        if image_b64:
            file_path = self._save_image(image_b64)
        return ImageResult(
            image_id=first.get("seed", "") and str(first.get("seed")) or "",
            provider=self.name,
            model=model,
            url=None,
            file_path=file_path,
            width=width,
            height=height,
            raw=data,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _parse_size(self, size: str) -> tuple[int, int]:
        try:
            w, h = size.split("x")
            return int(w), int(h)
        except Exception:
            return 1024, 1024

    def _save_image(self, b64: str) -> str:
        from ..config import IMAGES_DIR

        os.makedirs(IMAGES_DIR, exist_ok=True)
        import uuid

        name = f"{uuid.uuid4().hex}.png"
        path = os.path.join(IMAGES_DIR, name)
        try:
            raw = base64.b64decode(b64)
        except Exception:
            raw = b64.encode()
        with open(path, "wb") as f:
            f.write(raw)
        return path

    @staticmethod
    def _extract_error(exc: httpx.HTTPStatusError) -> str:
        try:
            data = exc.response.json()
            return str(data.get("message", exc.response.text))
        except Exception:
            return exc.response.text or str(exc)
