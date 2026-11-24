/**
 * FinTrace Excel Add-in Live Linked Footnote Citation Drawer & In-Sheet Audited Cell Tags
 * Governed by Sprint 12 Task S12-05, AGENTS.md Rule 13, Rule 15 (Zero Emoji),
 * and frontend-4file-and-resilient-ui (3 UI states, >=48px touch targets, ADR-003).
 */

import React from 'react';
import {
  FileText,
  ExternalLink,
  Tag,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  BookOpen,
  X,
  Clock,
  ChevronRight,
  ShieldCheck,
} from 'lucide-react';

export interface AuditedCellData {
  cellAddress: string;
  lineItem: string;
  value: number;
  formattedValue: string;
  auditStatus: 'verified' | 'restated' | 'pending' | 'discrepancy';
  footnoteNumber?: string;
  footnoteTitle?: string;
  footnoteSummary?: string;
  documentId: string;
  pageNumber: number;
  boundingBox: [number, number, number, number];
  confidence: number;
  lastAuditedAt?: number;
  auditorName?: string;
}

export interface AuditedCellDrawerProps {
  isOpen: boolean;
  cellData: AuditedCellData | null;
  isLoading?: boolean;
  errorMessage?: string | null;
  onClose: () => void;
  onRetry?: () => void;
  onJumpToPdf?: (
    documentId: string,
    pageNumber: number,
    boundingBox: [number, number, number, number]
  ) => void;
  onInsertAuditNote?: (cellData: AuditedCellData) => void;
}

