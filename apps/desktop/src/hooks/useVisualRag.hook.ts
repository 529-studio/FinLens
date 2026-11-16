/**
 * File 3 of 4: Custom React Hook for Visual RAG State Machine
 * Governed by 529 Engineering Standards (frontend-4file-and-resilient-ui)
 */

import { useState, useCallback, useRef } from 'react';
import {
  QueryRequestDTO,
  QueryResponseDTO,
  GroundedEvidenceDTO,
  UIState,
} from '../types/visual_rag.types';
import { fetchQuery, ApiError } from '../api/visual_rag.fetch';

export function useVisualRag(documentId: string) {
  const [state, setState] = useState<UIState>('idle');
  const [error, setError] = useState<string | null>(null);
  const [activeEvidence, setActiveEvidence] = useState<GroundedEvidenceDTO | null>(null);
  const [history, setHistory] = useState<QueryResponseDTO[]>([]);
  const abortControllerRef = useRef<AbortController | null>(null);

  const ask = useCallback(
    async (queryText: string, mode: 'auto' | 'local' | 'cloud' = 'auto') => {
      if (!queryText.trim()) return;

      setState('loading');
      setError(null);

      // Abort previous in-flight request
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      abortControllerRef.current = new AbortController();

      try {
        const payload: QueryRequestDTO = {
          document_id: documentId,
          query_text: queryText,
          inference_mode: mode,
        };
        const response = await fetchQuery(payload, abortControllerRef.current.signal);

        setHistory((prev) => [...prev, response]);
        setState('success');

        // Automatically focus on the first evidence if available
        if (response.evidences.length > 0) {
          setActiveEvidence(response.evidences[0]);
        }
      } catch (err: any) {
        if (err.name === 'AbortError') return;
        const msg = err instanceof ApiError ? err.message : 'Unknown communication failure';
        setError(msg);
        setState('error');
      }
    },
    [documentId]
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
    activeEvidence,
    ask,
    focusEvidence,
    clearError,
  };
}
