import asyncio
import os

from ..database import get_db
from ..providers.factory import get_llm_provider, get_image_provider
from ..routers.settings import get_setting_value
from ..templates.story_prompt import build_story_system_prompt, build_story_user_prompt
from ..templates.image_prompt import build_image_system_prompt, build_image_user_prompt
from ..config import settings, UPLOADS_DIR, STATIC_DIR
from .ws_manager import ConnectionManager

SEPARATOR = "#########"


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


async def generate_story(project_id: int, ws_manager: ConnectionManager | None = None) -> dict:
    project = await _get_project(project_id)

    if project["status"] != "draft":
        raise ValueError(f"Cannot generate story: project status is '{project['status']}', expected 'draft'")

    # Get custom prompt if set
    custom_prompt = await get_setting_value("story_system_prompt")
    system_prompt = build_story_system_prompt(project, custom_prompt or None)
    user_prompt = build_story_user_prompt(project)

    llm = await get_llm_provider(project.get("llm_provider"))
    raw_story = await _stream_llm(llm, system_prompt, user_prompt, ws_manager, project_id, "story")

    # Parse segments
    segments = [s.strip() for s in raw_story.split(SEPARATOR) if s.strip()]
    if len(segments) < 15:
        raise ValueError(
            f"Expected 15 story segments, got {len(segments)}. Raw output saved."
        )

    # Save to DB
    db = await get_db()
    try:
        # Update pages 2-16 with story text
        for i, text in enumerate(segments[:15]):
            page_number = i + 2
            await db.execute(
                "UPDATE pages SET text = ? WHERE project_id = ? AND page_number = ?",
                (text, project_id, page_number),
            )

        # Cover gets a title text
        await db.execute(
            "UPDATE pages SET text = ? WHERE project_id = ? AND page_number = 1",
            (f"Przygoda {project['child_name']}", project_id),
        )
        # Back page
        await db.execute(
            "UPDATE pages SET text = ? WHERE project_id = ? AND page_number = 17",
            ("Koniec", project_id),
        )
        await db.commit()
    finally:
        await db.close()

    await _update_project_status(project_id, "story_generated", raw_story=raw_story)
    return await _get_project(project_id)


async def generate_image_prompts(project_id: int, ws_manager: ConnectionManager | None = None) -> dict:
    project = await _get_project(project_id)

    if project["status"] != "story_generated":
        raise ValueError(f"Cannot generate prompts: project status is '{project['status']}', expected 'story_generated'")

    if not project.get("raw_story"):
        raise ValueError("Story not generated yet")

    custom_prompt = await get_setting_value("image_system_prompt")
    system_prompt = build_image_system_prompt(project, custom_prompt or None)
    user_prompt = build_image_user_prompt(project, project["raw_story"])

    llm = await get_llm_provider(project.get("llm_provider"))
    raw_prompts = await _stream_llm(llm, system_prompt, user_prompt, ws_manager, project_id, "prompts")

    # Parse prompts (18 total: 1 reference + 17 pages)
    prompts = [p.strip() for p in raw_prompts.split(SEPARATOR) if p.strip()]
    if len(prompts) < 18:
        raise ValueError(
            f"Expected 18 image prompts, got {len(prompts)}. Raw output saved."
        )

    # First prompt is the character reference sheet
    reference_prompt = prompts[0]
    page_prompts = prompts[1:18]

    # Save page prompts to DB
    db = await get_db()
    try:
        for i, prompt in enumerate(page_prompts):
            page_number = i + 1
            await db.execute(
                "UPDATE pages SET image_prompt = ? WHERE project_id = ? AND page_number = ?",
                (prompt, project_id, page_number),
            )
        await db.commit()
    finally:
        await db.close()

    await _update_project_status(
        project_id, "prompts_generated",
        raw_image_prompts=raw_prompts,
        reference_image_prompt=reference_prompt,
    )
    return await _get_project(project_id)


