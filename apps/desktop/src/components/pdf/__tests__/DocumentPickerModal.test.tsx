import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { DocumentPickerModal } from '../DocumentPickerModal';

describe('DocumentPickerModal Component', () => {
  const baseProps = {
    isOpen: true,
    activeDocumentId: 'VNM_BCTC_2023_AUDITED',
    documents: ['VNM_BCTC_2023_AUDITED', 'VNM_2022_COMP', 'VNM_2023_COMP'],
    isLoading: false,
    errorMessage: null,
    isUploading: false,
    uploadError: null,
    onClose: vi.fn(),
    onRetry: vi.fn(),
    onSelectDocument: vi.fn(),
    onUploadFile: vi.fn(),
  };

  it('renders indexed documents and selects document on click with >=48px touch targets', () => {
    render(<DocumentPickerModal {...baseProps} />);
    const opt = screen.getByTestId('doc-option-VNM_2022_COMP');
    expect(opt.className).toContain('min-h-[48px]');
    fireEvent.click(opt);
    expect(baseProps.onSelectDocument).toHaveBeenCalledWith('VNM_2022_COMP');
    expect(baseProps.onClose).toHaveBeenCalled();
  });

  it('renders skeleton loading state', () => {
    render(<DocumentPickerModal {...baseProps} isLoading={true} />);
    expect(screen.getByTestId('doc-picker-skeleton')).toBeDefined();
  });

  it('renders error state with >=48px retry button', () => {
    render(<DocumentPickerModal {...baseProps} errorMessage="Daemon offline" />);
    expect(screen.getByTestId('doc-picker-error')).toBeDefined();
    const retry = screen.getByTestId('doc-picker-retry-btn');
    expect(retry.className).toContain('min-h-[48px]');
    fireEvent.click(retry);
    expect(baseProps.onRetry).toHaveBeenCalled();
  });

  it('renders empty state when no documents indexed', () => {
    render(<DocumentPickerModal {...baseProps} documents={[]} />);
    expect(screen.getByTestId('doc-picker-empty')).toBeDefined();
  });
});
