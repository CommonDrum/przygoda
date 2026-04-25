import asyncio
import logging
import os
import random

from ..database import get_db
from ..errors import classify_error

logger = logging.getLogger(__name__)
from ..providers.factory import get_llm_provider, get_image_provider
from ..routers.settings import get_setting_value
from ..routers.prompts import get_prompt_content
from ..templates.story_prompt import build_story_system_prompt, build_story_user_prompt
from ..templates.image_prompt import (
    build_reference_system_prompt,
    build_reference_user_prompt,
    build_page_system_prompt,
    build_page_user_prompt,
    build_cover_image_prompt,
    build_back_image_prompt,
)
from ..config import settings, UPLOADS_DIR, STATIC_DIR
from .ws_manager import ConnectionManager

SEPARATOR = "#########"
MAX_LLM_RETRIES = 2  # on top of the first call → up to 3 total

STATUS_DRAFT = "draft"
STATUS_REF_GENERATING = "ref_pic_generating"
STATUS_REF_REVIEW = "ref_pic_review"
STATUS_STORY_GENERATING = "story_generating"
STATUS_STORY_GENERATED = "story_generated"
STATUS_PROMPTS_GENERATING = "prompts_generating"
STATUS_PROMPTS_GENERATED = "prompts_generated"
STATUS_IMAGES_GENERATING = "images_generating"
STATUS_IMAGES_PARTIAL = "images_partial"  # some page images failed — user can retry
STATUS_REVIEW = "review"
STATUS_EXPORTED = "exported"

# Per-page image states
IMG_PENDING = "pending"
IMG_GENERATING = "generating"
IMG_DONE = "done"
IMG_FAILED = "failed"


async def _set_page_image_status(
    db, page_id: int, status: str, error: str | None = None,
):
    """Set per-page image_status (+ optional error message). Caller commits."""
    await db.execute(
        "UPDATE pages SET image_status = ?, image_error = ? WHERE id = ?",
        (status, (error[:500] if error else None), page_id),
    )


def _load_image_bytes(static_url: str | None) -> bytes | None:
    """Resolve a /static/... URL to absolute path and read bytes, or None."""
    if not static_url:
        return None
    abs_path = str(STATIC_DIR / static_url.removeprefix("/static/"))
    if not os.path.exists(abs_path):
        return None
    with open(abs_path, "rb") as f:
        return f.read()


def _build_reference_images(project: dict, include_character: bool) -> list[bytes]:
    """Build the ordered list of reference images passed to the image provider.

    Order matters for providers that can only use one — character ref last so
    it wins (see NanoBananaImage.generate_image).
    """
    images: list[bytes] = []
    style_guide = _load_image_bytes(project.get("style_guide_image_path"))
    if style_guide:
        images.append(style_guide)
    if include_character:
        character = _load_image_bytes(project.get("reference_image_path"))
        if character:
            images.append(character)
    return images


def _build_page_reference_images(project: dict, page: dict) -> list[bytes]:
    """Per-page references. Back cover skips the character ref so providers
    that take only one image (nano_banana) don't pull the kid into a page
    whose prompt is supposed to be a character-less symbolic scene."""
    include_character = page.get("page_type") != "back"
    return _build_reference_images(project, include_character=include_character)


async def _get_project(project_id: int) -> dict:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        row = await cursor.fetchone()
        if not row:
            raise ValueError(f"Project {project_id} not found")
        return {k: row[k] for k in row.keys()}
    finally:
        await db.close()


async def _update_project_status(project_id: int, status: str, **extra_fields):
    db = await get_db()
    try:
        sets = ["status = ?", "updated_at = CURRENT_TIMESTAMP"]
        params: list = [status]
        for k, v in extra_fields.items():
            sets.append(f"{k} = ?")
            params.append(v)
        params.append(project_id)
        await db.execute(
            f"UPDATE projects SET {', '.join(sets)} WHERE id = ?", params
        )
        await db.commit()
    finally:
        await db.close()


async def _broadcast_status(ws_manager: ConnectionManager | None, project_id: int, status: str):
    if ws_manager is None:
        return
    await ws_manager.send_to_project(project_id, {
        "type": "project_status",
        "status": status,
    })


