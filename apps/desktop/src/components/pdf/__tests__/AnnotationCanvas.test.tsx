/**
 * Vitest Test Suite for Desktop Native PDF Highlight Annotation Layer & Visual Comment Pinning
 * Governed by Sprint 12 Task S12-03, AGENTS.md Rule 13, Rule 15 (Zero Emoji),
 * and frontend-4file-and-resilient-ui (3 UI states, >=48px touch targets).
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { AnnotationCanvas } from '../AnnotationCanvas';
import type { AuditAnnotationDTO } from '../../../types/session_sync.types';

const mockAnnotations: AuditAnnotationDTO[] = [
  {
    annotation_id: 'ann-1',
    document_id: 'VNM_2023_AUDITED',
    page_number: 1,
    bounding_box: [100, 150, 300, 850],
    comment: 'Cần kiểm tra lại mục Doanh thu tài chính ghi nhận 1,200 tỷ.',
    author_id: 'usr-auditor-1',
    author_name: 'Nguyễn Văn Kiểm',
    created_at: 1732490000,
    resolved: false,
  },
  {
    annotation_id: 'ann-2',
    document_id: 'VNM_2023_AUDITED',
    page_number: 1,
    bounding_box: [500, 200, 700, 800],
    comment: 'Khoản chi phí bán hàng tăng 15% so với cùng kỳ.',
    author_id: 'usr-senior-2',
    author_name: 'Trần Thị Trưởng',
    created_at: 1732491000,
    resolved: true,
    resolved_by: 'Nguyễn Văn Kiểm',
  },
  {
    annotation_id: 'ann-3',
    document_id: 'VNM_2023_AUDITED',
    page_number: 2, // Different page
    bounding_box: [100, 100, 200, 500],
    comment: 'Trang 2 ghi chú tài sản dở dang dài hạn.',
    author_id: 'usr-auditor-1',
    author_name: 'Nguyễn Văn Kiểm',
    created_at: 1732492000,
    resolved: false,
  },
];

describe('AnnotationCanvas Component', () => {
  it('renders annotations only for current page', () => {
    render(
      <AnnotationCanvas
        documentId="VNM_2023_AUDITED"
        pageNumber={1}
        renderedWidth={800}
        renderedHeight={1000}
        annotations={mockAnnotations}
      />
    );

    // Page 1 should have ann-1 and ann-2, but not ann-3
    expect(screen.getByTestId('annotation-box-ann-1')).toBeDefined();
    expect(screen.getByTestId('annotation-box-ann-2')).toBeDefined();
    expect(screen.queryByTestId('annotation-box-ann-3')).toBeNull();
  });

  it('renders 1. Skeleton Loading State when isLoading is true', () => {
    render(
      <AnnotationCanvas
        documentId="VNM_2023_AUDITED"
        pageNumber={1}
        renderedWidth={800}
        renderedHeight={1000}
        annotations={[]}
        isLoading={true}
      />
    );

    expect(screen.getByTestId('annotation-skeleton')).toBeDefined();
  });

  it('renders 2. Error State with retry button satisfying >=48px touch target', () => {
    const handleRetry = vi.fn();
    render(
      <AnnotationCanvas
        documentId="VNM_2023_AUDITED"
        pageNumber={1}
        renderedWidth={800}
        renderedHeight={1000}
        annotations={[]}
        errorMessage="Không thể tải danh sách ghi chú từ WebSocket"
        onRetry={handleRetry}
      />
    );

    const errorContainer = screen.getByTestId('annotation-error');
    expect(errorContainer).toBeDefined();
    expect(screen.getByText(/Không thể tải danh sách ghi chú/)).toBeDefined();

    const retryBtn = screen.getByTestId('annotation-retry-btn');
    expect(retryBtn.className).toContain('min-h-[48px]');
    fireEvent.click(retryBtn);
    expect(handleRetry).toHaveBeenCalledOnce();
  });

  it('renders 3. Actionable Empty State when 0 annotations exist', () => {
    render(
      <AnnotationCanvas
        documentId="VNM_2023_AUDITED"
        pageNumber={1}
        renderedWidth={800}
        renderedHeight={1000}
        annotations={[]}
      />
    );

    expect(screen.getByTestId('annotation-empty')).toBeDefined();
    expect(screen.getByText(/Chưa có ghi chú nào/)).toBeDefined();
  });

  it('opens comment drawer/popover when comment pin is clicked with resolve/delete triggers', () => {
    const handleResolve = vi.fn();
    const handleDelete = vi.fn();

    render(
      <AnnotationCanvas
        documentId="VNM_2023_AUDITED"
        pageNumber={1}
        renderedWidth={800}
        renderedHeight={1000}
        annotations={mockAnnotations}
        onResolveAnnotation={handleResolve}
        onDeleteAnnotation={handleDelete}
      />
    );

    // Click pin for ann-1
    const pin1 = screen.getByTestId('annotation-pin-ann-1');
    fireEvent.click(pin1);

    // Popover should display comment details
    expect(screen.getByTestId('annotation-popover-ann-1')).toBeDefined();
    expect(screen.getByText(/Cần kiểm tra lại mục Doanh thu tài chính/)).toBeDefined();
    expect(screen.getByText('Nguyễn Văn Kiểm')).toBeDefined();

    // Verify action buttons satisfy >=48px touch targets
    const resolveBtn = screen.getByTestId('annotation-resolve-btn');
    expect(resolveBtn.className).toContain('min-h-[48px]');
    fireEvent.click(resolveBtn);
    expect(handleResolve).toHaveBeenCalledWith('ann-1');

    const deleteBtn = screen.getByTestId('annotation-delete-btn');
    expect(deleteBtn.className).toContain('min-h-[48px]');
    fireEvent.click(deleteBtn);
    expect(handleDelete).toHaveBeenCalledWith('ann-1');
  });

  it('allows interactive drag-to-select box creation when drawing is enabled', () => {
    const handleAdd = vi.fn();
    render(
      <AnnotationCanvas
        documentId="VNM_2023_AUDITED"
        pageNumber={1}
        renderedWidth={800}
        renderedHeight={1000}
        annotations={[]}
        isDrawingEnabled={true}
        onAddAnnotation={handleAdd}
      />
    );

    const canvas = screen.getByTestId('annotation-canvas-container');

    // Simulate drag from (100, 100) to (300, 400)
    fireEvent.mouseDown(canvas, { clientX: 100, clientY: 100 });
    fireEvent.mouseMove(canvas, { clientX: 300, clientY: 400 });
    fireEvent.mouseUp(canvas, { clientX: 300, clientY: 400 });

    // Dialog for new annotation comment should appear
    const commentInput = screen.getByTestId('annotation-comment-input');
    fireEvent.change(commentInput, { target: { value: 'Khoản mục chi phí bất thường' } });

    const submitBtn = screen.getByTestId('annotation-save-btn');
    expect(submitBtn.className).toContain('min-h-[48px]');
    fireEvent.click(submitBtn);

    expect(handleAdd).toHaveBeenCalledOnce();
    const calledWith = handleAdd.mock.calls[0][0];
    expect(calledWith.document_id).toBe('VNM_2023_AUDITED');
    expect(calledWith.page_number).toBe(1);
    expect(calledWith.comment).toBe('Khoản mục chi phí bất thường');
    expect(calledWith.bounding_box).toBeDefined();
    expect(calledWith.bounding_box[0]).toBeGreaterThanOrEqual(0);
    expect(calledWith.bounding_box[2]).toBeLessThanOrEqual(1000);
  });
});
