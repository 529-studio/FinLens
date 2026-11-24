/**
 * FinTrace Desktop Native PDF Highlight Annotation Layer & Visual Comment Pinning
 * Governed by Sprint 12 Task S12-03, AGENTS.md Rule 13, Rule 15 (Zero Emoji),
 * and frontend-4file-and-resilient-ui (3 UI states, >=48px touch targets, ADR-003).
 */

import React, { useState, useRef, useMemo } from 'react';
import {
  Pin,
  MessageSquare,
  Check,
  Trash2,
  X,
  AlertCircle,
  RefreshCw,
  Plus,
  Highlighter,
} from 'lucide-react';
import type { AuditAnnotationDTO } from '../../types/session_sync.types';

export interface AnnotationCanvasProps {
  documentId: string;
  pageNumber: number;
  renderedWidth: number;
  renderedHeight: number;
  zoomLevel?: number;
  annotations: AuditAnnotationDTO[];
  isLoading?: boolean;
  errorMessage?: string | null;
  currentUserId?: string;
  currentUserRole?: string;
  isDrawingEnabled?: boolean;
  className?: string;
  onRetry?: () => void;
  onAddAnnotation?: (newAnnotation: {
    document_id: string;
    page_number: number;
    bounding_box: [number, number, number, number];
    comment: string;
    author_id: string;
    author_name: string;
  }) => void;
  onResolveAnnotation?: (annotationId: string) => void;
  onDeleteAnnotation?: (annotationId: string) => void;
}

interface DragBox {
  startX: number;
  startY: number;
  currentX: number;
  currentY: number;
}

