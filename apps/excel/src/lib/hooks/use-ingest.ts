/**
 * File 3 of 4: TanStack Query Hooks for Financial Document Ingestion & State
 * Governed by 529 Engineering Standards (frontend-4file-and-resilient-ui)
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { uploadFinancialDocument, fetchDocumentList } from '../api/finsight';
import { DocumentIngestResponseDTO } from '../../types/api';

export const useDocumentUpload = (options?: {
  onSuccess?: (data: DocumentIngestResponseDTO) => void;
  onError?: (error: Error) => void;
}) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      file,
      renderDpi = 150,
      documentId,
    }: {
      file: File;
      renderDpi?: number;
      documentId?: string;
    }) => uploadFinancialDocument(file, renderDpi, documentId),
    onSuccess: (data) => {
      // Invalidate document list cache
      queryClient.invalidateQueries({ queryKey: ['documents-list'] });
      options?.onSuccess?.(data);
    },
    onError: (err: Error) => {
      options?.onError?.(err);
    },
  });
};

export const useDocumentList = () => {
  return useQuery({
    queryKey: ['documents-list'],
    queryFn: fetchDocumentList,
    staleTime: 30000,
  });
};
