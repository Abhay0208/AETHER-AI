"""Base classes and normalized data model for provider adapters.

All adapters implement :class:`ProviderAdapter` and expose a single method
:meth:`ProviderAdapter.chat_completions` that returns either a full
:class:`ChatCompletionResponse` (non-streaming) or an iterator of
:class:`ChatCompletionChunk` (streaming).
"""
from __future__ import annotations

import abc
import time
import uuid
from typing import Any, Iterator


class ProviderError(Exception):
    """Raised by an adapter when a provider request fails."""

    def __init__(self, message: str, status_code: int = 502, provider: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.provider = provider


class ChatMessage:
    def __init__(self, role: str, content: str | None = None, tool_calls: list[dict] | None = None):
        self.role = role
        self.content = content
        self.tool_calls = tool_calls

    def to_dict(self) -> dict:
        d: dict[str, Any] = {"role": self.role}
        if self.content is not None:
            d["content"] = self.content
        if self.tool_calls is not None:
            d["tool_calls"] = self.tool_calls
        return d


class ChatChoice:
    def __init__(self, index: int, message: ChatMessage, finish_reason: str | None = None):
        self.index = index
        self.message = message
        self.finish_reason = finish_reason


class ChatCompletionResponse:
    """Non-streaming response from a provider, normalized to an OpenAI-like shape."""

    def __init__(
        self,
        id: str,
        model: str,
        created: int,
        choices: list[ChatChoice],
        usage: dict[str, int] | None = None,
        raw: dict | None = None,
    ):
        self.id = id
        self.model = model
        self.created = created
        self.choices = choices
        self.usage = usage or {}
        self.raw = raw or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "object": "chat.completion",
            "created": self.created,
            "model": self.model,
            "choices": [
                {
                    "index": c.index,
                    "message": c.message.to_dict(),
                    "finish_reason": c.finish_reason,
                }
                for c in self.choices
            ],
            "usage": self.usage,
        }


class ChatCompletionChunk:
    """Streaming chunk from a provider."""

    def __init__(
        self,
        id: str,
        model: str,
        created: int,
        choices: list[dict],
        raw: dict | None = None,
    ):
        self.id = id
        self.model = model
        self.created = created
        self.choices = choices
        self.raw = raw or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "object": "chat.completion.chunk",
            "created": self.created,
            "model": self.model,
            "choices": self.choices,
        }


class ProviderAdapter(abc.ABC):
    """Abstract provider adapter.

    `provider` is a row from the `providers` table (as a dict-like object).
    `api_key` is the decrypted secret key, or None if the provider is keyless
    (e.g. Ollama, LM Studio).
    """

    def __init__(self, provider: dict, api_key: str | None = None):
        self.provider = provider
        self.api_key = api_key
        self.name = provider["name"]
        self.base_url = provider.get("base_url") or ""

    # ------------------------------------------------------------------
    # Subclass overrides
    # ------------------------------------------------------------------
    @abc.abstractmethod
    def list_models(self) -> list[dict[str, Any]]:
        """Return a list of model dicts discovered from the provider.

        Each dict: {id, display_name, context_window, capabilities:[...],
        supports_tools, supports_vision, supports_streaming}
        """
        raise NotImplementedError

    @abc.abstractmethod
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
        """Yield chunks (streaming) or return a full response (non-streaming)."""
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    @staticmethod
    def _now() -> int:
        return int(time.time())

    @staticmethod
    def _uid(prefix: str = "chatcmpl") -> str:
        return f"{prefix}-{uuid.uuid4().hex[:24]}"
