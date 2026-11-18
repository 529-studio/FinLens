export interface CitationEvent {
  type: 'JUMP_TO_SOURCE';
  citationId: string;
}

class InteropBridge {
  private socket: WebSocket | null = null;
  // Use environment variable or fallback to default
  private url = import.meta.env.VITE_BRIDGE_URL || 'ws://localhost:8080';

  connect() {
    this.socket = new WebSocket(this.url);
  }

  sendCitation(citationId: string) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      const event: CitationEvent = { type: 'JUMP_TO_SOURCE', citationId };
      this.socket.send(JSON.stringify(event));
    } else {
      this.connect();
    }
  }
}

export const bridge = new InteropBridge();
