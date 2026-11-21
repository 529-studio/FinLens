/**
 * File 3 of 4: Custom React Hook for Visual RAG State Machine
 * Governed by 529 Engineering Standards (frontend-4file-and-resilient-ui)
 */

import { useState, useCallback, useRef } from 'react';
import {
  QueryRequestDTO,
  QueryResponseDTO,
  GroundedEvidenceDTO,
  ComparativeQueryRequestDTO,
  ComparativeQueryResponseDTO,
  UIState,
} from '../types/visual_rag.types';
import { fetchQuery, fetchComparativeQuery, ApiError } from '../api/visual_rag.fetch';

export function useVisualRag(documentId: string) {
  const [state, setState] = useState<UIState>('idle');
  const [error, setError] = useState<string | null>(null);
  const [activeEvidence, setActiveEvidence] = useState<GroundedEvidenceDTO | null>(null);
  const [history, setHistory] = useState<QueryResponseDTO[]>([]);
  const [comparativeHistory, setComparativeHistory] = useState<ComparativeQueryResponseDTO[]>([]);
  const [streamingAnswer, setStreamingAnswer] = useState<string>('');
  const abortControllerRef = useRef<AbortController | null>(null);

  const ask = useCallback(
    async (queryText: string, mode: 'auto' | 'local' | 'cloud' = 'auto') => {
      if (!queryText.trim()) return;

      setState('loading');
      setError(null);
      setStreamingAnswer('');

      // Abort previous in-flight request
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      abortControllerRef.current = new AbortController();

      const payload: QueryRequestDTO = {
        document_id: documentId,
        query_text: queryText,
        inference_mode: mode,
      };

      let streamedSuccessfully = false;
      try {
        if (typeof WebSocket !== 'undefined') {
          await new Promise<void>((resolve, reject) => {
            const ws = new WebSocket('ws://127.0.0.1:8765/ws/query/stream');
            let accumulated = '';
            let evidences: GroundedEvidenceDTO[] = [];

            ws.onopen = () => {
              ws.send(JSON.stringify(payload));
            };

            ws.onmessage = (event) => {
              try {
                const data = JSON.parse(event.data);
                if (data.event === 'token' && typeof data.token === 'string') {
                  accumulated += data.token;
                  setStreamingAnswer(accumulated);
                } else if (data.event === 'evidence' && Array.isArray(data.evidences)) {
                  evidences = data.evidences;
                } else if (data.event === 'done') {
                  streamedSuccessfully = true;
                  const fullResp: QueryResponseDTO = {
                    document_id: documentId,
                    query_text: queryText,
                    answer: data.answer || accumulated,
                    evidences: evidences,
                    retrieved_page_numbers: evidences.map((e) => e.page_number),
                    engine_used: 'vlm-stream',
                    latency_ms: data.elapsed_ms || 0,
                    cached: false,
                  };
                  setHistory((prev) => [...prev, fullResp]);
                  if (evidences.length > 0) {
                    setActiveEvidence(evidences[0]);
                  }
                  setStreamingAnswer('');
                  setState('success');
                  ws.close();
                  resolve();
                } else if (data.event === 'error') {
                  ws.close();
                  reject(new Error(data.error));
                }
              } catch (e) {
                reject(e);
              }
            };

            ws.onerror = () => {
              reject(new Error('WebSocket connection failed'));
            };
          });
        }
      } catch {
        // Fall back gracefully to REST fetchQuery if WebSocket fails
      }

      if (!streamedSuccessfully) {
        try {
          const response = await fetchQuery(payload, abortControllerRef.current?.signal);
          setHistory((prev) => [...prev, response]);
          setState('success');
          setStreamingAnswer('');
          if (response.evidences.length > 0) {
            setActiveEvidence(response.evidences[0]);
          }
        } catch (err: any) {
          if (err.name === 'AbortError') return;
          const msg = err instanceof ApiError ? err.message : 'Unknown communication failure';
          setError(msg);
          setState('error');
          setStreamingAnswer('');
        }
      }
    },
    [documentId]
  );

  const askComparative = useCallback(
    async (documentIds: string[], queryText: string, mode: 'auto' | 'local' | 'cloud' = 'auto') => {
      if (!queryText.trim() || documentIds.length < 2) return;

      setState('loading');
      setError(null);

      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      abortControllerRef.current = new AbortController();

      try {
        const payload: ComparativeQueryRequestDTO = {
          document_ids: documentIds,
          query_text: queryText,
          top_k_per_doc: 1,
          inference_mode: mode,
        };
        const response = await fetchComparativeQuery(payload, abortControllerRef.current.signal);

        setComparativeHistory((prev) => [...prev, response]);
        setState('success');

        if (response.evidences.length > 0) {
          setActiveEvidence(response.evidences[0]);
        }
      } catch (err: any) {
        if (err.name === 'AbortError') return;
        const msg = err instanceof ApiError ? err.message : 'Lỗi truy vấn so sánh đa tài liệu';
        setError(msg);
        setState('error');
      }
    },
    []
  );

  const focusEvidence = useCallback((evidence: GroundedEvidenceDTO) => {
    setActiveEvidence(evidence);
  }, []);

  const clearError = useCallback(() => {
    setError(null);
    setState(history.length > 0 ? 'success' : 'idle');
  }, [history.length]);

  return {
    state,
    error,
    history,
    comparativeHistory,
    activeEvidence,
    streamingAnswer,
    ask,
    askComparative,
    focusEvidence,
    clearError,
  };
}
