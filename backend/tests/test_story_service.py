"""Integration tests for story_service — directly exercise generate_reference
and generate_images against a real temp DB with mocked providers. Covers the
INSERT paths into image_versions that historically broke under NOT NULL
constraints.
"""
from unittest.mock import AsyncMock, patch

import pytest

from app import database as db_module
from app.services import story_service


# Minimal PNG so writing to disk doesn't blow up
PNG_1x1 = (
    b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
    b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00'
    b'\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00'
    b'\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82'
)


async def _seed_project() -> int:
    """Create a minimal draft project + 17 page slots, return project_id."""
    db = await db_module.get_db()
    try:
        cursor = await db.execute(
            """INSERT INTO projects
               (child_name, child_age, llm_provider, image_provider, status)
               VALUES ('Zosia', 5, 'anthropic', 'nano_banana', 'draft')"""
        )
        project_id = cursor.lastrowid
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
        return project_id
    finally:
        await db.close()


def _fake_llm(response_text: str):
    """LLM mock that supports both generate() and generate_stream()."""
    mock = AsyncMock()
    mock.generate.return_value = response_text

    async def _stream(*_a, **_kw):
        yield response_text
    mock.generate_stream = _stream
    return mock


def _fake_image():
    mock = AsyncMock()
    mock.generate_image.return_value = PNG_1x1
    return mock


REFERENCE_PROMPT = (
    "Zosia, pięcioletnia dziewczynka z blond włosami w kucyku, "
    "w czerwonej sukience, stoi na białym tle."
)


class TestGenerateReference:
    @pytest.mark.asyncio
    async def test_insert_succeeds_and_sets_status(self, setup_test_db, tmp_path, monkeypatch):
        """End-to-end: generate_reference writes an image_versions row with
        page_id=NULL. This is the exact path that was throwing NOT NULL."""
        monkeypatch.setattr(story_service, "UPLOADS_DIR", tmp_path)

        project_id = await _seed_project()
        llm = _fake_llm(REFERENCE_PROMPT)
        img = _fake_image()

        with patch.object(story_service, "get_llm_provider", return_value=llm), \
             patch.object(story_service, "get_image_provider", return_value=img):
            result = await story_service.generate_reference(project_id)

        assert result["status"] == "ref_pic_review"
        assert result["reference_image_path"].endswith("reference_v1.png")

        db = await db_module.get_db()
        try:
            cursor = await db.execute(
                "SELECT page_id, kind, version_number FROM image_versions WHERE project_id = ?",
                (project_id,),
            )
            rows = list(await cursor.fetchall())
            assert len(rows) == 1
            assert rows[0]["page_id"] is None, "reference row must have no page_id"
            assert rows[0]["kind"] == "reference"
            assert rows[0]["version_number"] == 1
        finally:
            await db.close()

    @pytest.mark.asyncio
    async def test_regenerate_bumps_version(self, setup_test_db, tmp_path, monkeypatch):
        monkeypatch.setattr(story_service, "UPLOADS_DIR", tmp_path)

        project_id = await _seed_project()
        llm = _fake_llm(REFERENCE_PROMPT)
        img = _fake_image()

        with patch.object(story_service, "get_llm_provider", return_value=llm), \
             patch.object(story_service, "get_image_provider", return_value=img):
            await story_service.generate_reference(project_id)
            await story_service.regenerate_reference(project_id)

        db = await db_module.get_db()
        try:
            cursor = await db.execute(
                """SELECT version_number FROM image_versions
                   WHERE project_id = ? AND kind = 'reference'
                   ORDER BY version_number""",
                (project_id,),
            )
            versions = [r["version_number"] for r in await cursor.fetchall()]
            assert versions == [1, 2]
        finally:
            await db.close()


