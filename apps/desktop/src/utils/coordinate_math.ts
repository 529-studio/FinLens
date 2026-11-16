/**
 * Utility: Coordinate Math for Visual Grounding & Bounding Box Scaling
 * Governed by 529 Engineering Standards:
 * - ADR-003: Normalized coordinate system on integer scale [0, 1000] for [ymin, xmin, ymax, xmax]
 * - Viewport, DPI, and Zoom-independent scaling calculations
 */

import type { BoundingBoxDTO } from '../types/visual_rag.types';

export interface ScaledBoundingBox {
  top: number;
  left: number;
  width: number;
  height: number;
}

export interface DimensionOptions {
  renderedWidth: number;
  renderedHeight: number;
  zoomLevel?: number; // e.g. 1.0, 1.25, 1.5, defaults to 1.0
  dpiScale?: number; // devicePixelRatio or canvas backing store scale, defaults to 1.0
}

/**
 * Validates that an object conforms to BoundingBoxDTO with valid 0-1000 coordinate bounds.
 */
export function isValidBoundingBox(box: unknown): box is BoundingBoxDTO {
  if (!box || typeof box !== 'object') return false;
  const b = box as Record<string, unknown>;
  return (
    typeof b.ymin === 'number' &&
    typeof b.xmin === 'number' &&
    typeof b.ymax === 'number' &&
    typeof b.xmax === 'number' &&
    Number.isFinite(b.ymin) &&
    Number.isFinite(b.xmin) &&
    Number.isFinite(b.ymax) &&
    Number.isFinite(b.xmax) &&
    b.ymin >= 0 &&
    b.ymin <= 1000 &&
    b.xmin >= 0 &&
    b.xmin <= 1000 &&
    b.ymax >= 0 &&
    b.ymax <= 1000 &&
    b.xmax >= 0 &&
    b.xmax <= 1000 &&
    b.ymin <= b.ymax &&
    b.xmin <= b.xmax
  );
}

/**
 * Clamps raw coordinates to valid [0, 1000] normalized space.
 */
export function sanitizeBoundingBox(box: BoundingBoxDTO): BoundingBoxDTO {
  const ymin = Math.max(0, Math.min(1000, Number.isFinite(box.ymin) ? box.ymin : 0));
  const xmin = Math.max(0, Math.min(1000, Number.isFinite(box.xmin) ? box.xmin : 0));
  const ymax = Math.max(ymin, Math.min(1000, Number.isFinite(box.ymax) ? box.ymax : 1000));
  const xmax = Math.max(xmin, Math.min(1000, Number.isFinite(box.xmax) ? box.xmax : 1000));

  return { ymin, xmin, ymax, xmax };
}

/**
 * Converts normalized 0-1000 coordinates to viewport pixel dimensions.
 * Formula:
 *  top = (ymin / 1000) * renderedHeight * zoomLevel
 *  left = (xmin / 1000) * renderedWidth * zoomLevel
 *  height = ((ymax - ymin) / 1000) * renderedHeight * zoomLevel
 *  width = ((xmax - xmin) / 1000) * renderedWidth * zoomLevel
 */
export function scaleBoundingBox(
  box: BoundingBoxDTO,
  options: DimensionOptions
): ScaledBoundingBox {
  const { renderedWidth, renderedHeight, zoomLevel = 1.0, dpiScale = 1.0 } = options;

  const sanitized = sanitizeBoundingBox(box);

  const effectiveWidth = Math.max(0, renderedWidth * zoomLevel * (dpiScale > 0 ? 1 : 1));
  const effectiveHeight = Math.max(0, renderedHeight * zoomLevel * (dpiScale > 0 ? 1 : 1));

  const top = (sanitized.ymin / 1000) * effectiveHeight;
  const left = (sanitized.xmin / 1000) * effectiveWidth;
  const height = ((sanitized.ymax - sanitized.ymin) / 1000) * effectiveHeight;
  const width = ((sanitized.xmax - sanitized.xmin) / 1000) * effectiveWidth;

  return {
    top: Math.round(top * 100) / 100,
    left: Math.round(left * 100) / 100,
    width: Math.round(width * 100) / 100,
    height: Math.round(height * 100) / 100,
  };
}

/**
 * Calculates the center point of a scaled bounding box (used for auto-scroll/zoom focusing).
 */
export function calculateBoundingBoxCenter(box: ScaledBoundingBox): { centerX: number; centerY: number } {
  return {
    centerX: box.left + box.width / 2,
    centerY: box.top + box.height / 2,
  };
}

/**
 * Formats confidence decimal into a clean human percentage string.
 */
export function formatConfidence(confidence: number): string {
  if (!Number.isFinite(confidence)) return '0%';
  const clamped = Math.max(0, Math.min(1, confidence));
  return `${Math.round(clamped * 100)}%`;
}
