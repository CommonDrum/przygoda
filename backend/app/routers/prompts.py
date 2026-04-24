from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from ..database import get_db
from ..models.schemas import PromptCreate, PromptUpdate, PromptResponse

router = APIRouter(prefix="/prompts", tags=["prompts"])


def _row(row) -> dict:
    d = {k: row[k] for k in row.keys()}
    d["is_default"] = bool(d.get("is_default", 0))
    return d


@router.get("", response_model=list[PromptResponse])
async def list_prompts(kind: Literal["story", "image"] | None = Query(default=None)):
    db = await get_db()
    try:
        if kind:
            cursor = await db.execute(
                "SELECT * FROM prompts WHERE kind = ? ORDER BY is_default DESC, updated_at DESC",
                (kind,),
            )
        else:
            cursor = await db.execute(
                "SELECT * FROM prompts ORDER BY kind, is_default DESC, updated_at DESC"
            )
        return [_row(r) for r in await cursor.fetchall()]
    finally:
        await db.close()


@router.get("/{prompt_id}", response_model=PromptResponse)
async def get_prompt(prompt_id: int):
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM prompts WHERE id = ?", (prompt_id,))
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(404, "Prompt not found")
        return _row(row)
    finally:
        await db.close()


@router.post("", response_model=PromptResponse, status_code=201)
async def create_prompt(data: PromptCreate):
    db = await get_db()
    try:
        cursor = await db.execute(
            """INSERT INTO prompts (kind, title, content, is_default)
               VALUES (?, ?, ?, 0)""",
            (data.kind, data.title, data.content),
        )
        await db.commit()
        new_id = cursor.lastrowid
        cursor = await db.execute("SELECT * FROM prompts WHERE id = ?", (new_id,))
        return _row(await cursor.fetchone())
    finally:
        await db.close()


@router.put("/{prompt_id}", response_model=PromptResponse)
async def update_prompt(prompt_id: int, data: PromptUpdate):
    fields = {k: v for k, v in data.model_dump().items() if v is not None}
    if not fields:
        raise HTTPException(422, "No fields to update")

    db = await get_db()
    try:
        cursor = await db.execute("SELECT id FROM prompts WHERE id = ?", (prompt_id,))
        if not await cursor.fetchone():
            raise HTTPException(404, "Prompt not found")

        set_clause = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [prompt_id]
        await db.execute(
            f"UPDATE prompts SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            values,
        )
        await db.commit()
        cursor = await db.execute("SELECT * FROM prompts WHERE id = ?", (prompt_id,))
        return _row(await cursor.fetchone())
    finally:
        await db.close()


@router.delete("/{prompt_id}", status_code=204)
async def delete_prompt(prompt_id: int):
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT is_default FROM prompts WHERE id = ?", (prompt_id,)
        )
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(404, "Prompt not found")
        if row["is_default"]:
            raise HTTPException(403, "Nie można usunąć domyślnego promptu")

        await db.execute(
            "UPDATE projects SET story_prompt_id = NULL WHERE story_prompt_id = ?",
            (prompt_id,),
        )
        await db.execute(
            "UPDATE projects SET image_prompt_id = NULL WHERE image_prompt_id = ?",
            (prompt_id,),
        )
        await db.execute("DELETE FROM prompts WHERE id = ?", (prompt_id,))
        await db.commit()
    finally:
        await db.close()


async def get_prompt_content(prompt_id: int | None, kind: str) -> str | None:
    """Return content of selected prompt, or the default one for the given kind,
    or None if nothing is stored (callers fall back to the code template)."""
    db = await get_db()
    try:
        if prompt_id is not None:
            cursor = await db.execute(
                "SELECT content FROM prompts WHERE id = ? AND kind = ?",
                (prompt_id, kind),
            )
            row = await cursor.fetchone()
            if row:
                return row["content"]

        cursor = await db.execute(
            "SELECT content FROM prompts WHERE kind = ? AND is_default = 1 LIMIT 1",
            (kind,),
        )
        row = await cursor.fetchone()
        return row["content"] if row else None
    finally:
        await db.close()
