/**
 * File 1 of 4: DTOs & Interfaces for Visual RAG
 * Governed by 529 Engineering Standards (frontend-4file-and-resilient-ui)
 */

export interface BoundingBoxDTO {
  ymin: number; // 0-1000
  xmin: number; // 0-1000
  ymax: number; // 0-1000
  xmax: number; // 0-1000
}

export interface GroundedEvidenceDTO {
  page_number: number;
  bounding_box: BoundingBoxDTO;
  label: string;
  extracted_value?: string | number;
  confidence: number;
  document_id?: string;
}

export interface QueryRequestDTO {
  document_id: string;
  query_text: string;
  top_k_pages?: number;
  inference_mode?: 'auto' | 'local' | 'cloud';
}

export interface FootnoteReferenceDTO {
  line_item: string;
  code?: string;
  footnote_number: string;
  footnote_title: string;
  summary: string;
  page_number: number;
  bounding_box: BoundingBoxDTO;
}

export interface QueryResponseDTO {
  document_id: string;
  query_text: string;
  answer: string;
  evidences: GroundedEvidenceDTO[];
  footnotes?: FootnoteReferenceDTO[];
  retrieved_page_numbers: number[];
  engine_used: string;
  latency_ms: number;
  cached?: boolean;
}

export interface ComparativeMetricDTO {
  metric: string;
  unit?: string;
  doc_values: Record<string, string | number>;
  yoy_growth?: string;
  trend?: 'up' | 'down' | 'neutral';
}

export interface ComparativeQueryRequestDTO {
  document_ids: string[];
  query_text: string;
  top_k_per_doc?: number;
  inference_mode?: 'auto' | 'local' | 'cloud';
}

export interface ComparativeQueryResponseDTO {
  document_ids: string[];
  query_text: string;
  answer: string;
  comparative_metrics: ComparativeMetricDTO[];
  evidences: GroundedEvidenceDTO[];
  retrieved_pages: Record<string, number[]>;
  engine_used: string;
  latency_ms: number;
}


export interface DocumentIngestResponseDTO {
  document_id: string;
  total_pages: number;
  rendered_image_paths: string[];
  indexed_vectors_count: number;
  duration_ms: number;
  from_cache?: boolean;
}

export interface DocumentInfoDTO {
  document_id: string;
  total_pages: number;
  available_pages: number[];
}

export interface RenderedPageSize {
  width: number;
  height: number;
}

export type UIState = 'idle' | 'loading' | 'success' | 'error';
