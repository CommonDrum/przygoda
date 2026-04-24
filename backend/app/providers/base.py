from abc import ABC, abstractmethod
from collections.abc import AsyncIterator


class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Returns raw text response from LLM."""
        ...

    async def generate_stream(
        self, system_prompt: str, user_prompt: str
    ) -> AsyncIterator[str]:
        """Yields text chunks. Default fallback: single yield of full response."""
        result = await self.generate(system_prompt, user_prompt)
        yield result


class ImageProvider(ABC):
    @abstractmethod
    async def generate_image(
        self, prompt: str,
        reference_images: list[bytes] | None = None,
        aspect_ratio: str = "1:1",
        image_size: str = "1K",
    ) -> bytes:
        """Returns image bytes.

        `reference_images` can contain multiple images — typically a style guide
        and a character reference. Providers that only support one reference
        (e.g. nanobanana.com) pick the first; providers that support many
        (e.g. Gemini) pass all.
        """
        ...
