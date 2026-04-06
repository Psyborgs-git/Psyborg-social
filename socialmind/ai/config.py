from __future__ import annotations

import dspy

from socialmind.config.settings import settings


def configure_dspy() -> dspy.LM:
    """Configure DSPy with the appropriate LM backend."""
    if settings.LLM_PROVIDER == "ollama":
        lm = dspy.LM(
            model=f"ollama_chat/{settings.OLLAMA_MODEL}",
            api_base=settings.OLLAMA_URL,
            max_tokens=2048,
            temperature=0.7,
        )
    elif settings.LLM_PROVIDER == "openai":
        lm = dspy.LM(
            model=f"openai/{settings.OPENAI_MODEL}",
            api_key=settings.OPENAI_API_KEY,
            max_tokens=2048,
        )
    elif settings.LLM_PROVIDER == "anthropic":
        lm = dspy.LM(
            model=f"anthropic/{settings.ANTHROPIC_MODEL}",
            api_key=settings.ANTHROPIC_API_KEY,
            max_tokens=2048,
        )
    else:
        lm = dspy.LM(
            model=settings.LITELLM_MODEL or "ollama_chat/llama3.2",
            api_base=settings.LITELLM_BASE_URL or settings.OLLAMA_URL,
            max_tokens=2048,
        )
    dspy.configure(lm=lm)
    return lm


def configure_embeddings() -> dspy.Embedder:
    """Configure DSPy embeddings with the appropriate provider."""
    if settings.EMBED_PROVIDER == "ollama":
        return dspy.Embedder(
            model=f"ollama/{settings.OLLAMA_EMBED_MODEL}",
            api_base=settings.OLLAMA_URL,
        )
    return dspy.Embedder(model="openai/text-embedding-3-small")
