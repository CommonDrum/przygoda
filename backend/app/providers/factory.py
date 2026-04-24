from .base import LLMProvider, ImageProvider
from .anthropic_llm import AnthropicLLM
from .openai_llm import OpenAILLM
from .google_llm import GoogleLLM
from .nano_banana_image import NanoBananaImage
from .dalle_image import DalleImage
from .google_image import GoogleImage
from .catalog import (
    default_llm_model,
    default_image_model,
    is_valid_llm_model,
    is_valid_image_model,
)
from ..config import settings
from ..routers.settings import get_setting_value


async def get_llm_provider(
    override: str | None = None,
    model_override: str | None = None,
) -> LLMProvider:
    provider = override or await get_setting_value("default_llm_provider") or settings.LLM_PROVIDER

    if model_override and is_valid_llm_model(provider, model_override):
        model = model_override
    else:
        model = default_llm_model(provider)

    match provider:
        case "anthropic":
            return AnthropicLLM(model=model)
        case "openai":
            return OpenAILLM(model=model)
        case "google":
            return GoogleLLM(model=model)
        case _:
            raise ValueError(f"Unknown LLM provider: {provider}")


async def get_image_provider(
    override: str | None = None,
    model_override: str | None = None,
) -> ImageProvider:
    provider = override or await get_setting_value("default_image_provider") or settings.IMAGE_PROVIDER

    if model_override and is_valid_image_model(provider, model_override):
        model = model_override
    else:
        model = default_image_model(provider)

    match provider:
        case "nano_banana":
            return NanoBananaImage(model=model)
        case "dalle":
            return DalleImage(model=model)
        case "google":
            return GoogleImage(model=model)
        case _:
            raise ValueError(f"Unknown image provider: {provider}")
