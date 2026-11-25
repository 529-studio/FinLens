/// <reference types="vite/client" />
import { useEffect, useRef } from 'react';

// Basic security validation
const isValidCitationEvent = (data: any): data is { type: 'JUMP_TO_SOURCE'; citationId: string } => {
  return (
    typeof data === 'object' &&
    data !== null &&
    data.type === 'JUMP_TO_SOURCE' &&
    typeof data.citationId === 'string' &&
    data.citationId.length > 0
  );
};

export const useBridgeServer = (onCitationJump: (citationId: string) => void) => {
  const callbackRef = useRef(onCitationJump);
  callbackRef.current = onCitationJump;

  useEffect(() => {
    const rawPort = import.meta.env.VITE_WS_BRIDGE_PORT || '8765';
    const port = parseInt(rawPort, 10);

    if (isNaN(port)) {
      throw new Error('Invalid WebSocket port configured.');
    }

    if (typeof WebSocket === 'undefined') {
      return;
    }

    let disposed = false;
    const socket = new WebSocket(`ws://127.0.0.1:${port}/ws`);

    socket.onopen = () => {
      if (disposed) {
        socket.close();
      }
    };

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (isValidCitationEvent(data)) {
          callbackRef.current(data.citationId);
        }
      } catch (e) {
        console.error('Failed to parse WebSocket message', e);
      }
    };

    return () => {
      disposed = true;
      if (socket.readyState === WebSocket.OPEN) {
        socket.close();
      }
    };
  }, []);
};
