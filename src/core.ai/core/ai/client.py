# -*- coding: utf-8 -*-

"""

    Module :mod:`core.ai.client`

    The Claude client and cost tracking. Anything with a ``create(**kwargs)``
    method works as a client, which is how tests swap in a fake.

"""

# ----------- START: Native Imports ---------- #
from typing import Any, Protocol
# ----------- END: Native Imports ---------- #

# ----------- START: Third Party Imports ---------- #
import anthropic
# ----------- END: Third Party Imports ---------- #

# ----------- START: In-App Imports ---------- #
from core.utils.config import get_settings
# ----------- END: In-App Imports ---------- #

__all__ = ["LLMClient", "AINotConfiguredError", "UnconfiguredClient", "default_client", "MODEL_PRICES", "usage_cost"]

# USD per 1M tokens (Nov 2026). Cache read ≈ 0.1× input, cache write ≈ 1.25× input. Update if pricing changes.
MODEL_PRICES = {
    "claude-haiku-5-5": {"input": 0.10, "output": 0.50, "cache_read": 0.01, "cache_write": 0.125},
    "claude-sonnet-5-5": {"input": 2.00, "output": 10.00, "cache_read": 0.20, "cache_write": 2.50},
    "claude-opus-5-5": {"input": 4.00, "output": 20.00, "cache_read": 0.20, "cache_write": 5.00},
}


class LLMClient(Protocol):
    def create(self, **kwargs: Any) -> Any: ...


class AINotConfiguredError(anthropic.AnthropicError):
    """No Claude API key is configured."""


class UnconfiguredClient:
    """Stand-in used when no API key is set: every call raises a clear error instead of crashing."""

    def create(self, **kwargs: Any) -> Any:
        raise AINotConfiguredError("No Claude API key. Set ANTHROPIC_API_KEY in .env")


def default_client() -> LLMClient:
    """The real Claude Messages API, using ANTHROPIC_API_KEY from the environment or .env."""
    api_key = get_settings().anthropic_api_key
    if not api_key:
        return UnconfiguredClient()
    return anthropic.Anthropic(api_key=api_key).messages


def usage_cost(model: str, usage: Any) -> tuple[dict[str, int], float]:
    """Token counts from a response's ``usage`` and their cost in USD (0 for unknown models)."""
    tokens = {
        "input_tokens": getattr(usage, "input_tokens", 0) or 0,
        "output_tokens": getattr(usage, "output_tokens", 0) or 0,
        "cache_read_tokens": getattr(usage, "cache_read_input_tokens", 0) or 0,
        "cache_write_tokens": getattr(usage, "cache_creation_input_tokens", 0) or 0,
    }
    price = MODEL_PRICES.get(model)
    if price is None:
        return tokens, 0.0
    cost = (
        tokens["input_tokens"] * price["input"]
        + tokens["output_tokens"] * price["output"]
        + tokens["cache_read_tokens"] * price["cache_read"]
        + tokens["cache_write_tokens"] * price["cache_write"]
    ) / 1_000_000
    return tokens, cost
