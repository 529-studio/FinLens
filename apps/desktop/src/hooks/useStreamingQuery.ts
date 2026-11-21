/**
 * FinSight Real-Time WebSocket Streaming Query Hook
 * Connects to /ws/query/stream for progressive token generation.
 * Governed by Sprint 8 Task S8-03, AGENTS.md Rule 13, and frontend-4file-and-resilient-ui.
 */

import { useState, useCallback, useRef } from 'react';
import { GroundedEvidenceDTO, UIState } from '../types/visual_rag.types';

export interface UseStreamingQueryReturn {
  state: UIState;
  isStreaming: boolean;
  streamingText: string;
  streamEvidences: GroundedEvidenceDTO[];
  error: string | null;
  sendStreamQuery: (documentId: string, queryText: string, mode?: 'auto' | 'local' | 'cloud') => void;
  resetStream: () => void;
}

export function useStreamingQuery(wsUrl: string = 'ws://127.0.0.1:8765/ws/query/stream'): UseStreamingQueryReturn {
  const [state, setState] = useState<UIState>('idle');
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [streamingText, setStreamingText] = useState<string>('');
  const [streamEvidences, setStreamEvidences] = useState<GroundedEvidenceDTO[]>([]);
  const [error, setError] = useState<string | null>(null);

  const socketRef = useRef<WebSocket | null>(null);

  const resetStream = useCallback(() => {
    if (socketRef.current) {
      socketRef.current.close();
      socketRef.current = null;
    }
    setState('idle');
    setIsStreaming(false);
    setStreamingText('');
    setStreamEvidences([]);
    setError(null);
  }, []);

  const sendStreamQuery = useCallback(
    (documentId: string, queryText: string, mode: 'auto' | 'local' | 'cloud' = 'auto') => {
      if (!queryText.trim() || !documentId.trim()) return;

      if (socketRef.current) {
        socketRef.current.close();
      }

      setState('loading');
      setIsStreaming(true);
      setStreamingText('');
      setStreamEvidences([]);
      setError(null);

      try {
        const ws = new WebSocket(wsUrl);
        socketRef.current = ws;

        ws.onopen = () => {
          ws.send(
            JSON.stringify({
              document_id: documentId,
              query_text: queryText,
              inference_mode: mode,
            })
          );
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.event === 'token' && typeof data.token === 'string') {
              setStreamingText((prev) => prev + data.token);
            } else if (data.event === 'evidence' && Array.isArray(data.evidences)) {
              setStreamEvidences(data.evidences);
            } else if (data.event === 'done') {
              setIsStreaming(false);
              setState('success');
              if (data.answer) {
                setStreamingText(data.answer);
              }
              ws.close();
            } else if (data.event === 'error') {
              setError(data.error || 'Streaming error');
              setIsStreaming(false);
              setState('error');
              ws.close();
            }
          } catch {
            setError('Failed to parse streaming payload');
            setIsStreaming(false);
            setState('error');
          }
        };

        ws.onerror = () => {
          setError('WebSocket connection failure');
          setIsStreaming(false);
          setState('error');
        };

        ws.onclose = () => {
          setIsStreaming(false);
        };
      } catch (err: any) {
        setError(err.message || 'Failed to initialize WebSocket');
        setIsStreaming(false);
        setState('error');
      }
    },
    [wsUrl]
  );

  return {
    state,
    isStreaming,
    streamingText,
    streamEvidences,
    error,
    sendStreamQuery,
    resetStream,
  };
}
