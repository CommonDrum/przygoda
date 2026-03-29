import base64

import httpx

from .base import ImageProvider
from ..config import settings
from ..routers.settings import get_setting_value


class NanoBananaImage(ImageProvider):
    API_URL = "https://api.nanobanana.com/v1/generate"

    async def generate_image(
        self, prompt: str,
        reference_image_bytes: bytes | None = None,
        aspect_ratio: str = "1:1",
        image_size: str = "1K",
    ) -> bytes:
        api_key = await get_setting_value("nano_banana_api_key") or settings.NANO_BANANA_API_KEY
        if not api_key:
            raise ValueError("Nano Banana API key not configured")

        payload: dict = {
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
        }
        if reference_image_bytes:
            b64 = base64.b64encode(reference_image_bytes).decode()
            payload["reference_image"] = f"data:image/png;base64,{b64}"

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                self.API_URL,
                json=payload,
                headers={"Authorization": f"Bearer {api_key}"},
            )
            resp.raise_for_status()
            data = resp.json()

            # Download the generated image
            image_url = data.get("image_url") or data.get("url")
            if not image_url:
                raise ValueError(f"No image URL in response: {data}")

            img_resp = await client.get(image_url)
            img_resp.raise_for_status()
            return img_resp.content
