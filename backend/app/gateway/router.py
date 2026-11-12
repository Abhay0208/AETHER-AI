"""Unified API gateway router.

Routes OpenAI-compatible chat-completion requests to the right provider
adapter, with API-key rotation, automatic fallback on provider errors, load
balancing across keys, and usage tracking.

This is the engine behind `/api/v1/*` (OpenAI-compatible) endpoints.
"""
from __future__ import annotations

import time
from typing import Any, Iterator

import json
import logging
import time
from typing import Any, Iterator

from ..database import transaction
from ..providers.base import (
    ChatCompletionChunk,
    ChatCompletionResponse,
    ChatMessage,
    ProviderError,
)
from ..providers.registry import ProviderAdapterRegistry

log = logging.getLogger("aether.gateway")


class UnifiedGateway:
    def __init__(self, registry: ProviderAdapterRegistry):
        self.registry = registry

    # ------------------------------------------------------------------
    # Model listing (OpenAI-compatible /v1/models)
    # ------------------------------------------------------------------
    def list_models(self) -> list[dict[str, Any]]:
        """All enabled models across all enabled providers.

        Primary source: the model registry (DB), so the list is available even
        when no provider keys are configured. Optionally enriched by live
        discovery from providers that expose a models endpoint.
        """
        models: list[dict[str, Any]] = []
        with transaction() as conn:
            rows = conn.execute(
                """
                SELECT m.model_id AS id, m.display_name, m.context_window,
                       m.supports_tools, m.supports_vision, m.supports_streaming,
                       m.capabilities, p.name AS provider
                FROM models m JOIN providers p ON m.provider_id = p.id
                WHERE m.is_enabled = 1 AND p.is_enabled = 1
                ORDER BY p.name, m.model_id
                """
            ).fetchall()
        for r in rows:
            caps = r["capabilities"]
            if isinstance(caps, str):
                try:
                    caps = json.loads(caps)
                except json.JSONDecodeError:
                    caps = [caps]
            models.append(
                {
                    "id": r["id"],
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": r["provider"],
                    "display_name": r["display_name"] or r["id"],
                    "context_window": r["context_window"],
                    "capabilities": caps or [],
                    "supports_tools": bool(r["supports_tools"]),
                    "supports_vision": bool(r["supports_vision"]),
                    "supports_streaming": bool(r["supports_streaming"]),
                }
            )
        return models

    # ------------------------------------------------------------------
    # Chat completions (OpenAI-compatible /v1/chat/completions)
    # ------------------------------------------------------------------
    def chat_completions(
        self,
        model: str,
        messages: list[dict],
        stream: bool = False,
        tools: list[dict] | None = None,
        tool_choice: str | dict | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        user: str | None = None,
        **kwargs: Any,
    ):
        """Route a chat-completion request.

        Returns ``("response", ChatCompletionResponse)`` or
        ``("stream", iterator_of_ChatCompletionChunk)``.
        """
        norm_messages = [
            ChatMessage(
                role=m.get("role", "user"),
                content=m.get("content"),
                tool_calls=m.get("tool_calls"),
            )
            for m in messages
        ]

        last_error: ProviderError | None = None
        _, provider = self.registry.get_adapter_for_model(model)
        provider_id = provider["provider_id"]

        # If the provider requires an API key and none is configured, fail fast
        # with a clear message instead of propagating the provider's auth error.
        if provider.get("api_key_env") and not self.registry.get_enabled_api_keys(provider_id):
            raise ProviderError(
                f"No API key configured for provider {provider.get('provider_name') or provider.get('name')}. "
                f"Add one in the API Key manager.",
                status_code=403,
                provider=provider.get("provider_name") or provider.get("name"),
            )

        # Try each enabled key in rotation order; fall back on provider error.
        for cand_adapter, key_id in self.registry.iter_adapters(provider_id):
            try:
                result = cand_adapter.chat_completions(
                    model=model,
                    messages=norm_messages,
                    stream=stream,
                    tools=tools,
                    tool_choice=tool_choice,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs,
                )
            except ProviderError as exc:
                last_error = exc
                log.warning(
                    "gateway: key %s on provider %s failed for model %s: %s",
                    key_id, provider.get("provider_name") or provider.get("name"), model, exc,
                )
                continue

            # Success: record usage + mark key tested OK.
            if stream:
                return ("stream", self._wrapped_stream(result, provider_id, model, key_id))
            self._record_success(provider_id, model, key_id, result)
            return ("response", result)

        # All keys exhausted.
        if last_error:
            raise last_error
        raise ProviderError(
            f"No enabled API key for provider {provider.get('provider_name') or provider.get('name')}"
            f" (model {model}). Add a key in the API Key manager.",
            status_code=403,
            provider=provider.get("provider_name") or provider.get("name"),
        )

    # ------------------------------------------------------------------
    # Streaming wrapper: usage accounting per completed stream
    # ------------------------------------------------------------------
    def _wrapped_stream(
        self, iterator: Iterator[ChatCompletionChunk], provider_id: int, model: str, key_id: str | None
    ):
        """Yield chunks; on completion record token usage and mark key tested."""
        total_completion = 0
        ok = False
        try:
            for chunk in iterator:
                total_completion += sum(
                    1 for c in chunk.choices if c.get("content")
                )
                yield chunk
            ok = True
        finally:
            # Best-effort usage: count completion tokens roughly from chunks.
            self._record_usage(
                provider_id, model, key_id,
                prompt_tokens=0, completion_tokens=total_completion, ok=ok,
            )
            self._mark_key_tested(provider_id, key_id, ok=ok)

    # ------------------------------------------------------------------
    # Usage tracking
    # ------------------------------------------------------------------
    def _record_success(
        self, provider_id: int, model: str, key_id: str | None,
        result: ChatCompletionResponse,
    ):
        usage = result.usage or {}
        self._record_usage(
            provider_id, model, key_id,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            ok=True,
        )
        self._mark_key_tested(provider_id, key_id, ok=True)

    def _record_usage(
        self,
        provider_id: int,
        model: str,
        key_id: str | None,
        prompt_tokens: int,
        completion_tokens: int,
        ok: bool,
        cost_usd: float = 0.0,
        error: str | None = None,
    ):
        with transaction() as conn:
            conn.execute(
                """
                INSERT INTO usage_events
                    (provider_id, model_id, tokens_in, tokens_out, cost_usd, ok)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (provider_id, model, prompt_tokens, completion_tokens, cost_usd, 1 if ok else 0),
            )
            if key_id:
                conn.execute(
                    "UPDATE api_keys SET usage_count = usage_count + 1 WHERE id = ?",
                    (key_id,),
                )

    def _mark_key_tested(self, provider_id: int, key_id: str | None, ok: bool):
        if not key_id:
            return
        with transaction() as conn:
            conn.execute(
                "UPDATE api_keys SET last_tested_at = datetime('now'), test_ok = ? WHERE id = ?",
                (1 if ok else 0, key_id),
            )
