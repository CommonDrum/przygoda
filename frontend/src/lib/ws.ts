import type { WsMessage } from "./types";
import { getToken } from "./auth";

export type WsStatus = "connected" | "reconnecting" | "disconnected";

export interface WsConnection {
  close(): void;
}

export function connectWebSocket(
  projectId: number,
  onMessage: (msg: WsMessage) => void,
  onStatusChange?: (status: WsStatus) => void,
): WsConnection {
  let attempt = 0;
  const MAX_ATTEMPTS = 5;
  let ws: WebSocket | null = null;
  let closed = false;

  function connect() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = import.meta.env.DEV ? "localhost:8000" : window.location.host;
    const token = getToken();
    ws = new WebSocket(
      `${protocol}//${host}/ws/generation/${projectId}?token=${token}`
    );

    ws.onopen = () => {
      attempt = 0;
      onStatusChange?.("connected");
    };

    ws.onmessage = (event) => {
      const msg: WsMessage = JSON.parse(event.data);
      onMessage(msg);
    };

    ws.onclose = () => {
      if (closed) return;
      if (attempt < MAX_ATTEMPTS) {
        onStatusChange?.("reconnecting");
        const delay = Math.min(1000 * 2 ** attempt, 8000);
        attempt++;
        setTimeout(connect, delay);
      } else {
        onStatusChange?.("disconnected");
      }
    };

    ws.onerror = () => {};
  }

  connect();

  return {
    close() {
      closed = true;
      ws?.close();
    },
  };
}
