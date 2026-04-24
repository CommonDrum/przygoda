from typing import Literal

from pydantic import BaseModel, Field


FulfillmentStatus = Literal["oczekuje", "w_drukarni", "wyslane", "doreczone"]


# --- Projects ---

class ProjectCreate(BaseModel):
    child_name: str = Field(min_length=1)
    child_age: int = Field(ge=2, le=12)
    child_gender: str = "dziewczynka"
    hair_color: str = Field(min_length=1)
    hair_style: str = Field(min_length=1)
    skin_tone: str = Field(min_length=1)
    eye_color: str = Field(min_length=1)
    outfit_description: str = Field(min_length=1)
    story_type: str = Field(min_length=1)
    hobby: str = Field(min_length=1)
    moral: str = Field(min_length=1)
    story_prompt_id: int | None = None
    image_prompt_id: int | None = None


class ProjectUpdate(BaseModel):
    child_name: str | None = None
    child_age: int | None = Field(default=None, ge=2, le=12)
    child_gender: str | None = None
    hair_color: str | None = None
    hair_style: str | None = None
    skin_tone: str | None = None
    eye_color: str | None = None
    outfit_description: str | None = None
    story_type: str | None = None
    hobby: str | None = None
    moral: str | None = None
    llm_provider: str | None = None
    image_provider: str | None = None
    story_prompt_id: int | None = None
    image_prompt_id: int | None = None
    fulfillment_status: FulfillmentStatus | None = None


class RegenerateRequest(BaseModel):
    prompt: str | None = None


class ProjectResponse(BaseModel):
    id: int
    child_name: str
    child_age: int
    child_gender: str
    hair_color: str
    hair_style: str
    skin_tone: str
    eye_color: str
    outfit_description: str
    story_type: str
    hobby: str
    moral: str
    raw_story: str | None = None
    raw_image_prompts: str | None = None
    llm_provider: str
    image_provider: str
    reference_image_prompt: str | None = None
    reference_image_path: str | None = None
    reference_image_version: int = 0
    story_prompt_id: int | None = None
    image_prompt_id: int | None = None
    fulfillment_status: FulfillmentStatus = "oczekuje"
    status: str
    created_at: str
    updated_at: str


# --- Pages ---

class PageResponse(BaseModel):
    id: int
    project_id: int
    page_number: int
    page_type: str
    text: str | None = None
    image_prompt: str | None = None
    current_image_path: str | None = None
    reference_image_path: str | None = None
    version: int


class PageUpdate(BaseModel):
    text: str | None = None
    image_prompt: str | None = None


# --- Image Versions ---

class ImageVersionResponse(BaseModel):
    id: int
    page_id: int | None = None
    project_id: int | None = None
    kind: str = "page"
    image_path: str
    prompt_used: str
    provider: str
    version_number: int
    created_at: str


class RestoreVersionRequest(BaseModel):
    version_id: int


# --- Prompts library ---

class PromptCreate(BaseModel):
    kind: Literal["story", "image"]
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1)


class PromptUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    content: str | None = Field(default=None, min_length=1)


class PromptResponse(BaseModel):
    id: int
    kind: Literal["story", "image"]
    title: str
    content: str
    is_default: bool
    created_at: str
    updated_at: str


# --- Export ---

class ExportRequest(BaseModel):
    format: str = Field(pattern=r"^(zip|excel|txt)$")


class ExportResponse(BaseModel):
    file_path: str


# --- Settings ---

class SettingsUpdate(BaseModel):
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    nano_banana_api_key: str | None = None
    google_api_key: str | None = None
    default_llm_provider: str | None = None
    default_image_provider: str | None = None
    image_aspect_ratio: str | None = None
    image_size: str | None = None


class SettingsResponse(BaseModel):
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    nano_banana_api_key: str = ""
    google_api_key: str = ""
    default_llm_provider: str = "anthropic"
    default_image_provider: str = "nano_banana"
    image_aspect_ratio: str = "1:1"
    image_size: str = "1K"


class ValidateKeyRequest(BaseModel):
    provider: str = Field(pattern=r"^(anthropic|openai|nano_banana|google)$")


class ValidateKeyResponse(BaseModel):
    valid: bool
    error: str | None = None