async def _stream_llm(llm, system_prompt: str, user_prompt: str,
                      ws_manager: ConnectionManager | None, project_id: int,
                      phase: str) -> str:
    """Stream LLM response, sending chunks via WS if available."""
    has_listeners = (
        ws_manager is not None
        and len(ws_manager.connections.get(project_id, [])) > 0
    )
    if has_listeners:
        chunks = []
        async for chunk in llm.generate_stream(system_prompt, user_prompt):
            chunks.append(chunk)
            await ws_manager.send_to_project(project_id, {
                "type": "text_stream",
                "chunk": chunk,
                "phase": phase,
            })
        await ws_manager.send_to_project(project_id, {
            "type": "text_done",
            "phase": phase,
        })
        return "".join(chunks)
    else:
        return await llm.generate(system_prompt, user_prompt)


async def _call_llm_with_retry(llm, system_prompt: str, user_prompt: str,
                                ws_manager, project_id, phase,
                                validate, parse):
    """Call LLM, parse+validate output. On validation failure re-ask with a correction
    hint up to MAX_LLM_RETRIES extra times. Returns parsed output."""
    last_error = None
    current_user_prompt = user_prompt

    for attempt in range(MAX_LLM_RETRIES + 1):
        raw = await _stream_llm(llm, system_prompt, current_user_prompt,
                                 ws_manager, project_id, phase)
        try:
            parsed = parse(raw)
            validate(parsed, raw)
            return raw, parsed
        except ValueError as e:
            last_error = e
            logger.warning(
                "LLM output validation failed (attempt %d/%d) for project %d phase %s: %s",
                attempt + 1, MAX_LLM_RETRIES + 1, project_id, phase, e,
            )
            current_user_prompt = (
                f"{user_prompt}\n\n"
                f"Poprzednia odpowiedź była niepoprawna: {e}. "
                f"Zwróć dokładnie oczekiwany format, bez dodatkowych komentarzy."
            )

    raise last_error  # type: ignore[misc]


# ============================================================
# Stage 1: Reference image (LLM prompt + first image)
# ============================================================

async def generate_reference(project_id: int, ws_manager: ConnectionManager | None = None) -> dict:
    project = await _get_project(project_id)

    if project["status"] not in (STATUS_DRAFT, STATUS_REF_REVIEW):
        raise ValueError(
            f"Cannot generate reference: project status is '{project['status']}', "
            f"expected '{STATUS_DRAFT}' or '{STATUS_REF_REVIEW}'"
        )

    await _update_project_status(project_id, STATUS_REF_GENERATING)
    await _broadcast_status(ws_manager, project_id, STATUS_REF_GENERATING)

    try:
        custom_prompt = await get_prompt_content(project.get("image_prompt_id"), "image")
        system_prompt = build_reference_system_prompt(project, custom_prompt)
        user_prompt = build_reference_user_prompt(project)

        llm = await get_llm_provider(project.get("llm_provider"), project.get("llm_model"))

        def _parse(raw: str) -> str:
            # Take the first non-empty block if LLM added separators anyway.
            blocks = [b.strip() for b in raw.split(SEPARATOR) if b.strip()]
            return blocks[0] if blocks else raw.strip()

        def _validate(parsed: str, raw: str):
            if len(parsed) < 40:
                raise ValueError(
                    f"Reference prompt za krótki ({len(parsed)} znaków), oczekiwano pełnego opisu postaci."
                )

        _, ref_prompt = await _call_llm_with_retry(
            llm, system_prompt, user_prompt, ws_manager, project_id,
            "reference", _validate, _parse,
        )

        # Generate the actual image
        image_provider = await get_image_provider(project.get("image_provider"), project.get("image_model"))
        aspect_ratio = await get_setting_value("image_aspect_ratio") or "1:1"
        image_size = await get_setting_value("image_size") or "1K"

        upload_dir = str(UPLOADS_DIR / str(project_id))
        os.makedirs(upload_dir, exist_ok=True)

        new_version = (project.get("reference_image_version") or 0) + 1
        if ws_manager:
            await ws_manager.send_to_project(project_id, {
                "type": "image_progress",
                "page_number": 0,
                "status": "generating",
            })

        image_bytes = await image_provider.generate_image(
            ref_prompt,
            reference_images=_build_reference_images(project, include_character=False),
            aspect_ratio=aspect_ratio, image_size=image_size,
        )

        filename = f"reference_v{new_version}.png"
        filepath = os.path.join(upload_dir, filename)
        with open(filepath, "wb") as f:
            f.write(image_bytes)
        image_path = f"/static/uploads/{project_id}/{filename}"

        db = await get_db()
        try:
            await db.execute(
                """INSERT INTO image_versions
                   (project_id, kind, image_path, prompt_used, provider, version_number)
                   VALUES (?, 'reference', ?, ?, ?, ?)""",
                (project_id, image_path, ref_prompt,
                 project.get("image_provider", "nano_banana"), new_version),
            )
            await db.commit()
        finally:
            await db.close()

        await _update_project_status(
            project_id, STATUS_REF_REVIEW,
            reference_image_prompt=ref_prompt,
            reference_image_path=image_path,
            reference_image_version=new_version,
            reference_image_is_custom=0,
        )
        await _broadcast_status(ws_manager, project_id, STATUS_REF_REVIEW)
        if ws_manager:
            await ws_manager.send_to_project(project_id, {
                "type": "image_progress",
                "page_number": 0,
                "status": "completed",
                "image_path": image_path,
                "version": new_version,
            })
        return await _get_project(project_id)
    except Exception:
        await _update_project_status(project_id, STATUS_DRAFT)
        await _broadcast_status(ws_manager, project_id, STATUS_DRAFT)
        raise


