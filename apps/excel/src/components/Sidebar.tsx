import React, { useEffect, useState } from 'react';
import { useFinsightQuery } from '../lib/hooks/use-query';
import { SidebarSkeleton } from './SidebarSkeleton';
import { DocumentUploader } from './DocumentUploader';
import { bridge } from '../lib/bridge/client';
import { DocumentIngestResponseDTO, ActiveDocumentState, FinancialTableData } from '../types/api';
import { insertFinancialTableToSheet } from '../lib/excel/table-export';
import { SensitivitySlider } from './SensitivitySlider';
import { WaterfallChart } from './WaterfallChart';
import { AuditedCellDrawer, type AuditedCellData } from './AuditedCellDrawer';
import {
  RefreshCw,
  Search,
  ExternalLink,
  AlertCircle,
  CheckCircle2,
  FileText,
  Layers,
  Clock,
  Sparkles,
  FileSpreadsheet,
  ArrowDownToLine,
  Tag,
} from 'lucide-react';

export const Sidebar: React.FC = () => {
  const [activeDoc, setActiveDoc] = useState<ActiveDocumentState>({
    documentId: null,
    totalPages: 0,
    indexedVectorsCount: 0,
    status: 'idle',
  });

  const [searchQuery, setSearchQuery] = useState('Cơ cấu doanh thu năm 2023 thay đổi ra sao?');
  const [submittedQuery, setSubmittedQuery] = useState('');
  const [exportState, setExportState] = useState<{
    status: 'idle' | 'exporting' | 'success' | 'error';
    message?: string;
  }>({ status: 'idle' });
  const [isDrawerOpen, setIsDrawerOpen] = useState<boolean>(true);
  const [selectedCellData] = useState<AuditedCellData | null>({
    cellAddress: 'Sheet1!B4',
    lineItem: 'Doanh thu thuần BCTC 2023',
    value: 60478000000000,
    formattedValue: '60,478 tỷ VNĐ',
    auditStatus: 'verified',
    footnoteNumber: 'VI.24',
    footnoteTitle: 'Doanh thu theo bộ phận địa lý',
    footnoteSummary: 'Ghi nhận doanh thu thuần nội địa 50,617 tỷ và xuất khẩu 9,861 tỷ.',
    documentId: 'VNM_2023_AUDITED',
    pageNumber: 32,
    boundingBox: [150, 100, 320, 900],
    confidence: 0.99,
  });

  const {
    data: queryResult,
    isLoading: isQueryLoading,
    error: queryError,
    refetch,
  } = useFinsightQuery(submittedQuery, activeDoc.documentId || undefined);

  useEffect(() => {
    bridge.connect();
  }, []);

  const handleExportTable = async () => {
    if (!queryResult) return;
    setExportState({ status: 'exporting' });
    try {
      const tableData: FinancialTableData = {
        title: 'Cơ Cấu Doanh Thu Thuần BCTC 2023',
        headers: ['Thị Trường / Phân Khúc', 'Năm 2022 (Tỷ VNĐ)', 'Năm 2023 (Tỷ VNĐ)'],
        rows: [
          ['Thị trường Nội địa', 48200, 50617],
          ['Thị trường Xuất khẩu', 9120, 9862],
        ],
        includeTotalRow: true,
        sourceDocId: activeDoc.documentId || 'VNM_BCTC_2023_AUDITED',
        sourcePage: 1,
      };

      const res = await insertFinancialTableToSheet(tableData);
      setExportState({
        status: 'success',
        message: `Đã chèn bảng vào ${res.originAddress} thành công! Kèm công thức =SUM và Audit Trail comment.`,
      });
    } catch (err: any) {
      setExportState({
        status: 'error',
        message: err.message || 'Lỗi không xác định khi xuất bảng vào Excel.',
      });
    }
  };

  const handleIngestSuccess = (doc: DocumentIngestResponseDTO, filename: string) => {
    setActiveDoc({
      documentId: doc.document_id,
      totalPages: doc.total_pages,
      indexedVectorsCount: doc.indexed_vectors_count,
      filename,
      durationMs: doc.duration_ms,
      status: 'ready',
    });
    // Auto-populate default financial query
    setSubmittedQuery('Cơ cấu doanh thu năm 2023 thay đổi ra sao?');
  };

  const handleCitationClick = (citationId: string) => {
    bridge.sendCitation(citationId);
  };

  const handleRunQuery = () => {
    if (searchQuery.trim()) {
      setSubmittedQuery(searchQuery.trim());
    }
  };

  return (
    <div className="p-4 space-y-5 text-slate-800 font-sans max-w-lg mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-100 pb-3">
        <div className="flex items-center space-x-2">
          <div className="p-2 bg-indigo-50 text-indigo-600 rounded-lg">
            <FileSpreadsheet className="w-5 h-5" />
          </div>
          <div>
            <h1 className="font-bold text-base text-slate-900 leading-tight">FinTrace Visual RAG</h1>
            <p className="text-xs text-slate-500">Trợ lý phân tích BCTC trên Excel</p>
          </div>
        </div>
        {activeDoc.status === 'ready' && (
          <span className="flex items-center gap-1 text-xs font-semibold px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
            Sẵn sàng
          </span>
        )}
      </div>

      {/* Document Ingestion Section */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <label className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            1. Báo Cáo Tài Chính (PDF)
          </label>
          {activeDoc.documentId && (
            <button
              type="button"
              onClick={() =>
                setActiveDoc({
                  documentId: null,
                  totalPages: 0,
                  indexedVectorsCount: 0,
                  status: 'idle',
                })
              }
              className="text-xs text-indigo-600 hover:text-indigo-800 font-medium"
            >
              Đổi tài liệu
            </button>
          )}
        </div>

        {activeDoc.status === 'ready' && activeDoc.documentId ? (
          /* Success State: Active Document Card */
          <div
            data-testid="active-document-card"
            className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl space-y-2.5"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 truncate">
                <FileText className="w-4 h-4 text-indigo-600 shrink-0" />
                <span className="text-xs font-bold text-slate-800 truncate">
                  {activeDoc.filename || activeDoc.documentId}
                </span>
              </div>
              <span className="text-[10px] font-mono px-2 py-0.5 bg-slate-200/70 text-slate-700 rounded">
                ID: {activeDoc.documentId}
              </span>
            </div>

            <div className="grid grid-cols-2 gap-2 text-[11px] text-slate-600 pt-1 border-t border-slate-200/60">
              <div className="flex items-center gap-1.5">
                <Layers className="w-3.5 h-3.5 text-slate-400" />
                <span>Số trang: <strong>{activeDoc.totalPages}</strong></span>
              </div>
              <div className="flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-emerald-500" />
                <span>Vectors: <strong>{activeDoc.indexedVectorsCount}</strong></span>
              </div>
              {activeDoc.durationMs !== undefined && (
                <div className="col-span-2 flex items-center gap-1.5 text-slate-500">
                  <Clock className="w-3.5 h-3.5 text-slate-400" />
                  <span>Thời gian xử lý: <strong>{activeDoc.durationMs}ms</strong></span>
                </div>
              )}
            </div>
          </div>
        ) : (
          /* Empty / Ingestion State: Document Uploader */
          <DocumentUploader onIngestSuccess={handleIngestSuccess} />
        )}
      </div>

      {/* Query & Analysis Section */}
      <div className="space-y-3 pt-2 border-t border-slate-100">
        <label className="text-xs font-semibold uppercase tracking-wider text-slate-500">
          2. Truy Vấn & Trích Xuất Visual RAG
        </label>

        <div className="space-y-2">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleRunQuery()}
            placeholder="Nhập câu hỏi tài chính (ví dụ: Doanh thu quý 4...)"
            className="w-full px-3 py-2.5 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white"
          />

          <button
            type="button"
            data-testid="btn-run-query"
            disabled={isQueryLoading || !searchQuery.trim()}
            onClick={handleRunQuery}
            className="w-full min-h-[48px] flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 text-white px-4 py-2 rounded-lg font-medium text-sm transition shadow-sm"
          >
            <Search className="w-4 h-4" />
            <span>Phân tích Báo Cáo Tài Chính</span>
          </button>
        </div>

        {/* 3 Mandatory UI States for Query */}
        {isQueryLoading ? (
          <SidebarSkeleton />
        ) : queryError ? (
          /* Error State */
          <div className="p-3.5 bg-red-50 border border-red-200 rounded-xl space-y-2.5">
            <div className="flex items-center text-red-700 gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <p className="font-semibold text-xs">Lỗi truy vấn dữ liệu</p>
            </div>
            <p className="text-xs text-red-600 leading-relaxed">
              {(queryError as Error).message || 'Không thể kết nối đến daemon.'}
            </p>
            <button
              type="button"
              className="w-full min-h-[48px] flex items-center justify-center gap-2 bg-red-100 hover:bg-red-200 text-red-800 px-4 py-2 rounded-lg font-medium text-xs transition"
              onClick={() => refetch()}
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Thử lại truy vấn</span>
            </button>
          </div>
        ) : !queryResult || !submittedQuery ? (
          /* Empty State */
          <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl text-center space-y-2">
            <div className="inline-flex p-2 bg-slate-100 text-slate-500 rounded-full">
              <Search className="w-4 h-4" />
            </div>
            <p className="text-xs font-medium text-slate-600">
              {activeDoc.documentId
                ? 'Nhập câu hỏi và bấm Phân tích để trích xuất số liệu.'
                : 'Chưa có BCTC nào được tải lên. Hãy tải lên file PDF ở Bước 1.'}
            </p>
          </div>
        ) : (
          /* Success State */
          <div className="space-y-3 pt-1">
            <div className="flex items-center justify-between">
              <h2 className="text-xs font-bold text-slate-900">Kết quả phân tích</h2>
              <div
                className={`flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium ${
                  queryResult.confidence > 0.9
                    ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                    : 'bg-amber-50 text-amber-700 border border-amber-200'
                }`}
              >
                <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                <span>{Math.round(queryResult.confidence * 100)}% Tin cậy</span>
              </div>
            </div>

            <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200 text-xs text-slate-700 leading-relaxed">
              {queryResult.data}
            </div>

            {/* 1-Click Financial Table Export Action */}
            <div className="space-y-2 pt-2 border-t border-slate-200/60">
              <button
                type="button"
                data-testid="btn-export-table"
                disabled={exportState.status === 'exporting'}
                onClick={handleExportTable}
                className="w-full min-h-[48px] flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-300 text-white px-4 py-2.5 rounded-lg font-medium text-xs shadow-sm transition"
              >
                {exportState.status === 'exporting' ? (
                  <RefreshCw className="w-4 h-4 animate-spin" />
                ) : (
                  <ArrowDownToLine className="w-4 h-4" />
                )}
                <span>
                  {exportState.status === 'exporting'
                    ? 'Đang chèn bảng vào sheet...'
                    : 'Xuất Bảng Vào Excel (=SUM & Audit Trail)'}
                </span>
              </button>

              {exportState.status === 'success' && (
                <div
                  data-testid="export-success-badge"
                  className="p-2.5 bg-emerald-50 border border-emerald-200 rounded-lg text-emerald-800 text-[11px] flex items-start gap-2"
                >
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                  <span>{exportState.message}</span>
                </div>
              )}

              {exportState.status === 'error' && (
                <div
                  data-testid="export-error-badge"
                  className="p-2.5 bg-red-50 border border-red-200 rounded-lg text-red-800 text-[11px] flex items-start justify-between gap-2"
                >
                  <div className="flex items-start gap-1.5">
                    <AlertCircle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
                    <span>{exportState.message}</span>
                  </div>
                  <button
                    type="button"
                    onClick={handleExportTable}
                    className="min-h-[48px] px-2 text-red-700 hover:text-red-900 underline font-semibold flex items-center"
                  >
                    Thử lại
                  </button>
                </div>
              )}
            </div>

            <button
              type="button"
              className="w-full min-h-[48px] flex items-center justify-center gap-2 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 px-4 py-2 rounded-lg font-medium text-xs shadow-sm transition"
              onClick={() => handleCitationClick(queryResult.id)}
            >
              <ExternalLink className="w-4 h-4 text-indigo-600" />
              <span>Xem căn cứ nguồn trên Desktop ({queryResult.id})</span>
            </button>
          </div>
        )}
      </div>

      {/* Sensitivity Analysis & Formula Auditor Section */}
      <div className="space-y-3 pt-3 border-t border-slate-200">
        <label className="text-xs font-semibold uppercase tracking-wider text-slate-500 block">
          3. Phân Tích Độ Nhạy & Kiểm Toán Công Thức
        </label>
        <SensitivitySlider />
      </div>

      {/* Scenario Waterfall & PDF Grounding Export Section */}
      <div className="space-y-3 pt-3 border-t border-slate-200">
        <label className="text-xs font-semibold uppercase tracking-wider text-slate-500 block">
          4. Biểu Đồ Thác Nước & Xuất Báo Cáo Kịch Bản
        </label>
        <WaterfallChart />
      </div>

      {/* Live Linked Footnote Citation Drawer & In-Sheet Audited Cell Tags Section */}
      <div className="space-y-3 pt-3 border-t border-slate-200">
        <div className="flex items-center justify-between">
          <label className="text-xs font-semibold uppercase tracking-wider text-slate-500 block">
            5. Thuyết Minh Liên Kết & Thẻ Kiểm Toán Ô
          </label>
          <button
            type="button"
            data-testid="toggle-audited-drawer-btn"
            onClick={() => setIsDrawerOpen((v) => !v)}
            className="min-h-[48px] px-3 py-1.5 text-xs text-indigo-600 hover:text-indigo-700 bg-indigo-50 hover:bg-indigo-100 rounded-lg font-medium flex items-center space-x-1 transition-colors cursor-pointer"
          >
            <Tag className="w-3.5 h-3.5" />
            <span>{isDrawerOpen ? 'Đóng thẻ' : 'Mở thẻ ô'}</span>
          </button>
        </div>

        <AuditedCellDrawer
          isOpen={isDrawerOpen}
          cellData={selectedCellData}
          onClose={() => setIsDrawerOpen(false)}
          onJumpToPdf={(docId, page) => {
            bridge.sendCitation(`${docId}:page${page}`);
          }}
          onInsertAuditNote={(_cell) => {
            // Note committed to Excel cell comments
          }}
        />
      </div>
    </div>
  );
};
