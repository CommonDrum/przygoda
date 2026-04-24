"""Catalog of available models per provider.

The `id` is what we pass to the upstream API; `label` is what the UI shows.
`is_default` marks the entry that applies when a project has no explicit model
set for that provider. There is exactly one default per (provider, kind).

Updated: 2026-04 — using current official model IDs from:
- https://platform.claude.com/docs/en/docs/about-claude/models/overview
- https://ai.google.dev/gemini-api/docs/models
- https://ai.google.dev/gemini-api/docs/image-generation
- OpenAI API docs
"""

LLM_MODELS: dict[str, list[dict]] = {
    "anthropic": [
        {"id": "claude-sonnet-4-6", "label": "Claude Sonnet 4.6 (balans)", "is_default": True},
        {"id": "claude-opus-4-7", "label": "Claude Opus 4.7 (najinteligentniejszy)", "is_default": False},
        {"id": "claude-haiku-4-5", "label": "Claude Haiku 4.5 (najszybszy)", "is_default": False},
        {"id": "claude-opus-4-6", "label": "Claude Opus 4.6 (legacy)", "is_default": False},
        {"id": "claude-sonnet-4-5", "label": "Claude Sonnet 4.5 (legacy)", "is_default": False},
    ],
    "openai": [
        {"id": "gpt-5.4", "label": "GPT-5.4 (flagship)", "is_default": True},
        {"id": "gpt-5.4-mini", "label": "GPT-5.4 mini (szybki)", "is_default": False},
        {"id": "gpt-5.4-nano", "label": "GPT-5.4 nano (najtańszy)", "is_default": False},
        {"id": "gpt-4.1", "label": "GPT-4.1 (legacy, zaawansowany)", "is_default": False},
        {"id": "gpt-4.1-mini", "label": "GPT-4.1 mini (legacy)", "is_default": False},
        {"id": "gpt-4o", "label": "GPT-4o (legacy)", "is_default": False},
    ],
    "google": [
        {"id": "gemini-3.1-pro-preview", "label": "Gemini 3.1 Pro (najinteligentniejszy)", "is_default": False},
        {"id": "gemini-3-flash-preview", "label": "Gemini 3 Flash (balans)", "is_default": True},
        {"id": "gemini-3.1-flash-lite-preview", "label": "Gemini 3.1 Flash Lite (najtańszy)", "is_default": False},
        {"id": "gemini-2.5-pro", "label": "Gemini 2.5 Pro (stable)", "is_default": False},
        {"id": "gemini-2.5-flash", "label": "Gemini 2.5 Flash (stable)", "is_default": False},
        {"id": "gemini-2.5-flash-lite", "label": "Gemini 2.5 Flash Lite (stable)", "is_default": False},
    ],
}

IMAGE_MODELS: dict[str, list[dict]] = {
    "google": [
        {"id": "gemini-3-pro-image-preview", "label": "Nano Banana Pro (Gemini 3 Pro Image)", "is_default": False},
        {"id": "gemini-3.1-flash-image-preview", "label": "Nano Banana 2 (Gemini 3.1 Flash Image)", "is_default": True},
        {"id": "gemini-2.5-flash-image", "label": "Nano Banana (Gemini 2.5 Flash Image, legacy)", "is_default": False},
    ],
    "dalle": [
        {"id": "gpt-image-2", "label": "GPT Image 2 (najnowszy)", "is_default": True},
        {"id": "gpt-image-1.5", "label": "GPT Image 1.5", "is_default": False},
        {"id": "gpt-image-1", "label": "GPT Image 1", "is_default": False},
        {"id": "dall-e-3", "label": "DALL-E 3 (legacy)", "is_default": False},
    ],
    "nano_banana": [
        # nanobanana.com is a single-model service; expose a single entry so the
        # UI renders a disabled select consistently.
        {"id": "default", "label": "Nano Banana (pojedynczy model)", "is_default": True},
    ],
}


def default_llm_model(provider: str) -> str:
    for m in LLM_MODELS.get(provider, []):
        if m["is_default"]:
            return m["id"]
    raise ValueError(f"No LLM default model configured for provider '{provider}'")


def default_image_model(provider: str) -> str:
    for m in IMAGE_MODELS.get(provider, []):
        if m["is_default"]:
            return m["id"]
    raise ValueError(f"No image default model configured for provider '{provider}'")


def is_valid_llm_model(provider: str, model: str) -> bool:
    return any(m["id"] == model for m in LLM_MODELS.get(provider, []))


def is_valid_image_model(provider: str, model: str) -> bool:
    return any(m["id"] == model for m in IMAGE_MODELS.get(provider, []))