async def regenerate_reference(project_id: int, ws_manager: ConnectionManager | None = None,
                                 new_prompt: str | None = None) -> dict:
    """Regenerate the reference IMAGE using the existing prompt (or a user-provided one).
    Does NOT re-call the LLM unless new_prompt replaces the stored prompt."""
    project = await _get_project(project_id)
    if project["status"] != STATUS_REF_REVIEW:
        raise ValueError(
            f"Cannot regenerate reference: project status is '{project['status']}', "
            f"expected '{STATUS_REF_REVIEW}'"
        )

    ref_prompt = new_prompt or project.get("reference_image_prompt")
    if not ref_prompt:
        raise ValueError("Brak promptu referencyjnego do regeneracji")

    image_provider = await get_image_provider(project.get("image_provider"), project.get("image_model"))
    aspect_ratio = await get_setting_value("image_aspect_ratio") or "1:1"
    image_size = await get_setting_value("image_size") or "1K"

    upload_dir = str(UPLOADS_DIR / str(project_id))
    os.makedirs(upload_dir, exist_ok=True)

    new_version = (project.get("reference_image_version") or 0) + 1

    if ws_manager:
        await ws_manager.send_to_project(project_id, {
            "type": "image_progress",
            "page_number": 0,
            "status": "generating",
        })

    image_bytes = await image_provider.generate_image(
        ref_prompt,
        reference_images=_build_reference_images(project, include_character=False),
        aspect_ratio=aspect_ratio, image_size=image_size,
    )
    filename = f"reference_v{new_version}.png"
    filepath = os.path.join(upload_dir, filename)
    with open(filepath, "wb") as f:
        f.write(image_bytes)
    image_path = f"/static/uploads/{project_id}/{filename}"

    db = await get_db()
    try:
        await db.execute(
            """INSERT INTO image_versions
               (project_id, kind, image_path, prompt_used, provider, version_number)
               VALUES (?, 'reference', ?, ?, ?, ?)""",
            (project_id, image_path, ref_prompt,
             project.get("image_provider", "nano_banana"), new_version),
        )
        await db.commit()
    finally:
        await db.close()

    await _update_project_status(
        project_id, STATUS_REF_REVIEW,
        reference_image_prompt=ref_prompt,
        reference_image_path=image_path,
        reference_image_version=new_version,
        reference_image_is_custom=0,
    )

    if ws_manager:
        await ws_manager.send_to_project(project_id, {
            "type": "image_progress",
            "page_number": 0,
            "status": "completed",
            "image_path": image_path,
            "version": new_version,
        })

    return await _get_project(project_id)


async def approve_reference(project_id: int, ws_manager: ConnectionManager | None = None) -> dict:
    project = await _get_project(project_id)
    if project["status"] != STATUS_REF_REVIEW:
        raise ValueError(
            f"Cannot approve reference: project status is '{project['status']}', "
            f"expected '{STATUS_REF_REVIEW}'"
        )
    await _update_project_status(project_id, STATUS_STORY_GENERATING)
    await _broadcast_status(ws_manager, project_id, STATUS_STORY_GENERATING)
    return await _get_project(project_id)


