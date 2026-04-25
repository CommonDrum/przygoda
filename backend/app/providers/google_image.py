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
        # Gemini Image API rejects anything other than 1K/2K with a 400. Old
        # deployments may have legacy '512' / '1024' / '4K' in their settings
        # row — coerce defensively so a stale config doesn't break generation.
        if image_size not in ("1K", "2K"):
            image_size = "1K"

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
            return _extract_image_bytes(response)

        return await with_retry(_call, label=f"google-image:{self.model}")


def _extract_image_bytes(response) -> bytes:
    """Pull PNG bytes out of a Gemini image response, or raise a ValueError
    that actually tells the caller what went wrong. Covers the cases where
    the SDK returns `parts=None` because the model refused (safety, recitation,
    empty output) instead of raising an exception."""
    prompt_feedback = getattr(response, "prompt_feedback", None)
    if prompt_feedback and getattr(prompt_feedback, "block_reason", None):
        reason = prompt_feedback.block_reason
        raise ValueError(
            f"Google zablokował prompt (block_reason={reason}) — zmień opis "
            f"obrazka i spróbuj ponownie."
        )

    candidates = getattr(response, "candidates", None) or []
    if not candidates:
        raise ValueError(
            "Google nie zwrócił żadnego kandydata (prawdopodobnie blokada "
            "bezpieczeństwa). Zmień prompt."
        )

    cand = candidates[0]
    finish_reason = getattr(cand, "finish_reason", None)
    content = getattr(cand, "content", None)
    parts = getattr(content, "parts", None) if content else None

    if not parts:
        # Content was suppressed — finish_reason is the real story.
        fr = str(finish_reason) if finish_reason else "unknown"
        raise ValueError(
            f"Google odrzucił obrazek (finish_reason={fr}). "
            f"Najczęściej: safety filter na postaci/scenie — zmień prompt "
            f"(np. mniej detali o wieku dziecka, neutralniejsza sceneria)."
        )

    image_parts = [
        p for p in parts
        if getattr(p, "inline_data", None)
        and p.inline_data.mime_type
        and p.inline_data.mime_type.startswith("image/")
    ]
    if not image_parts:
        # Got text back instead of image — surface what the model said.
        text_parts = [getattr(p, "text", "") for p in parts if getattr(p, "text", None)]
        text_hint = " | ".join(t for t in text_parts if t)[:200] or "(brak)"
        raise ValueError(
            f"Google zwrócił odpowiedź bez obrazka. Treść: {text_hint}"
        )

    return image_parts[0].inline_data.data
