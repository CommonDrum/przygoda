import httpx
import openai

from .base import ImageProvider
from ..config import settings
from ..routers.settings import get_setting_value


class DalleImage(ImageProvider):
    ASPECT_TO_SIZE = {
        "1:1": "1024x1024",
        "16:9": "1792x1024",
        "3:2": "1792x1024",
        "4:3": "1792x1024",
        "9:16": "1024x1792",
        "2:3": "1024x1792",
        "3:4": "1024x1792",
    }

    async def generate_image(
        self, prompt: str,
        reference_image_bytes: bytes | None = None,
        aspect_ratio: str = "1:1",
        image_size: str = "1K",
    ) -> bytes:
        api_key = await get_setting_value("openai_api_key") or settings.OPENAI_API_KEY
        if not api_key:
            raise ValueError("OpenAI API key not configured")

        size = self.ASPECT_TO_SIZE.get(aspect_ratio, "1024x1024")

        client = openai.AsyncOpenAI(api_key=api_key)
        response = await client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size=size,
            quality="standard",
            n=1,
        )
        image_url = response.data[0].url

        async with httpx.AsyncClient(timeout=60) as http:
            img_resp = await http.get(image_url)
            img_resp.raise_for_status()
            return img_resp.content
