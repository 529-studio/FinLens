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
}

export interface QueryRequestDTO {
  document_id: string;
  query_text: string;
  top_k_pages?: number;
  inference_mode?: 'auto' | 'local' | 'cloud';
}

export interface QueryResponseDTO {
  document_id: string;
  query_text: string;
  answer: string;
  evidences: GroundedEvidenceDTO[];
  retrieved_page_numbers: number[];
  engine_used: string;
  latency_ms: number;
}

export interface DocumentIngestResponseDTO {
  document_id: string;
  total_pages: number;
  rendered_image_paths: string[];
  indexed_vectors_count: number;
  duration_ms: number;
}

export type UIState = 'idle' | 'loading' | 'success' | 'error';
