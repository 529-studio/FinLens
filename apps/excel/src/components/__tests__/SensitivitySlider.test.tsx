// @vitest-environment jsdom

/**
 * Component Tests for SensitivitySlider
 * Validates 3 UI states, kiosk touch targets (>= 48px), Rule 15 zero raw emojis,
 * and interactive formula recalculation.
 * Governed by Sprint 10 Task S10-05, AGENTS.md Rule 1, Rule 13, Rule 15.
 */

import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup, waitFor } from '@testing-library/react';
import { SensitivitySlider } from '../SensitivitySlider';

describe('SensitivitySlider Component', () => {
  afterEach(() => {
    cleanup();
  });

  it('renders standard slider UI with header, driver cell, and >=48px kiosk controls', () => {
    const { container } = render(<SensitivitySlider />);

    expect(screen.getByTestId('sensitivity-slider-container')).toBeDefined();
    expect(screen.getByText('Độ Nhạy Mô Hình & Kiểm Toán Công Thức')).toBeDefined();
    expect(screen.getByText('B5')).toBeDefined();

    // Check kiosk ergonomic touch target minimum height on interactive buttons
    const buttons = container.querySelectorAll('button');
    expect(buttons.length).toBeGreaterThan(0);
    buttons.forEach((btn) => {
      expect(btn.className).toContain('min-h-[48px]');
    });

    // Check zero raw Unicode emojis in rendered container
    const emojiRegex = /\p{Extended_Pictographic}/u;
    expect(emojiRegex.test(container.innerHTML)).toBe(false);
  });

  it('renders Skeleton Loading state when isLoading prop is true', () => {
    render(<SensitivitySlider isLoading={true} />);

    const skeleton = screen.getByTestId('sensitivity-skeleton');
    expect(skeleton).toBeDefined();
    expect(skeleton.querySelectorAll('.animate-pulse').length).toBe(3);
  });

  it('renders Error state with retry button when model contains circular references', () => {
    const cyclicCells = {
      A1: { formula: '=B1 + 1' },
      B1: { formula: '=A1 + 1' },
    };

    render(
      <SensitivitySlider
        initialDriverAddress="A1"
        customCells={cyclicCells}
      />
    );

    const errorContainer = screen.getByTestId('sensitivity-error');
    expect(errorContainer).toBeDefined();
    expect(screen.getByText(/Circular Reference/i)).toBeDefined();

    const retryBtn = screen.getByRole('button', { name: /Thử lại/i });
    expect(retryBtn).toBeDefined();
    expect(retryBtn.className).toContain('min-h-[48px]');
  });

  it('renders Empty state when customCells is empty', () => {
    render(<SensitivitySlider customCells={{}} />);

    const emptyContainer = screen.getByTestId('sensitivity-empty');
    expect(emptyContainer).toBeDefined();
    expect(screen.getByText('Chưa có ô công thức nào được nạp')).toBeDefined();
  });

  it('updates scenario and recalculates metrics when preset chips are clicked', () => {
    render(<SensitivitySlider />);

    // Click 'Lạc quan' preset chip (+5%)
    const optChip = screen.getByRole('button', { name: /Lạc quan/i });
    fireEvent.click(optChip);

    // Delta indicator should show (+5.0%)
    expect(screen.getByText('(+5.0%)')).toBeDefined();

    // Reset back to Base (0%)
    const resetBtn = screen.getByRole('button', { name: /Cơ sở \(0%\)/i });
    fireEvent.click(resetBtn);
    expect(screen.getByText('(+0.0%)')).toBeDefined();
  });

  it('toggles formula dependency tree drawer when clicked', () => {
    render(<SensitivitySlider />);

    expect(screen.queryByTestId('formula-tree-drawer')).toBeNull();

    const toggleBtn = screen.getByRole('button', {
      name: /Cây Phụ Thuộc & Kiểm Toán Công Thức/i,
    });
    fireEvent.click(toggleBtn);

    const drawer = screen.getByTestId('formula-tree-drawer');
    expect(drawer).toBeDefined();
    expect(screen.getByText('[VERIFIED AUDIT TRAIL]')).toBeDefined();
    expect(screen.getByText(/Topological Order/i)).toBeDefined();
  });

  it('invokes onRecalculate callback when apply button is clicked', async () => {
    const onRecalc = vi.fn();
    render(<SensitivitySlider onRecalculate={onRecalc} />);

    const applyBtn = screen.getByRole('button', {
      name: /Áp Dụng Kịch Bản Vào Bảng Tính Excel/i,
    });
    fireEvent.click(applyBtn);

    await waitFor(() => {
      expect(onRecalc).toHaveBeenCalled();
    });

    const resultArg = onRecalc.mock.calls[0][0];
    expect(resultArg.driverAddress).toBe('B5');
    expect(resultArg.impactedKeyMetrics.length).toBeGreaterThan(0);
    expect(resultArg.impactedKeyMetrics[0].baseValue).toBeGreaterThan(0);
  });
});
