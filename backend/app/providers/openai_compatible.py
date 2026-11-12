"""OpenAI-compatible provider adapter.

Covers OpenAI, Groq, Together, Fireworks, Cerebras, xAI, Mistral, DeepSeek,
Cohere, LM Studio, vLLM, OpenRouter, Hugging Face, and any other provider
that exposes the standard `POST /chat/completions` + `GET /models` OpenAPI
shape.
"""
from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from .base import (
    ChatChoice,
    ChatCompletionChunk,
    ChatCompletionResponse,
    ChatMessage,
    ProviderAdapter,
    ProviderError,
)

log = logging.getLogger("aether.providers.openai_compatible")


class OpenAICompatibleAdapter(ProviderAdapter):
    def __init__(self, provider: dict, api_key: str | None = None):
        super().__init__(provider, api_key)
        base = (self.base_url or "").rstrip("/")
        self.chat_url = f"{base}/chat/completions"
        self.models_url = f"{base}/models"
        self.client = httpx.Client(timeout=120.0)

    # ------------------------------------------------------------------
    # Model discovery
    # ------------------------------------------------------------------
    def list_models(self) -> list[dict[str, Any]]:
        try:
            resp = self.client.get(self.models_url, headers=self._headers())
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderError(
                f"Failed to list models from {self.name}: {exc}",
                status_code=502,
                provider=self.name,
            )
        data = resp.json()
        models = []
        for item in data.get("data", []):
            model_id = item.get("id")
            if not model_id:
                continue
            caps = item.get("capabilities") or []
            models.append(
                {
                    "id": model_id,
                    "display_name": item.get("display_name") or model_id,
                    "context_window": item.get("context_window"),
                    "capabilities": caps,
                    "supports_tools": "tools" in caps or item.get("supports_tools"),
                    "supports_vision": "vision" in caps or item.get("supports_vision"),
                    "supports_streaming": True,
                }
            )
        return models

    # ------------------------------------------------------------------
    # Chat completions
    # ------------------------------------------------------------------
    def chat_completions(
        self,
        model: str,
        messages: list[ChatMessage],
        stream: bool = False,
        tools: list[dict] | None = None,
        tool_choice: str | dict | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ):
        body: dict[str, Any] = {
            "model": model,
            "messages": [m.to_dict() for m in messages],
            "stream": stream,
        }
        if tools:
            body["tools"] = tools
        if tool_choice is not None:
            body["tool_choice"] = tool_choice
        if temperature is not None:
            body["temperature"] = temperature
        if max_tokens is not None:
            body["max_tokens"] = max_tokens
        # pass through provider-specific extras
        for key in ("top_p", "presence_penalty", "frequency_penalty", "stop", "seed"):
            if key in kwargs and kwargs[key] is not None:
                body[key] = kwargs[key]

        try:
            if stream:
                return self._stream(body)
            return self._complete(body)
        except httpx.HTTPStatusError as exc:
            detail = self._extract_error(exc)
            raise ProviderError(
                f"{self.name} error: {detail}",
                status_code=exc.response.status_code,
                provider=self.name,
            )
        except httpx.HTTPError as exc:
            raise ProviderError(
                f"{self.name} request failed: {exc}",
                status_code=502,
                provider=self.name,
            )

    def _complete(self, body: dict[str, Any]) -> ChatCompletionResponse:
        resp = self.client.post(self.chat_url, headers=self._headers(), json=body)
        resp.raise_for_status()
        data = resp.json()
        return self._normalize_response(data)

    def _stream(self, body: dict[str, Any]) -> Iterator[ChatCompletionChunk]:
        with self.client.stream(
            "POST", self.chat_url, headers=self._headers(), json=body
        ) as resp:
            resp.raise_for_status()
            chunk_id = self._uid()
            created = self._now()
            for raw_line in resp.iter_lines():
                if not raw_line:
                    continue
                line = raw_line.strip()
                if line.startswith("data:"):
                    payload = line[5:].strip()
                    if payload == "[DONE]":
                        yield ChatCompletionChunk(
                            chunk_id, body["model"], created, [], raw={}
                        )
                        continue
                    try:
                        data = json.loads(payload)
                    except json.JSONDecodeError:
                        continue
                    yield self._normalize_chunk(data, chunk_id, created)

    # ------------------------------------------------------------------
    # Normalization
    # ------------------------------------------------------------------
    def _normalize_response(self, data: dict[str, Any]) -> ChatCompletionResponse:
        choices = []
        for item in data.get("choices", []):
            msg = item.get("message", {})
            choices.append(
                ChatChoice(
                    index=item.get("index", 0),
                    message=ChatMessage(
                        role=msg.get("role", "assistant"),
                        content=msg.get("content"),
                        tool_calls=msg.get("tool_calls"),
                    ),
                    finish_reason=item.get("finish_reason"),
                )
            )
        return ChatCompletionResponse(
            id=data.get("id", self._uid()),
            model=data.get("model", ""),
            created=data.get("created", self._now()),
            choices=choices,
            usage=data.get("usage", {}),
            raw=data,
        )

    def _normalize_chunk(
        self, data: dict[str, Any], chunk_id: str, created: int
    ) -> ChatCompletionChunk:
        choices = []
        for item in data.get("choices", []):
            delta = item.get("delta", {})
            choices.append(
                {
                    "index": item.get("index", 0),
                    "delta": {
                        k: v
                        for k, v in (
                            ("role", delta.get("role")),
                            ("content", delta.get("content")),
                            ("tool_calls", delta.get("tool_calls")),
                        )
                        if v is not None
                    },
                    "finish_reason": item.get("finish_reason"),
                }
            )
        return ChatCompletionChunk(
            id=data.get("id", chunk_id),
            model=data.get("model", ""),
            created=data.get("created", created),
            choices=choices,
            raw=data,
        )

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