# ============================================================
# Stage 2: Story
# ============================================================

async def generate_story(project_id: int, ws_manager: ConnectionManager | None = None) -> dict:
    project = await _get_project(project_id)

    if project["status"] != STATUS_STORY_GENERATING:
        raise ValueError(
            f"Cannot generate story: project status is '{project['status']}', "
            f"expected '{STATUS_STORY_GENERATING}'"
        )

    try:
        custom_prompt = await get_prompt_content(project.get("story_prompt_id"), "story")
        system_prompt = build_story_system_prompt(project, custom_prompt)
        user_prompt = build_story_user_prompt(project)

        llm = await get_llm_provider(project.get("llm_provider"), project.get("llm_model"))

        def _parse(raw: str):
            return [s.strip() for s in raw.split(SEPARATOR) if s.strip()]

        def _validate(segments, raw):
            if len(segments) < 15:
                raise ValueError(f"Oczekiwano 15 segmentów historii, otrzymano {len(segments)}.")

        raw_story, segments = await _call_llm_with_retry(
            llm, system_prompt, user_prompt, ws_manager, project_id,
            "story", _validate, _parse,
        )

        db = await get_db()
        try:
            for i, text in enumerate(segments[:15]):
                page_number = i + 2
                await db.execute(
                    "UPDATE pages SET text = ? WHERE project_id = ? AND page_number = ?",
                    (text, project_id, page_number),
                )
            await db.execute(
                "UPDATE pages SET text = ? WHERE project_id = ? AND page_number = 1",
                (f"Przygoda {project['child_name']}", project_id),
            )
            await db.execute(
                "UPDATE pages SET text = ? WHERE project_id = ? AND page_number = 17",
                ("Koniec", project_id),
            )
            await db.commit()
        finally:
            await db.close()

        await _update_project_status(project_id, STATUS_STORY_GENERATED, raw_story=raw_story)
        await _broadcast_status(ws_manager, project_id, STATUS_STORY_GENERATED)
        return await _get_project(project_id)
    except Exception:
        # Revert to the gate so the user can retry.
        await _update_project_status(project_id, STATUS_STORY_GENERATING)
        raise


# ============================================================
# Stage 3: Page image prompts (17 prompts — cover + 15 story + back)
# ============================================================

async def generate_page_prompts(project_id: int, ws_manager: ConnectionManager | None = None) -> dict:
    project = await _get_project(project_id)

    if project["status"] not in (STATUS_STORY_GENERATED, STATUS_PROMPTS_GENERATED):
        raise ValueError(
            f"Cannot generate prompts: project status is '{project['status']}', "
            f"expected '{STATUS_STORY_GENERATED}' or '{STATUS_PROMPTS_GENERATED}'"
        )
    if not project.get("raw_story"):
        raise ValueError("Historia nie została wygenerowana")

    await _update_project_status(project_id, STATUS_PROMPTS_GENERATING)
    await _broadcast_status(ws_manager, project_id, STATUS_PROMPTS_GENERATING)

    try:
        custom_prompt = await get_prompt_content(project.get("image_prompt_id"), "image")
        system_prompt = build_page_system_prompt(project, custom_prompt)
        user_prompt = build_page_user_prompt(
            project, project["raw_story"], project.get("reference_image_prompt"),
        )

        llm = await get_llm_provider(project.get("llm_provider"), project.get("llm_model"))

        def _parse(raw: str):
            return [p.strip() for p in raw.split(SEPARATOR) if p.strip()]

        def _validate(prompts, raw):
            # Accept 15 (new default — story prompts only) or 17+ (legacy
            # custom prompt that still produces cover+15+back). In the legacy
            # case we discard prompts[0] (cover) and prompts[16] (back) below
            # — Python templates always win for those.
            if len(prompts) not in (15,) and len(prompts) < 17:
                raise ValueError(
                    f"Oczekiwano 15 promptów (po jednym na segment historii), "
                    f"otrzymano {len(prompts)}."
                )

        raw_prompts, prompts = await _call_llm_with_retry(
            llm, system_prompt, user_prompt, ws_manager, project_id,
            "prompts", _validate, _parse,
        )

        # Pick the 15 story-page prompts regardless of whether the LLM
        # returned 15 (new) or 17 with cover+back (legacy custom prompt).
        if len(prompts) >= 17:
            story_prompts = prompts[1:16]
        else:
            story_prompts = prompts[:15]

        # Cover (page 1) and back (page 17) are ALWAYS built by Python
        # templates — invariant under any custom system prompt.
        cover_prompt = build_cover_image_prompt(project)
        back_prompt = build_back_image_prompt(project)

        db = await get_db()
        try:
            await db.execute(
                "UPDATE pages SET image_prompt = ? WHERE project_id = ? AND page_number = 1",
                (cover_prompt, project_id),
            )
            for i, prompt in enumerate(story_prompts):
                page_number = i + 2
                await db.execute(
                    "UPDATE pages SET image_prompt = ? WHERE project_id = ? AND page_number = ?",
                    (prompt, project_id, page_number),
                )
            await db.execute(
                "UPDATE pages SET image_prompt = ? WHERE project_id = ? AND page_number = 17",
                (back_prompt, project_id),
            )
            await db.commit()
        finally:
            await db.close()

        await _update_project_status(
            project_id, STATUS_PROMPTS_GENERATED,
            raw_image_prompts=raw_prompts,
        )
        await _broadcast_status(ws_manager, project_id, STATUS_PROMPTS_GENERATED)
        return await _get_project(project_id)
    except Exception:
        await _update_project_status(project_id, STATUS_STORY_GENERATED)
        raise