async def _seed_ready_for_images(project_id: int) -> list[int]:
    """Move a freshly-seeded project to prompts_generated with real prompts
    on every page. Returns the ordered page_ids."""
    db = await db_module.get_db()
    try:
        await db.execute(
            "UPDATE projects SET status = 'prompts_generated' WHERE id = ?",
            (project_id,),
        )
        cursor = await db.execute(
            "SELECT id FROM pages WHERE project_id = ? ORDER BY page_number",
            (project_id,),
        )
        page_ids = [r["id"] for r in await cursor.fetchall()]
        for pid in page_ids:
            await db.execute(
                "UPDATE pages SET image_prompt = ? WHERE id = ?",
                (f"prompt {pid}", pid),
            )
        await db.commit()
        return page_ids
    finally:
        await db.close()


class TestGenerateImages:
    @pytest.mark.asyncio
    async def test_page_rows_get_page_id(self, setup_test_db, tmp_path, monkeypatch):
        """generate_images must write image_versions rows with a real page_id,
        not NULL, so list_versions(page_id=...) actually finds them."""
        monkeypatch.setattr(story_service, "UPLOADS_DIR", tmp_path)

        project_id = await _seed_project()

        # Jump the project straight to prompts_generated with real prompts.
        db = await db_module.get_db()
        try:
            await db.execute(
                "UPDATE projects SET status = 'prompts_generated' WHERE id = ?",
                (project_id,),
            )
            cursor = await db.execute(
                "SELECT id FROM pages WHERE project_id = ? ORDER BY page_number",
                (project_id,),
            )
            page_ids = [r["id"] for r in await cursor.fetchall()]
            for pid in page_ids:
                await db.execute(
                    "UPDATE pages SET image_prompt = ? WHERE id = ?",
                    (f"prompt for page {pid}", pid),
                )
            await db.commit()
        finally:
            await db.close()

        img = _fake_image()
        ws = AsyncMock()

        with patch.object(story_service, "get_image_provider", return_value=img):
            await story_service.generate_images(project_id, ws)

        db = await db_module.get_db()
        try:
            cursor = await db.execute(
                "SELECT COUNT(*) AS n FROM image_versions WHERE project_id = ? AND kind = 'page'",
                (project_id,),
            )
            row = await cursor.fetchone()
            assert row["n"] == 17

            cursor = await db.execute(
                """SELECT COUNT(*) AS n FROM image_versions
                   WHERE project_id = ? AND kind = 'page' AND page_id IS NULL""",
                (project_id,),
            )
            row = await cursor.fetchone()
            assert row["n"] == 0, "page-kind rows must never have NULL page_id"

            cursor = await db.execute(
                "SELECT status FROM projects WHERE id = ?", (project_id,)
            )
            status = (await cursor.fetchone())["status"]
            assert status == "review"

            # Every page marked done
            cursor = await db.execute(
                """SELECT COUNT(*) AS n FROM pages
                   WHERE project_id = ? AND image_status = 'done'""",
                (project_id,),
            )
            assert (await cursor.fetchone())["n"] == 17
        finally:
            await db.close()

    @pytest.mark.asyncio
    async def test_partial_failure_sets_images_partial_status(
        self, setup_test_db, tmp_path, monkeypatch,
    ):
        """If N/17 pages fail, project ends in 'images_partial' and those
        pages have image_status='failed' with the error captured."""
        monkeypatch.setattr(story_service, "UPLOADS_DIR", tmp_path)

        project_id = await _seed_project()
        await _seed_ready_for_images(project_id)

        # Flaky provider: fail every 3rd call
        img = AsyncMock()
        call_count = {"n": 0}

        async def flaky(*_a, **_kw):
            call_count["n"] += 1
            if call_count["n"] % 3 == 0:
                raise RuntimeError("provider kaboom")
            return PNG_1x1
        img.generate_image = flaky

        ws = AsyncMock()
        with patch.object(story_service, "get_image_provider", return_value=img):
            await story_service.generate_images(project_id, ws)

        db = await db_module.get_db()
        try:
            cursor = await db.execute(
                "SELECT status FROM projects WHERE id = ?", (project_id,),
            )
            assert (await cursor.fetchone())["status"] == "images_partial"

            cursor = await db.execute(
                """SELECT image_status, image_error FROM pages
                   WHERE project_id = ? AND image_status = 'failed'""",
                (project_id,),
            )
            failed = list(await cursor.fetchall())
            assert len(failed) > 0
            # User-facing error text must be present — and must NOT leak the
            # raw "provider kaboom" internal message to non-technical users.
            for r in failed:
                assert r["image_error"]
                assert "kaboom" not in r["image_error"]
                # Generic fallback includes the suggestion to retry
                assert "spróbuj" in r["image_error"].lower() \
                    or "ponownie" in r["image_error"].lower()
        finally:
            await db.close()

    @pytest.mark.asyncio
    async def test_all_failures_go_back_to_prompts_generated(
        self, setup_test_db, tmp_path, monkeypatch,
    ):
        """If every page fails, project returns to prompts_generated so user
        can retry without a weird 'partial' state showing 0/17."""
        monkeypatch.setattr(story_service, "UPLOADS_DIR", tmp_path)

        project_id = await _seed_project()
        await _seed_ready_for_images(project_id)

        img = AsyncMock()
        img.generate_image.side_effect = RuntimeError("always fails")

        ws = AsyncMock()
        with patch.object(story_service, "get_image_provider", return_value=img):
            await story_service.generate_images(project_id, ws)

        db = await db_module.get_db()
        try:
            cursor = await db.execute(
                "SELECT status FROM projects WHERE id = ?", (project_id,),
            )
            assert (await cursor.fetchone())["status"] == "prompts_generated"
        finally:
            await db.close()


