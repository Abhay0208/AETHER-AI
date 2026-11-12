"""Image generation service.

Orchestrates image provider adapters, persists generated images to local
storage, tracks generation jobs, and exposes results through the API.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx

from ..config import IMAGES_DIR, STORAGE_DIR
from ..database import transaction
from ..security import decrypt_secret
from .base import ImageAdapter, ImageError, ImageResult
from .openai_compatible import OpenAICompatibleImageAdapter
from .stability import StabilityAdapter

ADAPTER_CLASSES: dict[str, str] = {
    "openai": "app.image_engine.openai_compatible.OpenAICompatibleImageAdapter",
    "stability": "app.image_engine.stability.StabilityAdapter",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_safe(obj: Any) -> str:
    return json.dumps(obj)


def _provider_name(provider_id: int) -> str:
    with transaction() as conn:
        row = conn.execute("SELECT name FROM providers WHERE id = ?", (provider_id,)).fetchone()
    return row["name"] if row else "unknown"


class ImageService:
    def __init__(self):
        self._adapters: dict[int, ImageAdapter] = {}

    # ------------------------------------------------------------------
    # Adapter access
    # ------------------------------------------------------------------
    def get_adapter(self, provider_id: int) -> ImageAdapter:
        if provider_id in self._adapters:
            return self._adapters[provider_id]
        adapter = self._build(provider_id)
        self._adapters[provider_id] = adapter
        return adapter

    def _build(self, provider_id: int) -> ImageAdapter:
        with transaction() as conn:
            row = conn.execute("SELECT * FROM providers WHERE id = ?", (provider_id,)).fetchone()
        if row is None:
            raise ImageError(f"Provider id {provider_id} not found.", status_code=404)
        provider = dict(row)

        api_key: str | None = None
        if provider.get("api_key_env"):
            with transaction() as conn:
                key_row = conn.execute(
                    "SELECT encrypted_key FROM api_keys WHERE provider_id = ? AND is_enabled = 1 LIMIT 1",
                    (provider_id,),
                ).fetchone()
            if key_row:
                api_key = decrypt_secret(key_row["encrypted_key"])

        class_path = ADAPTER_CLASSES.get(
            provider["name"],
            "app.image_engine.openai_compatible.OpenAICompatibleImageAdapter",
        )
        module_name, class_name = class_path.rsplit(".", 1)
        module = __import__(module_name, fromlist=[class_name])
        adapter_class = getattr(module, class_name)
        return adapter_class(provider, api_key)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def list_image_models(self, provider_id: int | None = None) -> list[dict]:
        with transaction() as conn:
            if provider_id:
                rows = conn.execute(
                    "SELECT * FROM providers WHERE id = ? AND is_enabled = 1",
                    (provider_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM providers WHERE is_enabled = 1 ORDER BY name"
                ).fetchall()
        models: list[dict] = []
        for row in rows:
            try:
                adapter = self.get_adapter(row["id"])
                discovered = adapter.list_models()
            except ImageError:
                continue
            for m in discovered:
                models.append(
                    {
                        "id": m["id"],
                        "provider": row["name"],
                        "provider_id": row["id"],
                        "display_name": m.get("display_name") or m["id"],
                        "capabilities": m.get("capabilities", []),
                        "sizes": m.get("sizes", []),
                        "default_size": m.get("default_size"),
                        "supports_aspect_ratio": bool(m.get("supports_aspect_ratio")),
                    }
                )
        return models

    def generate(
        self,
        model: str,
        prompt: str,
        provider_id: int,
        *,
        n: int = 1,
        size: str | None = None,
        aspect_ratio: str | None = None,
        negative_prompt: str | None = None,
        style: str | None = None,
        image: str | None = None,
        user_id: int | None = None,
    ) -> dict:
        """Create an image generation job and return it with the result."""
        adapter = self.get_adapter(provider_id)

        # Persist the image record as 'queued'.
        image_id = None
        job_id = str(uuid.uuid4())
        with transaction() as conn:
            cur = conn.execute(
                """INSERT INTO images
                   (prompt, model, provider, size, aspect_ratio, status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, 'queued', datetime('now'), datetime('now'))""",
                (prompt, model, _provider_name(provider_id), size, aspect_ratio),
            )
            image_id = cur.lastrowid
            conn.execute(
                """INSERT INTO image_jobs
                   (id, image_id, status, progress, created_at, updated_at)
                   VALUES (?, ?, 'queued', 0, datetime('now'), datetime('now'))""",
                (job_id, image_id),
            )

        try:
            result = adapter.generate(
                model=model,
                prompt=prompt,
                n=n,
                size=size,
                aspect_ratio=aspect_ratio,
                negative_prompt=negative_prompt,
                style=style,
                image=image,
            )
        except ImageError as exc:
            self._fail_job(job_id, image_id, str(exc))
            raise

        # Save image locally if we got base64 bytes (Stability) or download URL (OpenAI).
        file_path = result.file_path
        if result.url and not file_path:
            file_path = self._download_image(result.url)

        rel = os.path.relpath(file_path, STORAGE_DIR) if file_path else None

        # Mark complete.
        with transaction() as conn:
            conn.execute(
                """UPDATE images
                   SET status = 'completed', file_path = ?, url = ?, width = ?, height = ?,
                       updated_at = datetime('now')
                   WHERE id = ?""",
                (rel, result.url, result.width, result.height, image_id),
            )
            conn.execute(
                """UPDATE image_jobs
                   SET status = 'completed', progress = 100, result = ?,
                       updated_at = datetime('now'), completed_at = datetime('now')
                   WHERE id = ?""",
                (_json_safe(result.to_dict()), job_id),
            )

        return {
            "image_id": image_id,
            "job_id": job_id,
            "status": "completed",
            "result": result.to_dict(),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _fail_job(self, job_id: str, image_id: int, error: str):
        with transaction() as conn:
            conn.execute(
                "UPDATE images SET status = 'failed', updated_at = datetime('now') WHERE id = ?",
                (image_id,),
            )
            conn.execute(
                """UPDATE image_jobs
                   SET status = 'failed', error = ?,
                       updated_at = datetime('now'), completed_at = datetime('now')
                   WHERE id = ?""",
                (error, job_id),
            )

    def _download_image(self, url: str) -> str | None:
        """Download a remote image URL into local storage. Returns local path or None."""
        try:
            resp = httpx.get(url, timeout=60.0)
            resp.raise_for_status()
        except httpx.HTTPError:
            return None
        os.makedirs(IMAGES_DIR, exist_ok=True)
        name = f"{uuid.uuid4().hex}.png"
        path = os.path.join(IMAGES_DIR, name)
        with open(path, "wb") as f:
            f.write(resp.content)
        return path

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------
    def list_images(self, limit: int = 50) -> list[dict]:
        with transaction() as conn:
            rows = conn.execute(
                "SELECT * FROM images ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    def get_image(self, image_id: int) -> dict | None:
        with transaction() as conn:
            row = conn.execute("SELECT * FROM images WHERE id = ?", (image_id,)).fetchone()
        return dict(row) if row else None

    def delete_image(self, image_id: int) -> bool:
        with transaction() as conn:
            row = conn.execute(
                "SELECT file_path FROM images WHERE id = ?", (image_id,)
            ).fetchone()
            if not row:
                return False
            conn.execute("DELETE FROM images WHERE id = ?", (image_id,))
            conn.execute("DELETE FROM image_jobs WHERE image_id = ?", (image_id,))
        if row["file_path"]:
            full = os.path.join(STORAGE_DIR, row["file_path"])
            try:
                os.remove(full)
            except OSError:
                pass
        return True
