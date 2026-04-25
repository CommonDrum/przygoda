"""Test provider factory and validation."""
import pytest
import pytest_asyncio

from app.providers.factory import get_llm_provider, get_image_provider
from app.providers.anthropic_llm import AnthropicLLM
from app.providers.openai_llm import OpenAILLM
from app.providers.google_image import GoogleImage
from app.providers.openai_image import OpenAIImage


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
    async def test_google_provider(self):
        provider = await get_image_provider("google")
        assert isinstance(provider, GoogleImage)

    @pytest.mark.asyncio
    async def test_openai_provider(self):
        provider = await get_image_provider("openai")
        assert isinstance(provider, OpenAIImage)

    @pytest.mark.asyncio
    async def test_invalid_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown image provider"):
            await get_image_provider("midjourney")

    @pytest.mark.asyncio
    async def test_dead_provider_raises(self):
        """The retired `nano_banana` and `dalle` provider ids must NOT resolve
        — the factory should reject them so a stale config crashes loudly
        instead of silently routing to the wrong API."""
        with pytest.raises(ValueError, match="Unknown image provider"):
            await get_image_provider("nano_banana")
        with pytest.raises(ValueError, match="Unknown image provider"):
            await get_image_provider("dalle")


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
