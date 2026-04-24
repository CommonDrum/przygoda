from fastapi import APIRouter

from ..providers.catalog import LLM_MODELS, IMAGE_MODELS

router = APIRouter(prefix="/providers", tags=["providers"])


@router.get("/models")
async def get_model_catalog():
    """Return the catalog of available models per provider for UI dropdowns."""
    return {
        "llm": LLM_MODELS,
        "image": IMAGE_MODELS,
    }
