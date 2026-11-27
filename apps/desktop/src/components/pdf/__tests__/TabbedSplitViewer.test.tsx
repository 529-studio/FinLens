import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { TabbedSplitViewer, type OpenPdfTab } from '../TabbedSplitViewer';

// Mock PdfViewer so tests don't require real pdfjs-dist canvas workers
vi.mock('../PdfViewer', () => ({
  PdfViewer: ({ documentId, pageNumber, zoomLevel }: { documentId: string; pageNumber: number; zoomLevel: number }) => (
    <div data-testid={`mock-pdf-${documentId}`}>
      {documentId} - Page {pageNumber} ({Math.round(zoomLevel * 100)}%)
    </div>
  ),
}));

const SAMPLE_TABS: OpenPdfTab[] = [
  { documentId: 'VNM_2022_COMP', title: 'VNM 2022', totalPages: 5 },
  { documentId: 'VNM_2023_COMP', title: 'VNM 2023', totalPages: 6 },
];

describe('TabbedSplitViewer', () => {
  it('renders dual-pane side-by-side PDFs and synchronizes page navigation when sync is enabled', () => {
    const onSelectA = vi.fn();
    const onSelectB = vi.fn();

    render(
      <TabbedSplitViewer
        openTabs={SAMPLE_TABS}
        paneADocId="VNM_2022_COMP"
        paneBDocId="VNM_2023_COMP"
        onSelectPaneADoc={onSelectA}
        onSelectPaneBDoc={onSelectB}
      />
    );

    expect(screen.getByTestId('pdf-pane-a')).toBeTruthy();
    expect(screen.getByTestId('pdf-pane-b')).toBeTruthy();
    expect(screen.getByTestId('pane-a-page-indicator').textContent).toBe('1/5');
    expect(screen.getByTestId('pane-b-page-indicator').textContent).toBe('1/6');

    // Sync enabled by default: clicking next page on Pane A also advances Pane B
    fireEvent.click(screen.getByTestId('pane-a-next-page'));
    expect(screen.getByTestId('pane-a-page-indicator').textContent).toBe('2/5');
    expect(screen.getByTestId('pane-b-page-indicator').textContent).toBe('2/6');

    // Disable sync: Pane A advances independently without moving Pane B
    fireEvent.click(screen.getByTestId('sync-page-toggle-btn'));
    fireEvent.click(screen.getByTestId('pane-a-next-page'));
    expect(screen.getByTestId('pane-a-page-indicator').textContent).toBe('3/5');
    expect(screen.getByTestId('pane-b-page-indicator').textContent).toBe('2/6');
  });

  it('switches tabs and toggles single vs dual pane mode with >=48px touch targets', () => {
    const onSelectA = vi.fn();
    const onSelectB = vi.fn();

    render(
      <TabbedSplitViewer
        openTabs={SAMPLE_TABS}
        paneADocId="VNM_2022_COMP"
        paneBDocId="VNM_2023_COMP"
        onSelectPaneADoc={onSelectA}
        onSelectPaneBDoc={onSelectB}
      />
    );

    fireEvent.click(screen.getByTestId('pdf-tab-VNM_2023_COMP'));
    expect(onSelectA).toHaveBeenCalledWith('VNM_2023_COMP');

    const dualToggle = screen.getByTestId('dual-pane-toggle-btn');
    const syncToggle = screen.getByTestId('sync-page-toggle-btn');
    expect(dualToggle.className).toContain('min-h-[48px]');
    expect(syncToggle.className).toContain('min-h-[48px]');

    // Switch to single pane
    fireEvent.click(dualToggle);
    expect(screen.queryByTestId('pdf-pane-b')).toBeNull();
  });

  it('renders all 3 resilient UI states (Skeleton, Error with Retry, Empty)', () => {
    const onRetry = vi.fn();
    const onOpenPicker = vi.fn();

    const { rerender } = render(
      <TabbedSplitViewer
        openTabs={SAMPLE_TABS}
        paneADocId="VNM_2022_COMP"
        paneBDocId="VNM_2023_COMP"
        isLoading={true}
        onSelectPaneADoc={vi.fn()}
        onSelectPaneBDoc={vi.fn()}
      />
    );
    expect(screen.getByTestId('tabbed-split-skeleton')).toBeTruthy();

    rerender(
      <TabbedSplitViewer
        openTabs={SAMPLE_TABS}
        paneADocId="VNM_2022_COMP"
        paneBDocId="VNM_2023_COMP"
        errorMessage="Lỗi kết nối daemon"
        onRetry={onRetry}
        onSelectPaneADoc={vi.fn()}
        onSelectPaneBDoc={vi.fn()}
      />
    );
    expect(screen.getByTestId('tabbed-split-error')).toBeTruthy();
    fireEvent.click(screen.getByTestId('tabbed-split-retry-btn'));
    expect(onRetry).toHaveBeenCalledTimes(1);

    rerender(
      <TabbedSplitViewer
        openTabs={[]}
        paneADocId=""
        paneBDocId={null}
        onOpenDocumentPicker={onOpenPicker}
        onSelectPaneADoc={vi.fn()}
        onSelectPaneBDoc={vi.fn()}
      />
    );
    expect(screen.getByTestId('tabbed-split-empty')).toBeTruthy();
    fireEvent.click(screen.getByTestId('tabbed-split-open-picker-btn'));
    expect(onOpenPicker).toHaveBeenCalledTimes(1);
  });
});
