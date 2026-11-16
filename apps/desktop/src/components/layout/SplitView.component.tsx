/**
 * File 4 of 4: SplitView Desktop Component with 3 Mandatory UI States
 * Governed by 529 Engineering Standards:
 * - 3 States: Skeleton, Error with Retry, Empty State with Action
 * - Kiosk Ergonomics: >= 48px interactive target size
 */

import { useState, type FormEvent, type FC } from 'react';
import { useVisualRag } from '../../hooks/useVisualRag.hook';
import { ResizableSplitView } from './ResizableSplitView';
import { BoundingBoxOverlay } from '../pdf/BoundingBoxOverlay';
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
  PieChart
} from 'lucide-react';

interface SplitViewProps {
  documentId: string;
  documentTitle: string;
}

export const SplitView: FC<SplitViewProps> = ({ documentId, documentTitle }) => {
  const [inputText, setInputText] = useState('');
  const [zoomLevel, setZoomLevel] = useState<number>(1.0);
  const { state, error, history, activeEvidence, ask, focusEvidence, clearError } = useVisualRag(documentId);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!inputText.trim()) return;
    ask(inputText);
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
          <span className="font-semibold text-sm truncate max-w-[200px] 2xl:max-w-md">{documentTitle}</span>
        </div>

        <div className="flex items-center space-x-3 flex-shrink-0">
          {activeEvidence && (
            <div className="hidden sm:flex items-center space-x-2 bg-indigo-950/70 border border-indigo-700/50 px-2.5 py-1 rounded text-xs text-indigo-300 truncate max-w-xs">
              <Eye className="w-3.5 h-3.5 text-indigo-400 flex-shrink-0" />
              <span className="truncate">Trang {activeEvidence.page_number}: {activeEvidence.label}</span>
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
        </div>
      </header>

      <div className="flex-1 relative overflow-auto p-6 flex justify-center items-start sm:items-center bg-slate-950/50">
        {/* Simulated PDF Page Viewport with Scale Tracking */}
        <div
          style={{
            width: `${500 * zoomLevel}px`,
            height: `${700 * zoomLevel}px`,
          }}
          className="relative bg-white rounded shadow-2xl overflow-hidden border border-slate-700 transition-all duration-150 flex-shrink-0 my-auto"
        >
          <div
            style={{
              transform: `scale(${zoomLevel})`,
              transformOrigin: 'top left',
              width: '500px',
              height: '700px',
            }}
            className="p-8 text-slate-900 text-xs space-y-4 select-none pointer-events-none"
          >
            <h2 className="text-base font-bold text-center border-b pb-2">BÁO CÁO TÀI CHÍNH KIỂM TOÁN</h2>
            <div className="grid grid-cols-2 gap-4">
              <div className="h-32 bg-slate-100 rounded border border-dashed border-slate-300 flex items-center justify-center text-slate-400">
                [Biểu đồ Cơ Cấu Doanh Thu]
              </div>
              <div className="h-32 bg-slate-100 rounded border border-dashed border-slate-300 flex items-center justify-center text-slate-400">
                [Biểu đồ Biên Lợi Nhuận YoY]
              </div>
            </div>
            <div className="h-48 bg-slate-50 border border-slate-200 rounded p-2">
              <p className="font-semibold">Bảng Cân Đối Kế Toán (Trích yếu)</p>
              <div className="mt-2 space-y-1">
                <div className="flex justify-between border-b pb-1"><span>Tài sản ngắn hạn</span><span>142.500 tỷ</span></div>
                <div className="flex justify-between border-b pb-1"><span>Tiền & tương đương tiền</span><span>28.120 tỷ</span></div>
                <div className="flex justify-between"><span>Đầu tư tài chính</span><span>45.000 tỷ</span></div>
              </div>
            </div>
          </div>

          {/* Visual Grounding Bounding Box Overlay with zoom scale */}
          <BoundingBoxOverlay
            evidence={activeEvidence}
            renderedWidth={500}
            renderedHeight={700}
            zoomLevel={zoomLevel}
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
          <h1 className="font-semibold text-sm">FinSight AI Copilot</h1>
        </div>
        <span className="text-xs text-slate-400 bg-slate-800 px-2.5 py-1 rounded-full border border-slate-700">
          Visual RAG Native
        </span>
      </header>

      {/* Message Thread Area with 3 UI States */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {/* STATE 1: EMPTY STATE */}
        {history.length === 0 && state !== 'loading' && state !== 'error' && (
          <div className="h-full flex flex-col items-center justify-center text-center p-8 space-y-4 text-slate-400">
            <div className="w-16 h-16 rounded-full bg-indigo-950/80 border border-indigo-700/40 flex items-center justify-center text-indigo-400">
              <FileText className="w-8 h-8" />
            </div>
            <div className="space-y-1">
              <h3 className="text-base font-semibold text-slate-200">Sẵn sàng phân tích Báo cáo tài chính</h3>
              <p className="text-xs max-w-sm">
                Đặt câu hỏi về bất kỳ biểu đồ tăng trưởng, biên lợi nhuận, hoặc bảng số liệu phức tạp trong tài liệu.
              </p>
            </div>
            <div className="flex flex-col gap-2 w-full max-w-sm pt-2">
              <button
                onClick={() => ask('Biên lợi nhuận gộp qua biểu đồ các năm thay đổi như thế nào?')}
                className="min-h-[48px] px-4 py-2 bg-slate-800 hover:bg-slate-700 text-xs rounded border border-slate-700 text-left transition flex items-center space-x-2.5"
              >
                <BarChart3 className="w-4 h-4 text-indigo-400 flex-shrink-0" />
                <span>Phân tích biên lợi nhuận gộp qua biểu đồ</span>
              </button>
              <button
                onClick={() => ask('Cơ cấu doanh thu theo mảng kinh doanh năm 2023?')}
                className="min-h-[48px] px-4 py-2 bg-slate-800 hover:bg-slate-700 text-xs rounded border border-slate-700 text-left transition flex items-center space-x-2.5"
              >
                <PieChart className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                <span>Cơ cấu doanh thu theo từng mảng</span>
              </button>
            </div>
          </div>
        )}

        {/* Chat History List */}
        {history.map((msg, idx) => (
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
                    <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-2">
                      Bằng chứng kiểm toán (Visual Grounding):
                    </span>
                    <div className="flex flex-wrap gap-2">
                      {msg.evidences.map((ev, evIdx) => (
                        <button
                          key={evIdx}
                          onClick={() => focusEvidence(ev)}
                          className="min-h-[48px] px-3 py-1.5 bg-red-950/60 hover:bg-red-900/60 border border-red-700/60 text-red-300 text-xs rounded-lg flex items-center space-x-2 transition cursor-pointer"
                        >
                          <ExternalLink className="w-3.5 h-3.5" />
                          <span>P.{ev.page_number}: {ev.label}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                <div className="text-[10px] text-slate-400 flex justify-between pt-1">
                  <span>Engine: {msg.engine_used}</span>
                  <span>{msg.latency_ms} ms</span>
                </div>
              </div>
            </div>
          </div>
        ))}

        {/* STATE 2: SKELETON LOADING STATE */}
        {state === 'loading' && (
          <div className="flex justify-start animate-pulse">
            <div className="bg-slate-800/60 border border-slate-700/50 p-4 rounded-2xl rounded-tl-none w-full max-w-md space-y-3">
              <div className="h-4 bg-slate-700 rounded w-3/4"></div>
              <div className="h-4 bg-slate-700 rounded w-5/6"></div>
              <div className="h-4 bg-slate-700 rounded w-1/2"></div>
              <div className="h-8 bg-slate-700/50 rounded w-1/3 mt-2"></div>
            </div>
          </div>
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
                if (history.length > 0) {
                  ask(history[history.length - 1].query_text);
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
          placeholder="Hỏi về biểu đồ, doanh thu, lợi nhuận, chú thích chân trang..."
          className="flex-1 bg-slate-800/80 border border-slate-700 text-sm px-4 py-3 rounded-xl focus:outline-none focus:border-indigo-500 text-slate-100 placeholder-slate-400 min-h-[48px]"
        />
        <button
          type="submit"
          disabled={state === 'loading' || !inputText.trim()}
          className="min-w-[48px] min-h-[48px] bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 disabled:text-slate-600 text-white rounded-xl flex items-center justify-center transition shadow"
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
    </div>
  );
};
