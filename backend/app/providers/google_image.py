from google import genai
from google.genai import types

from .base import ImageProvider
from .catalog import default_image_model
from .retry import with_retry
from ..config import settings
from ..routers.settings import get_setting_value


class GoogleImage(ImageProvider):
    def __init__(self, model: str | None = None):
        self.model = model or default_image_model("google")

    async def _get_client(self):
        api_key = await get_setting_value("google_api_key") or settings.GOOGLE_API_KEY
        if not api_key:
            raise ValueError("Google API key not configured")
        return genai.Client(api_key=api_key)

    async def generate_image(
        self, prompt: str,
        reference_images: list[bytes] | None = None,
        aspect_ratio: str = "1:1",
        image_size: str = "1K",
    ) -> bytes:
        client = await self._get_client()

        contents = []
        for img in reference_images or []:
            contents.append(
                types.Part(
                    inline_data=types.Blob(
                        mime_type="image/png",
                        data=img,
                    )
                )
            )
        contents.append(prompt)

        async def _call() -> bytes:
            response = await client.aio.models.generate_content(
                model=self.model,
                contents=contents,
                config=types.GenerateContentConfig(
                    image_config=types.ImageConfig(
                        aspect_ratio=aspect_ratio,
                        image_size=image_size,
                    ),
                ),
            )

            image_parts = [
                part for part in response.candidates[0].content.parts
                if part.inline_data and part.inline_data.mime_type.startswith("image/")
            ]
            if not image_parts:
                raise ValueError("Google returned no image in response")

            return image_parts[0].inline_data.data

        return await with_retry(_call, label=f"google-image:{self.model}")
