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
                image_provider TEXT DEFAULT 'nano_banana',
                reference_image_prompt TEXT,
                reference_image_path TEXT,
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
                UNIQUE(project_id, page_number)
            );

            CREATE TABLE IF NOT EXISTS image_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                page_id INTEGER NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
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
        """)
        await db.commit()

        # Migrations for existing databases
        for col, default in [
            ("reference_image_prompt", None),
            ("reference_image_path", None),
        ]:
            try:
                await db.execute(
                    f"ALTER TABLE projects ADD COLUMN {col} TEXT"
                )
                await db.commit()
            except Exception:
                pass  # Column already exists
    finally:
        await db.close()
