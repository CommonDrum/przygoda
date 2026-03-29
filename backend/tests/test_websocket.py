"""Test WebSocket connection and manager."""
import pytest

from tests.conftest import VALID_PROJECT


class TestWebSocket:
    def test_ws_connect_and_disconnect(self, client):
        """WebSocket should accept connection and handle disconnect."""
        client.post("/api/projects", json=VALID_PROJECT)

        with client.websocket_connect("/api/ws/generation/1") as ws:
            # Connection established — just verify it doesn't crash
            pass
        # Disconnect should be clean (no exception)

    def test_ws_nonexistent_project_still_connects(self, client):
        """WS doesn't validate project existence — it's just a message channel."""
        with client.websocket_connect("/api/ws/generation/999") as ws:
            pass


class TestConnectionManager:
    @pytest.mark.asyncio
    async def test_send_to_project_no_connections(self):
        """Sending to project with no connections should not crash."""
        from app.services.ws_manager import ConnectionManager

        manager = ConnectionManager()
        # Should not raise
        await manager.send_to_project(1, {"type": "test"})

    @pytest.mark.asyncio
    async def test_disconnect_nonexistent_ws(self):
        """Disconnecting a WS that was never connected should not crash."""
        from app.services.ws_manager import ConnectionManager
        from unittest.mock import MagicMock

        manager = ConnectionManager()
        fake_ws = MagicMock()
        # Should not raise
        manager.disconnect(1, fake_ws)
