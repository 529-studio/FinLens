/**
 * Vitest Unit Test Suite for AuditedCellDrawer Component
 * Governed by Sprint 12 Task S12-05, AGENTS.md Rule 13, Rule 15 (Zero Emoji),
 * and frontend-4file-and-resilient-ui (3 UI states, >=48px touch targets).
 */

import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { AuditedCellDrawer, type AuditedCellData } from '../AuditedCellDrawer';

const mockAuditedCell: AuditedCellData = {
  cellAddress: 'Sheet1!B4',
  lineItem: 'Doanh thu thuần từ bán hàng và cung cấp dịch vụ',
  value: 60478000000000,
  formattedValue: '60,478 tỷ VNĐ',
  auditStatus: 'verified',
  footnoteNumber: 'VI.24',
  footnoteTitle: 'Doanh thu bán hàng và cung cấp dịch vụ theo bộ phận',
  footnoteSummary: 'Bao gồm doanh thu xuất khẩu sang thị trường Mỹ, Nhật Bản và nội địa.',
  documentId: 'VNM_2023_AUDITED',
  pageNumber: 32,
  boundingBox: [150, 100, 320, 900],
  confidence: 0.985,
  lastAuditedAt: 1732490000,
  auditorName: 'Nguyễn Văn Kiểm',
};

describe('AuditedCellDrawer Component', () => {
  it('renders audited cell provenance details and tags when open', () => {
    const handleJump = vi.fn();
    const handleClose = vi.fn();

    render(
      <AuditedCellDrawer
        isOpen={true}
        cellData={mockAuditedCell}
        onClose={handleClose}
        onJumpToPdf={handleJump}
      />
    );

    expect(screen.getByTestId('audited-cell-drawer')).toBeDefined();
    expect(screen.getByText('Sheet1!B4')).toBeDefined();
    expect(screen.getByText(/Doanh thu thuần từ bán hàng/)).toBeDefined();
    expect(screen.getByText(/VI.24/)).toBeDefined();
    expect(screen.getAllByText(/Trang 32/).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('98.5%')).toBeDefined();

    // Verify "Jump to PDF Source" button has >=48px touch target
    const jumpBtn = screen.getByTestId('drawer-jump-pdf-btn');
    expect(jumpBtn.className).toContain('min-h-[48px]');
    fireEvent.click(jumpBtn);
    expect(handleJump).toHaveBeenCalledWith('VNM_2023_AUDITED', 32, [150, 100, 320, 900]);
  });

  it('renders 1. Skeleton Loading State when isLoading is true', () => {
    render(
      <AuditedCellDrawer
        isOpen={true}
        cellData={null}
        isLoading={true}
        onClose={vi.fn()}
      />
    );

    expect(screen.getByTestId('drawer-skeleton')).toBeDefined();
  });

  it('renders 2. Error State with retry button satisfying >=48px touch target', () => {
    const handleRetry = vi.fn();
    render(
      <AuditedCellDrawer
        isOpen={true}
        cellData={null}
        errorMessage="Không thể kết nối daemon để tải thông tin thuyết minh"
        onRetry={handleRetry}
        onClose={vi.fn()}
      />
    );

    expect(screen.getByTestId('drawer-error')).toBeDefined();
    const retryBtn = screen.getByTestId('drawer-retry-btn');
    expect(retryBtn.className).toContain('min-h-[48px]');
    fireEvent.click(retryBtn);
    expect(handleRetry).toHaveBeenCalledOnce();
  });

  it('renders 3. Actionable Empty State when no audited cell is selected', () => {
    render(
      <AuditedCellDrawer
        isOpen={true}
        cellData={null}
        onClose={vi.fn()}
      />
    );

    expect(screen.getByTestId('drawer-empty')).toBeDefined();
    expect(screen.getByText(/Chọn một ô số liệu tài chính đã kiểm toán/)).toBeDefined();
  });

  it('invokes onInsertAuditNote callback with >=48px touch target', () => {
    const handleInsertNote = vi.fn();
    render(
      <AuditedCellDrawer
        isOpen={true}
        cellData={mockAuditedCell}
        onClose={vi.fn()}
        onInsertAuditNote={handleInsertNote}
      />
    );

    const noteBtn = screen.getByTestId('drawer-insert-note-btn');
    expect(noteBtn.className).toContain('min-h-[48px]');
    fireEvent.click(noteBtn);
    expect(handleInsertNote).toHaveBeenCalledWith(mockAuditedCell);
  });
});
