/**
 * File 4 of 4: PDF Viewer Canvas Component with 3 Mandatory UI States
 * Governed by 529 Engineering Standards (frontend-4file-and-resilient-ui & Rule 15)
 */
import { FC, useEffect } from 'react';
import { AlertCircle, FileText, RefreshCw } from 'lucide-react';
import { usePdfViewer } from '../../hooks/usePdfViewer.hook';
import type { RenderedPageSize } from '../../types/visual_rag.types';

interface PdfViewerProps {
  documentId: string;
  pageNumber: number;
  zoomLevel: number;
  onPageRendered?: (size: RenderedPageSize) => void;
}

export const PdfViewer: FC<PdfViewerProps> = ({
  documentId,
  pageNumber,
  zoomLevel,
  onPageRendered,
}) => {
  const { canvasRef, renderPage, loading, error, renderedSize, retry } = usePdfViewer(documentId);

  useEffect(() => {
    renderPage(pageNumber, zoomLevel);
  }, [pageNumber, zoomLevel, renderPage]);

  useEffect(() => {
    onPageRendered?.(renderedSize);
  }, [renderedSize, onPageRendered]);

  const displayWidth = Math.round(renderedSize.width * zoomLevel);
  const displayHeight = Math.round(renderedSize.height * zoomLevel);

  return (
    <div
      className="relative overflow-hidden border border-slate-700 bg-slate-900 rounded-sm shadow-2xl"
      role="presentation"
      data-testid="pdf-viewer-container"
      style={{
        width: `${displayWidth}px`,
        height: `${displayHeight}px`,
      }}
    >
      {/* 1. Loading Skeleton State */}
      {loading && (
        <div
          data-testid="pdf-viewer-skeleton"
          className="absolute inset-0 z-10 bg-slate-900/95 p-6 flex flex-col justify-between animate-pulse"
        >
          <div className="space-y-3">
            <div className="h-5 bg-slate-800 rounded w-2/3" />
            <div className="h-3 bg-slate-800 rounded w-1/3" />
          </div>
          <div className="space-y-3">
            <div className="h-32 bg-slate-800/80 rounded-lg" />
            <div className="h-24 bg-slate-800/60 rounded-lg" />
            <div className="h-24 bg-slate-800/60 rounded-lg" />
          </div>
          <div className="text-xs text-slate-400 text-center">
            Đang tải trang {pageNumber} tài liệu {documentId}...
          </div>
        </div>
      )}

      {/* 2. Error State with >=48px Retry */}
      {!loading && error && (
        <div
          data-testid="pdf-viewer-error"
          className="absolute inset-0 z-10 bg-slate-900/95 p-6 flex flex-col items-center justify-center text-center space-y-4"
        >
          <div className="w-12 h-12 rounded-full bg-rose-950/80 border border-rose-800/60 flex items-center justify-center text-rose-400">
            <AlertCircle className="w-6 h-6" />
          </div>
          <div className="space-y-1 max-w-xs">
            <h4 className="text-sm font-semibold text-rose-200">
              Không thể hiển thị trang {pageNumber}
            </h4>
            <p className="text-xs text-rose-300/90">{error}</p>
          </div>
          <button
            type="button"
            data-testid="pdf-viewer-retry-btn"
            onClick={() => retry(pageNumber, zoomLevel)}
            className="min-h-[48px] px-4 py-2 bg-rose-800 hover:bg-rose-700 text-white text-xs font-semibold rounded-lg flex items-center space-x-2 transition cursor-pointer"
          >
            <RefreshCw className="w-4 h-4" />
            <span>Thử lại tải trang</span>
          </button>
        </div>
      )}

      {/* 3. Empty State when no document selected */}
      {!loading && !error && !documentId && (
        <div
          data-testid="pdf-viewer-empty"
          className="absolute inset-0 z-10 bg-slate-900 p-6 flex flex-col items-center justify-center text-center space-y-3"
        >
          <FileText className="w-10 h-10 text-slate-500" />
          <p className="text-xs text-slate-400">
            Chưa chọn tài liệu PDF. Vui lòng chọn hoặc tải lên BCTC để xem trang gốc.
          </p>
        </div>
      )}

      <canvas ref={canvasRef} className="block bg-white" data-testid="pdf-viewer-canvas" />
    </div>
  );
};
