"""Anthropic provider adapter (Claude).

Maps AETHER's normalized chat contract onto Anthropic's Messages API
(`POST /v1/messages`). Anthropic does not use OpenAI-style tool roles natively;
tool results are folded into the conversation textually.
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

log = logging.getLogger("aether.providers.anthropic")

# Anthropic -> OpenAI role mapping. Anthropic only has user/assistant; tool
# outputs are rendered as user messages carrying the tool result text.
_ANTHROPIC_ROLES = {"user": "user", "assistant": "assistant", "system": "user"}


class AnthropicAdapter(ProviderAdapter):
    def __init__(self, provider: dict, api_key: str | None = None):
        super().__init__(provider, api_key)
        base = (self.base_url or "https://api.anthropic.com").rstrip("/")
        self.messages_url = f"{base}/v1/messages"
        self.client = httpx.Client(timeout=120.0)

    # ------------------------------------------------------------------
    # Model discovery
    # ------------------------------------------------------------------
    def list_models(self) -> list[dict[str, Any]]:
        # Anthropic does not expose a public models list without a key; return
        # a sensible curated default if no key, otherwise query /v1/models if
        # it ever becomes available.
        known = [
            {"id": "claude-3-5-sonnet-20241022", "context_window": 200000},
            {"id": "claude-3-5-haiku-20241022", "context_window": 200000},
            {"id": "claude-3-opus-20240229", "context_window": 200000},
        ]
        if not self.api_key:
            return [
                {**m, "display_name": m["id"], "capabilities": ["chat", "vision"],
                 "supports_tools": True, "supports_vision": True, "supports_streaming": True}
                for m in known
            ]
        try:
            resp = self.client.get(f"{base}/v1/models", headers=self._headers())
            resp.raise_for_status()
            items = resp.json().get("data", [])
        except httpx.HTTPError:
            items = []
        models = []
        for item in items:
            mid = item.get("id")
            if not mid:
                continue
            models.append(
                {
                    "id": mid,
                    "display_name": mid,
                    "context_window": item.get("context_window", 200000),
                    "capabilities": ["chat", "vision", "tools"],
                    "supports_tools": True,
                    "supports_vision": True,
                    "supports_streaming": True,
                }
            )
        return models or [
            {**m, "display_name": m["id"], "capabilities": ["chat", "vision"],
             "supports_tools": True, "supports_vision": True, "supports_streaming": True}
            for m in known
        ]

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
        system = ""
        anthro_messages = []
        for m in messages:
            if m.role == "system":
                system = (system + "\n" + m.content).strip() if m.content else system
                continue
            anthro_messages.append(
                {"role": _ANTHROPIC_ROLES.get(m.role, "user"), "content": m.content or ""}
            )

        body: dict[str, Any] = {
            "model": model,
            "messages": anthro_messages,
            "max_tokens": max_tokens or 1024,
            "stream": stream,
        }
        if system:
            body["system"] = system
        if temperature is not None:
            body["temperature"] = temperature
        if tools:
            body["tools"] = [
                {
                    "name": t.get("name", "tool"),
                    "description": t.get("description", ""),
                    "input_schema": t.get("parameters", {"type": "object"}),
                }
                for t in tools
            ]
        if tool_choice is not None:
            body["tool_choice"] = tool_choice
        for key in ("top_p", "stop_sequences"):
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
        resp = self.client.post(
            self.messages_url, headers=self._headers(), json=body
        )
        resp.raise_for_status()
        return self._normalize_response(resp.json())

    def _stream(self, body: dict[str, Any]) -> Iterator[ChatCompletionChunk]:
        chunk_id = self._uid()
        created = self._now()
        model = body["model"]
        with self.client.stream(
            "POST", self.messages_url, headers=self._headers(), json=body
        ) as resp:
            resp.raise_for_status()
            for raw_line in resp.iter_lines():
                if not raw_line:
                    continue
                line = raw_line.strip()
                if not line.startswith("data:"):
                    continue
                payload = line[5:].strip()
                try:
                    event = json.loads(payload)
                except json.JSONDecodeError:
                    continue
                etype = event.get("type")
                if etype == "message_delta":
                    delta = event.get("delta", {})
                    stop = event.get("delta", {}).get("stop_reason")
                    choices = [
                        {
                            "index": 0,
                            "delta": {"content": delta.get("text", "")},
                            "finish_reason": stop,
                        }
                    ]
                    yield ChatCompletionChunk(
                        chunk_id, model, created, choices, raw=event
                    )
                elif etype == "content_block_delta":
                    choices = [
                        {
                            "index": 0,
                            "delta": {
                                "content": event.get("delta", {}).get("text", "")
                            },
                            "finish_reason": None,
                        }
                    ]
                    yield ChatCompletionChunk(
                        chunk_id, model, created, choices, raw=event
                    )

    def _normalize_response(self, data: dict[str, Any]) -> ChatCompletionResponse:
        blocks = data.get("content", [])
        text_parts = [b.get("text", "") for b in blocks if b.get("type") == "text"]
        tool_calls = [
            b for b in blocks if b.get("type") == "tool_use"
        ]
        message: ChatMessage = ChatMessage(
            role="assistant",
            content="".join(text_parts) or None,
            tool_calls=tool_calls or None,
        )
        return ChatCompletionResponse(
            id=data.get("id", self._uid()),
            model=data.get("model", ""),
            created=self._now(),
            choices=[
                ChatChoice(index=0, message=message, finish_reason=data.get("stop_reason"))
            ],
            usage={
                "prompt_tokens": data.get("usage", {}).get("input_tokens", 0),
                "completion_tokens": data.get("usage", {}).get("output_tokens", 0),
                "total_tokens": (
                    data.get("usage", {}).get("input_tokens", 0)
                    + data.get("usage", {}).get("output_tokens", 0)
                ),
            },
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
