"""Provider adapter registry.

Loads providers from the database, instantiates the right adapter for each,
and caches them keyed by (provider_id, key_id). The registry is the single
point through which the gateway obtains an authenticated adapter for a
model/provider, with support for API-key rotation and fallback.
"""
from __future__ import annotations

import importlib
from typing import Any

from ..database import transaction
from ..security import decrypt_secret
from .base import ProviderAdapter, ProviderError

# provider name -> adapter class path
ADAPTER_CLASSES: dict[str, str] = {
    "openai": "app.providers.openai_compatible.OpenAICompatibleAdapter",
    "anthropic": "app.providers.anthropic.AnthropicAdapter",
    "google": "app.providers.google.GoogleAdapter",
    "ollama": "app.providers.ollama.OllamaAdapter",
    "groq": "app.providers.openai_compatible.OpenAICompatibleAdapter",
    "together": "app.providers.openai_compatible.OpenAICompatibleAdapter",
    "fireworks": "app.providers.openai_compatible.OpenAICompatibleAdapter",
    "cerebras": "app.providers.openai_compatible.OpenAICompatibleAdapter",
    "xai": "app.providers.openai_compatible.OpenAICompatibleAdapter",
    "mistral": "app.providers.openai_compatible.OpenAICompatibleAdapter",
    "deepseek": "app.providers.openai_compatible.OpenAICompatibleAdapter",
    "cohere": "app.providers.openai_compatible.OpenAICompatibleAdapter",
    "lmstudio": "app.providers.openai_compatible.OpenAICompatibleAdapter",
    "vllm": "app.providers.openai_compatible.OpenAICompatibleAdapter",
    "openrouter": "app.providers.openai_compatible.OpenAICompatibleAdapter",
    "huggingface": "app.providers.openai_compatible.OpenAICompatibleAdapter",
}


def _load_adapter_class(dotted: str) -> type[ProviderAdapter]:
    module_name, class_name = dotted.rsplit(".", 1)
    module = importlib.import_module(module_name)
    return getattr(module, class_name)


class ProviderAdapterRegistry:
    def __init__(self):
        # cache keyed by (provider_id, key_id or None)
        self._adapters: dict[tuple[int, str | None], ProviderAdapter] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def get_adapter(self, provider_id: int) -> ProviderAdapter:
        """Return an adapter using the best (least-used, tested) enabled key."""
        keys = self.get_enabled_api_keys(provider_id)
        key_id = keys[0]["id"] if keys else None
        return self.build_adapter_with_key(provider_id, key_id)

    def iter_adapters(self, provider_id: int):
        """Yield (adapter, key_id) for every enabled key, best first.

        Used by the gateway for key rotation / fallback. Providers that need
        no key (e.g. Ollama) yield a single adapter with key_id=None.
        """
        keys = self.get_enabled_api_keys(provider_id)
        if not keys:
            yield self.build_adapter_with_key(provider_id, None), None
            return
        for key in keys:
            yield self.build_adapter_with_key(provider_id, key["id"]), key["id"]

    def get_adapter_for_model(self, model_id: str) -> tuple[ProviderAdapter, dict]:
        """Return (adapter, provider_row) for `model_id`, best key first.

        Raises ProviderError if the model is unknown or disabled.
        """
        with transaction() as conn:
            row = conn.execute(
                """
                SELECT m.*, p.name AS provider_name, p.base_url, p.api_key_env,
                       p.is_enabled AS p_enabled,
                       m.is_enabled AS m_enabled, p.id AS provider_id
                FROM models m JOIN providers p ON m.provider_id = p.id
                WHERE m.model_id = ?
                """,
                (model_id,),
            ).fetchone()
        if row is None:
            raise ProviderError(f"Model '{model_id}' is not registered.", status_code=404)
        if not row["p_enabled"] or not row["m_enabled"]:
            raise ProviderError(
                f"Model '{model_id}' or its provider is disabled.", status_code=403
            )
        provider = dict(row)
        adapter = self.get_adapter(provider["provider_id"])
        return adapter, provider

    def get_adapter_for_provider(self, provider_id: int) -> tuple[ProviderAdapter, dict]:
        with transaction() as conn:
            row = conn.execute("SELECT * FROM providers WHERE id = ?", (provider_id,)).fetchone()
        if row is None:
            raise ProviderError(f"Provider id {provider_id} not found.", status_code=404)
        if not row["is_enabled"]:
            raise ProviderError("Provider is disabled.", status_code=403)
        provider = dict(row)
        adapter = self.get_adapter(provider["id"])
        return adapter, provider

    def list_enabled_providers(self) -> list[dict]:
        with transaction() as conn:
            rows = conn.execute(
                "SELECT * FROM providers WHERE is_enabled = 1 ORDER BY name"
            ).fetchall()
        return [dict(r) for r in rows]

    def get_enabled_api_keys(self, provider_id: int) -> list[dict]:
        """Return enabled API keys for a provider, best-first.

        Ordering: keys that have been tested OK and used least come first;
        untested keys last.
        """
        with transaction() as conn:
            rows = conn.execute(
                """
                SELECT id, name, encrypted_key, key_prefix, usage_count, test_ok
                FROM api_keys
                WHERE provider_id = ? AND is_enabled = 1
                ORDER BY (test_ok = 1) DESC, usage_count ASC, id ASC
                """,
                (provider_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------
    def build_adapter_with_key(
        self, provider_id: int, key_id: str | None
    ) -> ProviderAdapter:
        cache_key = (provider_id, key_id)
        if cache_key in self._adapters:
            return self._adapters[cache_key]
        adapter = self._build(provider_id, key_id)
        self._adapters[cache_key] = adapter
        return adapter

    def _build(self, provider_id: int, key_id: str | None) -> ProviderAdapter:
        with transaction() as conn:
            row = conn.execute("SELECT * FROM providers WHERE id = ?", (provider_id,)).fetchone()
        if row is None:
            raise ProviderError(f"Provider id {provider_id} not found.", status_code=404)
        provider = dict(row)

        api_key: str | None = None
        if key_id and provider.get("api_key_env"):
            with transaction() as conn:
                key_row = conn.execute(
                    "SELECT encrypted_key FROM api_keys WHERE id = ?", (key_id,)
                ).fetchone()
            if key_row:
                api_key = decrypt_secret(key_row["encrypted_key"])

        adapter_class_path = ADAPTER_CLASSES.get(
            provider["name"],
            "app.providers.openai_compatible.OpenAICompatibleAdapter",
        )
        adapter_class = _load_adapter_class(adapter_class_path)
        return adapter_class(provider, api_key)
