/**
 * File 4 of 4: SplitView Desktop Component with 3 Mandatory UI States
 * Governed by 529 Engineering Standards:
 * - 3 States: Skeleton, Error with Retry, Empty State with Action
 * - Kiosk Ergonomics: >= 48px interactive target size
 * - Multi-Document Comparative Visual RAG (Sprint 7 Task S7-02)
 */

import { useState, type FormEvent, type FC } from 'react';
import { useVisualRag } from '../../hooks/useVisualRag.hook';
import { useSettings } from '../../hooks/useSettings.hook';
import { useBridgeServer } from '../../hooks/useBridgeServer';
import { useDaemonLifecycle } from '../../hooks/useDaemonLifecycle';
import { ResizableSplitView } from './ResizableSplitView';
import { BoundingBoxOverlay } from '../pdf/BoundingBoxOverlay';
import { AnnotationCanvas } from '../pdf/AnnotationCanvas';
import { PdfViewer } from '../pdf/PdfViewer';
import { SettingsDialog } from '../settings/SettingsDialog';
import { FootnoteChip } from '../chat/FootnoteChip';
import type { AuditAnnotationDTO } from '../../types/session_sync.types';
import {
  FileText,
  Send,
  RefreshCw,
  AlertCircle,
  Eye,
  Sparkles,
  ExternalLink,
  ZoomIn,
  ZoomOut,
  BarChart3,
  PieChart,
  Settings,
  GitCompare,
  TrendingUp,
  Layers,
  Highlighter,
} from 'lucide-react';

interface SplitViewProps {
  documentId: string;
  documentTitle: string;
}

