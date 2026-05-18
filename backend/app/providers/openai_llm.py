from collections.abc import AsyncIterator

import openai

from .base import LLMProvider
from .catalog import default_llm_model
from .retry import with_retry, stream_with_retry
from ..config import settings
from ..routers.settings import get_setting_value


class OpenAILLM(LLMProvider):
    def __init__(self, model: str | None = None):
        self.model = model or default_llm_model("openai")

    async def _get_client(self):
        api_key = await get_setting_value("openai_api_key") or settings.OPENAI_API_KEY
        if not api_key:
            raise ValueError("OpenAI API key not configured")
        return openai.AsyncOpenAI(api_key=api_key)

    def _token_limit_kwargs(self, value: int) -> dict:
        # gpt-5.x / o-series only accept max_completion_tokens; legacy chat
        # completions models still want max_tokens. Pick by model prefix.
        if self.model.startswith(("gpt-5", "o1", "o3", "o4")):
            return {"max_completion_tokens": value}
        return {"max_tokens": value}

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        client = await self._get_client()

        async def _call():
            response = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                **self._token_limit_kwargs(16384),
            )
            if not response.choices or not response.choices[0].message.content:
                raise ValueError("OpenAI returned empty response")
            return response.choices[0].message.content

        return await with_retry(_call, label=f"openai:{self.model}")

    async def generate_stream(
        self, system_prompt: str, user_prompt: str
    ) -> AsyncIterator[str]:
        client = await self._get_client()

        async def _stream():
            stream = await client.chat.completions.create(
                model=self.model,
                stream=True,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                **self._token_limit_kwargs(16384),
            )
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        async for chunk in stream_with_retry(_stream, label=f"openai-stream:{self.model}"):
            yield chunk