class TestRetryFailedImages:
    @pytest.mark.asyncio
    async def test_retries_only_non_done_pages(
        self, setup_test_db, tmp_path, monkeypatch,
    ):
        """retry_failed_images must skip pages that already succeeded. Scenario:
        first pass fails 6 pages → retry pass where provider now works → all
        17 end up done, and `review` status."""
        monkeypatch.setattr(story_service, "UPLOADS_DIR", tmp_path)

        project_id = await _seed_project()
        await _seed_ready_for_images(project_id)

        img = AsyncMock()
        fail_every_3rd = {"n": 0}

        async def flaky_then_stable(*_a, **_kw):
            fail_every_3rd["n"] += 1
            if fail_every_3rd["n"] <= 17 and fail_every_3rd["n"] % 3 == 0:
                raise RuntimeError("flaky")
            return PNG_1x1
        img.generate_image = flaky_then_stable

        ws = AsyncMock()
        with patch.object(story_service, "get_image_provider", return_value=img):
            await story_service.generate_images(project_id, ws)

        db = await db_module.get_db()
        try:
            cursor = await db.execute(
                """SELECT COUNT(*) AS n FROM pages
                   WHERE project_id = ? AND image_status = 'failed'""",
                (project_id,),
            )
            failed_first_pass = (await cursor.fetchone())["n"]
            assert failed_first_pass > 0

            cursor = await db.execute(
                """SELECT COUNT(*) AS n FROM pages
                   WHERE project_id = ? AND image_status = 'done'""",
                (project_id,),
            )
            done_before = (await cursor.fetchone())["n"]
        finally:
            await db.close()

        # Provider now stable — retry
        good_img = _fake_image()
        with patch.object(story_service, "get_image_provider", return_value=good_img):
            await story_service.retry_failed_images(project_id, ws)

        # Retry should only call for the failed count
        assert good_img.generate_image.call_count == failed_first_pass

        db = await db_module.get_db()
        try:
            cursor = await db.execute(
                """SELECT COUNT(*) AS n FROM pages
                   WHERE project_id = ? AND image_status = 'done'""",
                (project_id,),
            )
            assert (await cursor.fetchone())["n"] == 17

            cursor = await db.execute(
                "SELECT status FROM projects WHERE id = ?", (project_id,),
            )
            assert (await cursor.fetchone())["status"] == "review"
        finally:
            await db.close()

    @pytest.mark.asyncio
    async def test_retry_rejects_wrong_project_status(self, setup_test_db):
        """Can't retry from draft/story_generating/etc."""
        project_id = await _seed_project()  # still in 'draft'
        with pytest.raises(ValueError, match="Cannot retry"):
            await story_service.retry_failed_images(project_id, ws_manager=None)
