import aiosqlite
from .config import settings

DB_PATH = settings.DATABASE_URL


async def get_db() -> aiosqlite.Connection:
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    return db


async def init_db():
    db = await get_db()
    try:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                child_name TEXT NOT NULL,
                child_age INTEGER NOT NULL,
                child_gender TEXT NOT NULL DEFAULT 'dziewczynka',
                hair_color TEXT NOT NULL DEFAULT '',
                hair_style TEXT NOT NULL DEFAULT '',
                skin_tone TEXT NOT NULL DEFAULT '',
                eye_color TEXT NOT NULL DEFAULT '',
                outfit_description TEXT NOT NULL DEFAULT '',
                story_type TEXT NOT NULL DEFAULT '',
                hobby TEXT NOT NULL DEFAULT '',
                moral TEXT NOT NULL DEFAULT '',
                raw_story TEXT,
                raw_image_prompts TEXT,
                llm_provider TEXT DEFAULT 'anthropic',
                llm_model TEXT,
                image_provider TEXT DEFAULT 'google',
                image_model TEXT,
                reference_image_prompt TEXT,
                reference_image_path TEXT,
                reference_image_version INTEGER DEFAULT 0,
                reference_image_is_custom INTEGER DEFAULT 0,
                style_guide_image_path TEXT,
                story_prompt_id INTEGER,
                image_prompt_id INTEGER,
                art_style TEXT NOT NULL DEFAULT 'storybook',
                fulfillment_status TEXT NOT NULL DEFAULT 'oczekuje',
                status TEXT DEFAULT 'draft',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS pages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                page_number INTEGER NOT NULL,
                page_type TEXT NOT NULL DEFAULT 'story',
                text TEXT,
                image_prompt TEXT,
                current_image_path TEXT,
                reference_image_path TEXT,
                version INTEGER DEFAULT 0,
                image_status TEXT NOT NULL DEFAULT 'pending',
                image_error TEXT,
                UNIQUE(project_id, page_number)
            );

            CREATE TABLE IF NOT EXISTS image_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                page_id INTEGER REFERENCES pages(id) ON DELETE CASCADE,
                project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
                kind TEXT NOT NULL DEFAULT 'page',
                image_path TEXT NOT NULL,
                prompt_used TEXT NOT NULL,
                provider TEXT NOT NULL,
                version_number INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS exports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                format TEXT NOT NULL,
                file_path TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS prompts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL CHECK(kind IN ('story','image')),
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                is_default INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        await db.commit()

        # Migrations for existing databases — best-effort ALTER TABLE
        migrations = [
            ("projects", "reference_image_prompt", "TEXT"),
            ("projects", "reference_image_path", "TEXT"),
            ("projects", "reference_image_version", "INTEGER DEFAULT 0"),
            ("projects", "story_prompt_id", "INTEGER"),
            ("projects", "image_prompt_id", "INTEGER"),
            ("projects", "fulfillment_status", "TEXT NOT NULL DEFAULT 'oczekuje'"),
            ("projects", "llm_provider", "TEXT DEFAULT 'anthropic'"),
            ("projects", "llm_model", "TEXT"),
            ("projects", "image_provider", "TEXT DEFAULT 'google'"),
            ("projects", "image_model", "TEXT"),
            ("projects", "reference_image_is_custom", "INTEGER DEFAULT 0"),
            ("projects", "style_guide_image_path", "TEXT"),
            ("projects", "art_style", "TEXT NOT NULL DEFAULT 'storybook'"),
            ("image_versions", "project_id", "INTEGER"),
            ("image_versions", "kind", "TEXT NOT NULL DEFAULT 'page'"),
            ("pages", "image_status", "TEXT NOT NULL DEFAULT 'pending'"),
            ("pages", "image_error", "TEXT"),
        ]
        for table, col, coltype in migrations:
            try:
                await db.execute(
                    f"ALTER TABLE {table} ADD COLUMN {col} {coltype}"
                )
                await db.commit()
            except Exception:
                pass  # Column already exists

        # Rebuild image_versions if an old schema left page_id NOT NULL
        # (reference-kind rows don't have a page_id, so inserts would fail).
        await _ensure_image_versions_nullable_page_id(db)

        # Backfill image_status for pages from pre-status migration: anything
        # that already has an image is done; the rest stays pending.
        await db.execute(
            """UPDATE pages SET image_status = 'done'
               WHERE image_status = 'pending'
                 AND current_image_path IS NOT NULL"""
        )
        await db.commit()

        # Migrate retired image-provider ids. Wrapped in try/except because
        # ancient legacy schemas may not yet have an `image_provider` column at
        # all — the ALTER TABLE migrations above just added it, but on really
        # exotic shapes (test fixtures) the UPDATE could still fail.
        try:
            # `nano_banana` was a dead stub pointing at a non-existent
            # api.nanobanana.com endpoint. The public name "Nano Banana" is
            # just Google's gemini-2.5-flash-image, so route to Google.
            await db.execute(
                """UPDATE projects
                   SET image_provider = 'google',
                       image_model = COALESCE(NULLIF(image_model, 'default'), 'gemini-2.5-flash-image')
                   WHERE image_provider = 'nano_banana'"""
            )
            # `dalle` was the legacy id for OpenAI's images API — same provider,
            # just renamed for consistency with the LLM provider naming.
            await db.execute(
                "UPDATE projects SET image_provider = 'openai' WHERE image_provider = 'dalle'"
            )
            await db.commit()
        except Exception:
            pass

        # If google_api_key is empty but nano_banana_api_key was set, copy it
        # over so existing deployments don't lose access on first boot. Then
        # drop the dead key.
        try:
            await db.execute(
                """INSERT INTO settings (key, value)
                   SELECT 'google_api_key', value FROM settings
                   WHERE key = 'nano_banana_api_key' AND value != ''
                     AND NOT EXISTS (
                         SELECT 1 FROM settings WHERE key = 'google_api_key' AND value != ''
                     )"""
            )
            await db.execute("DELETE FROM settings WHERE key = 'nano_banana_api_key'")
            await db.execute(
                "UPDATE settings SET value = 'google' WHERE key = 'default_image_provider' AND value = 'nano_banana'"
            )
            # Gemini Image API only accepts '1K' or '2K' — older deployments had
            # '512' / '4K' in the dropdown; map anything illegal back to '1K'.
            await db.execute(
                "UPDATE settings SET value = '1K' WHERE key = 'image_size' AND value NOT IN ('1K', '2K')"
            )
            await db.commit()
        except Exception:
            pass

        # Seed prompts library from legacy settings if empty
        await _seed_prompts_from_settings(db)
    finally:
        await db.close()


