import os
from pathlib import Path

from pydantic_settings import BaseSettings

# backend/ directory — all paths are relative to this
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    DATABASE_URL: str = str(BASE_DIR / "przygoda.db")
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""
    LLM_PROVIDER: str = "anthropic"
    IMAGE_PROVIDER: str = "google"
    IMAGE_CONCURRENCY: int = 3  # max parallel image gen requests (2–3 to stay under typical provider RPM)
    APP_USERNAME: str = "admin"
    APP_PASSWORD_HASH: str = ""
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_EXPIRE_MINUTES: int = 1440
    CORS_ORIGINS: str = "http://localhost:5173"
    DATA_DIR: str = ""

    model_config = {"env_file": str(BASE_DIR / ".env")}


settings = Settings()

# Derived paths — DATA_DIR overrides defaults when set (Docker)
if settings.DATA_DIR:
    _data = Path(settings.DATA_DIR)
    STATIC_DIR = _data / "static"
    UPLOADS_DIR = STATIC_DIR / "uploads"
    EXPORTS_DIR = STATIC_DIR / "exports"
else:
    STATIC_DIR = BASE_DIR / "app" / "static"
    UPLOADS_DIR = STATIC_DIR / "uploads"
    EXPORTS_DIR = STATIC_DIR / "exports"