# ============================================================
# Stage 4: Page images (17 parallel, using already-generated reference)
# ============================================================

async def _generate_one_page(
    project: dict, page: dict, *,
    image_provider, reference_images: list[bytes],
    aspect_ratio: str, image_size: str,
    upload_dir: str, ws_manager: ConnectionManager | None,
) -> bool:
    """Generate a single page image and persist it. Returns True on success.

    Sets `pages.image_status` and `pages.image_error` in all paths so the UI
    always reflects reality, and broadcasts per-page progress via WS.
    """
    project_id = project["id"]
    page_id = page["id"]
    page_num = page["page_number"]

    # Mark generating + broadcast
    db0 = await get_db()
    try:
        await _set_page_image_status(db0, page_id, IMG_GENERATING)
        await db0.commit()
    finally:
        await db0.close()

    if ws_manager:
        await ws_manager.send_to_project(project_id, {
            "type": "image_progress",
            "page_number": page_num,
            "page_id": page_id,
            "status": "generating",
        })

    # Small jitter so N parallel calls don't hit the API in the exact same tick.
    await asyncio.sleep(random.uniform(0, 0.2))

    try:
        image_bytes = await image_provider.generate_image(
            page["image_prompt"],
            reference_images=reference_images,
            aspect_ratio=aspect_ratio, image_size=image_size,
        )

        new_version = (page.get("version") or 0) + 1
        filename = f"page_{page_num}_v{new_version}.png"
        filepath = os.path.join(upload_dir, filename)
        with open(filepath, "wb") as f:
            f.write(image_bytes)
        image_path = f"/static/uploads/{project_id}/{filename}"

        db = await get_db()
        try:
            await db.execute(
                "UPDATE pages SET current_image_path = ?, version = ? WHERE id = ?",
                (image_path, new_version, page_id),
            )
            await _set_page_image_status(db, page_id, IMG_DONE)
            await db.execute(
                """INSERT INTO image_versions
                   (page_id, project_id, kind, image_path, prompt_used, provider, version_number)
                   VALUES (?, ?, 'page', ?, ?, ?, ?)""",
                (page_id, project_id, image_path, page["image_prompt"],
                 project.get("image_provider", "nano_banana"), new_version),
            )
            await db.commit()
        finally:
            await db.close()

        if ws_manager:
            await ws_manager.send_to_project(project_id, {
                "type": "image_progress",
                "page_number": page_num,
                "page_id": page_id,
                "status": "completed",
                "image_path": image_path,
                "version": new_version,
            })
        return True
    except Exception as e:
        friendly = classify_error(e)
        logger.error(
            "Image gen failed page %d → %s: %s",
            page_num, friendly.code, e, exc_info=True,
        )
        # Store user-facing message in DB so the UI shows something sensible
        # even hours later (after the exception itself is long gone).
        stored = f"{friendly.title}. {friendly.hint}"
        db = await get_db()
        try:
            await _set_page_image_status(db, page_id, IMG_FAILED, stored)
            await db.commit()
        finally:
            await db.close()
        if ws_manager:
            await ws_manager.send_to_project(project_id, {
                "type": "image_progress",
                "page_number": page_num,
                "page_id": page_id,
                "status": "failed",
                "error": friendly.title,
                "code": friendly.code,
                "hint": friendly.hint,
                "retryable": friendly.retryable,
            })
        return False


