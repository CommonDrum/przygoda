import asyncio
import os
import sys
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio

# Ensure backend is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Prevent seed from running in tests
os.environ["TESTING"] = "1"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def setup_test_db(tmp_path_factory):
    """Use a temp file DB for each test (aiosqlite doesn't support :memory: well with multiple connections)."""
    db_path = str(tmp_path_factory.mktemp("db") / "test.db")

    # Patch DB_PATH before importing anything that uses it
    import app.database as db_module
    original_path = db_module.DB_PATH
    db_module.DB_PATH = db_path

    await db_module.init_db()
    yield db_path

    db_module.DB_PATH = original_path


@pytest.fixture
def client(setup_test_db):
    """Sync test client for FastAPI."""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.routers.generation import set_ws_manager
    from app.services.ws_manager import ConnectionManager

    set_ws_manager(ConnectionManager())

    with TestClient(app) as c:
        yield c


VALID_PROJECT = {
    "child_name": "Zosia",
    "child_age": 5,
    "child_gender": "dziewczynka",
    "hair_color": "blond",
    "hair_style": "kucyk",
    "skin_tone": "jasna",
    "eye_color": "niebieskie",
    "outfit_description": "czerwona sukienka",
    "story_type": "magiczna podróż",
    "hobby": "malowanie",
    "moral": "wiara w siebie",
}


@pytest.fixture
def mock_llm():
    """Returns a mock LLM provider."""
    mock = AsyncMock()
    return mock


@pytest.fixture
def mock_image_provider():
    """Returns a mock image provider that returns a 1x1 PNG."""
    # Minimal valid PNG (1x1 transparent pixel)
    png_bytes = (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
        b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00'
        b'\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00'
        b'\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82'
    )
    mock = AsyncMock()
    mock.generate_image.return_value = png_bytes
    return mock