export const AuditedCellDrawer: React.FC<AuditedCellDrawerProps> = ({
  isOpen,
  cellData,
  isLoading = false,
  errorMessage = null,
  onClose,
  onRetry,
  onJumpToPdf,
  onInsertAuditNote,
}) => {
  if (!isOpen) {
    return null;
  }

  // 1. Loading State: Skeleton Shimmer
  if (isLoading) {
    return (
      <div
        data-testid="drawer-skeleton"
        className="w-full bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-4 animate-pulse text-slate-400"
      >
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="h-4 bg-slate-800 rounded w-28" />
          <div className="w-6 h-6 bg-slate-800 rounded-full" />
        </div>
        <div className="space-y-2">
          <div className="h-5 bg-slate-800 rounded w-3/4" />
          <div className="h-4 bg-slate-800 rounded w-1/2" />
        </div>
        <div className="h-24 bg-slate-800/60 rounded-xl p-3" />
        <div className="h-12 bg-slate-800 rounded-lg" />
      </div>
    );
  }

  // 2. Error State: Localized Banner with >=48px Retry Button
  if (errorMessage) {
    return (
      <div
        data-testid="drawer-error"
        className="w-full bg-rose-950/70 border border-rose-800/80 rounded-xl p-4 text-rose-200 space-y-3"
      >
        <div className="flex items-start justify-between">
          <div className="flex items-center space-x-2">
            <AlertCircle className="w-5 h-5 text-rose-400 shrink-0" />
            <h4 className="text-xs font-semibold uppercase tracking-wider text-rose-300">
              Lỗi tải thuyết minh BCTC
            </h4>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-rose-400 hover:text-white p-1 rounded cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
        <p className="text-xs text-rose-200">{errorMessage}</p>
        {onRetry && (
          <button
            type="button"
            data-testid="drawer-retry-btn"
            onClick={onRetry}
            className="min-h-[48px] w-full px-4 py-2 bg-rose-700 hover:bg-rose-600 active:bg-rose-800 text-white text-xs font-semibold rounded-lg flex items-center justify-center space-x-2 transition-colors cursor-pointer"
          >
            <RefreshCw className="w-4 h-4" />
            <span>Thử tải lại</span>
          </button>
        )}
      </div>
    );
  }

  // 3. Actionable Empty State: No Cell Selected
  if (!cellData) {
    return (
      <div
        data-testid="drawer-empty"
        className="w-full bg-slate-900/90 border border-slate-800 rounded-xl p-5 text-center space-y-3 text-slate-300"
      >
        <div className="w-10 h-10 rounded-full bg-slate-800 mx-auto flex items-center justify-center text-slate-400">
          <Tag className="w-5 h-5" />
        </div>
        <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-200">
          Chưa chọn ô số liệu kiểm toán
        </h4>
        <p className="text-xs text-slate-400 leading-relaxed max-w-xs mx-auto">
          Chọn một ô số liệu tài chính đã kiểm toán trên bảng tính để xem nguồn thuyết minh và trích dẫn BCTC.
        </p>
      </div>
    );
  }

  const statusConfig = {
    verified: {
      label: 'Đã kiểm toán & Xác thực',
      icon: <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />,
      colorClass: 'bg-emerald-950/60 text-emerald-300 border-emerald-600/50',
    },
    restated: {
      label: 'Số liệu hồi tố (Restated)',
      icon: <AlertCircle className="w-3.5 h-3.5 text-amber-400" />,
      colorClass: 'bg-amber-950/60 text-amber-300 border-amber-600/50',
    },
    discrepancy: {
      label: 'Phát hiện chênh lệch (Cảnh báo)',
      icon: <AlertCircle className="w-3.5 h-3.5 text-rose-400" />,
      colorClass: 'bg-rose-950/60 text-rose-300 border-rose-600/50',
    },
    pending: {
      label: 'Chờ đối chiếu thuyết minh',
      icon: <Clock className="w-3.5 h-3.5 text-indigo-400" />,
      colorClass: 'bg-indigo-950/60 text-indigo-300 border-indigo-600/50',
    },
  }[cellData.auditStatus];

  return (
    <div
      data-testid="audited-cell-drawer"
      className="w-full bg-slate-900 border border-slate-800 rounded-2xl p-4 shadow-xl text-slate-100 space-y-4 animate-in fade-in slide-in-from-right-4 duration-200"
    >
      {/* Header with Cell Coordinates & Close Trigger */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center space-x-2">
          <span className="px-2 py-0.5 bg-indigo-600/20 border border-indigo-500/40 text-indigo-300 rounded font-mono text-xs font-bold">
            {cellData.cellAddress}
          </span>
          <span className="text-xs text-slate-400 truncate max-w-[150px]">
            {cellData.documentId}
          </span>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="w-7 h-7 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 flex items-center justify-center cursor-pointer transition-colors"
          title="Đóng bảng chi tiết"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Main Metric Information */}
      <div className="space-y-1">
        <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
          Chỉ tiêu báo cáo
        </div>
        <h3 className="text-sm font-semibold text-slate-100 leading-snug">
          {cellData.lineItem}
        </h3>
        <div className="text-lg font-bold font-mono text-emerald-400 mt-1">
          {cellData.formattedValue}
        </div>
      </div>

      {/* Audit Status Tag Badge */}
      <div className="flex items-center space-x-2">
        <div
          className={`px-2.5 py-1 rounded-full text-xs font-medium border flex items-center space-x-1.5 ${statusConfig.colorClass}`}
        >
          {statusConfig.icon}
          <span>{statusConfig.label}</span>
        </div>
        <div className="text-[11px] text-slate-400 font-mono">
          Độ tin cậy: <span className="text-slate-200 font-semibold">{`${(cellData.confidence * 100).toFixed(1)}%`}</span>
        </div>
      </div>

      {/* Linked Footnote Disclosure Box */}
      {cellData.footnoteNumber && (
        <div className="bg-slate-950/70 border border-slate-800 rounded-xl p-3 space-y-2">
          <div className="flex items-center space-x-2 text-indigo-400">
            <BookOpen className="w-4 h-4 shrink-0" />
            <span className="text-xs font-semibold">
              Thuyết minh {cellData.footnoteNumber}
              {cellData.footnoteTitle ? `: ${cellData.footnoteTitle}` : ''}
            </span>
          </div>
          {cellData.footnoteSummary && (
            <p className="text-xs text-slate-300 leading-relaxed pl-6 border-l-2 border-indigo-500/30">
              {cellData.footnoteSummary}
            </p>
          )}
          <div className="text-[11px] text-slate-400 pl-6 flex items-center space-x-2">
            <span>Trang {cellData.pageNumber}</span>
            <span>•</span>
            <span className="font-mono text-[10px] text-slate-400">
              Vùng tọa độ: [{cellData.boundingBox.join(', ')}]
            </span>
          </div>
        </div>
      )}

      {/* Interactive Action Buttons (>=48px touch targets) */}
      <div className="space-y-2 pt-1 border-t border-slate-800">
        {onJumpToPdf && (
          <button
            type="button"
            data-testid="drawer-jump-pdf-btn"
            onClick={() => onJumpToPdf(cellData.documentId, cellData.pageNumber, cellData.boundingBox)}
            className="min-h-[48px] w-full px-4 py-2 bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700 text-white text-xs font-semibold rounded-xl flex items-center justify-center space-x-2 transition-colors cursor-pointer shadow-md"
          >
            <ExternalLink className="w-4 h-4" />
            <span>Mở vị trí trích dẫn trên BCTC gốc (Trang {cellData.pageNumber})</span>
          </button>
        )}

        {onInsertAuditNote && (
          <button
            type="button"
            data-testid="drawer-insert-note-btn"
            onClick={() => onInsertAuditNote(cellData)}
            className="min-h-[48px] w-full px-4 py-2 bg-slate-800 hover:bg-slate-700 active:bg-slate-850 text-slate-200 text-xs font-medium rounded-xl flex items-center justify-center space-x-2 transition-colors cursor-pointer border border-slate-700"
          >
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span>Chèn ghi chú kiểm toán vào ô Excel</span>
          </button>
        )}
      </div>
    </div>
  );
};
