import shutil

from fastapi import APIRouter, HTTPException

from ..config import UPLOADS_DIR, EXPORTS_DIR
from ..database import get_db
from ..models.schemas import ProjectCreate, ProjectUpdate, ProjectResponse
from .settings import get_setting_value

router = APIRouter(prefix="/projects", tags=["projects"])


def row_to_project(row) -> dict:
    return {k: row[k] for k in row.keys()}


@router.get("", response_model=list[ProjectResponse])
async def list_projects():
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM projects ORDER BY updated_at DESC"
        )
        rows = await cursor.fetchall()
        return [row_to_project(r) for r in rows]
    finally:
        await db.close()


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: int):
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        )
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(404, "Project not found")
        return row_to_project(row)
    finally:
        await db.close()


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(data: ProjectCreate):
    llm_prov = await get_setting_value("default_llm_provider") or "anthropic"
    img_prov = await get_setting_value("default_image_provider") or "nano_banana"

    db = await get_db()
    try:
        cursor = await db.execute(
            """INSERT INTO projects
               (child_name, child_age, child_gender, hair_color, hair_style,
                skin_tone, eye_color, outfit_description, story_type, hobby, moral,
                llm_provider, image_provider)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                data.child_name, data.child_age, data.child_gender,
                data.hair_color, data.hair_style, data.skin_tone,
                data.eye_color, data.outfit_description,
                data.story_type, data.hobby, data.moral,
                llm_prov, img_prov,
            ),
        )
        project_id = cursor.lastrowid

        # Create 17 page slots
        page_defs = (
            [(project_id, 1, "cover")]
            + [(project_id, i, "story") for i in range(2, 17)]
            + [(project_id, 17, "back")]
        )
        await db.executemany(
            "INSERT INTO pages (project_id, page_number, page_type) VALUES (?, ?, ?)",
            page_defs,
        )
        await db.commit()

        cursor = await db.execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        )
        return row_to_project(await cursor.fetchone())
    finally:
        await db.close()


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: int, data: ProjectUpdate):
    fields = {k: v for k, v in data.model_dump().items() if v is not None}
    if not fields:
        raise HTTPException(422, "No fields to update")

    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT id FROM projects WHERE id = ?", (project_id,)
        )
        if not await cursor.fetchone():
            raise HTTPException(404, "Project not found")

        set_clause = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [project_id]
        await db.execute(
            f"UPDATE projects SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            values,
        )
        await db.commit()

        cursor = await db.execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        )
        return row_to_project(await cursor.fetchone())
    finally:
        await db.close()


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: int):
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT id FROM projects WHERE id = ?", (project_id,)
        )
        if not await cursor.fetchone():
            raise HTTPException(404, "Project not found")

        await db.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        await db.commit()

        # Clean up files
        upload_dir = UPLOADS_DIR / str(project_id)
        if upload_dir.exists():
            shutil.rmtree(upload_dir)
        export_dir = EXPORTS_DIR / str(project_id)
        if export_dir.exists():
            shutil.rmtree(export_dir)
    finally:
        await db.close()
