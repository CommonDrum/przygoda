from .base import LLMProvider, ImageProvider
from .anthropic_llm import AnthropicLLM
from .openai_llm import OpenAILLM
from .google_llm import GoogleLLM
from .nano_banana_image import NanoBananaImage
from .dalle_image import DalleImage
from .google_image import GoogleImage
from ..config import settings
from ..routers.settings import get_setting_value


async def get_llm_provider(override: str | None = None) -> LLMProvider:
    provider = override
    if not provider:
        provider = await get_setting_value("default_llm_provider") or settings.LLM_PROVIDER
    match provider:
        case "anthropic":
            return AnthropicLLM()
        case "openai":
            return OpenAILLM()
        case "google":
            return GoogleLLM()
        case _:
            raise ValueError(f"Unknown LLM provider: {provider}")


async def get_image_provider(override: str | None = None) -> ImageProvider:
    provider = override
    if not provider:
        provider = await get_setting_value("default_image_provider") or settings.IMAGE_PROVIDER
    match provider:
        case "nano_banana":
            return NanoBananaImage()
        case "dalle":
            return DalleImage()
        case "google":
            return GoogleImage()
        case _:
            raise ValueError(f"Unknown image provider: {provider}")
