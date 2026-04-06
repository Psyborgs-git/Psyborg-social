from __future__ import annotations

import dspy
from socialmind.config.settings import settings


def configure_dspy() -> None:
    """Configure DSPy with the appropriate LLM provider from settings."""
    if settings.LLM_PROVIDER == "openai" and settings.OPENAI_API_KEY:
        lm = dspy.OpenAI(model=settings.OPENAI_MODEL, api_key=settings.OPENAI_API_KEY)
    elif settings.LLM_PROVIDER == "anthropic" and settings.ANTHROPIC_API_KEY:
        lm = dspy.LM(
            f"anthropic/{settings.ANTHROPIC_MODEL}",
            api_key=settings.ANTHROPIC_API_KEY,
        )
    elif settings.LLM_PROVIDER == "litellm" and settings.LITELLM_MODEL:
        lm = dspy.LM(
            settings.LITELLM_MODEL,
            base_url=settings.LITELLM_BASE_URL,
        )
    else:
        # Default: Ollama local model
        lm = dspy.LM(
            f"ollama_chat/{settings.OLLAMA_MODEL}",
            api_base=settings.OLLAMA_URL,
        )
    dspy.configure(lm=lm)
