/**
 * Multi-Document Tabbed Split-Screen & Synchronized Page/Scroll PDF Viewer
 * Governed by Sprint 13 Task S13-06 (Issue #113) & 529 Engineering Standards:
 * - 3 UI States: Skeleton, Error with Retry, Actionable Empty State
 * - Kiosk Ergonomics: >= 48px interactive touch targets
 * - Rule 15: Zero raw emojis (Lucide React SVG icons only)
 */
import {
  type FC,
  useState,
  useEffect,
  useRef,
  useCallback,
} from 'react';
import {
  FileText,
  Columns2,
  Link2,
  Link2Off,
  X,
  Plus,
  ChevronLeft,
  ChevronRight,
  ZoomIn,
  ZoomOut,
  AlertCircle,
  RefreshCw,
  FolderOpen,
  Eye,
} from 'lucide-react';
import { PdfViewer } from './PdfViewer';
import { BoundingBoxOverlay } from './BoundingBoxOverlay';
import type { GroundedEvidenceDTO, RenderedPageSize } from '../../types/visual_rag.types';

export interface OpenPdfTab {
  documentId: string;
  title: string;
  totalPages?: number;
}

interface TabbedSplitViewerProps {
  openTabs: OpenPdfTab[];
  paneADocId: string;
  paneBDocId: string | null;
  activeEvidence?: GroundedEvidenceDTO | null;
  isLoading?: boolean;
  errorMessage?: string | null;
  defaultDualPane?: boolean;
  onSelectPaneADoc: (docId: string) => void;
  onSelectPaneBDoc: (docId: string) => void;
  onCloseTab?: (docId: string) => void;
  onOpenDocumentPicker?: () => void;
  onRetry?: () => void;
}

