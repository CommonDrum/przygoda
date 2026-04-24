import base64

import httpx

from .base import ImageProvider
from .retry import with_retry
from ..config import settings
from ..routers.settings import get_setting_value


class NanoBananaImage(ImageProvider):
    API_URL = "https://api.nanobanana.com/v1/generate"

    def __init__(self, model: str | None = None):
        self.model = model

    async def generate_image(
        self, prompt: str,
        reference_images: list[bytes] | None = None,
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
        # API supports only one reference — prefer the last one (character ref
        # wins over style guide if both are passed).
        if reference_images:
            last = reference_images[-1]
            b64 = base64.b64encode(last).decode()
            payload["reference_image"] = f"data:image/png;base64,{b64}"

        async def _call() -> bytes:
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(
                    self.API_URL,
                    json=payload,
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                resp.raise_for_status()
                data = resp.json()

                image_url = data.get("image_url") or data.get("url")
                if not image_url:
                    raise ValueError(f"No image URL in response: {data}")

                img_resp = await client.get(image_url)
                img_resp.raise_for_status()
                return img_resp.content

        return await with_retry(_call, label="nano_banana")
