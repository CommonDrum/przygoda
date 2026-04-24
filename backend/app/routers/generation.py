import asyncio
import logging

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect
from jose import JWTError
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)

from ..auth import verify_token
from ..models.schemas import ProjectResponse, PageResponse, RegenerateRequest
from ..services.story_service import (
    generate_reference,
    regenerate_reference,
    approve_reference,
    generate_story,
    generate_page_prompts,
    generate_images,
    regenerate_single_image,
)
from ..services.ws_manager import ConnectionManager

router = APIRouter(tags=["generation"])
ws_router = APIRouter(tags=["websocket"])

limiter = Limiter(key_func=get_remote_address)

# Singleton — will be set from main.py
ws_manager: ConnectionManager | None = None


def set_ws_manager(manager: ConnectionManager):
    global ws_manager
    ws_manager = manager


def _handle_error(e: Exception):
    msg = str(e)
    if "not found" in msg.lower():
        raise HTTPException(404, msg)
    if "Cannot" in msg or "oczekiwano" in msg.lower() or "expected" in msg.lower():
        raise HTTPException(409, msg)
    raise HTTPException(500, msg)


# ---- Reference image stage ----

@router.post(
    "/projects/{project_id}/generate-reference",
    response_model=ProjectResponse,
)
@limiter.limit("3/minute")
async def api_generate_reference(project_id: int, request: Request):
    try:
        return await generate_reference(project_id, ws_manager=ws_manager)
    except HTTPException:
        raise
    except Exception as e:
        _handle_error(e)


@router.post(
    "/projects/{project_id}/regenerate-reference",
    response_model=ProjectResponse,
)
@limiter.limit("6/minute")
async def api_regenerate_reference(
    project_id: int, request: Request, body: RegenerateRequest | None = None,
):
    try:
        return await regenerate_reference(
            project_id, ws_manager=ws_manager,
            new_prompt=(body.prompt if body else None),
        )
    except HTTPException:
        raise
    except Exception as e:
        _handle_error(e)


@router.post(
    "/projects/{project_id}/approve-reference",
    response_model=ProjectResponse,
)
@limiter.limit("10/minute")
async def api_approve_reference(project_id: int, request: Request):
    try:
        return await approve_reference(project_id, ws_manager=ws_manager)
    except HTTPException:
        raise
    except Exception as e:
        _handle_error(e)


# ---- Story + page prompts ----

@router.post(
    "/projects/{project_id}/generate-story",
    response_model=ProjectResponse,
)
@limiter.limit("3/minute")
async def api_generate_story(project_id: int, request: Request):
    try:
        return await generate_story(project_id, ws_manager=ws_manager)
    except HTTPException:
        raise
    except Exception as e:
        _handle_error(e)


@router.post(
    "/projects/{project_id}/generate-prompts",
    response_model=ProjectResponse,
)
@limiter.limit("3/minute")
async def api_generate_prompts(project_id: int, request: Request):
    try:
        return await generate_page_prompts(project_id, ws_manager=ws_manager)
    except HTTPException:
        raise
    except Exception as e:
        _handle_error(e)


# ---- Page images ----

@router.post("/projects/{project_id}/generate-images", status_code=202)
@limiter.limit("2/minute")
async def api_generate_images(project_id: int, request: Request):
    if not ws_manager:
        raise HTTPException(500, "WebSocket manager not initialized")

    from ..database import get_db
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT status FROM projects WHERE id = ?", (project_id,)
        )
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(404, "Projekt nie znaleziony")
        if row["status"] == "images_generating":
            raise HTTPException(409, "Generowanie obrazków już trwa")
        if row["status"] != "prompts_generated":
            raise HTTPException(409, f"Nie można generować obrazków w statusie '{row['status']}'")
    finally:
        await db.close()

    async def _run():
        try:
            await generate_images(project_id, ws_manager)
        except Exception:
            logger.exception("generate_images task crashed for project %d", project_id)

    asyncio.create_task(_run())
    return {"status": "started"}


@router.post("/pages/{page_id}/regenerate-image", response_model=PageResponse)
@limiter.limit("6/minute")
async def api_regenerate_image(
    page_id: int, request: Request, body: RegenerateRequest | None = None,
):
    try:
        prompt = body.prompt if body else None
        return await regenerate_single_image(page_id, prompt=prompt)
    except HTTPException:
        raise
    except Exception as e:
        _handle_error(e)


@ws_router.websocket("/ws/generation/{project_id}")
async def generation_ws(websocket: WebSocket, project_id: int):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001)
        return
    try:
        verify_token(token)
    except JWTError:
        await websocket.close(code=4001)
        return
    if not ws_manager:
        await websocket.close()
        return
    await ws_manager.connect(project_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(project_id, websocket)
