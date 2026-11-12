"""Google Gemini provider adapter.

Maps onto Gemini's `generateContent` API (`POST /v1beta/models/{model}:generateContent`).
Supports streaming via `?alt=sse`. Tool calling is mapped through Gemini's
`functionDeclarations` / `toolConfig` shape.
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

log = logging.getLogger("aether.providers.google")

_GEMINI_ROLES = {"user": "user", "assistant": "model", "system": "user"}


class GoogleAdapter(ProviderAdapter):
    def __init__(self, provider: dict, api_key: str | None = None):
        super().__init__(provider, api_key)
        base = (self.base_url or "https://generativelanguage.googleapis.com").rstrip("/")
        self.base = base
        self.client = httpx.Client(timeout=120.0)

    def _model_url(self, model: str, stream: bool) -> str:
        suffix = "streamGenerateContent?alt=sse" if stream else "generateContent"
        return f"{self.base}/v1beta/models/{model}:{suffix}"

    # ------------------------------------------------------------------
    # Model discovery
    # ------------------------------------------------------------------
    def list_models(self) -> list[dict[str, Any]]:
        known = [
            {"id": "gemini-1.5-pro", "context_window": 2097152},
            {"id": "gemini-1.5-flash", "context_window": 1048576},
            {"id": "gemini-1.0-pro", "context_window": 30720},
        ]
        if not self.api_key:
            return [
                {**m, "display_name": m["id"], "capabilities": ["chat", "vision", "tools"],
                 "supports_tools": True, "supports_vision": True, "supports_streaming": True}
                for m in known
            ]
        try:
            resp = self.client.get(
                f"{self.base}/v1beta/models", headers=self._headers()
            )
            resp.raise_for_status()
            items = resp.json().get("models", [])
        except httpx.HTTPError:
            items = []
        models = []
        for item in items:
            mid = item.get("name", "").replace("models/", "")
            if not mid:
                continue
            models.append(
                {
                    "id": mid,
                    "display_name": mid,
                    "context_window": item.get("inputTokenLimit", 2097152),
                    "capabilities": ["chat", "vision", "tools"],
                    "supports_tools": True,
                    "supports_vision": True,
                    "supports_streaming": True,
                }
            )
        return models or [
            {**m, "display_name": m["id"], "capabilities": ["chat", "vision", "tools"],
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
        system_instruction = None
        contents = []
        for m in messages:
            if m.role == "system":
                system_instruction = {"parts": [{"text": m.content or ""}]}
                continue
            contents.append(
                {
                    "role": _GEMINI_ROLES.get(m.role, "user"),
                    "parts": [{"text": m.content or ""}],
                }
            )

        body: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {},
        }
        if system_instruction:
            body["systemInstruction"] = system_instruction
        if temperature is not None:
            body["generationConfig"]["temperature"] = temperature
        if max_tokens is not None:
            body["generationConfig"]["maxOutputTokens"] = max_tokens
        if tools:
            body["tools"] = [
                {
                    "functionDeclarations": [
                        {
                            "name": t.get("name", "tool"),
                            "description": t.get("description", ""),
                            "parameters": t.get("parameters", {"type": "object"}),
                        }
                        for t in tools
                    ]
                }
            ]
        if tool_choice is not None:
            mode = (
                "ANY"
                if tool_choice == "required"
                else ("NONE" if tool_choice == "none" else "AUTO")
            )
            body["toolConfig"] = {"functionCallingConfig": {"mode": mode}}
        for key in ("top_p", "top_k", "stop_sequences"):
            if key in kwargs and kwargs[key] is not None:
                body["generationConfig"][key] = kwargs[key]

        try:
            if stream:
                return self._stream(model, body)
            return self._complete(model, body)
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

    def _complete(self, model: str, body: dict[str, Any]) -> ChatCompletionResponse:
        resp = self.client.post(
            self._model_url(model, stream=False),
            headers=self._headers(),
            json=body,
        )
        resp.raise_for_status()
        return self._normalize_response(resp.json())

    def _stream(self, model: str, body: dict[str, Any]) -> Iterator[ChatCompletionChunk]:
        chunk_id = self._uid()
        created = self._now()
        resp = self.client.post(
            self._model_url(model, stream=True),
            headers=self._headers(),
            json=body,
        )
        resp.raise_for_status()
        for raw_line in resp.iter_lines():
            if not raw_line:
                continue
            line = raw_line.strip()
            if line.startswith("data:"):
                payload = line[5:].strip()
            else:
                payload = line
            try:
                event = json.loads(payload)
            except json.JSONDecodeError:
                continue
            candidates = event.get("candidates", [])
            choices = []
            for c in candidates:
                content = c.get("content", {})
                parts = content.get("parts", [])
                text = "".join(p.get("text", "") for p in parts if p.get("text"))
                fn = c.get("finishReason")
                choices.append(
                    {
                        "index": c.get("index", 0),
                        "delta": {"content": text} if text else {},
                        "finish_reason": fn,
                    }
                )
            yield ChatCompletionChunk(
                chunk_id, model, created, choices, raw=event
            )

    def _normalize_response(self, data: dict[str, Any]) -> ChatCompletionResponse:
        candidates = data.get("candidates", [])
        choice = candidates[0] if candidates else {}
        content = choice.get("content", {})
        parts = content.get("parts", [])
        text = "".join(p.get("text", "") for p in parts if p.get("text"))
        fn_calls = [p.get("functionCall") for p in parts if p.get("functionCall")]
        return ChatCompletionResponse(
            id=data.get("name", self._uid()),
            model=data.get("model", ""),
            created=self._now(),
            choices=[
                ChatChoice(
                    index=0,
                    message=ChatMessage(
                        role="assistant",
                        content=text or None,
                        tool_calls=fn_calls or None,
                    ),
                    finish_reason=choice.get("finishReason"),
                )
            ],
            usage={
                "prompt_tokens": data.get("usageMetadata", {}).get("promptTokenCount", 0),
                "completion_tokens": data.get("usageMetadata", {}).get(
                    "candidatesTokenCount", 0
                ),
                "total_tokens": data.get("usageMetadata", {}).get("totalTokenCount", 0),
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
