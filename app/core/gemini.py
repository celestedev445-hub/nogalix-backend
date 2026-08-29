"""Compatibilité. Tout réglage IA se fait dans app.core.ai."""

from app.core.ai import (
    AI_MODELS,
    AiError,
    AiResult,
    ai_complete,
    ai_enabled,
    ai_json,
    ai_models,
    ai_text,
    parse_ai_json,
)

GEMINI_FALLBACKS = AI_MODELS
gemini_models = ai_models

__all__ = [
    "AI_MODELS",
    "AiError",
    "AiResult",
    "GEMINI_FALLBACKS",
    "ai_complete",
    "ai_enabled",
    "ai_json",
    "ai_models",
    "ai_text",
    "gemini_models",
    "parse_ai_json",
]
