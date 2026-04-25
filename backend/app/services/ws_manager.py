import json
import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self.connections: dict[int, list[WebSocket]] = {}

    async def connect(self, project_id: int, ws: WebSocket):
        """Register an already-accepted websocket. The handler is responsible
        for calling `accept()` (possibly with a subprotocol) so it stays in
        control of auth-ticket echoing."""
        self.connections.setdefault(project_id, []).append(ws)

    def disconnect(self, project_id: int, ws: WebSocket):
        conns = self.connections.get(project_id, [])
        if ws in conns:
            conns.remove(ws)

    async def send_to_project(self, project_id: int, message: dict):
        # Snapshot the list — we may mutate it while iterating (dropping dead
        # sockets) and don't want to skip entries.
        for ws in list(self.connections.get(project_id, [])):
            try:
                await ws.send_text(json.dumps(message))
            except Exception as e:
                logger.warning(
                    "WS send failed for project %d (%s) — dropping connection",
                    project_id, type(e).__name__,
                )
                self.disconnect(project_id, ws)