async def _ensure_image_versions_nullable_page_id(db):
    """SQLite can't ALTER COLUMN to drop NOT NULL, so rebuild the table
    when a legacy DB has `page_id INTEGER NOT NULL`. Preserves all existing
    rows."""
    cursor = await db.execute("PRAGMA table_info(image_versions)")
    cols = await cursor.fetchall()
    page_id_notnull = any(
        c["name"] == "page_id" and c["notnull"] == 1 for c in cols
    )
    if not page_id_notnull:
        return

    await db.executescript("""
        CREATE TABLE image_versions_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            page_id INTEGER REFERENCES pages(id) ON DELETE CASCADE,
            project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
            kind TEXT NOT NULL DEFAULT 'page',
            image_path TEXT NOT NULL,
            prompt_used TEXT NOT NULL,
            provider TEXT NOT NULL,
            version_number INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        INSERT INTO image_versions_new
            (id, page_id, project_id, kind, image_path,
             prompt_used, provider, version_number, created_at)
        SELECT id, page_id, project_id, kind, image_path,
               prompt_used, provider, version_number, created_at
        FROM image_versions;
        DROP TABLE image_versions;
        ALTER TABLE image_versions_new RENAME TO image_versions;
    """)
    await db.commit()


async def _seed_prompts_from_settings(db):
    """One-time migration: move legacy story/image_system_prompt from settings
    into the prompts library as the default entries."""
    from .templates.story_prompt import DEFAULT_STORY_SYSTEM_PROMPT
    from .templates.image_prompt import DEFAULT_REFERENCE_SYSTEM_PROMPT

    for kind, legacy_key, fallback in [
        ("story", "story_system_prompt", DEFAULT_STORY_SYSTEM_PROMPT),
        ("image", "image_system_prompt", DEFAULT_REFERENCE_SYSTEM_PROMPT),
    ]:
        cursor = await db.execute(
            "SELECT COUNT(*) AS n FROM prompts WHERE kind = ?", (kind,)
        )
        row = await cursor.fetchone()
        if row["n"] > 0:
            continue

        cursor = await db.execute(
            "SELECT value FROM settings WHERE key = ?", (legacy_key,)
        )
        row = await cursor.fetchone()
        content = row["value"] if row and row["value"] else fallback

        await db.execute(
            """INSERT INTO prompts (kind, title, content, is_default)
               VALUES (?, ?, ?, 1)""",
            (kind, "Domyślny", content),
        )
        await db.commit()
