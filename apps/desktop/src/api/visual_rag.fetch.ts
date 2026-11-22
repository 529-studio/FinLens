/**
 * File 2 of 4: Resilient Fetcher for Visual RAG
 * Governed by 529 Engineering Standards (resilient-networking-and-waf & frontend-4file)
 */

import {
  QueryRequestDTO,
  QueryResponseDTO,
  DocumentIngestResponseDTO,
  ComparativeQueryRequestDTO,
  ComparativeQueryResponseDTO,
} from '../types/visual_rag.types';

const BASE_URL = 'http://127.0.0.1:8765';
const DEFAULT_TIMEOUT_MS = 25000;

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export async function fetchQuery(
  payload: QueryRequestDTO,
  signal?: AbortSignal
): Promise<QueryResponseDTO> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), DEFAULT_TIMEOUT_MS);

  // Combine external abort signal if provided
  if (signal) {
    signal.addEventListener('abort', () => controller.abort());
  }

  try {
    const res = await fetch(`${BASE_URL}/api/v1/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'User-Agent': 'FinTrace-Desktop-Client/1.0',
      },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });

    if (!res.ok) {
      const errBody = await res.text().catch(() => '');
      throw new ApiError(res.status, `Daemon error ${res.status}: ${errBody || res.statusText}`);
    }

    return (await res.json()) as QueryResponseDTO;
  } catch (err: any) {
    if (err.name === 'AbortError') {
      throw new ApiError(408, 'Query timed out after 25s. Check engine load.');
    }
    throw err;
  } finally {
    clearTimeout(timeoutId);
  }
}

export async function ingestDocument(
  filePath: string,
  dpi = 150
): Promise<DocumentIngestResponseDTO> {
  const res = await fetch(`${BASE_URL}/api/v1/documents/ingest`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'User-Agent': 'FinTrace-Desktop-Client/1.0',
    },
    body: JSON.stringify({ file_path: filePath, render_dpi: dpi }),
  });

  if (!res.ok) {
    throw new ApiError(res.status, `Failed to render PDF: ${res.statusText}`);
  }

  return (await res.json()) as DocumentIngestResponseDTO;
}

export async function fetchComparativeQuery(
  payload: ComparativeQueryRequestDTO,
  signal?: AbortSignal
): Promise<ComparativeQueryResponseDTO> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), DEFAULT_TIMEOUT_MS);

  if (signal) {
    signal.addEventListener('abort', () => controller.abort());
  }

  try {
    const res = await fetch(`${BASE_URL}/api/v1/query/comparative`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'User-Agent': 'FinTrace-Desktop-Client/1.0',
      },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });

    if (!res.ok) {
      const errBody = await res.text().catch(() => '');
      throw new ApiError(res.status, `Lỗi so sánh tài liệu (${res.status}): ${errBody || res.statusText}`);
    }

    return (await res.json()) as ComparativeQueryResponseDTO;
  } catch (err: any) {
    if (err.name === 'AbortError') {
      throw new ApiError(408, 'Thời gian xử lý so sánh tài liệu vượt quá giới hạn (25s). Vui lòng thử lại.');
    }
    throw err;
  } finally {
    clearTimeout(timeoutId);
  }
}

