"""Schema / migration tests — lock in the fixes for historical DB bugs.

These tests don't use the HTTP client (so the pre-existing auth-fixture breakage
doesn't block them). They exercise `init_db` directly against a temp DB.
"""
import aiosqlite
import pytest

import app.database as db_module


# The autouse setup_test_db fixture in conftest already runs init_db against a
# fresh temp DB, but some of these tests need to seed a *legacy* schema first
# and then re-run init_db. We override the path per-test.


async def _table_info(db, table: str) -> list[aiosqlite.Row]:
    cursor = await db.execute(f"PRAGMA table_info({table})")
    return list(await cursor.fetchall())


async def _column(db, table: str, name: str) -> aiosqlite.Row | None:
    for row in await _table_info(db, table):
        if row["name"] == name:
            return row
    return None


class TestImageVersionsSchema:
    @pytest.mark.asyncio
    async def test_fresh_db_has_nullable_page_id(self, setup_test_db):
        """A fresh init_db gives us a schema where reference rows (no page_id)
        can be inserted."""
        db = await db_module.get_db()
        try:
            page_id = await _column(db, "image_versions", "page_id")
            assert page_id is not None
            assert page_id["notnull"] == 0, (
                "page_id must be nullable — reference-kind rows don't have one"
            )
        finally:
            await db.close()

    @pytest.mark.asyncio
    async def test_reference_insert_without_page_id_succeeds(self, setup_test_db):
        """The exact INSERT shape that story_service.generate_reference issues."""
        db = await db_module.get_db()
        try:
            # Seed a project so the FK (if enforced) is satisfied
            cursor = await db.execute(
                """INSERT INTO projects (child_name, child_age)
                   VALUES ('Zosia', 5)"""
            )
            project_id = cursor.lastrowid

            await db.execute(
                """INSERT INTO image_versions
                   (project_id, kind, image_path, prompt_used, provider, version_number)
                   VALUES (?, 'reference', ?, ?, ?, ?)""",
                (project_id, "/static/uploads/x/reference_v1.png",
                 "a prompt", "google", 1),
            )
            await db.commit()

            cursor = await db.execute(
                "SELECT page_id, kind FROM image_versions WHERE project_id = ?",
                (project_id,),
            )
            row = await cursor.fetchone()
            assert row["page_id"] is None
            assert row["kind"] == "reference"
        finally:
            await db.close()

    @pytest.mark.asyncio
    async def test_migration_rebuilds_legacy_not_null_page_id(
        self, tmp_path_factory, monkeypatch,
    ):
        """Simulate a legacy install where page_id was NOT NULL; init_db must
        rebuild the table so inserts without page_id start working."""
        db_path = str(tmp_path_factory.mktemp("legacy") / "legacy.db")
        monkeypatch.setattr(db_module, "DB_PATH", db_path)

        # Seed with the ANCIENT schema shape that caused the bug
        legacy = await aiosqlite.connect(db_path)
        legacy.row_factory = aiosqlite.Row
        await legacy.executescript("""
            CREATE TABLE projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                child_name TEXT NOT NULL,
                child_age INTEGER NOT NULL
            );
            CREATE TABLE pages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                page_number INTEGER NOT NULL,
                current_image_path TEXT
            );
            CREATE TABLE image_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                page_id INTEGER NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
                image_path TEXT NOT NULL,
                prompt_used TEXT NOT NULL,
                provider TEXT NOT NULL,
                version_number INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        # Seed some real data that must survive the rebuild
        cursor = await legacy.execute(
            "INSERT INTO projects (child_name, child_age) VALUES ('Ola', 6)"
        )
        project_id = cursor.lastrowid
        cursor = await legacy.execute(
            "INSERT INTO pages (project_id, page_number) VALUES (?, 3)",
            (project_id,),
        )
        page_id = cursor.lastrowid
        await legacy.execute(
            """INSERT INTO image_versions
               (page_id, image_path, prompt_used, provider, version_number)
               VALUES (?, '/static/p/3.png', 'old prompt', 'google', 1)""",
            (page_id,),
        )
        await legacy.commit()
        await legacy.close()

        # Run migration
        await db_module.init_db()

        db = await db_module.get_db()
        try:
            page_id_col = await _column(db, "image_versions", "page_id")
            assert page_id_col["notnull"] == 0, "migration must drop NOT NULL"

            # Existing page-kind row preserved
            cursor = await db.execute(
                "SELECT page_id, image_path, version_number FROM image_versions"
            )
            rows = list(await cursor.fetchall())
            assert len(rows) == 1
            assert rows[0]["image_path"] == "/static/p/3.png"
            assert rows[0]["page_id"] == page_id

            # And the insert that used to fail now works
            await db.execute(
                """INSERT INTO image_versions
                   (project_id, kind, image_path, prompt_used, provider, version_number)
                   VALUES (?, 'reference', ?, ?, ?, ?)""",
                (project_id, "/static/r/1.png", "ref", "google", 1),
            )
            await db.commit()
        finally:
            await db.close()

    @pytest.mark.asyncio
    async def test_migration_is_idempotent(self, setup_test_db):
        """Running init_db a second time on an already-fixed DB must be a no-op."""
        await db_module.init_db()  # second run
        db = await db_module.get_db()
        try:
            page_id = await _column(db, "image_versions", "page_id")
            assert page_id["notnull"] == 0
        finally:
            await db.close()

    @pytest.mark.asyncio
    async def test_image_status_backfilled_for_existing_rows(
        self, tmp_path_factory, monkeypatch,
    ):
        """Pages with an existing image must end up image_status='done';
        pages without must stay 'pending'. This is what lets the 'retry
        failed' UI be accurate on legacy projects."""
        db_path = str(tmp_path_factory.mktemp("bf") / "bf.db")
        monkeypatch.setattr(db_module, "DB_PATH", db_path)

        legacy = await aiosqlite.connect(db_path)
        legacy.row_factory = aiosqlite.Row
        await legacy.executescript("""
            CREATE TABLE projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                child_name TEXT NOT NULL,
                child_age INTEGER NOT NULL
            );
            CREATE TABLE pages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                page_number INTEGER NOT NULL,
                current_image_path TEXT
            );
        """)
        cursor = await legacy.execute(
            "INSERT INTO projects (child_name, child_age) VALUES ('Ola', 6)"
        )
        project_id = cursor.lastrowid
        await legacy.execute(
            "INSERT INTO pages (project_id, page_number, current_image_path) "
            "VALUES (?, 1, '/static/ok.png')", (project_id,),
        )
        await legacy.execute(
            "INSERT INTO pages (project_id, page_number, current_image_path) "
            "VALUES (?, 2, NULL)", (project_id,),
        )
        await legacy.commit()
        await legacy.close()

        await db_module.init_db()

        db = await db_module.get_db()
        try:
            cursor = await db.execute(
                "SELECT page_number, image_status FROM pages "
                "WHERE project_id = ? ORDER BY page_number",
                (project_id,),
            )
            rows = list(await cursor.fetchall())
            assert rows[0]["image_status"] == "done"
            assert rows[1]["image_status"] == "pending"
        finally:
            await db.close()

    @pytest.mark.asyncio
    async def test_page_insert_with_page_id_still_works(self, setup_test_db):
        """The per-page INSERT (page_id set) must remain working after the
        nullability change — regression guard."""
        db = await db_module.get_db()
        try:
            cursor = await db.execute(
                "INSERT INTO projects (child_name, child_age) VALUES ('Ala', 4)"
            )
            project_id = cursor.lastrowid
            cursor = await db.execute(
                "INSERT INTO pages (project_id, page_number) VALUES (?, 1)",
                (project_id,),
            )
            page_id = cursor.lastrowid

            await db.execute(
                """INSERT INTO image_versions
                   (page_id, project_id, kind, image_path,
                    prompt_used, provider, version_number)
                   VALUES (?, ?, 'page', ?, ?, ?, ?)""",
                (page_id, project_id, "/static/p/1.png",
                 "page prompt", "google", 1),
            )
            await db.commit()

            cursor = await db.execute(
                "SELECT kind, page_id FROM image_versions WHERE page_id = ?",
                (page_id,),
            )
            row = await cursor.fetchone()
            assert row["kind"] == "page"
            assert row["page_id"] == page_id
        finally:
            await db.close()
