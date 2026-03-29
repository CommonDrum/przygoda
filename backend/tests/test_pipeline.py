"""Test pipeline status transitions and generation flow with mocked providers."""
from unittest.mock import patch, AsyncMock

import pytest

from tests.conftest import VALID_PROJECT
from app.services.story_service import SEPARATOR


def make_story_output() -> str:
    """Generate valid 15-segment story output."""
    segments = [f"Story segment {i+1}. " + "Text " * 30 for i in range(15)]
    return f"\n{SEPARATOR}\n".join(segments)


def make_prompts_output() -> str:
    """Generate valid 17-prompt output."""
    prompts = [f"Image prompt {i+1}. Zosia in a scene. --ar 1:1" for i in range(17)]
    return f"\n{SEPARATOR}\n".join(prompts)


class TestStatusTransitions:
    def test_generate_story_from_draft(self, client):
        """draft → story_generated works."""
        client.post("/api/projects", json=VALID_PROJECT)

        mock_llm = AsyncMock()
        mock_llm.generate.return_value = make_story_output()

        with patch("app.services.story_service.get_llm_provider", return_value=mock_llm):
            resp = client.post("/api/projects/1/generate-story")

        assert resp.status_code == 200
        assert resp.json()["status"] == "story_generated"

    def test_generate_story_wrong_status_409(self, client):
        """Cannot generate story if not in draft status."""
        client.post("/api/projects", json=VALID_PROJECT)

        # First generate story
        mock_llm = AsyncMock()
        mock_llm.generate.return_value = make_story_output()
        with patch("app.services.story_service.get_llm_provider", return_value=mock_llm):
            client.post("/api/projects/1/generate-story")

        # Try again — should fail with 409
        with patch("app.services.story_service.get_llm_provider", return_value=mock_llm):
            resp = client.post("/api/projects/1/generate-story")
        assert resp.status_code == 409

    def test_generate_prompts_from_story_generated(self, client):
        """story_generated → prompts_generated works."""
        client.post("/api/projects", json=VALID_PROJECT)

        mock_llm = AsyncMock()
        mock_llm.generate.return_value = make_story_output()
        with patch("app.services.story_service.get_llm_provider", return_value=mock_llm):
            client.post("/api/projects/1/generate-story")

        mock_llm.generate.return_value = make_prompts_output()
        with patch("app.services.story_service.get_llm_provider", return_value=mock_llm):
            resp = client.post("/api/projects/1/generate-prompts")

        assert resp.status_code == 200
        assert resp.json()["status"] == "prompts_generated"

    def test_generate_prompts_wrong_status_409(self, client):
        """Cannot generate prompts from draft status."""
        client.post("/api/projects", json=VALID_PROJECT)

        resp = client.post("/api/projects/1/generate-prompts")
        assert resp.status_code == 409

    def test_generate_story_nonexistent_project_404(self, client):
        resp = client.post("/api/projects/999/generate-story")
        assert resp.status_code == 404

    def test_generate_prompts_nonexistent_project_404(self, client):
        resp = client.post("/api/projects/999/generate-prompts")
        assert resp.status_code == 404


class TestStoryGeneration:
    def test_pages_populated_after_story(self, client):
        """After story generation, pages 2-16 have text, cover/back have title/ending."""
        client.post("/api/projects", json=VALID_PROJECT)

        mock_llm = AsyncMock()
        mock_llm.generate.return_value = make_story_output()
        with patch("app.services.story_service.get_llm_provider", return_value=mock_llm):
            client.post("/api/projects/1/generate-story")

        pages = client.get("/api/projects/1/pages").json()

        # Cover page
        assert pages[0]["text"] == "Przygoda Zosia"
        # Story pages
        for p in pages[1:16]:
            assert p["text"] is not None
            assert len(p["text"]) > 0
        # Back page
        assert pages[16]["text"] == "Koniec"

    def test_too_few_segments_returns_500(self, client):
        """LLM returns fewer than 15 segments → error."""
        client.post("/api/projects", json=VALID_PROJECT)

        mock_llm = AsyncMock()
        segments = [f"Short segment {i}" for i in range(10)]
        mock_llm.generate.return_value = f"\n{SEPARATOR}\n".join(segments)

        with patch("app.services.story_service.get_llm_provider", return_value=mock_llm):
            resp = client.post("/api/projects/1/generate-story")
        assert resp.status_code == 500
        assert "Expected 15" in resp.json()["detail"]

    def test_raw_story_saved(self, client):
        """Raw LLM output should be saved in project."""
        client.post("/api/projects", json=VALID_PROJECT)

        raw = make_story_output()
        mock_llm = AsyncMock()
        mock_llm.generate.return_value = raw
        with patch("app.services.story_service.get_llm_provider", return_value=mock_llm):
            client.post("/api/projects/1/generate-story")

        project = client.get("/api/projects/1").json()
        assert project["raw_story"] == raw


class TestImagePromptGeneration:
    def test_prompts_assigned_to_pages(self, client):
        """After prompt generation, all 17 pages have image_prompt."""
        client.post("/api/projects", json=VALID_PROJECT)

        mock_llm = AsyncMock()
        mock_llm.generate.return_value = make_story_output()
        with patch("app.services.story_service.get_llm_provider", return_value=mock_llm):
            client.post("/api/projects/1/generate-story")

        mock_llm.generate.return_value = make_prompts_output()
        with patch("app.services.story_service.get_llm_provider", return_value=mock_llm):
            client.post("/api/projects/1/generate-prompts")

        pages = client.get("/api/projects/1/pages").json()
        for p in pages:
            assert p["image_prompt"] is not None
            assert len(p["image_prompt"]) > 0
