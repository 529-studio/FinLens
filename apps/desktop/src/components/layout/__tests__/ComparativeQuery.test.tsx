/**
 * Component tests for Multi-Document Comparative Visual RAG UI (Sprint 7 Task S7-02)
 * Governed by 529 Engineering Standards:
 * - 3 States: Skeleton, Error with Retry, Empty State
 * - Kiosk Ergonomics: >= 48px interactive target size
 * - Zero Unicode Emojis: Lucide React vector SVGs only
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { SplitView } from '../SplitView.component';

// Mock child components
vi.mock('../../pdf/PdfViewer', () => ({
  PdfViewer: () => <div data-testid="mock-pdf-viewer">PDF Viewer</div>,
}));

vi.mock('../../pdf/BoundingBoxOverlay', () => ({
  BoundingBoxOverlay: () => <div data-testid="mock-bbox-overlay">Bounding Box Overlay</div>,
}));

vi.mock('../../settings/SettingsDialog', () => ({
  SettingsDialog: () => null,
}));

vi.mock('../../../hooks/useSettings.hook', () => ({
  useSettings: () => ({
    inferenceMode: 'auto',
    updateInferenceMode: vi.fn(),
  }),
}));

vi.mock('../../../hooks/useBridgeServer', () => ({
  useBridgeServer: vi.fn(),
}));

describe('Comparative Visual RAG Component Tests', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it('renders mode tabs and defaults to single query mode', () => {
    render(
      <SplitView
        documentId="VNM_BCTC_2023_AUDITED"
        documentTitle="Vinamilk BCTC 2023"
      />
    );

    const singleTab = screen.getByTestId('tab-single-query');
    const compTab = screen.getByTestId('tab-comparative-query');

    expect(singleTab).toBeTruthy();
    expect(compTab).toBeTruthy();
    expect(singleTab.textContent).toContain('Truy vấn đơn lẻ');
    expect(compTab.textContent).toContain('So sánh đa BCTC (YoY)');
  });

  it('switches to comparative mode and displays document chips and suggestions', () => {
    render(
      <SplitView
        documentId="VNM_BCTC_2023_AUDITED"
        documentTitle="Vinamilk BCTC 2023"
      />
    );

    const compTab = screen.getByTestId('tab-comparative-query');
    fireEvent.click(compTab);

    // Document chips
    expect(screen.getByText('VNM_2022_COMP')).toBeTruthy();
    expect(screen.getByText('VNM_2023_COMP')).toBeTruthy();
    expect(screen.getByText('2 Tài liệu')).toBeTruthy();

    // Suggestion buttons
    const suggest1 = screen.getByTestId('btn-suggest-comparative-1');
    const suggest2 = screen.getByTestId('btn-suggest-comparative-2');
    expect(suggest1).toBeTruthy();
    expect(suggest2).toBeTruthy();
  });

  it('satisfies Kiosk touch target rule (min-height >= 48px)', () => {
    render(
      <SplitView
        documentId="VNM_BCTC_2023_AUDITED"
        documentTitle="Vinamilk BCTC 2023"
      />
    );

    const singleTab = screen.getByTestId('tab-single-query');
    const compTab = screen.getByTestId('tab-comparative-query');
    const submitBtn = screen.getByTestId('btn-submit-query');

    expect(singleTab.className).toContain('min-h-[48px]');
    expect(compTab.className).toContain('min-h-[48px]');
    expect(submitBtn.className).toContain('min-h-[48px]');
  });
});