async def generate_images(project_id: int, ws_manager: ConnectionManager):
    project = await _get_project(project_id)

    if project["status"] != "prompts_generated":
        raise ValueError(f"Cannot generate images: project status is '{project['status']}', expected 'prompts_generated'")

    await _update_project_status(project_id, "images_generating")
    project = await _get_project(project_id)

    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM pages WHERE project_id = ? ORDER BY page_number",
            (project_id,),
        )
        pages = [
            {k: r[k] for k in r.keys()} for r in await cursor.fetchall()
        ]
    finally:
        await db.close()

    image_provider = await get_image_provider(project.get("image_provider"))
    semaphore = asyncio.Semaphore(settings.IMAGE_CONCURRENCY)
    completed_count = 0
    failed_count = 0

    # Read image settings
    aspect_ratio = await get_setting_value("image_aspect_ratio") or "1:1"
    image_size = await get_setting_value("image_size") or "1K"

    # Ensure upload directory exists
    upload_dir = str(UPLOADS_DIR / str(project_id))
    os.makedirs(upload_dir, exist_ok=True)

    # Step 1: Generate reference image first
    reference_bytes: bytes | None = None
    ref_prompt = project.get("reference_image_prompt")
    if ref_prompt:
        await ws_manager.send_to_project(project_id, {
            "type": "image_progress",
            "page_number": 0,
            "status": "generating",
        })
        try:
            reference_bytes = await image_provider.generate_image(
                ref_prompt, aspect_ratio=aspect_ratio, image_size=image_size,
            )
            ref_filename = "reference_v1.png"
            ref_filepath = os.path.join(upload_dir, ref_filename)
            with open(ref_filepath, "wb") as f:
                f.write(reference_bytes)
            ref_image_path = f"/static/uploads/{project_id}/{ref_filename}"
            await _update_project_status(
                project_id, "images_generating",
                reference_image_path=ref_image_path,
            )
            await ws_manager.send_to_project(project_id, {
                "type": "image_progress",
                "page_number": 0,
                "status": "completed",
                "image_path": ref_image_path,
            })
        except Exception as e:
            await ws_manager.send_to_project(project_id, {
                "type": "image_progress",
                "page_number": 0,
                "status": "failed",
                "error": str(e),
            })

    # Step 2: Generate page images with reference
    async def generate_one(page: dict):
        nonlocal completed_count, failed_count
        if not page.get("image_prompt"):
            return

        async with semaphore:
            page_num = page["page_number"]
            page_id = page["id"]

            await ws_manager.send_to_project(project_id, {
                "type": "image_progress",
                "page_number": page_num,
                "status": "generating",
            })

            try:
                image_bytes = await image_provider.generate_image(
                    page["image_prompt"], reference_bytes,
                    aspect_ratio=aspect_ratio, image_size=image_size,
                )

                new_version = page["version"] + 1
                filename = f"page_{page_num}_v{new_version}.png"
                filepath = os.path.join(upload_dir, filename)

                with open(filepath, "wb") as f:
                    f.write(image_bytes)

                image_path = f"/static/uploads/{project_id}/{filename}"

                # Update DB
                db2 = await get_db()
                try:
                    await db2.execute(
                        "UPDATE pages SET current_image_path = ?, version = ? WHERE id = ?",
                        (image_path, new_version, page_id),
                    )
                    await db2.execute(
                        """INSERT INTO image_versions
                           (page_id, image_path, prompt_used, provider, version_number)
                           VALUES (?, ?, ?, ?, ?)""",
                        (page_id, image_path, page["image_prompt"],
                         project.get("image_provider", "nano_banana"), new_version),
                    )
                    await db2.commit()
                finally:
                    await db2.close()

                await ws_manager.send_to_project(project_id, {
                    "type": "image_progress",
                    "page_number": page_num,
                    "status": "completed",
                    "image_path": image_path,
                })
                completed_count += 1
            except Exception as e:
                await ws_manager.send_to_project(project_id, {
                    "type": "image_progress",
                    "page_number": page_num,
                    "status": "failed",
                    "error": str(e),
                })
                failed_count += 1

    await asyncio.gather(*[generate_one(p) for p in pages])

    if completed_count > 0:
        await _update_project_status(project_id, "review")
    else:
        # All failed — revert to prompts_generated so user can retry
        await _update_project_status(project_id, "prompts_generated")


async def regenerate_single_image(page_id: int, prompt: str | None = None) -> dict:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM pages WHERE id = ?", (page_id,))
        page = await cursor.fetchone()
        if not page:
            raise ValueError("Page not found")
        page = {k: page[k] for k in page.keys()}

        # Update prompt if provided
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
    image_provider = await get_image_provider(project.get("image_provider"))

    if not page.get("image_prompt"):
        raise ValueError("No image prompt for this page")

    # Load reference image bytes from disk if available
    reference_bytes: bytes | None = None
    ref_path = project.get("reference_image_path")
    if ref_path:
        # ref_path is like "/static/uploads/{id}/reference_v1.png"
        abs_ref = str(STATIC_DIR / ref_path.removeprefix("/static/"))
        if os.path.exists(abs_ref):
            with open(abs_ref, "rb") as f:
                reference_bytes = f.read()

    aspect_ratio = await get_setting_value("image_aspect_ratio") or "1:1"
    image_size = await get_setting_value("image_size") or "1K"

    image_bytes = await image_provider.generate_image(
        page["image_prompt"], reference_bytes,
        aspect_ratio=aspect_ratio, image_size=image_size,
    )

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
        await db.execute(
            """INSERT INTO image_versions
               (page_id, image_path, prompt_used, provider, version_number)
               VALUES (?, ?, ?, ?, ?)""",
            (page_id, image_path, page["image_prompt"],
             project.get("image_provider", "nano_banana"), new_version),
        )
        await db.commit()

        cursor = await db.execute("SELECT * FROM pages WHERE id = ?", (page_id,))
        row = await cursor.fetchone()
        return {k: row[k] for k in row.keys()}
    finally:
        await db.close()
