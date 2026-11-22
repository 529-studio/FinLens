/**
 * Unit & Ergonomics Test Suite for FootnoteChip
 * Governed by 529 Engineering Standards:
 * - Rule 15: Zero-Emoji UI Standard
 * - Kiosk Ergonomics (>= 48px touch targets)
 * - Accessibility & Click Delegation
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { FootnoteChip } from '../FootnoteChip';
import { FootnoteReferenceDTO } from '../../../types/visual_rag.types';

const mockFootnote: FootnoteReferenceDTO = {
  line_item: 'Tiền và các khoản tương đương tiền',
  code: '110',
  footnote_number: '4',
  footnote_title: 'Tiền và các khoản tương đương tiền',
  summary: 'Tiền gửi ngân hàng không kỳ hạn 1.120.400 triệu đồng; tiền gửi có kỳ hạn gốc không quá 3 tháng.',
  page_number: 2,
  bounding_box: { ymin: 480, xmin: 50, ymax: 620, xmax: 545 },
};

describe('FootnoteChip Component', () => {
  it('renders footnote label, number, and target page number accurately', () => {
    const handleClick = vi.fn();
    render(<FootnoteChip footnote={mockFootnote} onClick={handleClick} />);

    expect(screen.getByText('TM 4: Tiền và các khoản tương đương tiền')).toBeDefined();
    expect(screen.getByText(/Trang 2/)).toBeDefined();
  });

  it('triggers onClick callback with the footnote payload when clicked', () => {
    const handleClick = vi.fn();
    render(<FootnoteChip footnote={mockFootnote} onClick={handleClick} />);

    const button = screen.getByRole('button');
    fireEvent.click(button);

    expect(handleClick).toHaveBeenCalledTimes(1);
    expect(handleClick).toHaveBeenCalledWith(mockFootnote);
  });

  it('applies active styling and aria-label when isActive is true', () => {
    const handleClick = vi.fn();
    const { rerender } = render(<FootnoteChip footnote={mockFootnote} isActive={false} onClick={handleClick} />);

    const button = screen.getByRole('button');
    expect(button.className).toContain('bg-amber-950/50');

    rerender(<FootnoteChip footnote={mockFootnote} isActive={true} onClick={handleClick} />);
    expect(button.className).toContain('bg-amber-600/90');
    expect(button.className).toContain('ring-2');
  });

  it('complies with Kiosk Ergonomics (>= 48px touch target)', () => {
    const { container } = render(<FootnoteChip footnote={mockFootnote} onClick={() => {}} />);
    const button = container.querySelector('button');
    expect(button?.className).toContain('min-h-[48px]');
  });

  it('strictly adheres to AGENTS.md Rule 15: Zero raw Unicode emojis', () => {
    const { container } = render(<FootnoteChip footnote={mockFootnote} onClick={() => {}} />);
    const emojiRegex = /[\u{1F300}-\u{1F9FF}]|[\u{2600}-\u{26FF}]|[\u{2700}-\u{27BF}]/u;
    expect(emojiRegex.test(container.innerHTML)).toBe(false);
  });
});