export const SplitView: FC<SplitViewProps> = ({ documentId, documentTitle }) => {
  const [inputText, setInputText] = useState('');
  const [zoomLevel, setZoomLevel] = useState<number>(1.0);
  const [isSettingsOpen, setIsSettingsOpen] = useState<boolean>(false);
  const [modeTab, setModeTab] = useState<'single' | 'comparative'>('single');
  const [selectedDocIds] = useState<string[]>(['VNM_2022_COMP', 'VNM_2023_COMP']);
  const [isDrawingEnabled, setIsDrawingEnabled] = useState<boolean>(false);
  const [annotations, setAnnotations] = useState<AuditAnnotationDTO[]>([]);

  const {
    state,
    error,
    history,
    comparativeHistory,
    activeEvidence,
    streamingAnswer,
    ask,
    askComparative,
    focusEvidence,
    focusFootnote,
    clearError,
  } = useVisualRag(documentId);

  const { inferenceMode } = useSettings();
  const daemon = useDaemonLifecycle();

  useBridgeServer((citationId) => {
    console.log(`Navigation requested for citation: ${citationId}`);
    const allEvidences = [
      ...history.flatMap((h) => h.evidences),
      ...comparativeHistory.flatMap((c) => c.evidences),
    ];
    const evidence = allEvidences.find((e) => e.label === citationId);
    if (evidence) {
      focusEvidence(evidence);
    }
  });

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!inputText.trim()) return;

    if (modeTab === 'comparative') {
      askComparative(selectedDocIds, inputText, inferenceMode);
    } else {
      ask(inputText, inferenceMode);
    }
    setInputText('');
  };

  const handleZoomIn = () => setZoomLevel((z) => Math.min(1.8, Math.round((z + 0.1) * 10) / 10));
  const handleZoomOut = () => setZoomLevel((z) => Math.max(0.6, Math.round((z - 0.1) * 10) / 10));
  const handleZoomReset = () => setZoomLevel(1.0);

  const leftPaneContent = (
    <div className="h-full w-full flex flex-col relative bg-slate-900 border-r border-slate-800 overflow-hidden">
      <header className="h-14 border-b border-slate-800 px-4 flex items-center justify-between gap-2 flex-shrink-0">
        <div className="flex items-center space-x-2 min-w-0">
          <FileText className="w-5 h-5 text-indigo-400 flex-shrink-0" />
          <span className="font-semibold text-sm truncate max-w-[200px] 2xl:max-w-md">
            {activeEvidence?.document_id ? `${activeEvidence.document_id} (Trích dẫn)` : documentTitle}
          </span>
        </div>

        <div className="flex items-center space-x-3 flex-shrink-0">
          {activeEvidence && (
            <div className="hidden sm:flex items-center space-x-2 bg-indigo-950/70 border border-indigo-700/50 px-2.5 py-1 rounded text-xs text-indigo-300 truncate max-w-xs">
              <Eye className="w-3.5 h-3.5 text-indigo-400 flex-shrink-0" />
              <span className="truncate">
                {activeEvidence.document_id ? `[${activeEvidence.document_id}] ` : ''}Trang {activeEvidence.page_number}: {activeEvidence.label}
              </span>
            </div>
          )}

          {/* Interactive Zoom Controls */}
          <div className="flex items-center space-x-1 bg-slate-800/90 border border-slate-700 rounded-lg p-0.5 shadow-sm">
            <button
              type="button"
              onClick={handleZoomOut}
              className="p-1 hover:bg-slate-700 text-slate-300 rounded text-xs transition"
              title="Thu nhỏ (Zoom Out)"
              aria-label="Thu nhỏ"
            >
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onClick={handleZoomReset}
              className="px-1.5 py-0.5 hover:bg-slate-700 text-slate-300 rounded text-[11px] font-mono transition"
              title="Đặt lại 100%"
            >
              {Math.round(zoomLevel * 100)}%
            </button>
            <button
              type="button"
              onClick={handleZoomIn}
              className="p-1 hover:bg-slate-700 text-slate-300 rounded text-xs transition"
              title="Phóng to (Zoom In)"
              aria-label="Phóng to"
            >
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
          </div>

          <button
            type="button"
            onClick={() => setIsDrawingEnabled((v) => !v)}
            data-testid="toggle-annotation-mode-btn"
            className={`min-h-[48px] px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition-colors cursor-pointer ${
              isDrawingEnabled
                ? 'bg-indigo-600 text-white shadow-md'
                : 'bg-slate-800 hover:bg-slate-700 text-slate-300'
            }`}
            title="Bật/Tắt chế độ ghi chú kiểm toán"
          >
            <Highlighter className="w-3.5 h-3.5" />
            <span>Ghi chú</span>
          </button>
        </div>
      </header>

      <div className="flex-1 relative overflow-auto p-6 flex justify-center items-start sm:items-center bg-slate-950/50">
        <div className="relative shadow-2xl overflow-hidden flex-shrink-0 my-auto">
          <PdfViewer
            documentId={activeEvidence?.document_id || documentId}
            pageNumber={activeEvidence?.page_number || 1}
            zoomLevel={zoomLevel}
          />
          <BoundingBoxOverlay
            evidence={activeEvidence}
            renderedWidth={500}
            renderedHeight={700}
            zoomLevel={zoomLevel}
          />
          <AnnotationCanvas
            documentId={activeEvidence?.document_id || documentId}
            pageNumber={activeEvidence?.page_number || 1}
            renderedWidth={500}
            renderedHeight={700}
            zoomLevel={zoomLevel}
            annotations={annotations}
            isDrawingEnabled={isDrawingEnabled}
            onAddAnnotation={(newAnn) => {
              const created: AuditAnnotationDTO = {
                ...newAnn,
                annotation_id: `ann-${Date.now()}`,
                created_at: Math.floor(Date.now() / 1000),
                resolved: false,
              };
              setAnnotations((prev) => [...prev, created]);
            }}
            onResolveAnnotation={(id) => {
              setAnnotations((prev) =>
                prev.map((a) =>
                  a.annotation_id === id
                    ? { ...a, resolved: !a.resolved, resolved_by: 'Kiểm toán viên' }
                    : a
                )
              );
            }}
            onDeleteAnnotation={(id) => {
              setAnnotations((prev) => prev.filter((a) => a.annotation_id !== id));
            }}
          />
        </div>
      </div>
    </div>
  );

  const rightPaneContent = (
    <div className="h-full w-full flex flex-col bg-slate-900/60 overflow-hidden">
      <header className="h-14 border-b border-slate-800 px-6 flex items-center justify-between flex-shrink-0">
        <div className="flex items-center space-x-2">
          <Sparkles className="w-5 h-5 text-indigo-400" />
          <h1 className="font-semibold text-sm">FinTrace AI Copilot</h1>
        </div>
        <div className="flex items-center space-x-2">
          {/* Daemon Lifecycle Status Badge */}
          <div
            data-testid="daemon-status-badge"
            className="flex items-center space-x-1.5 px-2.5 py-1 rounded-full text-xs font-mono bg-slate-800/80 border border-slate-700"
            title={daemon.error || (daemon.status === 'online' ? `Daemon online on port ${daemon.port}` : 'Connecting to daemon...')}
          >
            <span
              className={`w-2 h-2 rounded-full ${
                daemon.status === 'online'
                  ? 'bg-emerald-400'
                  : daemon.status === 'connecting'
                  ? 'bg-amber-400 animate-pulse'
                  : 'bg-rose-400'
              }`}
            />
            <span className="text-slate-300 text-[11px]">
              {daemon.status === 'online'
                ? `:8765${daemon.latencyMs !== null ? ` (${daemon.latencyMs}ms)` : ''}`
                : daemon.status === 'connecting'
                ? 'Connecting...'
                : 'Offline'}
            </span>
            {daemon.status === 'offline' && (
              <button
                type="button"
                onClick={daemon.retry}
                className="min-h-[48px] px-2 text-indigo-400 hover:text-indigo-300 underline text-[11px] flex items-center"
                title="Thử kết nối lại"
                aria-label="Thử kết nối lại daemon"
              >
                <RefreshCw className="w-3 h-3 mr-0.5" />
                Retry
              </button>
            )}
          </div>

          <button
            type="button"
            onClick={() => setIsSettingsOpen(true)}
            className="min-h-[48px] min-w-[48px] p-2 hover:bg-slate-800 text-slate-400 hover:text-slate-200 rounded-lg transition flex items-center justify-center"
            title="Cài đặt mô hình AI"
            aria-label="Cài đặt mô hình AI"
          >
            <Settings className="w-4 h-4" />
          </button>
          <span className="text-xs text-slate-400 bg-slate-800 px-2.5 py-1 rounded-full border border-slate-700">
            {inferenceMode === 'local' ? 'MLX Local' : inferenceMode === 'cloud' ? 'Cloud BYOK' : 'Auto'}
          </span>
        </div>
      </header>

      {/* Mode Selector Tabs (Single vs Comparative YoY) */}
      <div className="flex border-b border-slate-800 bg-slate-900/80 px-4 py-2 gap-2 flex-shrink-0">
        <button
          type="button"
          data-testid="tab-single-query"
          onClick={() => setModeTab('single')}
          className={`min-h-[48px] px-3.5 py-2 rounded-lg text-xs font-semibold flex items-center gap-2 transition ${
            modeTab === 'single'
              ? 'bg-indigo-600 text-white shadow-sm'
              : 'bg-slate-800/80 text-slate-400 hover:text-slate-200 hover:bg-slate-800'
          }`}
        >
          <FileText className="w-4 h-4" />
          <span>Truy vấn đơn lẻ</span>
        </button>
        <button
          type="button"
          data-testid="tab-comparative-query"
          onClick={() => setModeTab('comparative')}
          className={`min-h-[48px] px-3.5 py-2 rounded-lg text-xs font-semibold flex items-center gap-2 transition ${
            modeTab === 'comparative'
              ? 'bg-indigo-600 text-white shadow-sm'
              : 'bg-slate-800/80 text-slate-400 hover:text-slate-200 hover:bg-slate-800'
          }`}
        >
          <GitCompare className="w-4 h-4" />
          <span>So sánh đa BCTC (YoY)</span>
        </button>
      </div>

      {/* Comparative Document Selection Chips (When in Comparative mode) */}
      {modeTab === 'comparative' && (
        <div className="bg-slate-950/60 border-b border-slate-800/80 px-4 py-2.5 flex items-center justify-between gap-2 flex-shrink-0">
          <div className="flex items-center gap-2 overflow-x-auto text-xs">
            <span className="text-slate-400 font-medium text-[11px] uppercase tracking-wider shrink-0">
              Đối chiếu:
            </span>
            {selectedDocIds.map((id, i) => (
              <span
                key={id}
                className={`px-2.5 py-1 rounded-full text-[11px] font-mono border flex items-center gap-1 shrink-0 ${
                  i === 0
                    ? 'bg-sky-950/80 text-sky-300 border-sky-700/60'
                    : 'bg-indigo-950/80 text-indigo-300 border-indigo-700/60'
                }`}
              >
                <Layers className="w-3 h-3" />
                {id}
              </span>
            ))}
          </div>
          <span className="text-[10px] text-emerald-400 font-medium bg-emerald-950/60 border border-emerald-800/60 px-2 py-0.5 rounded-full shrink-0">
            2 Tài liệu
          </span>
        </div>
      )}

      {/* Message Thread Area with 3 UI States */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {/* STATE 1: EMPTY STATE */}
        {((modeTab === 'single' && history.length === 0) ||
          (modeTab === 'comparative' && comparativeHistory.length === 0)) &&
          state !== 'loading' &&
          state !== 'error' && (
            <div className="h-full flex flex-col items-center justify-center text-center p-8 space-y-4 text-slate-400">
              <div className="w-16 h-16 rounded-full bg-indigo-950/80 border border-indigo-700/40 flex items-center justify-center text-indigo-400">
                {modeTab === 'comparative' ? (
                  <GitCompare className="w-8 h-8" />
                ) : (
                  <FileText className="w-8 h-8" />
                )}
              </div>
              <div className="space-y-1">
                <h3 className="text-base font-semibold text-slate-200">
                  {modeTab === 'comparative'
                    ? 'Chế độ so sánh đa kỳ BCTC (YoY)'
                    : 'Sẵn sàng phân tích Báo cáo tài chính'}
                </h3>
                <p className="text-xs max-w-sm">
                  {modeTab === 'comparative'
                    ? 'Đối chiếu số liệu, doanh thu, lợi nhuận và biên lãi gộp giữa nhiều năm tài chính cùng lúc.'
                    : 'Đặt câu hỏi về bất kỳ biểu đồ tăng trưởng, biên lợi nhuận, hoặc bảng số liệu phức tạp trong tài liệu.'}
                </p>
              </div>

              <div className="flex flex-col gap-2 w-full max-w-sm pt-2">
                {modeTab === 'comparative' ? (
                  <>
                    <button
                      type="button"
                      data-testid="btn-suggest-comparative-1"
                      onClick={() =>
                        askComparative(
                          selectedDocIds,
                          'So sánh cơ cấu doanh thu nội địa và xuất khẩu giữa hai năm tài chính',
                          inferenceMode
                        )
                      }
                      className="min-h-[48px] px-4 py-2 bg-slate-800 hover:bg-slate-700 text-xs rounded border border-slate-700 text-left transition flex items-center space-x-2.5"
                    >
                      <TrendingUp className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                      <span>So sánh cơ cấu doanh thu & tăng trưởng 2 năm</span>
                    </button>
                    <button
                      type="button"
                      data-testid="btn-suggest-comparative-2"
                      onClick={() =>
                        askComparative(
                          selectedDocIds,
                          'Đối chiếu tổng tài sản và số dư tiền mặt giữa hai kỳ BCTC',
                          inferenceMode
                        )
                      }
                      className="min-h-[48px] px-4 py-2 bg-slate-800 hover:bg-slate-700 text-xs rounded border border-slate-700 text-left transition flex items-center space-x-2.5"
                    >
                      <BarChart3 className="w-4 h-4 text-indigo-400 flex-shrink-0" />
                      <span>Đối chiếu số dư tiền mặt & tổng tài sản</span>
                    </button>
                  </>
                ) : (
                  <>
                    <button
                      type="button"
                      onClick={() => ask('Biên lợi nhuận gộp qua biểu đồ các năm thay đổi như thế nào?')}
                      className="min-h-[48px] px-4 py-2 bg-slate-800 hover:bg-slate-700 text-xs rounded border border-slate-700 text-left transition flex items-center space-x-2.5"
                    >
                      <BarChart3 className="w-4 h-4 text-indigo-400 flex-shrink-0" />
                      <span>Phân tích biên lợi nhuận gộp qua biểu đồ</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => ask('Cơ cấu doanh thu theo mảng kinh doanh năm 2023?')}
                      className="min-h-[48px] px-4 py-2 bg-slate-800 hover:bg-slate-700 text-xs rounded border border-slate-700 text-left transition flex items-center space-x-2.5"
                    >
                      <PieChart className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                      <span>Cơ cấu doanh thu theo từng mảng</span>
                    </button>
                  </>
                )}
              </div>
            </div>
          )}

        {/* SINGLE MODE HISTORY */}
        {modeTab === 'single' &&
          history.map((msg, idx) => (
            <div key={idx} className="space-y-3">
              <div className="flex justify-end">
                <div className="bg-indigo-600 text-white text-sm px-4 py-2.5 rounded-2xl rounded-tr-none max-w-xl 2xl:max-w-2xl shadow">
                  {msg.query_text}
                </div>
              </div>

              <div className="flex justify-start">
                <div className="bg-slate-800/90 border border-slate-700 text-slate-200 text-sm p-4 rounded-2xl rounded-tl-none max-w-2xl 2xl:max-w-4xl space-y-3 shadow-lg">
                  <p className="leading-relaxed whitespace-pre-wrap">{msg.answer}</p>

                  {/* Audit Trail Evidence Chips */}
                  {msg.evidences.length > 0 && (
                    <div className="pt-2 border-t border-slate-700/80">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                          Bằng chứng kiểm toán (Visual Grounding):
                        </span>
                        {new Set(msg.evidences.map((e) => e.page_number)).size > 1 && (
                          <span className="text-[10px] font-medium bg-indigo-900/60 border border-indigo-700/60 text-indigo-300 px-2 py-0.5 rounded-full">
                            Liên kết đa trang ({new Set(msg.evidences.map((e) => e.page_number)).size} trang)
                          </span>
                        )}
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {msg.evidences.map((ev, evIdx) => {
                          const isActive =
                            activeEvidence?.page_number === ev.page_number &&
                            activeEvidence?.label === ev.label;
                          return (
                            <button
                              key={evIdx}
                              onClick={() => focusEvidence(ev)}
                              className={`min-h-[48px] px-3 py-1.5 border text-xs rounded-lg flex items-center space-x-2 transition cursor-pointer ${
                                isActive
                                  ? 'bg-red-800/80 border-red-500 text-white font-medium shadow-md'
                                  : 'bg-red-950/60 hover:bg-red-900/60 border-red-700/60 text-red-300'
                              }`}
                            >
                              <ExternalLink className="w-3.5 h-3.5 flex-shrink-0" />
                              <span>P.{ev.page_number}: {ev.label}</span>
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {/* Footnote Disambiguation Chips */}
                  {msg.footnotes && msg.footnotes.length > 0 && (
                    <div className="pt-2 border-t border-slate-700/80">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-[11px] font-semibold text-amber-400/90 uppercase tracking-wider block">
                          Thuyết minh BCTC liên quan (Footnotes):
                        </span>
                        <span className="text-[10px] font-medium bg-amber-950/70 border border-amber-800/60 text-amber-300 px-2 py-0.5 rounded-full">
                          {msg.footnotes.length} Thuyết minh
                        </span>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {msg.footnotes.map((fn, fnIdx) => {
                          const isActive =
                            activeEvidence?.page_number === fn.page_number &&
                            activeEvidence?.label.includes(`TM ${fn.footnote_number}`);
                          return (
                            <FootnoteChip
                              key={fnIdx}
                              footnote={fn}
                              isActive={isActive}
                              onClick={focusFootnote}
                            />
                          );
                        })}
                      </div>
                    </div>
                  )}

                  <div className="text-[10px] text-slate-400 flex justify-between items-center pt-1">
                    <span>Engine: {msg.engine_used}</span>
                    <span className="flex items-center space-x-1.5 font-mono">
                      {msg.cached && (
                        <span className="text-[9px] text-emerald-400 bg-emerald-950/70 border border-emerald-800/60 px-1.5 py-0.5 rounded uppercase tracking-wider font-semibold">
                          Cache
                        </span>
                      )}
                      <span>{msg.latency_ms} ms</span>
                    </span>
                  </div>
                </div>
              </div>
            </div>
          ))}

        {/* COMPARATIVE MODE HISTORY */}
        {modeTab === 'comparative' &&
          comparativeHistory.map((msg, idx) => (
            <div key={idx} className="space-y-3">
              <div className="flex justify-end">
                <div className="bg-indigo-600 text-white text-sm px-4 py-2.5 rounded-2xl rounded-tr-none max-w-xl 2xl:max-w-2xl shadow">
                  {msg.query_text}
                </div>
              </div>

              <div
                data-testid="comparative-result-card"
                className="flex justify-start"
              >
                <div className="bg-slate-800/90 border border-slate-700 text-slate-200 text-sm p-4 rounded-2xl rounded-tl-none max-w-2xl 2xl:max-w-4xl space-y-3.5 shadow-lg">
                  {/* Header Badge */}
                  <div className="flex items-center justify-between border-b border-slate-700/80 pb-2">
                    <div className="flex items-center gap-1.5 text-xs font-bold text-slate-100">
                      <GitCompare className="w-4 h-4 text-indigo-400" />
                      <span>Kết quả phân tích so sánh đa BCTC (YoY)</span>
                    </div>
                    <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950/70 border border-emerald-800/60 px-2 py-0.5 rounded-full">
                      {msg.document_ids.length} Kỳ đối chiếu
                    </span>
                  </div>

                  {/* YoY Comparative Metrics Grid */}
                  {msg.comparative_metrics && msg.comparative_metrics.length > 0 && (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                      {msg.comparative_metrics.map((m, mIdx) => (
                        <div
                          key={mIdx}
                          className="bg-slate-900/80 border border-slate-700/70 rounded-xl p-3 space-y-1.5"
                        >
                          <div className="flex items-center justify-between text-xs">
                            <span className="font-semibold text-slate-300">{m.metric}</span>
                            {m.yoy_growth && (
                              <span className="flex items-center gap-0.5 text-[11px] font-bold text-emerald-400 bg-emerald-950/60 px-1.5 py-0.5 rounded border border-emerald-800/60">
                                <TrendingUp className="w-3 h-3" />
                                {m.yoy_growth}
                              </span>
                            )}
                          </div>
                          <div className="grid grid-cols-2 gap-2 text-[11px] text-slate-400 pt-1 border-t border-slate-800">
                            {Object.entries(m.doc_values).map(([docId, val]) => (
                              <div key={docId} className="truncate">
                                <span className="text-[10px] text-slate-400 block truncate">{docId}:</span>
                                <strong className="text-slate-100">{String(val)}</strong>
                              </div>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Comparative Narrative Answer */}
                  <p className="leading-relaxed whitespace-pre-wrap text-xs text-slate-200">
                    {msg.answer}
                  </p>

                  {/* Dual-Document Grounding Citations */}
                  {msg.evidences.length > 0 && (
                    <div className="pt-2 border-t border-slate-700/80">
                      <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-2">
                        Bằng chứng đối chiếu theo tài liệu (Visual Grounding):
                      </span>
                      <div className="flex flex-wrap gap-2">
                        {msg.evidences.map((ev, evIdx) => {
                          const isActive =
                            activeEvidence?.page_number === ev.page_number &&
                            activeEvidence?.label === ev.label;
                          const isDocA = ev.document_id === msg.document_ids[0];
                          return (
                            <button
                              key={evIdx}
                              onClick={() => focusEvidence(ev)}
                              className={`min-h-[48px] px-3 py-1.5 border text-xs rounded-lg flex items-center space-x-2 transition cursor-pointer ${
                                isActive
                                  ? 'bg-red-800/80 border-red-500 text-white font-medium shadow-md'
                                  : isDocA
                                  ? 'bg-sky-950/60 hover:bg-sky-900/60 border-sky-700/60 text-sky-300'
                                  : 'bg-indigo-950/60 hover:bg-indigo-900/60 border-indigo-700/60 text-indigo-300'
                              }`}
                            >
                              <ExternalLink className="w-3.5 h-3.5 flex-shrink-0" />
                              <span>
                                {ev.document_id ? `[${ev.document_id}] ` : ''}P.{ev.page_number}: {ev.label}
                              </span>
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  <div className="text-[10px] text-slate-400 flex justify-between items-center pt-1 border-t border-slate-800/80">
                    <span>Engine: {msg.engine_used}</span>
                    <span className="font-mono">{msg.latency_ms} ms</span>
                  </div>
                </div>
              </div>
            </div>
          ))}

        {/* STATE 2: STREAMING PROGRESSIVE OR SKELETON LOADING STATE */}
        {state === 'loading' && (
          streamingAnswer ? (
            <div className="flex justify-start">
              <div className="bg-slate-800/90 border border-indigo-500/50 text-slate-200 text-sm p-4 rounded-2xl rounded-tl-none max-w-2xl 2xl:max-w-4xl space-y-2 shadow-lg">
                <div className="flex items-center space-x-2 text-indigo-400 text-xs font-semibold uppercase tracking-wider mb-1">
                  <Sparkles className="w-3.5 h-3.5 animate-spin" />
                  <span>Đang suy luận streaming qua WebSocket...</span>
                </div>
                <p className="leading-relaxed whitespace-pre-wrap">{streamingAnswer}</p>
              </div>
            </div>
          ) : (
            <div className="flex justify-start animate-pulse">
              <div className="bg-slate-800/60 border border-slate-700/50 p-4 rounded-2xl rounded-tl-none w-full max-w-md space-y-3">
                <div className="h-4 bg-slate-700 rounded w-3/4"></div>
                <div className="h-4 bg-slate-700 rounded w-5/6"></div>
                <div className="h-4 bg-slate-700 rounded w-1/2"></div>
                <div className="h-8 bg-slate-700/50 rounded w-1/3 mt-2"></div>
              </div>
            </div>
          )
        )}

        {/* STATE 3: ERROR STATE WITH RETRY (Kiosk Ergonomics >= 48px) */}
        {state === 'error' && (
          <div className="p-4 bg-red-950/50 border border-red-800/60 rounded-xl text-red-200 space-y-3">
            <div className="flex items-center space-x-2">
              <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0" />
              <span className="text-sm font-semibold">Lỗi truy vấn Visual RAG Engine</span>
            </div>
            <p className="text-xs text-red-300">{error}</p>
            <button
              onClick={() => {
                clearError();
                if (modeTab === 'comparative' && comparativeHistory.length > 0) {
                  askComparative(
                    selectedDocIds,
                    comparativeHistory[comparativeHistory.length - 1].query_text,
                    inferenceMode
                  );
                } else if (history.length > 0) {
                  ask(history[history.length - 1].query_text, inferenceMode);
                }
              }}
              className="min-h-[48px] px-4 py-2 bg-red-800 hover:bg-red-700 text-white text-xs font-semibold rounded-lg flex items-center justify-center space-x-2 transition"
            >
              <RefreshCw className="w-4 h-4" />
              <span>Thử lại truy vấn (Retry)</span>
            </button>
          </div>
        )}
      </div>

      {/* Input Bar with Kiosk Touch Target */}
      <form onSubmit={handleSubmit} className="p-4 border-t border-slate-800 flex items-center gap-2 flex-shrink-0">
        <input
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          placeholder={
            modeTab === 'comparative'
              ? 'Hỏi so sánh YoY (ví dụ: So sánh doanh thu và lợi nhuận 2 kỳ...)'
              : 'Hỏi về biểu đồ, doanh thu, lợi nhuận, chú thích chân trang...'
          }
          className="flex-1 bg-slate-800/80 border border-slate-700 text-sm px-4 py-3 rounded-xl focus:outline-none focus:border-indigo-500 text-slate-100 placeholder-slate-400 min-h-[48px]"
        />
        <button
          type="submit"
          data-testid="btn-submit-query"
          disabled={state === 'loading' || !inputText.trim()}
          className="min-w-[48px] min-h-[48px] bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 disabled:text-slate-600 text-white rounded-xl flex items-center justify-center transition shadow cursor-pointer"
        >
          <Send className="w-5 h-5" />
        </button>
      </form>
    </div>
  );

  return (
    <div className="h-full w-full bg-slate-950 text-slate-100 font-sans antialiased overflow-hidden flex flex-col">
      <ResizableSplitView
        leftPane={leftPaneContent}
        rightPane={rightPaneContent}
        minLeftWidth={350}
        minRightWidth={350}
        initialRatio={0.5}
      />
      <SettingsDialog
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
      />
    </div>
  );
};
