/// <reference types="vite/client" />
import { useEffect } from 'react';

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
  useEffect(() => {
    const rawPort = import.meta.env.VITE_WS_BRIDGE_PORT;
    if (!rawPort) {
      throw new Error('VITE_WS_BRIDGE_PORT is not defined in environment variables.');
    }
    const port = parseInt(rawPort, 10);
    
    if (isNaN(port)) {
      throw new Error('Invalid WebSocket port configured.');
    }

    const socket = new WebSocket(`ws://127.0.0.1:${port}/ws`);

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (isValidCitationEvent(data)) {
          onCitationJump(data.citationId);
        }
      } catch (e) {
        console.error('Failed to parse WebSocket message', e);
      }
    };

    return () => {
      socket.close();
    };
  }, [onCitationJump]);
};
