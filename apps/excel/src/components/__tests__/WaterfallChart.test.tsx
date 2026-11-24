// @vitest-environment jsdom

/**
 * Component Tests for WaterfallChart
 * Validates 3 UI states, kiosk touch targets (>= 48px), Rule 15 zero raw emojis,
 * multi-scenario switching, and PDF grounding export.
 * Governed by Sprint 11 Task S11-05, AGENTS.md Rule 1, Rule 13, Rule 15.
 */

import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { WaterfallChart } from '../WaterfallChart';

describe('WaterfallChart Component', () => {
  afterEach(() => {
    cleanup();
  });

  it('renders standard Waterfall Chart with SVG canvas, headers, and scenario chips', () => {
    const { container } = render(<WaterfallChart />);

    expect(screen.getByTestId('waterfall-chart-container')).toBeDefined();
    expect(screen.getByText('Cầu Nối Lợi Nhuận & So Sánh Kịch Bản')).toBeDefined();
    expect(screen.getByText(/Vinamilk \(VNM\)/i)).toBeDefined();
    expect(screen.getByTestId('waterfall-svg')).toBeDefined();

    // Check all bars rendered
    expect(screen.getByTestId('waterfall-bar-revenue')).toBeDefined();
    expect(screen.getByTestId('waterfall-bar-cogs')).toBeDefined();
    expect(screen.getByTestId('waterfall-bar-gross_profit')).toBeDefined();
    expect(screen.getByTestId('waterfall-bar-net_income')).toBeDefined();

    // Check zero raw Unicode emojis
    const emojiRegex = /\p{Extended_Pictographic}/u;
    expect(emojiRegex.test(container.innerHTML)).toBe(false);
  });

  it('renders Skeleton Loading state when isLoading is true', () => {
    render(<WaterfallChart isLoading={true} />);

    const skeleton = screen.getByTestId('waterfall-skeleton');
    expect(skeleton).toBeDefined();
    expect(skeleton.className).toContain('animate-pulse');
  });

  it('renders Error state with >=48px retry button when errorMessage is provided', () => {
    const handleRetry = vi.fn();
    render(
      <WaterfallChart
        errorMessage="Không thể nạp dữ liệu biến động"
        onRetry={handleRetry}
      />
    );

    const errorContainer = screen.getByTestId('waterfall-error');
    expect(errorContainer).toBeDefined();
    expect(screen.getByText('Không thể nạp dữ liệu biến động')).toBeDefined();

    const retryBtn = screen.getByTestId('waterfall-retry-btn');
    expect(retryBtn).toBeDefined();
    expect(retryBtn.className).toContain('min-h-[48px]');

    fireEvent.click(retryBtn);
    expect(handleRetry).toHaveBeenCalledTimes(1);
  });

  it('renders Empty state when initialDrivers is empty', () => {
    const handleRetry = vi.fn();
    render(<WaterfallChart initialDrivers={[]} onRetry={handleRetry} />);

    const emptyContainer = screen.getByTestId('waterfall-empty');
    expect(emptyContainer).toBeDefined();
    expect(screen.getByText('Chưa có dữ liệu phân tích biến động')).toBeDefined();

    const sampleBtn = screen.getByTestId('waterfall-load-sample-btn');
    expect(sampleBtn).toBeDefined();
    expect(sampleBtn.className).toContain('min-h-[48px]');

    fireEvent.click(sampleBtn);
    expect(handleRetry).toHaveBeenCalledTimes(1);
  });

  it('switches scenarios and recalculates deltas when Bull and Bear chips are clicked', () => {
    render(<WaterfallChart />);

    // Click Bull scenario chip (+10%)
    const bullChip = screen.getByTestId('scenario-chip-bull');
    fireEvent.click(bullChip);

    expect(screen.getByText(/Tăng trưởng doanh thu \+10%/i)).toBeDefined();

    // Click Bear scenario chip (-10%)
    const bearChip = screen.getByTestId('scenario-chip-bear');
    fireEvent.click(bearChip);

    expect(screen.getByText(/Suy giảm doanh thu -10%/i)).toBeDefined();
  });

  it('opens detailed drill-down card with footnote citation when a bar is clicked', () => {
    const handleCitationClick = vi.fn();
    render(<WaterfallChart onCitationClick={handleCitationClick} />);

    // Click on COGS bar
    const cogsBar = screen.getByTestId('waterfall-bar-cogs');
    fireEvent.click(cogsBar);

    const detailCard = screen.getByTestId('waterfall-detail-card');
    expect(detailCard).toBeDefined();
    expect(screen.getByText('Giá vốn hàng bán')).toBeDefined();
    expect(detailCard.textContent).toContain('TM 25');

    // Click view citation button
    const viewBtn = screen.getByTestId('view-citation-btn');
    expect(viewBtn).toBeDefined();
    expect(viewBtn.className).toContain('min-h-[48px]');

    fireEvent.click(viewBtn);
    expect(handleCitationClick).toHaveBeenCalledTimes(1);
  });

  it('triggers PDF export report generation when export button is clicked', () => {
    render(<WaterfallChart />);

    const exportBtn = screen.getByTestId('waterfall-export-btn');
    expect(exportBtn).toBeDefined();
    expect(exportBtn.className).toContain('min-h-[48px]');

    // Mock window.open
    const originalOpen = window.open;
    window.open = vi.fn().mockReturnValue({
      document: {
        open: vi.fn(),
        write: vi.fn(),
        close: vi.fn(),
      },
      focus: vi.fn(),
      print: vi.fn(),
    });

    fireEvent.click(exportBtn);
    expect(window.open).toHaveBeenCalledTimes(1);

    window.open = originalOpen;
  });

  it('enforces kiosk ergonomics (>= 48px touch targets) on all interactive buttons', () => {
    const { container } = render(<WaterfallChart />);

    const buttons = container.querySelectorAll('button');
    expect(buttons.length).toBeGreaterThan(0);
    buttons.forEach((btn) => {
      expect(btn.className).toContain('min-h-[48px]');
    });
  });

  it('strictly adheres to Rule 15: Zero raw Unicode emojis in rendered UI', () => {
    const { container } = render(<WaterfallChart />);

    const emojiRegex = /\p{Extended_Pictographic}/u;
    expect(emojiRegex.test(container.innerHTML)).toBe(false);
  });
});
