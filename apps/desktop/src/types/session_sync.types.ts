/**
 * FinTrace Collaborative Audit Session Sync TypeScript DTOs
 * Governed by Sprint 11 Task S11-03, AGENTS.md Rule 13, and frontend-4file-and-resilient-ui.
 */

export type SessionEventType =
  | 'join'
  | 'leave'
  | 'presence'
  | 'cursor_move'
  | 'annotation_add'
  | 'annotation_resolve'
  | 'annotation_delete'
  | 'heartbeat'
  | 'session_state'
  | 'error';

export type SyncStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

export interface UserPresenceDTO {
  user_id: string;
  name: string;
  role: string;
  color: string;
  active_page: number;
  cursor_x?: number | null;
  cursor_y?: number | null;
  last_seen: number;
}

export interface AuditAnnotationDTO {
  annotation_id: string;
  document_id: string;
  page_number: number;
  bounding_box: [number, number, number, number];
  comment: string;
  author_id: string;
  author_name: string;
  created_at: number;
  resolved: boolean;
  resolved_by?: string | null;
}

export interface SessionStateDTO {
  session_id: string;
  document_id: string;
  created_at: number;
  active_users: Record<string, UserPresenceDTO>;
  annotations: AuditAnnotationDTO[];
}

export interface CollaborativeMessageDTO {
  event: SessionEventType;
  session_id: string;
  user_id?: string;
  payload: any;
  timestamp: number;
}