export const AnnotationCanvas: React.FC<AnnotationCanvasProps> = ({
  documentId,
  pageNumber,
  renderedWidth,
  renderedHeight,
  zoomLevel = 1.0,
  annotations,
  isLoading = false,
  errorMessage = null,
  currentUserId = 'usr-current',
  currentUserRole = 'Auditor',
  isDrawingEnabled = false,
  className = '',
  onRetry,
  onAddAnnotation,
  onResolveAnnotation,
  onDeleteAnnotation,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [selectedAnnotationId, setSelectedAnnotationId] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [dragBox, setDragBox] = useState<DragBox | null>(null);
  const [pendingBox, setPendingBox] = useState<[number, number, number, number] | null>(null);
  const [newComment, setNewComment] = useState<string>('');

  // Filter annotations for current page
  const pageAnnotations = useMemo(() => {
    return annotations.filter((a) => a.page_number === pageNumber);
  }, [annotations, pageNumber]);

  // Coordinate conversion helper: normalized [0, 1000] -> rendered pixels
  const toPixels = (box: [number, number, number, number]) => {
    const [ymin, xmin, ymax, xmax] = box;
    const top = (ymin / 1000) * renderedHeight * zoomLevel;
    const left = (xmin / 1000) * renderedWidth * zoomLevel;
    const width = ((xmax - xmin) / 1000) * renderedWidth * zoomLevel;
    const height = ((ymax - ymin) / 1000) * renderedHeight * zoomLevel;
    return { top, left, width, height };
  };

  // Coordinate conversion helper: client mouse pixels -> normalized [0, 1000]
  const toNormalized = (
    startX: number,
    startY: number,
    endX: number,
    endY: number
  ): [number, number, number, number] => {
    const actualWidth = renderedWidth * zoomLevel;
    const actualHeight = renderedHeight * zoomLevel;

    const minX = Math.max(0, Math.min(startX, endX));
    const maxX = Math.min(actualWidth, Math.max(startX, endX));
    const minY = Math.max(0, Math.min(startY, endY));
    const maxY = Math.min(actualHeight, Math.max(startY, endY));

    const ymin = Math.round((minY / actualHeight) * 1000);
    const xmin = Math.round((minX / actualWidth) * 1000);
    const ymax = Math.round((maxY / actualHeight) * 1000);
    const xmax = Math.round((maxX / actualWidth) * 1000);

    return [ymin, xmin, ymax, xmax];
  };

  // Mouse handlers for drag-to-select annotation
  const handleMouseDown = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!isDrawingEnabled || pendingBox) return;

    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return;

    const startX = e.clientX - rect.left;
    const startY = e.clientY - rect.top;

    setIsDragging(true);
    setDragBox({ startX, startY, currentX: startX, currentY: startY });
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!isDragging || !dragBox) return;

    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return;

    const currentX = e.clientX - rect.left;
    const currentY = e.clientY - rect.top;

    setDragBox((prev) => (prev ? { ...prev, currentX, currentY } : null));
  };

  const handleMouseUp = () => {
    if (!isDragging || !dragBox) return;

    setIsDragging(false);
    const widthDelta = Math.abs(dragBox.currentX - dragBox.startX);
    const heightDelta = Math.abs(dragBox.currentY - dragBox.startY);

    // Minimum size threshold (e.g. > 15px) to prevent accidental clicks
    if (widthDelta > 15 && heightDelta > 15) {
      const normalized = toNormalized(
        dragBox.startX,
        dragBox.startY,
        dragBox.currentX,
        dragBox.currentY
      );
      setPendingBox(normalized);
      setNewComment('');
    }
    setDragBox(null);
  };

  const handleSavePendingAnnotation = () => {
    if (!pendingBox || !newComment.trim()) return;

    onAddAnnotation?.({
      document_id: documentId,
      page_number: pageNumber,
      bounding_box: pendingBox,
      comment: newComment.trim(),
      author_id: currentUserId,
      author_name: currentUserRole === 'Auditor' ? 'Nguyễn Văn Kiểm' : 'Chuyên Viên Kiểm Toán',
    });

    setPendingBox(null);
    setNewComment('');
  };

  const handleCancelPendingAnnotation = () => {
    setPendingBox(null);
    setNewComment('');
  };

  // 1. Loading State: Skeleton Shimmer
  if (isLoading) {
    return (
      <div
        data-testid="annotation-skeleton"
        className={`absolute inset-0 bg-slate-900/40 backdrop-blur-[1px] animate-pulse flex items-center justify-center z-30 ${className}`}
        style={{
          width: `${renderedWidth * zoomLevel}px`,
          height: `${renderedHeight * zoomLevel}px`,
        }}
      >
        <div className="bg-slate-800/90 border border-slate-700/80 rounded-xl px-5 py-4 flex items-center space-x-3 text-slate-300">
          <Highlighter className="w-5 h-5 text-indigo-400 animate-spin" />
          <span className="text-xs font-medium">Đang tải lớp ghi chú kiểm toán...</span>
        </div>
      </div>
    );
  }

  // 2. Error State: Localized Banner with >=48px Retry Button
  if (errorMessage) {
    return (
      <div
        data-testid="annotation-error"
        className={`absolute top-4 left-4 right-4 z-40 bg-rose-950/90 border border-rose-800 rounded-xl p-4 shadow-xl flex items-center justify-between text-rose-200 ${className}`}
      >
        <div className="flex items-center space-x-3">
          <AlertCircle className="w-5 h-5 text-rose-400 shrink-0" />
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wider text-rose-300">
              Lỗi hiển thị ghi chú
            </h4>
            <p className="text-xs text-rose-200 mt-0.5">{errorMessage}</p>
          </div>
        </div>
        {onRetry && (
          <button
            type="button"
            data-testid="annotation-retry-btn"
            onClick={onRetry}
            className="min-h-[48px] px-4 py-2 bg-rose-700 hover:bg-rose-600 active:bg-rose-800 text-white text-xs font-semibold rounded-lg flex items-center space-x-2 transition-colors cursor-pointer shrink-0"
          >
            <RefreshCw className="w-4 h-4" />
            <span>Thử lại</span>
          </button>
        )}
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      data-testid="annotation-canvas-container"
      className={`absolute inset-0 overflow-visible select-none z-20 ${
        isDrawingEnabled ? 'cursor-crosshair' : 'pointer-events-none'
      } ${className}`}
      style={{
        width: `${renderedWidth * zoomLevel}px`,
        height: `${renderedHeight * zoomLevel}px`,
      }}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
    >
      {/* 3. Empty State Helper Badge */}
      {pageAnnotations.length === 0 && !pendingBox && (
        <div
          data-testid="annotation-empty"
          className="absolute bottom-4 left-1/2 -translate-x-1/2 pointer-events-auto bg-slate-900/85 backdrop-blur-md border border-slate-700/80 rounded-full px-4 py-2 text-xs text-slate-300 shadow-lg flex items-center space-x-2"
        >
          <MessageSquare className="w-4 h-4 text-slate-400" />
          <span>Chưa có ghi chú nào trên trang này. Kéo chuột để tạo vùng ghi chú mới.</span>
        </div>
      )}

      {/* SVG Layer for Highlights */}
      <svg className="absolute inset-0 w-full h-full pointer-events-none overflow-visible">
        {pageAnnotations.map((ann) => {
          const { top, left, width, height } = toPixels(ann.bounding_box);
          const isSelected = selectedAnnotationId === ann.annotation_id;
          const strokeColor = ann.resolved ? '#10B981' : isSelected ? '#6366F1' : '#F59E0B';
          const fillColor = ann.resolved
            ? 'rgba(16, 185, 129, 0.12)'
            : isSelected
            ? 'rgba(99, 102, 241, 0.20)'
            : 'rgba(245, 158, 11, 0.15)';

          return (
            <rect
              key={`rect-${ann.annotation_id}`}
              data-testid={`annotation-box-${ann.annotation_id}`}
              x={left}
              y={top}
              width={width}
              height={height}
              rx="4"
              ry="4"
              fill={fillColor}
              stroke={strokeColor}
              strokeWidth={isSelected ? '2.5' : '1.5'}
              strokeDasharray={ann.resolved ? '4 2' : 'none'}
              className="transition-all duration-200"
            />
          );
        })}

        {/* Live Dragging Selection Box */}
        {isDragging && dragBox && (
          <rect
            data-testid="annotation-drag-rect"
            x={Math.min(dragBox.startX, dragBox.currentX)}
            y={Math.min(dragBox.startY, dragBox.currentY)}
            width={Math.abs(dragBox.currentX - dragBox.startX)}
            height={Math.abs(dragBox.currentY - dragBox.startY)}
            rx="4"
            ry="4"
            fill="rgba(99, 102, 241, 0.18)"
            stroke="#6366F1"
            strokeWidth="1.5"
            strokeDasharray="4 3"
          />
        )}
      </svg>

      {/* Interactive Comment Pins */}
      {pageAnnotations.map((ann) => {
        const { top, left, width } = toPixels(ann.bounding_box);
        const pinLeft = Math.max(0, left + width - 12);
        const pinTop = Math.max(0, top - 12);
        const isSelected = selectedAnnotationId === ann.annotation_id;

        return (
          <button
            key={`pin-${ann.annotation_id}`}
            type="button"
            data-testid={`annotation-pin-${ann.annotation_id}`}
            onClick={(e) => {
              e.stopPropagation();
              setSelectedAnnotationId(isSelected ? null : ann.annotation_id);
            }}
            className={`absolute pointer-events-auto w-7 h-7 rounded-full shadow-md flex items-center justify-center transition-transform hover:scale-110 cursor-pointer ${
              ann.resolved
                ? 'bg-emerald-600 text-white hover:bg-emerald-500'
                : isSelected
                ? 'bg-indigo-600 text-white ring-2 ring-indigo-300'
                : 'bg-amber-500 text-slate-950 hover:bg-amber-400'
            }`}
            style={{
              top: `${pinTop}px`,
              left: `${pinLeft}px`,
            }}
            title={ann.comment}
          >
            {ann.resolved ? <Check className="w-3.5 h-3.5" /> : <Pin className="w-3.5 h-3.5" />}
          </button>
        );
      })}

      {/* Selected Annotation Details Popover */}
      {selectedAnnotationId && (() => {
        const ann = pageAnnotations.find((a) => a.annotation_id === selectedAnnotationId);
        if (!ann) return null;

        const { top, left, width, height } = toPixels(ann.bounding_box);
        const popoverTop = top + height + 8;
        const popoverLeft = Math.min(Math.max(10, left), (renderedWidth * zoomLevel) - 320);

        return (
          <div
            data-testid={`annotation-popover-${ann.annotation_id}`}
            className="absolute pointer-events-auto z-50 w-80 bg-slate-900 border border-slate-700/80 rounded-xl p-4 shadow-2xl text-slate-100"
            style={{
              top: `${popoverTop}px`,
              left: `${popoverLeft}px`,
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Popover Header */}
            <div className="flex items-center justify-between border-b border-slate-800 pb-2 mb-2">
              <div className="flex items-center space-x-2">
                <div className="w-6 h-6 rounded-full bg-indigo-600/30 text-indigo-300 flex items-center justify-center text-xs font-bold">
                  {ann.author_name.charAt(0)}
                </div>
                <div>
                  <div className="text-xs font-semibold text-slate-200">{ann.author_name}</div>
                  <div className="text-[10px] text-slate-400">
                    {new Date(ann.created_at * 1000).toLocaleTimeString()}
                  </div>
                </div>
              </div>
              <button
                type="button"
                data-testid="annotation-close-btn"
                onClick={() => setSelectedAnnotationId(null)}
                className="w-7 h-7 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 flex items-center justify-center cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Comment Body */}
            <p className="text-xs text-slate-200 my-2 leading-relaxed bg-slate-950/50 p-2.5 rounded-lg border border-slate-800/80">
              {ann.comment}
            </p>

            {/* Resolved Status Notice */}
            {ann.resolved && (
              <div className="text-[11px] text-emerald-400 flex items-center space-x-1.5 mb-2 bg-emerald-950/40 px-2 py-1 rounded">
                <Check className="w-3.5 h-3.5" />
                <span>Đã được giải quyết bởi {ann.resolved_by || 'Kiểm toán viên'}</span>
              </div>
            )}

            {/* Action Bar (>=48px touch targets) */}
            <div className="flex items-center justify-end space-x-2 mt-3 pt-2 border-t border-slate-800">
              {onResolveAnnotation && (
                <button
                  type="button"
                  data-testid="annotation-resolve-btn"
                  onClick={() => onResolveAnnotation(ann.annotation_id)}
                  className="min-h-[48px] px-3 py-2 bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 border border-emerald-600/40 rounded-lg text-xs font-medium flex items-center space-x-1.5 cursor-pointer transition-colors"
                >
                  <Check className="w-4 h-4" />
                  <span>{ann.resolved ? 'Mở lại' : 'Giải quyết'}</span>
                </button>
              )}
              {onDeleteAnnotation && (
                <button
                  type="button"
                  data-testid="annotation-delete-btn"
                  onClick={() => onDeleteAnnotation(ann.annotation_id)}
                  className="min-h-[48px] px-3 py-2 bg-rose-600/20 hover:bg-rose-600/30 text-rose-300 border border-rose-600/40 rounded-lg text-xs font-medium flex items-center space-x-1.5 cursor-pointer transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                  <span>Xóa</span>
                </button>
              )}
            </div>
          </div>
        );
      })()}

      {/* New Annotation Creation Prompt Dialog */}
      {pendingBox && (
        <div
          data-testid="annotation-create-dialog"
          className="absolute inset-0 bg-slate-950/50 backdrop-blur-[2px] z-50 flex items-center justify-center p-4 pointer-events-auto"
        >
          <div className="bg-slate-900 border border-slate-700 rounded-2xl p-5 shadow-2xl max-w-sm w-full space-y-4 text-slate-100 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center space-x-2 text-indigo-400">
              <Highlighter className="w-5 h-5" />
              <h3 className="font-semibold text-sm text-slate-100">Ghim ghi chú kiểm toán mới</h3>
            </div>

            <div>
              <label htmlFor="annotation-comment" className="block text-xs text-slate-400 mb-1">
                Nội dung ghi chú hoặc lưu ý kiểm toán
              </label>
              <textarea
                id="annotation-comment"
                data-testid="annotation-comment-input"
                rows={3}
                value={newComment}
                onChange={(e) => setNewComment(e.target.value)}
                placeholder="Nhập nhận xét kiểm toán cho vùng đã chọn..."
                className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-xs text-slate-100 focus:outline-none focus:border-indigo-500 transition-colors resize-none"
              />
            </div>

            <div className="flex items-center justify-end space-x-2 pt-1">
              <button
                type="button"
                data-testid="annotation-cancel-btn"
                onClick={handleCancelPendingAnnotation}
                className="min-h-[48px] px-4 py-2 text-slate-400 hover:text-slate-200 text-xs font-medium rounded-lg cursor-pointer"
              >
                Hủy
              </button>
              <button
                type="button"
                data-testid="annotation-save-btn"
                onClick={handleSavePendingAnnotation}
                disabled={!newComment.trim()}
                className="min-h-[48px] px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:hover:bg-indigo-600 text-white text-xs font-semibold rounded-lg flex items-center space-x-1.5 cursor-pointer transition-colors shadow-md"
              >
                <Plus className="w-4 h-4" />
                <span>Lưu ghi chú</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
