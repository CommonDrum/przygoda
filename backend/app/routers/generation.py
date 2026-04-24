import asyncio
import logging

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from jose import JWTError

logger = logging.getLogger(__name__)

from ..auth import verify_token
from ..models.schemas import ProjectResponse, PageResponse, RegenerateRequest
from ..services.locks import (
    ProjectBusyError,
    is_project_busy,
    page_busy,
    project_busy,
)
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


def _busy_409() -> HTTPException:
    return HTTPException(409, "Dla tego projektu już trwa operacja")


# ---- Reference image stage ----

@router.post(
    "/projects/{project_id}/generate-reference",
    response_model=ProjectResponse,
)
async def api_generate_reference(project_id: int):
    try:
        async with project_busy(project_id):
            return await generate_reference(project_id, ws_manager=ws_manager)
    except ProjectBusyError:
        raise _busy_409()
    except HTTPException:
        raise
    except Exception as e:
        _handle_error(e)


@router.post(
    "/projects/{project_id}/regenerate-reference",
    response_model=ProjectResponse,
)
async def api_regenerate_reference(
    project_id: int, body: RegenerateRequest | None = None,
):
    try:
        async with project_busy(project_id):
            return await regenerate_reference(
                project_id, ws_manager=ws_manager,
                new_prompt=(body.prompt if body else None),
            )
    except ProjectBusyError:
        raise _busy_409()
    except HTTPException:
        raise
    except Exception as e:
        _handle_error(e)


@router.post(
    "/projects/{project_id}/approve-reference",
    response_model=ProjectResponse,
)
async def api_approve_reference(project_id: int):
    try:
        async with project_busy(project_id):
            return await approve_reference(project_id, ws_manager=ws_manager)
    except ProjectBusyError:
        raise _busy_409()
    except HTTPException:
        raise
    except Exception as e:
        _handle_error(e)


# ---- Story + page prompts ----

@router.post(
    "/projects/{project_id}/generate-story",
    response_model=ProjectResponse,
)
async def api_generate_story(project_id: int):
    try:
        async with project_busy(project_id):
            return await generate_story(project_id, ws_manager=ws_manager)
    except ProjectBusyError:
        raise _busy_409()
    except HTTPException:
        raise
    except Exception as e:
        _handle_error(e)


@router.post(
    "/projects/{project_id}/generate-prompts",
    response_model=ProjectResponse,
)
async def api_generate_prompts(project_id: int):
    try:
        async with project_busy(project_id):
            return await generate_page_prompts(project_id, ws_manager=ws_manager)
    except ProjectBusyError:
        raise _busy_409()
    except HTTPException:
        raise
    except Exception as e:
        _handle_error(e)


# ---- Page images ----

@router.post("/projects/{project_id}/generate-images", status_code=202)
async def api_generate_images(project_id: int):
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

    # Pre-flight check — the lock itself is taken inside the task (because the
    # work is fire-and-forget and outlives this request).
    if is_project_busy(project_id):
        raise _busy_409()

    async def _run():
        try:
            async with project_busy(project_id):
                await generate_images(project_id, ws_manager)
        except ProjectBusyError:
            pass  # lost the race with another task — fine
        except Exception:
            logger.exception("generate_images task crashed for project %d", project_id)

    asyncio.create_task(_run())
    return {"status": "started"}


@router.post("/pages/{page_id}/regenerate-image", response_model=PageResponse)
async def api_regenerate_image(
    page_id: int, body: RegenerateRequest | None = None,
):
    try:
        async with page_busy(page_id):
            prompt = body.prompt if body else None
            return await regenerate_single_image(page_id, prompt=prompt)
    except ProjectBusyError:
        raise HTTPException(409, "Ta strona jest w trakcie regeneracji")
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
