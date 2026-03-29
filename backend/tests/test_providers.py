"""Test provider factory and validation."""
import pytest
import pytest_asyncio

from app.providers.factory import get_llm_provider, get_image_provider
from app.providers.anthropic_llm import AnthropicLLM
from app.providers.openai_llm import OpenAILLM
from app.providers.nano_banana_image import NanoBananaImage
from app.providers.dalle_image import DalleImage


class TestLLMFactory:
    @pytest.mark.asyncio
    async def test_anthropic_provider(self):
        provider = await get_llm_provider("anthropic")
        assert isinstance(provider, AnthropicLLM)

    @pytest.mark.asyncio
    async def test_openai_provider(self):
        provider = await get_llm_provider("openai")
        assert isinstance(provider, OpenAILLM)

    @pytest.mark.asyncio
    async def test_invalid_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown LLM provider"):
            await get_llm_provider("invalid_provider")


class TestImageFactory:
    @pytest.mark.asyncio
    async def test_nano_banana_provider(self):
        provider = await get_image_provider("nano_banana")
        assert isinstance(provider, NanoBananaImage)

    @pytest.mark.asyncio
    async def test_dalle_provider(self):
        provider = await get_image_provider("dalle")
        assert isinstance(provider, DalleImage)

    @pytest.mark.asyncio
    async def test_invalid_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown image provider"):
            await get_image_provider("midjourney")


class TestProviderValidation:
    @pytest.mark.asyncio
    async def test_anthropic_no_key_raises(self):
        """Anthropic provider without API key should raise ValueError."""
        provider = AnthropicLLM()
        with pytest.raises(ValueError, match="API key not configured"):
            await provider.generate("system", "user")

    @pytest.mark.asyncio
    async def test_openai_no_key_raises(self):
        """OpenAI provider without API key should raise ValueError."""
        provider = OpenAILLM()
        with pytest.raises(ValueError, match="API key not configured"):
            await provider.generate("system", "user")
