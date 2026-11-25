import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { PdfViewer } from '../PdfViewer';
import * as fetchApi from '../../../api/visual_rag.fetch';

describe('PdfViewer Component', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders presentation container on initial mount', () => {
    vi.spyOn(fetchApi, 'fetchRenderedPageBlob').mockImplementation(() => new Promise(() => {}));
    render(<PdfViewer documentId="doc1" pageNumber={1} zoomLevel={1} />);
    expect(screen.getByRole('presentation')).toBeDefined();
    expect(screen.getByTestId('pdf-viewer-skeleton')).toBeDefined();
  });

  it('renders empty state when documentId is empty', () => {
    render(<PdfViewer documentId="" pageNumber={1} zoomLevel={1} />);
    expect(screen.getByRole('presentation')).toBeDefined();
    expect(screen.getByTestId('pdf-viewer-empty')).toBeDefined();
  });

  it('renders error state with >=48px retry button when page fetch fails', async () => {
    vi.spyOn(fetchApi, 'fetchRenderedPageBlob').mockRejectedValueOnce(new Error('404 Page missing'));
    render(<PdfViewer documentId="doc1" pageNumber={2} zoomLevel={1} />);

    await waitFor(() => {
      expect(screen.getByTestId('pdf-viewer-error')).toBeDefined();
    });
    const retryBtn = screen.getByTestId('pdf-viewer-retry-btn');
    expect(retryBtn.className).toContain('min-h-[48px]');
  });
});
