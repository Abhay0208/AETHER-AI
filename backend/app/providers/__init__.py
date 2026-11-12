"""Provider adapters package for AETHER.

Each provider adapter translates AETHER's normalized chat-completion contract
into a specific provider's API and back. Adapters never fake responses: they
make real HTTP calls and propagate real errors.
"""
from .base import (
    ProviderAdapter,
    ProviderError,
    ChatMessage,
    ChatChoice,
    ChatCompletionResponse,
    ChatCompletionChunk,
)
from .registry import ProviderAdapterRegistry

__all__ = [
    "ProviderAdapter",
    "ProviderError",
    "ChatMessage",
    "ChatChoice",
    "ChatCompletionResponse",
    "ChatCompletionChunk",
    "ProviderAdapterRegistry",
]
