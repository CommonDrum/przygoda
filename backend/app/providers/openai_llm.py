from collections.abc import AsyncIterator

import openai

from .base import LLMProvider
from ..config import settings
from ..routers.settings import get_setting_value


class OpenAILLM(LLMProvider):
    async def _get_client(self):
        api_key = await get_setting_value("openai_api_key") or settings.OPENAI_API_KEY
        if not api_key:
            raise ValueError("OpenAI API key not configured")
        return openai.AsyncOpenAI(api_key=api_key)

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        client = await self._get_client()
        response = await client.chat.completions.create(
            model="gpt-4o",
            max_tokens=8192,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        if not response.choices or not response.choices[0].message.content:
            raise ValueError("OpenAI returned empty response")
        return response.choices[0].message.content

    async def generate_stream(
        self, system_prompt: str, user_prompt: str
    ) -> AsyncIterator[str]:
        client = await self._get_client()
        stream = await client.chat.completions.create(
            model="gpt-4o",
            max_tokens=8192,
            stream=True,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
