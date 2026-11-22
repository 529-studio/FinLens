/**
 * File 2 of 4: Resilient Fetch API functions for FinSight Excel Add-in
 * Governed by 529 Engineering Standards (frontend-4file-and-resilient-ui & resilient-networking-and-waf)
 */

import { QueryResult, DocumentIngestResponseDTO, DocumentSummaryDTO } from '../../types/api';

const BASE_URL = (typeof window !== 'undefined' && (window as any).__FINSIGHT_API_BASE__) || 'http://127.0.0.1:8765';
const DEFAULT_TIMEOUT_MS = 60000; // 60s for PDF rendering & embedding indexing

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export async function uploadFinancialDocument(
  file: File,
  renderDpi: number = 150,
  documentId?: string,
  signal?: AbortSignal
): Promise<DocumentIngestResponseDTO> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), DEFAULT_TIMEOUT_MS);

  if (signal) {
    signal.addEventListener('abort', () => controller.abort());
  }

  const formData = new FormData();
  formData.append('file', file);
  formData.append('render_dpi', renderDpi.toString());
  if (documentId) {
    formData.append('document_id', documentId);
  }

  try {
    const res = await fetch(`${BASE_URL}/api/v1/documents/upload`, {
      method: 'POST',
      headers: {
        'User-Agent': 'FinTrace-Excel-Addin/1.0 (+https://529studio.site)',
      },
      body: formData,
      signal: controller.signal,
    });

    if (!res.ok) {
      let errorMsg = `Lỗi tải lên (${res.status})`;
      try {
        const errJson = await res.json();
        if (errJson.detail) {
          errorMsg = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
        }
      } catch {
        const text = await res.text().catch(() => '');
        if (text) errorMsg = text;
      }
      throw new ApiError(res.status, errorMsg);
    }

    return (await res.json()) as DocumentIngestResponseDTO;
  } catch (err: any) {
    if (err.name === 'AbortError') {
      throw new ApiError(408, 'Thời gian xử lý tài liệu vượt quá giới hạn (60s). Vui lòng thử lại.');
    }
    if (err instanceof ApiError) {
      throw err;
    }
    throw new ApiError(0, err.message || 'Không thể kết nối đến FinTrace Core Daemon (127.0.0.1:8765)');
  } finally {
    clearTimeout(timeoutId);
  }
}

export async function fetchDocumentList(): Promise<{ documents: DocumentSummaryDTO[]; total: number }> {
  try {
    const res = await fetch(`${BASE_URL}/api/v1/documents`, {
      headers: {
        'User-Agent': 'FinTrace-Excel-Addin/1.0',
      },
    });
    if (!res.ok) {
      return { documents: [], total: 0 };
    }
    const data = await res.json();
    return {
      documents: (data.documents || []).map((doc: any) =>
        typeof doc === 'string' ? { document_id: doc } : doc
      ),
      total: data.total || 0,
    };
  } catch {
    return { documents: [], total: 0 };
  }
}

export const fetchQueryResult = async (query: string, documentId?: string): Promise<QueryResult> => {
  if (!documentId) {
    // If no document is selected yet, return guide mock
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve({
          id: 'mock-guide',
          data: `Vui lòng tải lên Báo Cáo Tài Chính (PDF) để thực hiện truy vấn "${query}".`,
          confidence: 0.95,
        });
      }, 500);
    });
  }

  try {
    const res = await fetch(`${BASE_URL}/api/v1/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'User-Agent': 'FinTrace-Excel-Addin/1.0',
      },
      body: JSON.stringify({
        document_id: documentId,
        query_text: query,
        top_k_pages: 2,
      }),
    });

    if (!res.ok) {
      throw new Error(`Lỗi truy vấn: ${res.statusText}`);
    }

    const data = await res.json();
    const primaryEvidence = data.evidences?.[0];
    return {
      id: primaryEvidence ? `${data.document_id}_P${primaryEvidence.page_number}` : data.document_id,
      data: data.answer || 'Không tìm thấy câu trả lời.',
      confidence: primaryEvidence?.confidence ?? 0.95,
    };
  } catch (err: any) {
    return {
      id: documentId,
      data: `Phân tích cho "${query}": ${err.message}`,
      confidence: 0.85,
    };
  }
};
