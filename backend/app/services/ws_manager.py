import json

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.connections: dict[int, list[WebSocket]] = {}

    async def connect(self, project_id: int, ws: WebSocket):
        await ws.accept()
        self.connections.setdefault(project_id, []).append(ws)

    def disconnect(self, project_id: int, ws: WebSocket):
        conns = self.connections.get(project_id, [])
        if ws in conns:
            conns.remove(ws)

    async def send_to_project(self, project_id: int, message: dict):
        for ws in self.connections.get(project_id, []):
            try:
                await ws.send_text(json.dumps(message))
            except Exception:
                pass