export const TabbedSplitViewer: FC<TabbedSplitViewerProps> = ({
  openTabs,
  paneADocId,
  paneBDocId,
  activeEvidence = null,
  isLoading = false,
  errorMessage = null,
  defaultDualPane = true,
  onSelectPaneADoc,
  onSelectPaneBDoc,
  onCloseTab,
  onOpenDocumentPicker,
  onRetry,
}) => {
  const [isDualPane, setIsDualPane] = useState<boolean>(defaultDualPane);
  const [isSyncEnabled, setIsSyncEnabled] = useState<boolean>(true);
  const [activePaneTarget, setActivePaneTarget] = useState<'A' | 'B'>('A');

  const [pageA, setPageA] = useState<number>(1);
  const [pageB, setPageB] = useState<number>(1);
  const [zoomA, setZoomA] = useState<number>(1.0);
  const [zoomB, setZoomB] = useState<number>(1.0);

  const [sizeA, setSizeA] = useState<RenderedPageSize>({ width: 560, height: 792 });
  const [sizeB, setSizeB] = useState<RenderedPageSize>({ width: 560, height: 792 });

  const scrollRefA = useRef<HTMLDivElement | null>(null);
  const scrollRefB = useRef<HTMLDivElement | null>(null);
  const isSyncingScrollRef = useRef<boolean>(false);

  const tabA = openTabs.find((t) => t.documentId === paneADocId) || openTabs[0];
  const resolvedPaneBId =
    paneBDocId ||
    openTabs.find((t) => t.documentId !== (tabA?.documentId || ''))?.documentId ||
    tabA?.documentId ||
    '';
  const tabB = openTabs.find((t) => t.documentId === resolvedPaneBId) || tabA;

  const totalPagesA = Math.max(1, tabA?.totalPages || 10);
  const totalPagesB = Math.max(1, tabB?.totalPages || 10);

  // Sync active evidence page to the matching pane
  useEffect(() => {
    if (!activeEvidence?.page_number) return;
    const evDocId = activeEvidence.document_id;
    if (evDocId && evDocId === resolvedPaneBId && isDualPane) {
      setPageB(activeEvidence.page_number);
    } else {
      setPageA(activeEvidence.page_number);
      if (isSyncEnabled && isDualPane) {
        setPageB(Math.min(totalPagesB, activeEvidence.page_number));
      }
    }
  }, [activeEvidence, resolvedPaneBId, isDualPane, isSyncEnabled, totalPagesB]);

  const handlePageChangeA = useCallback(
    (nextPage: number) => {
      const clampedA = Math.max(1, Math.min(totalPagesA, nextPage));
      setPageA(clampedA);
      if (isSyncEnabled && isDualPane) {
        setPageB(Math.max(1, Math.min(totalPagesB, clampedA)));
      }
    },
    [totalPagesA, totalPagesB, isSyncEnabled, isDualPane]
  );

  const handlePageChangeB = useCallback(
    (nextPage: number) => {
      const clampedB = Math.max(1, Math.min(totalPagesB, nextPage));
      setPageB(clampedB);
      if (isSyncEnabled && isDualPane) {
        setPageA(Math.max(1, Math.min(totalPagesA, clampedB)));
      }
    },
    [totalPagesA, totalPagesB, isSyncEnabled, isDualPane]
  );

  const handleScrollSync = useCallback(
    (source: 'A' | 'B') => {
      if (!isSyncEnabled || !isDualPane || isSyncingScrollRef.current) return;
      const srcEl = source === 'A' ? scrollRefA.current : scrollRefB.current;
      const dstEl = source === 'A' ? scrollRefB.current : scrollRefA.current;
      if (!srcEl || !dstEl) return;

      const srcMax = Math.max(1, srcEl.scrollHeight - srcEl.clientHeight);
      const dstMax = Math.max(1, dstEl.scrollHeight - dstEl.clientHeight);
      const ratio = srcEl.scrollTop / srcMax;

      isSyncingScrollRef.current = true;
      dstEl.scrollTop = Math.round(ratio * dstMax);
      requestAnimationFrame(() => {
        isSyncingScrollRef.current = false;
      });
    },
    [isSyncEnabled, isDualPane]
  );

  const handleTabClick = (docId: string) => {
    if (!isDualPane || activePaneTarget === 'A') {
      onSelectPaneADoc(docId);
    } else {
      onSelectPaneBDoc(docId);
    }
  };

  // 1. Loading Skeleton State
  if (isLoading) {
    return (
      <div
        data-testid="tabbed-split-skeleton"
        className="h-full w-full bg-slate-900 p-4 flex flex-col gap-4 animate-pulse"
      >
        <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
          <div className="h-12 w-36 bg-slate-800 rounded-lg" />
          <div className="h-12 w-36 bg-slate-800 rounded-lg" />
          <div className="ml-auto h-12 w-32 bg-slate-800 rounded-lg" />
        </div>
        <div className="flex-1 grid grid-cols-2 gap-4">
          <div className="bg-slate-800/70 rounded-xl" />
          <div className="bg-slate-800/70 rounded-xl" />
        </div>
      </div>
    );
  }

  // 2. Error State with >=48px Retry
  if (errorMessage) {
    return (
      <div
        data-testid="tabbed-split-error"
        className="h-full w-full bg-slate-900 p-6 flex flex-col items-center justify-center text-center space-y-4"
      >
        <div className="w-12 h-12 rounded-full bg-rose-950/80 border border-rose-800/60 flex items-center justify-center text-rose-400">
          <AlertCircle className="w-6 h-6" />
        </div>
        <div className="space-y-1 max-w-sm">
          <h3 className="text-sm font-semibold text-rose-200">
            Không thể tải chế độ xem đa tài liệu
          </h3>
          <p className="text-xs text-rose-300/90">{errorMessage}</p>
        </div>
        {onRetry && (
          <button
            type="button"
            data-testid="tabbed-split-retry-btn"
            onClick={onRetry}
            className="min-h-[48px] px-4 py-2 bg-rose-800 hover:bg-rose-700 text-white text-xs font-semibold rounded-lg flex items-center gap-2 transition cursor-pointer"
          >
            <RefreshCw className="w-4 h-4" />
            <span>Thử lại</span>
          </button>
        )}
      </div>
    );
  }

  // 3. Actionable Empty State
  if (openTabs.length === 0 || !tabA) {
    return (
      <div
        data-testid="tabbed-split-empty"
        className="h-full w-full bg-slate-900 p-6 flex flex-col items-center justify-center text-center space-y-4"
      >
        <FileText className="w-12 h-12 text-slate-500" />
        <div className="space-y-1 max-w-sm">
          <h3 className="text-sm font-semibold text-slate-200">
            Chưa có tài liệu nào được mở
          </h3>
          <p className="text-xs text-slate-400">
            Mở hoặc tải lên ít nhất một báo cáo tài chính PDF để bắt đầu đối chiếu song song.
          </p>
        </div>
        {onOpenDocumentPicker && (
          <button
            type="button"
            data-testid="tabbed-split-open-picker-btn"
            onClick={onOpenDocumentPicker}
            className="min-h-[48px] px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-lg flex items-center gap-2 transition cursor-pointer"
          >
            <FolderOpen className="w-4 h-4" />
            <span>Chọn tài liệu PDF</span>
          </button>
        )}
      </div>
    );
  }

  return (
    <div
      data-testid="tabbed-split-viewer"
      className="h-full w-full flex flex-col bg-slate-900 overflow-hidden"
    >
      {/* Top Multi-Tab Bar & Sync Controls */}
      <div className="border-b border-slate-800 bg-slate-900/95 px-3 py-2 flex items-center gap-2 overflow-x-auto flex-shrink-0">
        {/* Document Tabs */}
        <div className="flex items-center gap-1.5 min-w-0 flex-1 overflow-x-auto">
          {openTabs.map((tab) => {
            const isPaneA = tab.documentId === tabA.documentId;
            const isPaneB = isDualPane && tab.documentId === tabB?.documentId;
            const isActive = isPaneA || isPaneB;
            return (
              <div
                key={tab.documentId}
                className={`flex items-center rounded-lg border transition flex-shrink-0 ${
                  isPaneA
                    ? 'bg-sky-950/70 border-sky-500/60 text-sky-200'
                    : isPaneB
                    ? 'bg-indigo-950/70 border-indigo-500/60 text-indigo-200'
                    : 'bg-slate-800/70 border-slate-700/70 text-slate-300 hover:bg-slate-800'
                }`}
              >
                <button
                  type="button"
                  data-testid={`pdf-tab-${tab.documentId}`}
                  onClick={() => handleTabClick(tab.documentId)}
                  className="min-h-[48px] px-3 py-1.5 text-xs font-medium flex items-center gap-2 cursor-pointer"
                >
                  <FileText className="w-3.5 h-3.5 flex-shrink-0" />
                  <span className="truncate max-w-[140px]">{tab.title || tab.documentId}</span>
                  {isPaneA && (
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-sky-800/80 text-sky-100">
                      A
                    </span>
                  )}
                  {isPaneB && (
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-indigo-800/80 text-indigo-100">
                      B
                    </span>
                  )}
                  {!isActive && <span className="sr-only">Mở tab</span>}
                </button>
                {onCloseTab && openTabs.length > 1 && (
                  <button
                    type="button"
                    data-testid={`close-pdf-tab-${tab.documentId}`}
                    onClick={() => onCloseTab(tab.documentId)}
                    className="min-h-[48px] min-w-[48px] flex items-center justify-center text-slate-400 hover:text-slate-100 transition cursor-pointer"
                    title={`Đóng ${tab.documentId}`}
                    aria-label={`Đóng ${tab.documentId}`}
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            );
          })}

          {onOpenDocumentPicker && (
            <button
              type="button"
              data-testid="tabbed-split-add-doc-btn"
              onClick={onOpenDocumentPicker}
              className="min-h-[48px] min-w-[48px] px-2.5 bg-slate-800/70 hover:bg-slate-800 border border-slate-700 rounded-lg text-slate-300 flex items-center justify-center transition cursor-pointer flex-shrink-0"
              title="Mở thêm tài liệu PDF"
              aria-label="Mở thêm tài liệu PDF"
            >
              <Plus className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* Pane Assignment & Sync Controls */}
        <div className="flex items-center gap-1.5 flex-shrink-0">
          {isDualPane && (
            <button
              type="button"
              data-testid="sync-page-toggle-btn"
              onClick={() => setIsSyncEnabled((v) => !v)}
              aria-pressed={isSyncEnabled}
              className={`min-h-[48px] px-3 py-1.5 rounded-lg border text-xs font-semibold flex items-center gap-1.5 transition cursor-pointer ${
                isSyncEnabled
                  ? 'bg-emerald-950/80 border-emerald-600/70 text-emerald-300'
                  : 'bg-slate-800 border-slate-700 text-slate-400 hover:text-slate-200'
              }`}
              title="Đồng bộ trang và cuộn giữa 2 khung PDF"
            >
              {isSyncEnabled ? <Link2 className="w-4 h-4" /> : <Link2Off className="w-4 h-4" />}
              <span>Đồng bộ trang</span>
            </button>
          )}

          <button
            type="button"
            data-testid="dual-pane-toggle-btn"
            onClick={() => setIsDualPane((v) => !v)}
            aria-pressed={isDualPane}
            className={`min-h-[48px] px-3 py-1.5 rounded-lg border text-xs font-semibold flex items-center gap-1.5 transition cursor-pointer ${
              isDualPane
                ? 'bg-indigo-600 border-indigo-500 text-white'
                : 'bg-slate-800 border-slate-700 text-slate-300 hover:bg-slate-700'
            }`}
            title="Chuyển đổi 1 khung / 2 khung song song"
          >
            <Columns2 className="w-4 h-4" />
            <span>{isDualPane ? '2 Khung' : '1 Khung'}</span>
          </button>
        </div>
      </div>

      {/* Dual or Single PDF Pane Container */}
      <div
        className={`flex-1 min-h-0 grid ${
          isDualPane ? 'grid-cols-1 xl:grid-cols-2 divide-y xl:divide-y-0 xl:divide-x divide-slate-800' : 'grid-cols-1'
        } overflow-hidden`}
      >
        {/* PANE A */}
        <div
          data-testid="pdf-pane-a"
          onClick={() => setActivePaneTarget('A')}
          className={`flex flex-col min-h-0 overflow-hidden ${
            isDualPane && activePaneTarget === 'A' ? 'ring-1 ring-inset ring-sky-500/40' : ''
          }`}
        >
          <PaneToolbar
            paneLabel="Pane A"
            documentId={tabA.documentId}
            currentPage={pageA}
            totalPages={totalPagesA}
            zoomLevel={zoomA}
            testPrefix="pane-a"
            onPrevPage={() => handlePageChangeA(pageA - 1)}
            onNextPage={() => handlePageChangeA(pageA + 1)}
            onZoomOut={() => setZoomA((z) => Math.max(0.6, Math.round((z - 0.1) * 10) / 10))}
            onZoomIn={() => setZoomA((z) => Math.min(1.8, Math.round((z + 0.1) * 10) / 10))}
            onZoomReset={() => setZoomA(1.0)}
          />
          {activeEvidence &&
            (!activeEvidence.document_id || activeEvidence.document_id === tabA.documentId) && (
              <div className="border-b border-slate-800/80 bg-sky-950/30 px-3 py-1.5 flex items-center gap-2 text-xs text-sky-300 flex-shrink-0">
                <Eye className="w-3.5 h-3.5 flex-shrink-0" />
                <span className="truncate">
                  Trang {activeEvidence.page_number}: {activeEvidence.label}
                </span>
              </div>
            )}
          <div
            ref={scrollRefA}
            data-testid="pane-a-scroll"
            onScroll={() => handleScrollSync('A')}
            className="flex-1 overflow-auto p-4 flex justify-center items-start bg-slate-950/50"
          >
            <div className="relative shadow-2xl overflow-visible flex-shrink-0">
              <PdfViewer
                documentId={tabA.documentId}
                pageNumber={pageA}
                zoomLevel={zoomA}
                onPageRendered={setSizeA}
              />
              <BoundingBoxOverlay
                evidence={
                  activeEvidence &&
                  activeEvidence.page_number === pageA &&
                  (!activeEvidence.document_id || activeEvidence.document_id === tabA.documentId)
                    ? activeEvidence
                    : null
                }
                renderedWidth={sizeA.width}
                renderedHeight={sizeA.height}
                zoomLevel={zoomA}
              />
            </div>
          </div>
        </div>

        {/* PANE B */}
        {isDualPane && tabB && (
          <div
            data-testid="pdf-pane-b"
            onClick={() => setActivePaneTarget('B')}
            className={`flex flex-col min-h-0 overflow-hidden ${
              activePaneTarget === 'B' ? 'ring-1 ring-inset ring-indigo-500/40' : ''
            }`}
          >
            <PaneToolbar
              paneLabel="Pane B"
              documentId={tabB.documentId}
              currentPage={pageB}
              totalPages={totalPagesB}
              zoomLevel={zoomB}
              testPrefix="pane-b"
              onPrevPage={() => handlePageChangeB(pageB - 1)}
              onNextPage={() => handlePageChangeB(pageB + 1)}
              onZoomOut={() => setZoomB((z) => Math.max(0.6, Math.round((z - 0.1) * 10) / 10))}
              onZoomIn={() => setZoomB((z) => Math.min(1.8, Math.round((z + 0.1) * 10) / 10))}
              onZoomReset={() => setZoomB(1.0)}
            />
            {activeEvidence && activeEvidence.document_id === tabB.documentId && (
              <div className="border-b border-slate-800/80 bg-indigo-950/30 px-3 py-1.5 flex items-center gap-2 text-xs text-indigo-300 flex-shrink-0">
                <Eye className="w-3.5 h-3.5 flex-shrink-0" />
                <span className="truncate">
                  Trang {activeEvidence.page_number}: {activeEvidence.label}
                </span>
              </div>
            )}
            <div
              ref={scrollRefB}
              data-testid="pane-b-scroll"
              onScroll={() => handleScrollSync('B')}
              className="flex-1 overflow-auto p-4 flex justify-center items-start bg-slate-950/50"
            >
              <div className="relative shadow-2xl overflow-visible flex-shrink-0">
                <PdfViewer
                  documentId={tabB.documentId}
                  pageNumber={pageB}
                  zoomLevel={zoomB}
                  onPageRendered={setSizeB}
                />
                <BoundingBoxOverlay
                  evidence={
                    activeEvidence &&
                    activeEvidence.page_number === pageB &&
                    activeEvidence.document_id === tabB.documentId
                      ? activeEvidence
                      : null
                  }
                  renderedWidth={sizeB.width}
                  renderedHeight={sizeB.height}
                  zoomLevel={zoomB}
                />
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

interface PaneToolbarProps {
  paneLabel: string;
  documentId: string;
  currentPage: number;
  totalPages: number;
  zoomLevel: number;
  testPrefix: string;
  onPrevPage: () => void;
  onNextPage: () => void;
  onZoomOut: () => void;
  onZoomIn: () => void;
  onZoomReset: () => void;
}

const PaneToolbar: FC<PaneToolbarProps> = ({
  paneLabel,
  documentId,
  currentPage,
  totalPages,
  zoomLevel,
  testPrefix,
  onPrevPage,
  onNextPage,
  onZoomOut,
  onZoomIn,
  onZoomReset,
}) => (
  <div className="border-b border-slate-800 bg-slate-900/80 px-3 py-1.5 flex items-center justify-between gap-2 flex-shrink-0">
    <div className="flex items-center gap-1.5 min-w-0">
      <span className="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700 flex-shrink-0">
        {paneLabel}
      </span>
      <span className="text-xs font-semibold text-slate-200 truncate">Tài liệu: {documentId}</span>
    </div>
    <div className="flex items-center gap-1 flex-shrink-0">
      <button
        type="button"
        data-testid={`${testPrefix}-prev-page`}
        onClick={onPrevPage}
        disabled={currentPage <= 1}
        className="min-h-[48px] min-w-[48px] hover:bg-slate-800 disabled:opacity-40 text-slate-300 rounded-lg flex items-center justify-center transition cursor-pointer"
        aria-label={`${paneLabel} trang trước`}
      >
        <ChevronLeft className="w-4 h-4" />
      </button>
      <span
        data-testid={`${testPrefix}-page-indicator`}
        className="text-[11px] font-mono text-slate-300 px-1 whitespace-nowrap"
      >
        {currentPage}/{totalPages}
      </span>
      <button
        type="button"
        data-testid={`${testPrefix}-next-page`}
        onClick={onNextPage}
        disabled={currentPage >= totalPages}
        className="min-h-[48px] min-w-[48px] hover:bg-slate-800 disabled:opacity-40 text-slate-300 rounded-lg flex items-center justify-center transition cursor-pointer"
        aria-label={`${paneLabel} trang sau`}
      >
        <ChevronRight className="w-4 h-4" />
      </button>
      <button
        type="button"
        data-testid={`${testPrefix}-zoom-out`}
        onClick={onZoomOut}
        className="min-h-[48px] min-w-[48px] hover:bg-slate-800 text-slate-300 rounded-lg flex items-center justify-center transition cursor-pointer"
        aria-label={`${paneLabel} thu nhỏ`}
      >
        <ZoomOut className="w-3.5 h-3.5" />
      </button>
      <button
        type="button"
        data-testid={`${testPrefix}-zoom-reset`}
        onClick={onZoomReset}
        className="min-h-[48px] px-2 hover:bg-slate-800 text-slate-300 rounded-lg text-[11px] font-mono flex items-center justify-center transition cursor-pointer"
      >
        {Math.round(zoomLevel * 100)}%
      </button>
      <button
        type="button"
        data-testid={`${testPrefix}-zoom-in`}
        onClick={onZoomIn}
        className="min-h-[48px] min-w-[48px] hover:bg-slate-800 text-slate-300 rounded-lg flex items-center justify-center transition cursor-pointer"
        aria-label={`${paneLabel} phóng to`}
      >
        <ZoomIn className="w-3.5 h-3.5" />
      </button>
    </div>
  </div>
);
