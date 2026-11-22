/**
 * FootnoteChip Component: Interactive Footnote Deep-Linking Badge
 * Governed by 529 Engineering Standards:
 * - Kiosk Ergonomics (min-h-[48px] touch targets)
 * - Rule 15: Zero-Emoji UI Standard (vector SVG only)
 * - Visual Grounding & Financial Footnote Disambiguation
 */

import { type FC } from 'react';
import { BookOpen } from 'lucide-react';
import { FootnoteReferenceDTO } from '../../types/visual_rag.types';

interface FootnoteChipProps {
  footnote: FootnoteReferenceDTO;
  isActive?: boolean;
  onClick: (footnote: FootnoteReferenceDTO) => void;
}

export const FootnoteChip: FC<FootnoteChipProps> = ({ footnote, isActive = false, onClick }) => {
  const labelText = `TM ${footnote.footnote_number}: ${footnote.line_item}`;
  const pageText = `Trang ${footnote.page_number}`;

  return (
    <button
      type="button"
      role="button"
      aria-label={`Chuyển đến ${labelText}, ${pageText}`}
      title={`${footnote.footnote_title} (Trang ${footnote.page_number}): ${footnote.summary}`}
      onClick={() => onClick(footnote)}
      className={`min-h-[48px] px-3.5 py-2 border text-xs rounded-xl flex items-center space-x-2.5 transition cursor-pointer text-left select-none ${
        isActive
          ? 'bg-amber-600/90 hover:bg-amber-600 border-amber-400 text-white font-medium shadow-md ring-2 ring-amber-400/30'
          : 'bg-amber-950/50 hover:bg-amber-900/60 border-amber-800/60 text-amber-200'
      }`}
    >
      <div className={`p-1.5 rounded-lg shrink-0 ${isActive ? 'bg-amber-700/80 text-white' : 'bg-amber-900/60 text-amber-300'}`}>
        <BookOpen className="w-3.5 h-3.5" />
      </div>
      <div className="flex flex-col min-w-0 pr-1">
        <span className="font-semibold truncate max-w-[220px] 2xl:max-w-xs">{labelText}</span>
        <span className={`text-[10px] ${isActive ? 'text-amber-100' : 'text-amber-400/80'}`}>
          {pageText} &bull; {footnote.footnote_title}
        </span>
      </div>
    </button>
  );
};
