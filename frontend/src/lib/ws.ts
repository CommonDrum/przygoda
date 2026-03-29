import type { WsMessage } from "./types";
import { getToken } from "./auth";

export function connectWebSocket(
  projectId: number,
  onMessage: (msg: WsMessage) => void
): WebSocket {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  // In dev, connect directly to backend (Bun doesn't support Vite WS proxy)
  const host = import.meta.env.DEV ? "localhost:8000" : window.location.host;
  const token = getToken();
  const ws = new WebSocket(
    `${protocol}//${host}/ws/generation/${projectId}?token=${token}`
  );

  ws.onmessage = (event) => {
    const msg: WsMessage = JSON.parse(event.data);
    onMessage(msg);
  };

  ws.onerror = (e) => console.error("WebSocket error:", e);

  return ws;
}
