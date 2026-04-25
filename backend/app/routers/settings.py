import anthropic
import openai
from fastapi import APIRouter
from google import genai

from ..database import get_db
from ..models.schemas import (
    SettingsUpdate,
    SettingsResponse,
    ValidateKeyRequest,
    ValidateKeyResponse,
)

router = APIRouter(prefix="/settings", tags=["settings"])

# Keys that are stored in the settings table
SETTING_KEYS = [
    "anthropic_api_key",
    "openai_api_key",
    "google_api_key",
    "default_llm_provider",
    "default_image_provider",
    "image_aspect_ratio",
    "image_size",
]

DEFAULTS = {
    "default_llm_provider": "anthropic",
    "default_image_provider": "google",
    "image_aspect_ratio": "1:1",
    "image_size": "1K",
}

PROVIDER_KEY_MAP = {
    "anthropic": "anthropic_api_key",
    "openai": "openai_api_key",
    "google": "google_api_key",
}


def _mask_key(val: str) -> str:
    """Show first 5 chars, mask the rest."""
    if len(val) > 5:
        return val[:5] + "•" * (len(val) - 5)
    return val


@router.get("", response_model=SettingsResponse)
async def get_settings():
    db = await get_db()
    try:
        result = {}
        for key in SETTING_KEYS:
            cursor = await db.execute(
                "SELECT value FROM settings WHERE key = ?", (key,)
            )
            row = await cursor.fetchone()
            if row:
                val = row["value"]
                if key.endswith("_api_key") and val:
                    val = _mask_key(val)
                result[key] = val
            else:
                result[key] = DEFAULTS.get(key, "")
        return SettingsResponse(**result)
    finally:
        await db.close()


@router.put("", response_model=SettingsResponse)
async def update_settings(data: SettingsUpdate):
    db = await get_db()
    try:
        for key in SETTING_KEYS:
            val = getattr(data, key, None)
            if val is None:
                continue
            # Don't save masked values back
            if key.endswith("_api_key") and "•" in val:
                continue
            await db.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, val),
            )
        await db.commit()

        # Return updated settings
        result = {}
        for key in SETTING_KEYS:
            cursor = await db.execute(
                "SELECT value FROM settings WHERE key = ?", (key,)
            )
            row = await cursor.fetchone()
            if row:
                val = row["value"]
                if key.endswith("_api_key") and val:
                    val = _mask_key(val)
                result[key] = val
            else:
                result[key] = DEFAULTS.get(key, "")
        return SettingsResponse(**result)
    finally:
        await db.close()


@router.post("/validate-key", response_model=ValidateKeyResponse)
async def validate_key(data: ValidateKeyRequest):
    """Test if an API key works by making a minimal API call."""
    db_key = PROVIDER_KEY_MAP[data.provider]
    api_key = await get_setting_value(db_key)
    if not api_key:
        return ValidateKeyResponse(valid=False, error="Klucz API nie jest ustawiony")

    try:
        if data.provider == "anthropic":
            client = anthropic.AsyncAnthropic(api_key=api_key)
            await client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1,
                messages=[{"role": "user", "content": "hi"}],
            )
        elif data.provider == "openai":
            client = openai.AsyncOpenAI(api_key=api_key)
            await client.models.list()
        elif data.provider == "google":
            client = genai.Client(api_key=api_key)
            await client.aio.models.get(model="gemini-2.0-flash")

        return ValidateKeyResponse(valid=True)
    except anthropic.AuthenticationError:
        return ValidateKeyResponse(valid=False, error="Nieprawidłowy klucz API")
    except openai.AuthenticationError:
        return ValidateKeyResponse(valid=False, error="Nieprawidłowy klucz API")
    except Exception as e:
        msg = str(e)
        if "api_key" in msg.lower() or "auth" in msg.lower() or "401" in msg or "403" in msg:
            return ValidateKeyResponse(valid=False, error="Nieprawidłowy klucz API")
        return ValidateKeyResponse(valid=False, error=f"Błąd połączenia: {msg[:200]}")


async def get_setting_value(key: str) -> str | None:
    """Helper to get a raw setting value (unmasked). Used by services."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        )
        row = await cursor.fetchone()
        return row["value"] if row else None
    finally:
        await db.close()
