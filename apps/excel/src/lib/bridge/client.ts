/// <reference types="vite/client" />
export interface CitationEvent {
  type: 'JUMP_TO_SOURCE';
  citationId: string;
}

class InteropBridge {
  private socket: WebSocket | null = null;
  private pendingCitations: string[] = [];
  private url = import.meta.env.VITE_BRIDGE_URL || 'ws://127.0.0.1:8765/ws';

  connect() {
    if (typeof WebSocket === 'undefined') return;
    if (
      this.socket &&
      (this.socket.readyState === WebSocket.OPEN || this.socket.readyState === WebSocket.CONNECTING)
    ) {
      return;
    }

    const ws = new WebSocket(this.url);
    ws.onopen = () => {
      while (this.pendingCitations.length > 0 && ws.readyState === WebSocket.OPEN) {
        const nextId = this.pendingCitations.shift();
        if (nextId) {
          const event: CitationEvent = { type: 'JUMP_TO_SOURCE', citationId: nextId };
          ws.send(JSON.stringify(event));
        }
      }
    };
    ws.onclose = () => {
      if (this.socket === ws) {
        this.socket = null;
      }
    };
    ws.onerror = () => {
      if (this.socket === ws) {
        this.socket = null;
      }
    };
    this.socket = ws;
  }

  sendCitation(citationId: string) {
    if (!citationId) return;
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      const event: CitationEvent = { type: 'JUMP_TO_SOURCE', citationId };
      this.socket.send(JSON.stringify(event));
    } else {
      this.pendingCitations.push(citationId);
      this.connect();
    }
  }
}

export const bridge = new InteropBridge();
