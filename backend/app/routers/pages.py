from fastapi import APIRouter, HTTPException

from ..database import get_db
from ..models.schemas import (
    PageResponse,
    PageUpdate,
    ImageVersionResponse,
    ProjectResponse,
    RestoreVersionRequest,
)

router = APIRouter(tags=["pages"])


def row_to_dict(row) -> dict:
    return {k: row[k] for k in row.keys()}


@router.get(
    "/projects/{project_id}/pages", response_model=list[PageResponse]
)
async def list_pages(project_id: int):
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM pages WHERE project_id = ? ORDER BY page_number",
            (project_id,),
        )
        rows = await cursor.fetchall()
        return [row_to_dict(r) for r in rows]
    finally:
        await db.close()


@router.get("/pages/{page_id}", response_model=PageResponse)
async def get_page(page_id: int):
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM pages WHERE id = ?", (page_id,)
        )
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(404, "Page not found")
        return row_to_dict(row)
    finally:
        await db.close()


@router.put("/pages/{page_id}", response_model=PageResponse)
async def update_page(page_id: int, data: PageUpdate):
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM pages WHERE id = ?", (page_id,)
        )
        if not await cursor.fetchone():
            raise HTTPException(404, "Page not found")

        updates = []
        params = []
        if data.text is not None:
            updates.append("text = ?")
            params.append(data.text)
        if data.image_prompt is not None:
            updates.append("image_prompt = ?")
            params.append(data.image_prompt)

        if updates:
            params.append(page_id)
            await db.execute(
                f"UPDATE pages SET {', '.join(updates)} WHERE id = ?",
                params,
            )
            await db.commit()

        cursor = await db.execute(
            "SELECT * FROM pages WHERE id = ?", (page_id,)
        )
        return row_to_dict(await cursor.fetchone())
    finally:
        await db.close()


@router.get(
    "/pages/{page_id}/versions",
    response_model=list[ImageVersionResponse],
)
async def list_versions(page_id: int):
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM image_versions WHERE page_id = ? ORDER BY version_number DESC",
            (page_id,),
        )
        rows = await cursor.fetchall()
        return [row_to_dict(r) for r in rows]
    finally:
        await db.close()


@router.post("/pages/{page_id}/restore-version", response_model=PageResponse)
async def restore_version(page_id: int, data: RestoreVersionRequest):
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM image_versions WHERE id = ? AND page_id = ?",
            (data.version_id, page_id),
        )
        version = await cursor.fetchone()
        if not version:
            raise HTTPException(404, "Wersja nie znaleziona dla tej strony")

        await db.execute(
            "UPDATE pages SET current_image_path = ?, version = ? WHERE id = ?",
            (version["image_path"], version["version_number"], page_id),
        )
        await db.commit()

        cursor = await db.execute("SELECT * FROM pages WHERE id = ?", (page_id,))
        return row_to_dict(await cursor.fetchone())
    finally:
        await db.close()


# --- Reference image versions (attached to project, not a page) ---

@router.get(
    "/projects/{project_id}/reference-versions",
    response_model=list[ImageVersionResponse],
)
async def list_reference_versions(project_id: int):
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT * FROM image_versions
               WHERE project_id = ? AND kind = 'reference'
               ORDER BY version_number DESC""",
            (project_id,),
        )
        rows = await cursor.fetchall()
        return [row_to_dict(r) for r in rows]
    finally:
        await db.close()


@router.post(
    "/projects/{project_id}/restore-reference", response_model=ProjectResponse
)
async def restore_reference(project_id: int, data: RestoreVersionRequest):
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT * FROM image_versions
               WHERE id = ? AND project_id = ? AND kind = 'reference'""",
            (data.version_id, project_id),
        )
        version = await cursor.fetchone()
        if not version:
            raise HTTPException(404, "Wersja referencyjna nie znaleziona")

        await db.execute(
            """UPDATE projects
               SET reference_image_path = ?,
                   reference_image_prompt = ?,
                   reference_image_version = ?,
                   updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (version["image_path"], version["prompt_used"],
             version["version_number"], project_id),
        )
        await db.commit()

        cursor = await db.execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        )
        return row_to_dict(await cursor.fetchone())
    finally:
        await db.close()
