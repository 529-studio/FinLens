/**
 * BoundingBoxOverlay Component
 * Governed by 529 Engineering Standards:
 * - Dynamic SVG/Canvas presentation layer for Visual Grounding
 * - ADR-003: Scales [0, 1000] normalized coordinates to rendered dimensions & zoom
 * - 2.5s pulse animation with red #EF4444 highlight and shadow
 * - Pure presentation layer: zero mutation of underlying PDF binary
 */

import { type FC } from 'react';
import type { GroundedEvidenceDTO } from '../../types/visual_rag.types';
import { scaleBoundingBox, formatConfidence, type DimensionOptions } from '../../utils/coordinate_math';

export interface BoundingBoxOverlayProps extends Partial<DimensionOptions> {
  evidence: GroundedEvidenceDTO | null;
  renderedWidth: number;
  renderedHeight: number;
  zoomLevel?: number;
  dpiScale?: number;
  showBadge?: boolean;
  className?: string;
  onClick?: (evidence: GroundedEvidenceDTO) => void;
}

export const BoundingBoxOverlay: FC<BoundingBoxOverlayProps> = ({
  evidence,
  renderedWidth,
  renderedHeight,
  zoomLevel = 1.0,
  dpiScale = 1.0,
  showBadge = true,
  className = '',
  onClick,
}) => {
  if (!evidence || !evidence.bounding_box) {
    return null;
  }

  const scaled = scaleBoundingBox(evidence.bounding_box, {
    renderedWidth,
    renderedHeight,
    zoomLevel,
    dpiScale,
  });

  const { top, left, width, height } = scaled;

  // Prevent badge from clipping outside container top
  const isNearTop = top < 28;

  return (
    <div
      data-testid="bounding-box-overlay-container"
      className={`absolute inset-0 pointer-events-none overflow-visible select-none z-20 ${className}`}
      style={{
        width: `${renderedWidth * zoomLevel}px`,
        height: `${renderedHeight * zoomLevel}px`,
      }}
    >
      {/* SVG Vector Highlight Rectangle with 2.5s Pulse Animation */}
      <svg
        className="absolute inset-0 w-full h-full overflow-visible pointer-events-none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          <filter id="red-evidence-glow" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="0" dy="0" stdDeviation="5" floodColor="#EF4444" floodOpacity="0.5" />
          </filter>
        </defs>
        <rect
          x={left}
          y={top}
          width={width}
          height={height}
          rx="4"
          ry="4"
          fill="rgba(239, 68, 68, 0.15)"
          stroke="#EF4444"
          strokeWidth="2"
          filter="url(#red-evidence-glow)"
          className="transition-all duration-300"
          style={{
            animation: 'pulse 2.5s cubic-bezier(0.4, 0, 0.6, 1) infinite',
          }}
          data-testid="bounding-box-svg-rect"
        />
      </svg>

      {/* Interactive HTML Bounding Box Frame & Evidence Badge */}
      <div
        data-testid="bounding-box-interactive-frame"
        style={{
          top: `${top}px`,
          left: `${left}px`,
          width: `${width}px`,
          height: `${height}px`,
        }}
        onClick={() => onClick?.(evidence)}
        className={`absolute rounded transition-all duration-300 ${
          onClick ? 'pointer-events-auto cursor-pointer' : 'pointer-events-none'
        }`}
      >
        {/* Evidence Metadata Badge */}
        {showBadge && (
          <div
            data-testid="bounding-box-badge"
            className={`absolute z-30 flex items-center space-x-1.5 bg-red-600 text-white text-[10px] font-bold px-2 py-0.5 rounded shadow-lg whitespace-nowrap transition-all duration-300 ${
              isNearTop ? 'top-1 left-1' : '-top-6 left-0'
            }`}
          >
            <span className="w-1.5 h-1.5 rounded-full bg-white animate-ping" />
            <span>
              Source: {evidence.label} ({formatConfidence(evidence.confidence)})
            </span>
            {evidence.extracted_value !== undefined && (
              <span className="bg-red-800/80 px-1 py-0.2 rounded text-[9px] text-red-100 font-mono">
                {String(evidence.extracted_value)}
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
