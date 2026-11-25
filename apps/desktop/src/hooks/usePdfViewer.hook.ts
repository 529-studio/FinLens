/**
 * File 3 of 4: PDF Viewer Logic Hook (Rendered Page Image Canvas)
 * Governed by 529 Engineering Standards (frontend-4file-and-resilient-ui & ADR-003)
 */
import { useRef, useState, useCallback, useEffect } from 'react';
import { fetchRenderedPageBlob } from '../api/visual_rag.fetch';
import type { RenderedPageSize } from '../types/visual_rag.types';

const BASE_LOGICAL_WIDTH = 560;
const DEFAULT_PAGE_SIZE: RenderedPageSize = { width: 560, height: 792 };

function loadImageElement(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error('Không thể giải mã hình ảnh trang PDF'));
    img.src = src;
  });
}

export function usePdfViewer(documentId: string) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [renderedSize, setRenderedSize] = useState<RenderedPageSize>(DEFAULT_PAGE_SIZE);
  const [hasPage, setHasPage] = useState(false);

  const abortRef = useRef<AbortController | null>(null);
  const mountedRef = useRef(true);
  const cachedPageRef = useRef<{
    docId: string;
    pageNumber: number;
    img: HTMLImageElement;
    logicalSize: RenderedPageSize;
  } | null>(null);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      abortRef.current?.abort();
    };
  }, []);

  const drawImageToCanvas = useCallback(
    (img: HTMLImageElement, logicalSize: RenderedPageSize, zoom: number) => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const dpr = typeof window !== 'undefined' && window.devicePixelRatio ? window.devicePixelRatio : 1;
      const cssWidth = Math.max(1, Math.round(logicalSize.width * zoom));
      const cssHeight = Math.max(1, Math.round(logicalSize.height * zoom));

      canvas.width = Math.max(1, Math.round(cssWidth * dpr));
      canvas.height = Math.max(1, Math.round(cssHeight * dpr));
      canvas.style.width = `${cssWidth}px`;
      canvas.style.height = `${cssHeight}px`;

      const ctx = canvas.getContext('2d');
      if (ctx) {
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        ctx.clearRect(0, 0, cssWidth, cssHeight);
        ctx.drawImage(img, 0, 0, cssWidth, cssHeight);
      }
    },
    []
  );

  const renderPage = useCallback(
    async (pageNumber: number, zoom: number) => {
      if (!documentId || !canvasRef.current) return;

      // Fast redraw if only zoom changed for the already-decoded page
      const cached = cachedPageRef.current;
      if (cached && cached.docId === documentId && cached.pageNumber === pageNumber) {
        drawImageToCanvas(cached.img, cached.logicalSize, zoom);
        setError(null);
        setHasPage(true);
        setRenderedSize(cached.logicalSize);
        return;
      }

      if (typeof fetch !== 'function') return;

      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      setLoading(true);
      setError(null);

      let objectUrl: string | null = null;
      try {
        const blob = await fetchRenderedPageBlob(documentId, pageNumber, controller.signal);
        if (controller.signal.aborted || !mountedRef.current) return;

        if (typeof URL === 'undefined' || typeof URL.createObjectURL !== 'function') {
          return;
        }

        objectUrl = URL.createObjectURL(blob);
        const img = await loadImageElement(objectUrl);
        if (controller.signal.aborted || !mountedRef.current) return;

        const naturalW = img.naturalWidth || DEFAULT_PAGE_SIZE.width;
        const naturalH = img.naturalHeight || DEFAULT_PAGE_SIZE.height;
        const logicalWidth = BASE_LOGICAL_WIDTH;
        const logicalHeight = Math.max(1, Math.round(logicalWidth * (naturalH / naturalW)));
        const logicalSize: RenderedPageSize = { width: logicalWidth, height: logicalHeight };

        cachedPageRef.current = { docId: documentId, pageNumber, img, logicalSize };
        drawImageToCanvas(img, logicalSize, zoom);
        setRenderedSize(logicalSize);
        setHasPage(true);
      } catch (err: any) {
        if (err?.name === 'AbortError' || controller.signal.aborted || !mountedRef.current) {
          return;
        }
        setError(err?.message || 'Không thể tải trang tài liệu PDF.');
        setHasPage(false);
      } finally {
        if (objectUrl && typeof URL !== 'undefined' && typeof URL.revokeObjectURL === 'function') {
          URL.revokeObjectURL(objectUrl);
        }
        if (mountedRef.current && !controller.signal.aborted) {
          setLoading(false);
        }
      }
    },
    [documentId, drawImageToCanvas]
  );

  const retry = useCallback(
    (pageNumber: number, zoom: number) => {
      cachedPageRef.current = null;
      return renderPage(pageNumber, zoom);
    },
    [renderPage]
  );

  return { canvasRef, renderPage, loading, error, renderedSize, hasPage, retry };
}