async def _run_page_batch(
    project_id: int, pages: list[dict], ws_manager: ConnectionManager | None,
) -> tuple[int, int]:
    """Run the given pages through the image provider under the shared
    concurrency semaphore. Returns (completed, failed) counts."""
    project = await _get_project(project_id)
    image_provider = await get_image_provider(
        project.get("image_provider"), project.get("image_model"),
    )
    semaphore = asyncio.Semaphore(settings.IMAGE_CONCURRENCY)
    aspect_ratio = await get_setting_value("image_aspect_ratio") or "1:1"
    image_size = await get_setting_value("image_size") or "1K"

    upload_dir = str(UPLOADS_DIR / str(project_id))
    os.makedirs(upload_dir, exist_ok=True)

    completed = 0
    failed = 0

    async def guarded(page: dict):
        nonlocal completed, failed
        if not page.get("image_prompt"):
            return
        async with semaphore:
            ok = await _generate_one_page(
                project, page,
                image_provider=image_provider,
                reference_images=_build_page_reference_images(project, page),
                aspect_ratio=aspect_ratio, image_size=image_size,
                upload_dir=upload_dir, ws_manager=ws_manager,
            )
            if ok:
                completed += 1
            else:
                failed += 1

    await asyncio.gather(*[guarded(p) for p in pages])
    return completed, failed


async def _finalize_image_batch(
    project_id: int, ws_manager: ConnectionManager | None,
):
    """Decide the terminal project status based on per-page image_status.
    - all 17 content pages done → STATUS_REVIEW
    - some done / some failed-or-pending → STATUS_IMAGES_PARTIAL
    - none done → STATUS_PROMPTS_GENERATED (back to gate)
    """
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT image_status, image_prompt
               FROM pages WHERE project_id = ?""",
            (project_id,),
        )
        rows = list(await cursor.fetchall())
    finally:
        await db.close()

    with_prompts = [r for r in rows if r["image_prompt"]]
    done = sum(1 for r in with_prompts if r["image_status"] == IMG_DONE)
    total = len(with_prompts)

    if total > 0 and done == total:
        status = STATUS_REVIEW
    elif done > 0:
        status = STATUS_IMAGES_PARTIAL
    else:
        status = STATUS_PROMPTS_GENERATED

    await _update_project_status(project_id, status)
    await _broadcast_status(ws_manager, project_id, status)


async def generate_images(project_id: int, ws_manager: ConnectionManager):
    project = await _get_project(project_id)

    if project["status"] != STATUS_PROMPTS_GENERATED:
        raise ValueError(
            f"Cannot generate images: project status is '{project['status']}', "
            f"expected '{STATUS_PROMPTS_GENERATED}'"
        )

    await _update_project_status(project_id, STATUS_IMAGES_GENERATING)
    await _broadcast_status(ws_manager, project_id, STATUS_IMAGES_GENERATING)

    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM pages WHERE project_id = ? ORDER BY page_number",
            (project_id,),
        )
        pages = [{k: r[k] for k in r.keys()} for r in await cursor.fetchall()]
    finally:
        await db.close()

    # finalize in `finally` so a mid-batch crash never leaves the project
    # stuck in images_generating — finalize reads per-page image_status from
    # DB and picks the right terminal state (review / partial / prompts_generated).
    try:
        await _run_page_batch(project_id, pages, ws_manager)
    finally:
        await _finalize_image_batch(project_id, ws_manager)


async def retry_failed_images(
    project_id: int, ws_manager: ConnectionManager | None = None,
) -> dict:
    """Re-run image generation only for pages where image_status != 'done'.
    Usable from STATUS_IMAGES_PARTIAL or STATUS_REVIEW (in case user added a
    page manually), never from an in-progress state."""
    project = await _get_project(project_id)
    if project["status"] in (STATUS_IMAGES_GENERATING,):
        raise ValueError(
            f"Cannot retry: generation already in progress"
        )
    if project["status"] not in (STATUS_IMAGES_PARTIAL, STATUS_REVIEW,
                                  STATUS_PROMPTS_GENERATED):
        raise ValueError(
            f"Cannot retry images: project status is '{project['status']}'"
        )

    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT * FROM pages
               WHERE project_id = ?
                 AND image_prompt IS NOT NULL
                 AND image_status != ?
               ORDER BY page_number""",
            (project_id, IMG_DONE),
        )
        pages = [{k: r[k] for k in r.keys()} for r in await cursor.fetchall()]
    finally:
        await db.close()

    if not pages:
        return await _get_project(project_id)

    await _update_project_status(project_id, STATUS_IMAGES_GENERATING)
    await _broadcast_status(ws_manager, project_id, STATUS_IMAGES_GENERATING)

    try:
        await _run_page_batch(project_id, pages, ws_manager)
    finally:
        await _finalize_image_batch(project_id, ws_manager)
    return await _get_project(project_id)


