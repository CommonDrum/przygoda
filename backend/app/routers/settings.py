from fastapi import APIRouter

from ..database import get_db
from ..models.schemas import SettingsUpdate, SettingsResponse

router = APIRouter(prefix="/settings", tags=["settings"])

# Keys that are stored in the settings table
SETTING_KEYS = [
    "anthropic_api_key",
    "openai_api_key",
    "nano_banana_api_key",
    "google_api_key",
    "default_llm_provider",
    "default_image_provider",
    "story_system_prompt",
    "image_system_prompt",
    "image_aspect_ratio",
    "image_size",
]

DEFAULTS = {
    "default_llm_provider": "anthropic",
    "default_image_provider": "nano_banana",
    "image_aspect_ratio": "1:1",
    "image_size": "1K",
}


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
                # Mask API keys — send only last 4 chars
                val = row["value"]
                if key.endswith("_api_key") and len(val) > 4:
                    val = "•" * (len(val) - 4) + val[-4:]
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
                if key.endswith("_api_key") and len(val) > 4:
                    val = "•" * (len(val) - 4) + val[-4:]
                result[key] = val
            else:
                result[key] = DEFAULTS.get(key, "")
        return SettingsResponse(**result)
    finally:
        await db.close()


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
