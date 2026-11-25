/**
 * File 3 of 4: Custom Hook for Document Listing & PDF Upload
 * Governed by 529 Engineering Standards (frontend-4file-and-resilient-ui)
 */
import { useState, useCallback, useEffect, useRef } from 'react';
import { fetchDocumentList, uploadFinancialPdf } from '../api/visual_rag.fetch';
import type { DocumentIngestResponseDTO } from '../types/visual_rag.types';

export function useDocuments(autoFetch = true) {
  const [documents, setDocuments] = useState<string[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState<boolean>(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const refresh = useCallback(async () => {
    if (typeof fetch !== 'function') return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetchDocumentList();
      if (mountedRef.current) {
        setDocuments(res.documents || []);
      }
    } catch (err: any) {
      if (mountedRef.current) {
        setError(err?.message || 'Không thể tải danh sách BCTC từ daemon.');
      }
    } finally {
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    if (autoFetch) {
      refresh();
    }
  }, [autoFetch, refresh]);

  const uploadPdf = useCallback(
    async (file: File, documentId?: string): Promise<DocumentIngestResponseDTO | null> => {
      if (!file.name.toLowerCase().endsWith('.pdf')) {
        setUploadError('Định dạng không hỗ trợ. Vui lòng chọn file PDF (.pdf).');
        return null;
      }

      setUploading(true);
      setUploadError(null);
      try {
        const res = await uploadFinancialPdf(file, 150, documentId);
        if (mountedRef.current) {
          setDocuments((prev) =>
            prev.includes(res.document_id) ? prev : [res.document_id, ...prev]
          );
        }
        return res;
      } catch (err: any) {
        if (mountedRef.current) {
          setUploadError(err?.message || 'Không thể tải lên và xử lý PDF.');
        }
        return null;
      } finally {
        if (mountedRef.current) {
          setUploading(false);
        }
      }
    },
    []
  );

  const clearUploadError = useCallback(() => setUploadError(null), []);

  return {
    documents,
    loading,
    error,
    uploading,
    uploadError,
    refresh,
    uploadPdf,
    clearUploadError,
  };
}
