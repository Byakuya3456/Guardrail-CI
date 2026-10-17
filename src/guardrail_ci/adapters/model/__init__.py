"""Model adapter interface and implementations."""

from guardrail_ci.adapters.model.base import ModelAdapter
from guardrail_ci.adapters.model.openai_compat import OpenAICompatAdapter

__all__ = ["ModelAdapter", "OpenAICompatAdapter"]
