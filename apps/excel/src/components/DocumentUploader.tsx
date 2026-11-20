import React, { useRef, useState } from 'react';
import {
  UploadCloud,
  AlertCircle,
  Loader2,
  RefreshCw,
  FolderOpen,
} from 'lucide-react';
import { DocumentIngestResponseDTO } from '../types/api';
import { useDocumentUpload } from '../lib/hooks/use-ingest';

interface DocumentUploaderProps {
  onIngestSuccess: (doc: DocumentIngestResponseDTO, filename: string) => void;
  isProcessing?: boolean;
}

export const DocumentUploader: React.FC<DocumentUploaderProps> = ({
  onIngestSuccess,
  isProcessing = false,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dragActive, setDragActive] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [lastUploadedName, setLastUploadedName] = useState<string | null>(null);

  const uploadMutation = useDocumentUpload({
    onSuccess: (data) => {
      setErrorMessage(null);
      if (lastUploadedName) {
        onIngestSuccess(data, lastUploadedName);
      }
    },
    onError: (err) => {
      setErrorMessage(err.message || 'Lỗi xử lý tài liệu BCTC. Vui lòng kiểm tra kết nối daemon.');
    },
  });

  const handleFileProcess = (file: File) => {
    setErrorMessage(null);
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setErrorMessage('Định dạng không được hỗ trợ. Vui lòng chọn file Báo Cáo Tài Chính định dạng PDF (.pdf).');
      return;
    }
    setLastUploadedName(file.name);
    uploadMutation.mutate({ file, renderDpi: 150 });
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileProcess(e.dataTransfer.files[0]);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFileProcess(e.target.files[0]);
    }
  };

  const isUploading = uploadMutation.isPending || isProcessing;

  return (
    <div className="space-y-3">
      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept="application/pdf"
        className="hidden"
        data-testid="pdf-file-input"
        onChange={handleInputChange}
        disabled={isUploading}
      />

      {/* Drag and drop zone */}
      <div
        className={`border-2 border-dashed rounded-xl p-4 text-center transition cursor-pointer select-none ${
          dragActive
            ? 'border-indigo-500 bg-indigo-50/50'
            : isUploading
            ? 'border-slate-300 bg-slate-50 cursor-not-allowed'
            : 'border-slate-200 hover:border-indigo-300 hover:bg-slate-50/60'
        }`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={() => !isUploading && fileInputRef.current?.click()}
      >
        <div className="flex flex-col items-center justify-center space-y-2">
          {isUploading ? (
            <div className="p-3 bg-indigo-50 text-indigo-600 rounded-full animate-spin">
              <Loader2 className="w-6 h-6" />
            </div>
          ) : (
            <div className="p-3 bg-slate-100 text-slate-600 rounded-full">
              <UploadCloud className="w-6 h-6" />
            </div>
          )}

          <div className="space-y-0.5">
            <p className="text-sm font-medium text-slate-800">
              {isUploading
                ? 'Đang render và trích xuất vector...'
                : 'Kéo thả file BCTC hoặc click để tải lên'}
            </p>
            <p className="text-xs text-slate-500">Hỗ trợ định dạng PDF (BCTC hợp nhất hoặc kiểm toán)</p>
          </div>
        </div>
      </div>

      {/* Primary Action Button - Kiosk 48px touch target */}
      <button
        type="button"
        data-testid="btn-upload-pdf"
        disabled={isUploading}
        onClick={() => fileInputRef.current?.click()}
        className="w-full min-h-[48px] px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 text-white rounded-lg font-medium text-sm transition flex items-center justify-center gap-2 shadow-sm"
      >
        {isUploading ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin" />
            <span>Đang xử lý BCTC...</span>
          </>
        ) : (
          <>
            <FolderOpen className="w-4 h-4" />
            <span>Chọn Báo Cáo Tài Chính (PDF)</span>
          </>
        )}
      </button>

      {/* Error state alert */}
      {errorMessage && (
        <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-xs space-y-2">
          <div className="flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
            <span className="font-medium">{errorMessage}</span>
          </div>
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="w-full min-h-[48px] flex items-center justify-center gap-1.5 bg-red-100 hover:bg-red-200 text-red-800 rounded font-medium transition"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Thử lại với file khác</span>
          </button>
        </div>
      )}
    </div>
  );
};
