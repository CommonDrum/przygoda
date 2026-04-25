import os
import shutil

from fastapi import APIRouter, HTTPException, UploadFile, File

from ..config import UPLOADS_DIR, EXPORTS_DIR, STATIC_DIR
from ..database import get_db
from ..models.schemas import ProjectCreate, ProjectUpdate, ProjectResponse
from .settings import get_setting_value

MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MiB
ALLOWED_IMAGE_MIMES = {"image/png", "image/jpeg", "image/webp"}


def _ext_from_mime(mime: str) -> str:
    return {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}.get(mime, "png")


async def _save_upload(file: UploadFile, dest_path: str) -> None:
    """Validate + save an uploaded image. Raises HTTPException on failure."""
    if file.content_type not in ALLOWED_IMAGE_MIMES:
        raise HTTPException(415, f"Nieobsługiwany typ pliku: {file.content_type}")
    data = await file.read()
    if len(data) > MAX_UPLOAD_SIZE:
        raise HTTPException(413, "Plik za duży (max 10 MiB)")
    if len(data) == 0:
        raise HTTPException(422, "Pusty plik")
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    with open(dest_path, "wb") as f:
        f.write(data)

router = APIRouter(prefix="/projects", tags=["projects"])


def row_to_project(row) -> dict:
    d = {k: row[k] for k in row.keys()}
    if "reference_image_is_custom" in d:
        d["reference_image_is_custom"] = bool(d["reference_image_is_custom"])
    return d


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
    llm_prov = data.llm_provider or await get_setting_value("default_llm_provider") or "anthropic"
    img_prov = data.image_provider or await get_setting_value("default_image_provider") or "google"

    db = await get_db()
    try:
        cursor = await db.execute(
            """INSERT INTO projects
               (child_name, child_age, child_gender, hair_color, hair_style,
                skin_tone, eye_color, outfit_description, story_type, hobby, moral,
                llm_provider, llm_model, image_provider, image_model,
                story_prompt_id, image_prompt_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                data.child_name, data.child_age, data.child_gender,
                data.hair_color, data.hair_style, data.skin_tone,
                data.eye_color, data.outfit_description,
                data.story_type, data.hobby, data.moral,
                llm_prov, data.llm_model,
                img_prov, data.image_model,
                data.story_prompt_id, data.image_prompt_id,
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
    # `exclude_unset` keeps explicit nulls (so UI can clear llm_model by sending
    # {"llm_model": null}) while skipping fields the client didn't mention.
    fields = data.model_dump(exclude_unset=True)
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


# --- Custom reference image upload (skip AI generation) ---

@router.post("/{project_id}/upload-reference", response_model=ProjectResponse)
async def upload_reference_image(project_id: int, file: UploadFile = File(...)):
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        )
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(404, "Projekt nie znaleziony")
        project = row_to_project(row)

        # Allow upload in early states; block once images are already being generated.
        if project["status"] in ("images_generating",):
            raise HTTPException(
                409, f"Nie można wgrać referencji w statusie '{project['status']}'"
            )

        ext = _ext_from_mime(file.content_type or "image/png")
        new_version = (project.get("reference_image_version") or 0) + 1
        filename = f"reference_v{new_version}.{ext}"
        dest = UPLOADS_DIR / str(project_id) / filename
        await _save_upload(file, str(dest))
        image_path = f"/static/uploads/{project_id}/{filename}"

        await db.execute(
            """UPDATE projects SET
               reference_image_path = ?,
               reference_image_prompt = ?,
               reference_image_version = ?,
               reference_image_is_custom = 1,
               status = CASE WHEN status = 'draft' THEN 'ref_pic_review' ELSE status END,
               updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (image_path,
             "(Wgrany obraz referencyjny — bez promptu AI)",
             new_version, project_id),
        )
        await db.execute(
            """INSERT INTO image_versions
               (project_id, kind, image_path, prompt_used, provider, version_number)
               VALUES (?, 'reference', ?, ?, 'upload', ?)""",
            (project_id, image_path, "(upload)", new_version),
        )
        await db.commit()

        cursor = await db.execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        )
        return row_to_project(await cursor.fetchone())
    finally:
        await db.close()


# --- Style guide image (moodboard-lite) ---

@router.post("/{project_id}/upload-style-guide", response_model=ProjectResponse)
async def upload_style_guide(project_id: int, file: UploadFile = File(...)):
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        )
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(404, "Projekt nie znaleziony")

        ext = _ext_from_mime(file.content_type or "image/png")
        filename = f"style_guide.{ext}"
        dest = UPLOADS_DIR / str(project_id) / filename
        await _save_upload(file, str(dest))
        image_path = f"/static/uploads/{project_id}/{filename}"

        await db.execute(
            """UPDATE projects SET style_guide_image_path = ?,
               updated_at = CURRENT_TIMESTAMP WHERE id = ?""",
            (image_path, project_id),
        )
        await db.commit()

        cursor = await db.execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        )
        return row_to_project(await cursor.fetchone())
    finally:
        await db.close()


@router.delete("/{project_id}/style-guide", response_model=ProjectResponse)
async def delete_style_guide(project_id: int):
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        )
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(404, "Projekt nie znaleziony")
        project = row_to_project(row)

        # Best-effort file cleanup
        if project.get("style_guide_image_path"):
            abs_path = STATIC_DIR / project["style_guide_image_path"].removeprefix("/static/")
            try:
                if abs_path.exists():
                    abs_path.unlink()
            except Exception:
                pass

        await db.execute(
            """UPDATE projects SET style_guide_image_path = NULL,
               updated_at = CURRENT_TIMESTAMP WHERE id = ?""",
            (project_id,),
        )
        await db.commit()

        cursor = await db.execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        )
        return row_to_project(await cursor.fetchone())
    finally:
        await db.close()
