/**
 * File 4 of 4: Document Picker & PDF Upload Modal
 * Governed by 529 Engineering Standards:
 * - 3 UI States (Skeleton, Error with Retry, Actionable Empty)
 * - Kiosk Ergonomics (>= 48px touch targets)
 * - Rule 15 Zero Raw Emojis (Lucide React SVG only)
 */
import React, { useRef, useState } from 'react';
import {
  X,
  UploadCloud,
  FileText,
  Search,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  Loader2,
  FolderOpen,
} from 'lucide-react';

export interface DocumentPickerModalProps {
  isOpen: boolean;
  activeDocumentId: string;
  documents: string[];
  isLoading: boolean;
  errorMessage: string | null;
  isUploading: boolean;
  uploadError: string | null;
  onClose: () => void;
  onRetry: () => void;
  onSelectDocument: (documentId: string) => void;
  onUploadFile: (file: File) => Promise<void> | void;
}

export const DocumentPickerModal: React.FC<DocumentPickerModalProps> = ({
  isOpen,
  activeDocumentId,
  documents,
  isLoading,
  errorMessage,
  isUploading,
  uploadError,
  onClose,
  onRetry,
  onSelectDocument,
  onUploadFile,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [dragActive, setDragActive] = useState(false);

  if (!isOpen) return null;

  const filteredDocs = documents.filter((id) =>
    id.toLowerCase().includes(searchTerm.trim().toLowerCase())
  );

  const handleFiles = async (files: FileList | null) => {
    if (files && files[0]) {
      await onUploadFile(files[0]);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Quản lý & Tải lên Báo Cáo Tài Chính"
      data-testid="document-picker-modal"
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4"
    >
      <div className="w-full max-w-2xl bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[88vh]">
        {/* Header */}
        <header className="h-16 px-6 border-b border-slate-800 flex items-center justify-between flex-shrink-0">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 rounded-xl bg-indigo-950/60 border border-indigo-700/50 text-indigo-400">
              <FolderOpen className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-slate-100">
                Chọn hoặc Tải Lên Báo Cáo Tài Chính (PDF)
              </h2>
              <p className="text-[11px] text-slate-400">
                Chọn BCTC đã index trong LanceDB hoặc tải file PDF mới
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Đóng chọn tài liệu"
            data-testid="btn-close-doc-picker"
            className="min-h-[48px] min-w-[48px] rounded-xl hover:bg-slate-800 text-slate-400 hover:text-slate-200 flex items-center justify-center transition cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </header>

        <div className="p-6 space-y-5 overflow-y-auto flex-1">
          {/* Upload Zone */}
          <div className="space-y-2">
            <input
              ref={fileInputRef}
              type="file"
              accept="application/pdf"
              className="hidden"
              data-testid="desktop-pdf-file-input"
              onChange={(e) => handleFiles(e.target.files)}
              disabled={isUploading}
            />
            <div
              onDragEnter={(e) => {
                e.preventDefault();
                setDragActive(true);
              }}
              onDragOver={(e) => {
                e.preventDefault();
                setDragActive(true);
              }}
              onDragLeave={() => setDragActive(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDragActive(false);
                handleFiles(e.dataTransfer.files);
              }}
              className={`border-2 border-dashed rounded-xl p-4 flex flex-col sm:flex-row items-center justify-between gap-3 transition ${
                dragActive
                  ? 'border-indigo-500 bg-indigo-950/40'
                  : 'border-slate-700 bg-slate-950/40 hover:border-indigo-600/60'
              }`}
            >
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 rounded-full bg-indigo-950/80 border border-indigo-700/40 flex items-center justify-center text-indigo-400 shrink-0">
                  {isUploading ? (
                    <Loader2 className="w-5 h-5 animate-spin" />
                  ) : (
                    <UploadCloud className="w-5 h-5" />
                  )}
                </div>
                <div>
                  <p className="text-xs font-semibold text-slate-200">
                    {isUploading
                      ? 'Đang render trang PDF và lập chỉ mục LanceDB...'
                      : 'Kéo thả file PDF BCTC vào đây'}
                  </p>
                  <p className="text-[11px] text-slate-400">
                    Hỗ trợ định dạng .pdf (150 DPI Visual RAG indexing)
                  </p>
                </div>
              </div>
              <button
                type="button"
                data-testid="btn-desktop-upload-pdf"
                disabled={isUploading}
                onClick={() => fileInputRef.current?.click()}
                className="min-h-[48px] px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-700 text-white text-xs font-semibold rounded-lg flex items-center space-x-2 transition shrink-0 cursor-pointer"
              >
                <UploadCloud className="w-4 h-4" />
                <span>{isUploading ? 'Đang xử lý...' : 'Tải PDF mới'}</span>
              </button>
            </div>

            {uploadError && (
              <div
                data-testid="doc-upload-error"
                className="p-3 bg-rose-950/50 border border-rose-800/60 rounded-lg text-xs text-rose-200 flex items-center space-x-2"
              >
                <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
                <span>{uploadError}</span>
              </div>
            )}
          </div>

          {/* Search Filter */}
          <div className="flex items-center space-x-2">
            <div className="relative flex-1">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Tìm mã tài liệu (ví dụ: VNM_BCTC_2023...)"
                className="w-full min-h-[48px] bg-slate-800/80 border border-slate-700 rounded-lg pl-9 pr-3 text-xs text-slate-100 placeholder-slate-400 focus:outline-none focus:border-indigo-500"
              />
            </div>
            <button
              type="button"
              onClick={onRetry}
              aria-label="Làm mới danh sách tài liệu"
              className="min-h-[48px] min-w-[48px] px-3 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg text-slate-300 flex items-center justify-center transition cursor-pointer"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>

          {/* 3 Mandatory UI States for Document List */}
          {isLoading ? (
            <div data-testid="doc-picker-skeleton" className="space-y-2 animate-pulse">
              <div className="h-12 bg-slate-800 rounded-lg" />
              <div className="h-12 bg-slate-800 rounded-lg" />
              <div className="h-12 bg-slate-800 rounded-lg" />
            </div>
          ) : errorMessage ? (
            <div
              data-testid="doc-picker-error"
              className="p-4 bg-rose-950/50 border border-rose-800/60 rounded-xl space-y-3"
            >
              <div className="flex items-center space-x-2 text-rose-300 text-xs font-semibold">
                <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
                <span>{errorMessage}</span>
              </div>
              <button
                type="button"
                data-testid="doc-picker-retry-btn"
                onClick={onRetry}
                className="min-h-[48px] px-4 py-2 bg-rose-800 hover:bg-rose-700 text-white text-xs font-semibold rounded-lg flex items-center space-x-2 transition cursor-pointer"
              >
                <RefreshCw className="w-4 h-4" />
                <span>Thử tải lại danh sách</span>
              </button>
            </div>
          ) : filteredDocs.length === 0 ? (
            <div
              data-testid="doc-picker-empty"
              className="p-6 bg-slate-950/40 border border-slate-800 rounded-xl text-center space-y-2"
            >
              <FileText className="w-8 h-8 text-slate-500 mx-auto" />
              <p className="text-xs font-medium text-slate-300">
                {documents.length === 0
                  ? 'Chưa có tài liệu nào được lập chỉ mục trong LanceDB.'
                  : 'Không tìm thấy tài liệu khớp từ khóa.'}
              </p>
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="min-h-[48px] px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-lg inline-flex items-center space-x-2 transition cursor-pointer"
              >
                <UploadCloud className="w-4 h-4" />
                <span>Tải lên PDF đầu tiên</span>
              </button>
            </div>
          ) : (
            <div data-testid="doc-picker-list" className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {filteredDocs.map((docId) => {
                const isSelected = docId === activeDocumentId;
                return (
                  <button
                    key={docId}
                    type="button"
                    data-testid={`doc-option-${docId}`}
                    onClick={() => {
                      onSelectDocument(docId);
                      onClose();
                    }}
                    className={`min-h-[48px] px-3.5 py-2.5 rounded-xl border text-left flex items-center justify-between gap-2 transition cursor-pointer ${
                      isSelected
                        ? 'bg-indigo-950/80 border-indigo-500 text-white'
                        : 'bg-slate-800/70 hover:bg-slate-800 border-slate-700 text-slate-200'
                    }`}
                  >
                    <div className="flex items-center space-x-2 min-w-0">
                      <FileText className="w-4 h-4 text-indigo-400 shrink-0" />
                      <span className="text-xs font-mono truncate">{docId}</span>
                    </div>
                    {isSelected && <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />}
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
