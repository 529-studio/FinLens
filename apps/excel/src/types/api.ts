export interface QueryResult {
  id: string;
  data: string;
  confidence: number;
}

export interface DocumentIngestResponseDTO {
  document_id: string;
  total_pages: number;
  rendered_image_paths: string[];
  indexed_vectors_count: number;
  duration_ms: number;
  from_cache?: boolean;
}

export interface DocumentSummaryDTO {
  document_id: string;
  total_pages?: number;
}

export interface ActiveDocumentState {
  documentId: string | null;
  totalPages: number;
  indexedVectorsCount: number;
  filename?: string;
  durationMs?: number;
  status: 'idle' | 'uploading' | 'ready' | 'error';
  errorMessage?: string;
}

export interface FinancialTableData {
  title?: string;
  headers: string[];
  rows: (string | number)[][];
  includeTotalRow?: boolean;
  sourceDocId: string;
  sourcePage: number;
}

export interface TableExportResult {
  success: boolean;
  insertedCellsCount: number;
  originAddress: string;
  auditComment: string;
}