# ============================================================
# Single page image regeneration
# ============================================================

async def regenerate_single_image(page_id: int, prompt: str | None = None) -> dict:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM pages WHERE id = ?", (page_id,))
        page = await cursor.fetchone()
        if not page:
            raise ValueError("Page not found")
        page = {k: page[k] for k in page.keys()}

        if prompt is not None:
            await db.execute(
                "UPDATE pages SET image_prompt = ? WHERE id = ?",
                (prompt, page_id),
            )
            await db.commit()
            page["image_prompt"] = prompt
    finally:
        await db.close()

    project = await _get_project(page["project_id"])
    image_provider = await get_image_provider(project.get("image_provider"), project.get("image_model"))

    if not page.get("image_prompt"):
        raise ValueError("No image prompt for this page")

    reference_images = _build_page_reference_images(project, page)

    aspect_ratio = await get_setting_value("image_aspect_ratio") or "1:1"
    image_size = await get_setting_value("image_size") or "1K"

    # Mark as generating so UI shows the spinner even for the one-off regen path.
    db = await get_db()
    try:
        await _set_page_image_status(db, page_id, IMG_GENERATING)
        await db.commit()
    finally:
        await db.close()

    try:
        image_bytes = await image_provider.generate_image(
            page["image_prompt"],
            reference_images=reference_images,
            aspect_ratio=aspect_ratio, image_size=image_size,
        )
    except Exception as e:
        friendly = classify_error(e)
        logger.error(
            "regenerate_single_image failed page %d → %s: %s",
            page_id, friendly.code, e, exc_info=True,
        )
        db = await get_db()
        try:
            await _set_page_image_status(
                db, page_id, IMG_FAILED,
                f"{friendly.title}. {friendly.hint}",
            )
            await db.commit()
        finally:
            await db.close()
        raise

    new_version = page["version"] + 1
    upload_dir = str(UPLOADS_DIR / str(page["project_id"]))
    os.makedirs(upload_dir, exist_ok=True)
    filename = f"page_{page['page_number']}_v{new_version}.png"
    filepath = os.path.join(upload_dir, filename)
    with open(filepath, "wb") as f:
        f.write(image_bytes)
    image_path = f"/static/uploads/{page['project_id']}/{filename}"

    db = await get_db()
    try:
        await db.execute(
            "UPDATE pages SET current_image_path = ?, version = ? WHERE id = ?",
            (image_path, new_version, page_id),
        )
        await _set_page_image_status(db, page_id, IMG_DONE)
        await db.execute(
            """INSERT INTO image_versions
               (page_id, project_id, kind, image_path, prompt_used, provider, version_number)
               VALUES (?, ?, 'page', ?, ?, ?, ?)""",
            (page_id, page["project_id"], image_path, page["image_prompt"],
             project.get("image_provider", "nano_banana"), new_version),
        )
        await db.commit()

        cursor = await db.execute("SELECT * FROM pages WHERE id = ?", (page_id,))
        row = await cursor.fetchone()
        return {k: row[k] for k in row.keys()}
    finally:
        await db.close()
