/**
 * File 2 of 3: PDF Viewer Canvas Component
 */
import { FC, useEffect } from 'react';
import { usePdfViewer } from '../../hooks/usePdfViewer.hook';

interface PdfViewerProps {
  documentId: string;
  pageNumber: number;
  zoomLevel: number;
}

export const PdfViewer: FC<PdfViewerProps> = ({ documentId, pageNumber, zoomLevel }) => {
  const { canvasRef, renderPage, loading } = usePdfViewer(documentId);

  useEffect(() => {
    renderPage(pageNumber, zoomLevel);
  }, [pageNumber, zoomLevel, renderPage]);

  return (
    <div className="relative overflow-auto border border-slate-700 bg-white">
      {loading && <div className="absolute inset-0 flex items-center justify-center">Đang tải...</div>}
      <canvas ref={canvasRef} />
    </div>
  );
};
