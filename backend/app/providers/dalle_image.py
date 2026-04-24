import httpx
import openai

from .base import ImageProvider
from .catalog import default_image_model
from ..config import settings
from ..routers.settings import get_setting_value


class DalleImage(ImageProvider):
    """OpenAI images API: supports dall-e-3 / dall-e-2 / gpt-image-* models.

    Kept the provider id `dalle` for backwards compatibility with stored projects.
    """

    ASPECT_TO_SIZE = {
        "1:1": "1024x1024",
        "16:9": "1792x1024",
        "3:2": "1792x1024",
        "4:3": "1792x1024",
        "9:16": "1024x1792",
        "2:3": "1024x1792",
        "3:4": "1024x1792",
    }

    def __init__(self, model: str | None = None):
        self.model = model or default_image_model("dalle")

    async def generate_image(
        self, prompt: str,
        reference_images: list[bytes] | None = None,
        aspect_ratio: str = "1:1",
        image_size: str = "1K",
    ) -> bytes:
        # DALL·E / gpt-image via images.generate() does not accept reference
        # images — ignore the param silently to keep a uniform provider API.
        _ = reference_images
        api_key = await get_setting_value("openai_api_key") or settings.OPENAI_API_KEY
        if not api_key:
            raise ValueError("OpenAI API key not configured")

        size = self.ASPECT_TO_SIZE.get(aspect_ratio, "1024x1024")

        client = openai.AsyncOpenAI(api_key=api_key)
        # gpt-image-* returns base64 by default; dall-e-3 returns a URL.
        # `response_format="url"` forces URL response for both families.
        kwargs: dict = {
            "model": self.model,
            "prompt": prompt,
            "size": size,
            "n": 1,
        }
        if self.model.startswith("dall-e"):
            kwargs["quality"] = "standard"
        response = await client.images.generate(**kwargs)
        datum = response.data[0]

        if getattr(datum, "b64_json", None):
            import base64
            return base64.b64decode(datum.b64_json)

        image_url = getattr(datum, "url", None)
        if not image_url:
            raise ValueError("OpenAI image response missing both url and b64_json")

        async with httpx.AsyncClient(timeout=60) as http:
            img_resp = await http.get(image_url)
            img_resp.raise_for_status()
            return img_resp.content
