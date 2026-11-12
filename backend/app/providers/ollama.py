"""Ollama provider adapter.

Uses Ollama's native `POST /api/chat` + `GET /api/tags` API. Ollama runs
locally and typically needs no API key, which makes it the default
offline-friendly provider.
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

log = logging.getLogger("aether.providers.ollama")


class OllamaAdapter(ProviderAdapter):
    def __init__(self, provider: dict, api_key: str | None = None):
        super().__init__(provider, api_key)
        base = (self.base_url or "http://localhost:11434").rstrip("/")
        self.chat_url = f"{base}/api/chat"
        self.tags_url = f"{base}/api/tags"
        self.client = httpx.Client(timeout=300.0)  # local models can be slow

    # ------------------------------------------------------------------
    # Model discovery
    # ------------------------------------------------------------------
    def list_models(self) -> list[dict[str, Any]]:
        try:
            resp = self.client.get(self.tags_url)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderError(
                f"Ollama not reachable at {self.base_url}: {exc}",
                status_code=502,
                provider=self.name,
            )
        models = []
        for item in resp.json().get("models", []):
            mid = item.get("name", "").split(":")[0]  # strip tag
            if not mid:
                continue
            models.append(
                {
                    "id": mid,
                    "display_name": mid,
                    "context_window": item.get("context_length", 4096),
                    "capabilities": ["chat"],
                    "supports_tools": True,
                    "supports_vision": False,
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
            "messages": [
                {"role": m.role, "content": m.content or ""} for m in messages
            ],
            "stream": stream,
        }
        if tools:
            body["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": t.get("name", "tool"),
                        "description": t.get("description", ""),
                        "parameters": t.get("parameters", {"type": "object"}),
                    },
                }
                for t in tools
            ]
        if tool_choice is not None:
            body["tool_choice"] = tool_choice
        options: dict[str, Any] = {}
        if temperature is not None:
            options["temperature"] = temperature
        if max_tokens is not None:
            options["num_predict"] = max_tokens
        for key in ("top_p", "stop", "seed"):
            if key in kwargs and kwargs[key] is not None:
                options[key] = kwargs[key]
        if options:
            body["options"] = options

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
        resp = self.client.post(self.chat_url, json=body)
        resp.raise_for_status()
        return self._normalize_response(resp.json())

    def _stream(self, body: dict[str, Any]) -> Iterator[ChatCompletionChunk]:
        chunk_id = self._uid()
        created = self._now()
        model = body["model"]
        with self.client.stream("POST", self.chat_url, json=body) as resp:
            resp.raise_for_status()
            for raw_line in resp.iter_lines():
                if not raw_line:
                    continue
                line = raw_line.strip()
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                msg = event.get("message", {})
                choices = [
                    {
                        "index": 0,
                        "delta": {
                            k: v
                            for k, v in (
                                ("role", msg.get("role")),
                                ("content", msg.get("content")),
                                ("tool_calls", msg.get("tool_calls")),
                            )
                            if v is not None
                        },
                        "finish_reason": (
                            event.get("done_reason") if event.get("done") else None
                        ),
                    }
                ]
                yield ChatCompletionChunk(chunk_id, model, created, choices, raw=event)
                if event.get("done"):
                    break

    def _normalize_response(self, data: dict[str, Any]) -> ChatCompletionResponse:
        msg = data.get("message", {})
        return ChatCompletionResponse(
            id=data.get("model", self._uid()),
            model=data.get("model", ""),
            created=self._now(),
            choices=[
                ChatChoice(
                    index=0,
                    message=ChatMessage(
                        role=msg.get("role", "assistant"),
                        content=msg.get("content"),
                        tool_calls=msg.get("tool_calls"),
                    ),
                    finish_reason=data.get("done_reason"),
                )
            ],
            usage={},
            raw=data,
        )

    @staticmethod
    def _extract_error(exc: httpx.HTTPStatusError) -> str:
        try:
            return exc.response.json().get("error", exc.response.text)
        except Exception:
            return exc.response.text or str(exc)
