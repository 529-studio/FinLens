/**
 * FinTrace Real-Time Collaborative Session Sync Hook
 * Connects to /ws/v1/sessions/{sessionId} for multi-auditor presence and visual annotations.
 * Governed by Sprint 11 Task S11-03, AGENTS.md Rule 13, and frontend-4file-and-resilient-ui.
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import {
  SyncStatus,
  UserPresenceDTO,
  AuditAnnotationDTO,
  SessionStateDTO,
  CollaborativeMessageDTO,
} from '../types/session_sync.types';

export interface UseSessionSyncOptions {
  sessionId: string;
  documentId: string;
  token?: string;
  initialPage?: number;
  wsBaseUrl?: string;
  heartbeatIntervalMs?: number;
}

export interface UseSessionSyncReturn {
  syncStatus: SyncStatus;
  activeUsers: UserPresenceDTO[];
  annotations: AuditAnnotationDTO[];
  errorMessage: string | null;
  sessionMetadata: { sessionId: string; documentId: string; createdAt: number } | null;
  sendCursorMove: (page: number, x?: number, y?: number) => void;
  addAnnotation: (
    pageNumber: number,
    boundingBox: [number, number, number, number],
    comment: string,
    annotationId?: string
  ) => void;
  resolveAnnotation: (annotationId: string) => void;
  deleteAnnotation: (annotationId: string) => void;
  reconnect: () => void;
}

export function useSessionSync({
  sessionId,
  documentId,
  token,
  initialPage = 1,
  wsBaseUrl = 'ws://127.0.0.1:8765',
  heartbeatIntervalMs = 15000,
}: UseSessionSyncOptions): UseSessionSyncReturn {
  const [syncStatus, setSyncStatus] = useState<SyncStatus>('connecting');
  const [activeUsers, setActiveUsers] = useState<UserPresenceDTO[]>([]);
  const [annotations, setAnnotations] = useState<AuditAnnotationDTO[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [sessionMetadata, setSessionMetadata] = useState<{
    sessionId: string;
    documentId: string;
    createdAt: number;
  } | null>(null);

  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const heartbeatIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const retryCountRef = useRef<number>(0);
  const isManuallyClosedRef = useRef<boolean>(false);

  const connect = useCallback(() => {
    if (!sessionId || !documentId) return;

    if (socketRef.current) {
      isManuallyClosedRef.current = true;
      socketRef.current.close();
      socketRef.current = null;
    }

    isManuallyClosedRef.current = false;
    setSyncStatus('connecting');
    setErrorMessage(null);

    const params = new URLSearchParams();
    if (token) params.set('token', token);
    params.set('document_id', documentId);
    params.set('active_page', String(initialPage));

    const url = `${wsBaseUrl}/ws/v1/sessions/${encodeURIComponent(sessionId)}?${params.toString()}`;

    try {
      const ws = new WebSocket(url);
      socketRef.current = ws;

      ws.onopen = () => {
        setSyncStatus('connected');
        setErrorMessage(null);
        retryCountRef.current = 0;

        // Start heartbeat timer
        if (heartbeatIntervalRef.current) clearInterval(heartbeatIntervalRef.current);
        heartbeatIntervalRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ event: 'heartbeat' }));
          }
        }, heartbeatIntervalMs);
      };

      ws.onmessage = (event: MessageEvent) => {
        try {
          const msg: CollaborativeMessageDTO = JSON.parse(event.data);

          switch (msg.event) {
            case 'session_state': {
              const state: SessionStateDTO = msg.payload;
              setSessionMetadata({
                sessionId: state.session_id,
                documentId: state.document_id,
                createdAt: state.created_at,
              });
              setActiveUsers(Object.values(state.active_users || {}));
              setAnnotations(state.annotations || []);
              break;
            }

            case 'join': {
              const newUser: UserPresenceDTO = msg.payload;
              setActiveUsers((prev) => {
                const exists = prev.find((u) => u.user_id === newUser.user_id);
                if (exists) {
                  return prev.map((u) => (u.user_id === newUser.user_id ? newUser : u));
                }
                return [...prev, newUser];
              });
              break;
            }

            case 'leave': {
              const leftUserId = msg.user_id || msg.payload?.user_id;
              if (leftUserId) {
                setActiveUsers((prev) => prev.filter((u) => u.user_id !== leftUserId));
              }
              break;
            }

            case 'presence': {
              const presence: UserPresenceDTO = msg.payload;
              if (presence && presence.user_id) {
                setActiveUsers((prev) =>
                  prev.map((u) => (u.user_id === presence.user_id ? { ...u, ...presence } : u))
                );
              }
              break;
            }

            case 'annotation_add': {
              const newAnno: AuditAnnotationDTO = msg.payload;
              setAnnotations((prev) => {
                if (prev.some((a) => a.annotation_id === newAnno.annotation_id)) {
                  return prev;
                }
                return [...prev, newAnno];
              });
              break;
            }

            case 'annotation_resolve': {
              const resolvedAnno: AuditAnnotationDTO = msg.payload;
              setAnnotations((prev) =>
                prev.map((a) => (a.annotation_id === resolvedAnno.annotation_id ? resolvedAnno : a))
              );
              break;
            }

            case 'annotation_delete': {
              const targetId = msg.payload?.annotation_id;
              if (targetId) {
                setAnnotations((prev) => prev.filter((a) => a.annotation_id !== targetId));
              }
              break;
            }

            case 'heartbeat':
              // Heartbeat pong received; vitality confirmed
              break;

            case 'error':
              setErrorMessage(msg.payload?.error || (msg as any).error || 'Lỗi đồng bộ phòng kiểm toán');
              break;

            default:
              break;
          }
        } catch (e) {
          console.error('Failed to parse collaborative WebSocket message', e);
        }
      };

      ws.onerror = () => {
        setSyncStatus('error');
        setErrorMessage('Không thể kết nối đến máy chủ đồng bộ kiểm toán');
      };

      ws.onclose = () => {
        if (heartbeatIntervalRef.current) {
          clearInterval(heartbeatIntervalRef.current);
          heartbeatIntervalRef.current = null;
        }

        if (!isManuallyClosedRef.current) {
          setSyncStatus('disconnected');
          // Exponential backoff reconnect
          const backoff = Math.min(1000 * Math.pow(2, retryCountRef.current), 10000);
          retryCountRef.current += 1;
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, backoff);
        }
      };
    } catch (e: any) {
      setSyncStatus('error');
      setErrorMessage(e.message || 'Lỗi khởi tạo WebSocket');
    }
  }, [sessionId, documentId, token, initialPage, wsBaseUrl, heartbeatIntervalMs]);

  useEffect(() => {
    connect();

    return () => {
      isManuallyClosedRef.current = true;
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (heartbeatIntervalRef.current) clearInterval(heartbeatIntervalRef.current);
      if (socketRef.current) {
        socketRef.current.close();
        socketRef.current = null;
      }
    };
  }, [connect]);

  const sendCursorMove = useCallback((page: number, x?: number, y?: number) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(
        JSON.stringify({
          event: 'cursor_move',
          payload: {
            active_page: page,
            cursor_x: x ?? null,
            cursor_y: y ?? null,
          },
        })
      );
    }
  }, []);

  const addAnnotation = useCallback(
    (
      pageNumber: number,
      boundingBox: [number, number, number, number],
      comment: string,
      annotationId?: string
    ) => {
      if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
        socketRef.current.send(
          JSON.stringify({
            event: 'annotation_add',
            payload: {
              annotation_id: annotationId,
              page_number: pageNumber,
              bounding_box: boundingBox,
              comment,
            },
          })
        );
      }
    },
    []
  );

  const resolveAnnotation = useCallback((annotationId: string) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(
        JSON.stringify({
          event: 'annotation_resolve',
          payload: { annotation_id: annotationId },
        })
      );
    }
  }, []);

  const deleteAnnotation = useCallback((annotationId: string) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(
        JSON.stringify({
          event: 'annotation_delete',
          payload: { annotation_id: annotationId },
        })
      );
    }
  }, []);

  const reconnect = useCallback(() => {
    retryCountRef.current = 0;
    connect();
  }, [connect]);

  return {
    syncStatus,
    activeUsers,
    annotations,
    errorMessage,
    sessionMetadata,
    sendCursorMove,
    addAnnotation,
    resolveAnnotation,
    deleteAnnotation,
    reconnect,
  };
}
