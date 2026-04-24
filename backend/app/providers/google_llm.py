from collections.abc import AsyncIterator

from google import genai
from google.genai import types

from .base import LLMProvider
from .catalog import default_llm_model
from ..config import settings
from ..routers.settings import get_setting_value


class GoogleLLM(LLMProvider):
    def __init__(self, model: str | None = None):
        self.model = model or default_llm_model("google")

    async def _get_client(self):
        api_key = await get_setting_value("google_api_key") or settings.GOOGLE_API_KEY
        if not api_key:
            raise ValueError("Google API key not configured")
        return genai.Client(api_key=api_key)

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        client = await self._get_client()
        response = await client.aio.models.generate_content(
            model=self.model,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                max_output_tokens=8192,
            ),
        )
        if not response.text:
            raise ValueError("Google returned empty response")
        return response.text

    async def generate_stream(
        self, system_prompt: str, user_prompt: str
    ) -> AsyncIterator[str]:
        client = await self._get_client()
        stream = await client.aio.models.generate_content_stream(
            model=self.model,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                max_output_tokens=8192,
            ),
        )
        async for chunk in stream:
            if chunk.text:
                yield chunk.text
