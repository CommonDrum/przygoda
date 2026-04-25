"""Test CRUD endpoints: projects, pages, settings."""
from tests.conftest import VALID_PROJECT


class TestProjects:
    def test_create_project(self, client):
        resp = client.post("/api/projects", json=VALID_PROJECT)
        assert resp.status_code == 201
        data = resp.json()
        assert data["child_name"] == "Zosia"
        assert data["status"] == "draft"
        assert data["id"] == 1

    def test_create_project_creates_17_pages(self, client):
        resp = client.post("/api/projects", json=VALID_PROJECT)
        project_id = resp.json()["id"]

        pages_resp = client.get(f"/api/projects/{project_id}/pages")
        pages = pages_resp.json()
        assert len(pages) == 17

        types = [p["page_type"] for p in pages]
        assert types[0] == "cover"
        assert types[-1] == "back"
        assert types[1:-1] == ["story"] * 15

        numbers = [p["page_number"] for p in pages]
        assert numbers == list(range(1, 18))

    def test_create_project_validation_rejects_empty_fields(self, client):
        bad = {**VALID_PROJECT, "child_name": ""}
        resp = client.post("/api/projects", json=bad)
        assert resp.status_code == 422

        bad2 = {**VALID_PROJECT, "hair_color": ""}
        resp2 = client.post("/api/projects", json=bad2)
        assert resp2.status_code == 422

    def test_create_project_validation_rejects_bad_age(self, client):
        bad = {**VALID_PROJECT, "child_age": 1}
        assert client.post("/api/projects", json=bad).status_code == 422

        bad2 = {**VALID_PROJECT, "child_age": 13}
        assert client.post("/api/projects", json=bad2).status_code == 422

    def test_list_projects(self, client):
        client.post("/api/projects", json=VALID_PROJECT)
        client.post("/api/projects", json={**VALID_PROJECT, "child_name": "Kasia"})

        resp = client.get("/api/projects")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_get_project(self, client):
        create_resp = client.post("/api/projects", json=VALID_PROJECT)
        pid = create_resp.json()["id"]

        resp = client.get(f"/api/projects/{pid}")
        assert resp.status_code == 200
        assert resp.json()["child_name"] == "Zosia"

    def test_get_nonexistent_project_404(self, client):
        resp = client.get("/api/projects/999")
        assert resp.status_code == 404

    def test_delete_project(self, client):
        create_resp = client.post("/api/projects", json=VALID_PROJECT)
        pid = create_resp.json()["id"]

        resp = client.delete(f"/api/projects/{pid}")
        assert resp.status_code == 204

        # Pages should be gone too (CASCADE)
        pages_resp = client.get(f"/api/projects/{pid}/pages")
        assert pages_resp.json() == []

    def test_delete_nonexistent_project_404(self, client):
        resp = client.delete("/api/projects/999")
        assert resp.status_code == 404


class TestPages:
    def test_update_page_text(self, client):
        client.post("/api/projects", json=VALID_PROJECT)
        pages = client.get("/api/projects/1/pages").json()
        page_id = pages[0]["id"]

        resp = client.put(f"/api/pages/{page_id}", json={"text": "Nowy tekst"})
        assert resp.status_code == 200
        assert resp.json()["text"] == "Nowy tekst"

    def test_update_page_image_prompt(self, client):
        client.post("/api/projects", json=VALID_PROJECT)
        pages = client.get("/api/projects/1/pages").json()
        page_id = pages[0]["id"]

        resp = client.put(
            f"/api/pages/{page_id}",
            json={"image_prompt": "A beautiful scene"},
        )
        assert resp.status_code == 200
        assert resp.json()["image_prompt"] == "A beautiful scene"

    def test_get_nonexistent_page_404(self, client):
        resp = client.get("/api/pages/999")
        assert resp.status_code == 404

    def test_versions_empty_initially(self, client):
        client.post("/api/projects", json=VALID_PROJECT)
        pages = client.get("/api/projects/1/pages").json()
        page_id = pages[0]["id"]

        resp = client.get(f"/api/pages/{page_id}/versions")
        assert resp.status_code == 200
        assert resp.json() == []


class TestSettings:
    def test_get_defaults(self, client):
        resp = client.get("/api/settings")
        assert resp.status_code == 200
        data = resp.json()
        assert data["default_llm_provider"] == "anthropic"
        assert data["default_image_provider"] == "google"

    def test_update_and_get(self, client):
        client.put(
            "/api/settings",
            json={"default_llm_provider": "openai"},
        )
        resp = client.get("/api/settings")
        assert resp.json()["default_llm_provider"] == "openai"

    def test_api_key_masking(self, client):
        client.put(
            "/api/settings",
            json={"anthropic_api_key": "sk-ant-super-secret-key-1234"},
        )
        resp = client.get("/api/settings")
        key = resp.json()["anthropic_api_key"]
        # Should be masked except last 4 chars
        assert key.endswith("1234")
        assert "•" in key
        assert "super-secret" not in key

    def test_masked_key_not_overwritten(self, client):
        # Set a real key
        client.put(
            "/api/settings",
            json={"anthropic_api_key": "sk-ant-real-key-5678"},
        )
        # Try to "update" with masked value
        client.put(
            "/api/settings",
            json={"anthropic_api_key": "••••••••••••••5678"},
        )
        # Should still return masked version of original key
        resp = client.get("/api/settings")
        assert resp.json()["anthropic_api_key"].endswith("5678")

    def test_update_prompts(self, client):
        custom = "Custom prompt: {name}"
        client.put(
            "/api/settings",
            json={"story_system_prompt": custom},
        )
        resp = client.get("/api/settings")
        assert resp.json()["story_system_prompt"] == custom
