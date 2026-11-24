/**
 * FinTrace Collaborative Audit Session Bar Component
 * Displays real-time presence indicators, active peer badges, and synchronization health.
 * Governed by Sprint 11 Task S11-03, AGENTS.md Rule 13, Rule 15 (Zero Emoji),
 * and frontend-4file-and-resilient-ui (3 UI states, >=48px touch targets).
 */

import React, { useState } from 'react';
import {
  Users,
  Wifi,
  WifiOff,
  RefreshCw,
  AlertCircle,
  MessageSquare,
  Copy,
  Check,
} from 'lucide-react';
import { SyncStatus, UserPresenceDTO, AuditAnnotationDTO } from '../../types/session_sync.types';

export interface CollaborativeSessionBarProps {
  sessionId: string;
  documentId: string;
  syncStatus: SyncStatus;
  activeUsers: UserPresenceDTO[];
  annotations: AuditAnnotationDTO[];
  errorMessage?: string | null;
  currentUserId?: string;
  onRetry?: () => void;
  onJumpToPage?: (page: number) => void;
}

export const CollaborativeSessionBar: React.FC<CollaborativeSessionBarProps> = ({
  sessionId,
  documentId,
  syncStatus,
  activeUsers,
  annotations,
  errorMessage,
  currentUserId,
  onRetry,
  onJumpToPage,
}) => {
  const [copied, setCopied] = useState<boolean>(false);

  const handleCopySessionId = () => {
    navigator.clipboard?.writeText(sessionId);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // 1. Loading / Connecting State: Skeleton Bar
  if (syncStatus === 'connecting') {
    return (
      <div
        data-testid="collaborative-skeleton"
        className="w-full bg-slate-900 border-b border-slate-800 px-4 py-3 flex items-center justify-between animate-pulse"
      >
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 rounded-full bg-slate-800" />
          <div className="space-y-1">
            <div className="w-32 h-3.5 bg-slate-800 rounded" />
            <div className="w-20 h-2.5 bg-slate-800 rounded" />
          </div>
        </div>
        <div className="flex items-center space-x-2">
          <div className="w-24 h-6 bg-slate-800 rounded-full" />
          <div className="w-24 h-6 bg-slate-800 rounded-full" />
        </div>
      </div>
    );
  }

  // 2. Error State: Localized Banner with Retry Button (>=48px touch target)
  if (syncStatus === 'error' || (syncStatus === 'disconnected' && errorMessage)) {
    return (
      <div
        data-testid="collaborative-error"
        className="w-full bg-rose-950/60 border-b border-rose-800/80 px-4 py-2 flex items-center justify-between"
      >
        <div className="flex items-center space-x-3 text-rose-200">
          <AlertCircle className="w-5 h-5 text-rose-400 shrink-0" />
          <div>
            <span className="font-semibold text-sm">Lỗi đồng bộ phòng kiểm toán:</span>
            <span className="ml-2 text-xs text-rose-300">
              {errorMessage || 'Mất kết nối với máy chủ WebSocket'}
            </span>
          </div>
        </div>
        {onRetry && (
          <button
            type="button"
            data-testid="collaborative-retry-btn"
            onClick={onRetry}
            className="min-h-[48px] px-4 py-2 bg-rose-700 hover:bg-rose-600 active:bg-rose-800 text-white text-xs font-semibold rounded-lg flex items-center space-x-2 transition-colors cursor-pointer"
          >
            <RefreshCw className="w-4 h-4" />
            <span>Thử lại</span>
          </button>
        )}
      </div>
    );
  }

  const otherUsers = activeUsers.filter((u) => u.user_id !== currentUserId);
  const unresolvedAnnotations = annotations.filter((a) => !a.resolved);

  return (
    <div
      data-testid="collaborative-session-bar"
      className="w-full bg-slate-900 border-b border-slate-800 px-4 py-2.5 flex items-center justify-between select-none"
    >
      {/* Left: Session metadata & connection status badge */}
      <div className="flex items-center space-x-3">
        <div className="flex items-center space-x-1.5 px-2.5 py-1 bg-slate-800/90 rounded-full text-xs font-medium text-slate-300">
          {syncStatus === 'connected' ? (
            <Wifi className="w-3.5 h-3.5 text-emerald-400" />
          ) : (
            <WifiOff className="w-3.5 h-3.5 text-amber-400" />
          )}
          <span className="font-mono text-slate-200">{sessionId}</span>
        </div>

        <button
          type="button"
          data-testid="copy-session-id-btn"
          onClick={handleCopySessionId}
          title="Sao chép mã phòng"
          className="min-h-[48px] min-w-[48px] p-2 hover:bg-slate-800 active:bg-slate-700 rounded-lg text-slate-400 hover:text-slate-200 flex items-center justify-center transition-colors cursor-pointer"
        >
          {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
        </button>

        <span className="text-xs text-slate-500 hidden md:inline">
          Tài liệu: <span className="font-mono text-slate-400">{documentId}</span>
        </span>
      </div>

      {/* Middle/Right: Peer Avatars or Empty State */}
      <div className="flex items-center space-x-3">
        {/* 3. Empty State: No other peers online */}
        {otherUsers.length === 0 ? (
          <div
            data-testid="collaborative-empty"
            className="flex items-center space-x-2 text-xs text-slate-400 px-3 py-1 bg-slate-800/40 rounded-lg border border-slate-800"
          >
            <Users className="w-4 h-4 text-slate-500" />
            <span>Chưa có đồng nghiệp nào tham gia phòng</span>
          </div>
        ) : (
          <div data-testid="collaborative-peers-list" className="flex items-center space-x-2">
            <span className="text-xs text-slate-400 font-medium hidden sm:inline">
              Đồng nghiệp ({otherUsers.length}):
            </span>
            <div className="flex items-center -space-x-1.5 overflow-hidden">
              {otherUsers.map((user) => {
                const initial = (user.name || user.user_id).charAt(0).toUpperCase();
                return (
                  <button
                    key={user.user_id}
                    type="button"
                    title={`${user.name} (${user.role}) — Trang ${user.active_page}`}
                    onClick={() => onJumpToPage && onJumpToPage(user.active_page)}
                    className="min-h-[48px] px-2 py-1 flex items-center space-x-1.5 bg-slate-800/80 hover:bg-slate-700/80 rounded-full border border-slate-700 text-xs text-slate-200 transition-colors cursor-pointer"
                  >
                    <span
                      className="w-6 h-6 rounded-full flex items-center justify-center text-[11px] font-bold text-white shadow-sm"
                      style={{ backgroundColor: user.color || '#4F46E5' }}
                    >
                      {initial}
                    </span>
                    <span className="max-w-[80px] truncate hidden md:inline font-medium">
                      {user.name}
                    </span>
                    <span className="px-1.5 py-0.5 text-[10px] bg-slate-900/80 text-indigo-300 rounded-full font-mono">
                      P.{user.active_page}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* Annotations counter badge */}
        <div
          data-testid="annotations-badge"
          className="flex items-center space-x-1.5 px-3 py-1 bg-slate-800/90 rounded-full text-xs font-medium text-slate-300"
        >
          <MessageSquare className="w-3.5 h-3.5 text-indigo-400" />
          <span>{annotations.length}</span>
          {unresolvedAnnotations.length > 0 && (
            <span className="w-2 h-2 rounded-full bg-amber-400" title="Có ghi chú chưa giải quyết" />
          )}
        </div>
      </div>
    </div>
  );
};
