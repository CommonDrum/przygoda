from collections.abc import AsyncIterator

import anthropic

from .base import LLMProvider
from ..config import settings
from ..routers.settings import get_setting_value


class AnthropicLLM(LLMProvider):
    async def _get_client(self):
        api_key = await get_setting_value("anthropic_api_key") or settings.ANTHROPIC_API_KEY
        if not api_key:
            raise ValueError("Anthropic API key not configured")
        return anthropic.AsyncAnthropic(api_key=api_key)

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        client = await self._get_client()
        message = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8192,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        if not message.content or not hasattr(message.content[0], "text"):
            raise ValueError("Anthropic returned empty or non-text response")
        return message.content[0].text

    async def generate_stream(
        self, system_prompt: str, user_prompt: str
    ) -> AsyncIterator[str]:
        client = await self._get_client()
        async with client.messages.stream(
            model="claude-sonnet-4-20250514",
            max_tokens=8192,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        ) as stream:
            async for text in stream.text_stream:
                yield text
