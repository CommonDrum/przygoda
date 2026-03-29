"""Test export functionality."""
import json
import os
import zipfile
from unittest.mock import patch, AsyncMock

from tests.conftest import VALID_PROJECT
from app.services.story_service import SEPARATOR


def make_story_output() -> str:
    segments = [f"Segment {i+1}. Text content." for i in range(15)]
    return f"\n{SEPARATOR}\n".join(segments)


def make_prompts_output() -> str:
    prompts = [f"Prompt {i+1}. Scene description. --ar 1:1" for i in range(17)]
    return f"\n{SEPARATOR}\n".join(prompts)


class TestZipExport:
    def test_export_zip_without_images(self, client):
        """Export ZIP with no images — should still work, just metadata."""
        client.post("/api/projects", json=VALID_PROJECT)

        # Generate story + prompts
        mock_llm = AsyncMock()
        mock_llm.generate.return_value = make_story_output()
        with patch("app.services.story_service.get_llm_provider", return_value=mock_llm):
            client.post("/api/projects/1/generate-story")

        mock_llm.generate.return_value = make_prompts_output()
        with patch("app.services.story_service.get_llm_provider", return_value=mock_llm):
            client.post("/api/projects/1/generate-prompts")

        # Force status to review for export
        import app.database as db_module
        import asyncio

        async def set_review():
            db = await db_module.get_db()
            await db.execute("UPDATE projects SET status = 'review' WHERE id = 1")
            await db.commit()
            await db.close()

        asyncio.get_event_loop().run_until_complete(set_review())

        resp = client.post("/api/projects/1/export", json={"format": "zip"})
        assert resp.status_code == 200

        file_path = resp.json()["file_path"]
        assert file_path.endswith(".zip")

        # Verify ZIP contents
        local_path = os.path.join("app", file_path.lstrip("/"))
        assert os.path.exists(local_path)

        with zipfile.ZipFile(local_path) as zf:
            names = zf.namelist()
            assert "metadata.json" in names

            meta = json.loads(zf.read("metadata.json"))
            assert meta["child_name"] == "Zosia"
            assert len(meta["pages"]) == 17

    def test_export_excel(self, client):
        """Export Excel — should create .xlsx file."""
        client.post("/api/projects", json=VALID_PROJECT)

        mock_llm = AsyncMock()
        mock_llm.generate.return_value = make_story_output()
        with patch("app.services.story_service.get_llm_provider", return_value=mock_llm):
            client.post("/api/projects/1/generate-story")

        mock_llm.generate.return_value = make_prompts_output()
        with patch("app.services.story_service.get_llm_provider", return_value=mock_llm):
            client.post("/api/projects/1/generate-prompts")

        import app.database as db_module
        import asyncio

        async def set_review():
            db = await db_module.get_db()
            await db.execute("UPDATE projects SET status = 'review' WHERE id = 1")
            await db.commit()
            await db.close()

        asyncio.get_event_loop().run_until_complete(set_review())

        resp = client.post("/api/projects/1/export", json={"format": "excel"})
        assert resp.status_code == 200

        file_path = resp.json()["file_path"]
        assert file_path.endswith(".xlsx")

        local_path = os.path.join("app", file_path.lstrip("/"))
        assert os.path.exists(local_path)

    def test_export_invalid_format_422(self, client):
        """Invalid format should return 422."""
        client.post("/api/projects", json=VALID_PROJECT)
        resp = client.post("/api/projects/1/export", json={"format": "pdf"})
        assert resp.status_code == 422
