/**
 * Component tests for BoundingBoxOverlay
 * Governed by 529 Engineering Standards
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { BoundingBoxOverlay } from '../BoundingBoxOverlay';
import type { GroundedEvidenceDTO } from '../../../types/visual_rag.types';

describe('BoundingBoxOverlay Component', () => {
  const mockEvidence: GroundedEvidenceDTO = {
    page_number: 1,
    bounding_box: {
      ymin: 200,
      xmin: 100,
      ymax: 600,
      xmax: 800,
    },
    label: 'Biểu đồ Doanh Thu Hợp Nhất',
    confidence: 0.95,
    extracted_value: '142.500 tỷ',
  };

  it('renders nothing when evidence is null', () => {
    const { container } = render(
      <BoundingBoxOverlay
        evidence={null}
        renderedWidth={500}
        renderedHeight={700}
      />
    );

    expect(container.firstChild).toBeNull();
  });

  it('renders SVG rectangle with red #EF4444 stroke and correct dimensions', () => {
    render(
      <BoundingBoxOverlay
        evidence={mockEvidence}
        renderedWidth={500}
        renderedHeight={700}
        zoomLevel={1.0}
      />
    );

    const svgRect = screen.getByTestId('bounding-box-svg-rect');
    expect(svgRect).toBeTruthy();
    expect(svgRect.getAttribute('stroke')).toBe('#EF4444');

    // top = (200/1000)*700 = 140, left = (100/1000)*500 = 50
    // height = ((600-200)/1000)*700 = 280, width = ((800-100)/1000)*500 = 350
    expect(svgRect.getAttribute('y')).toBe('140');
    expect(svgRect.getAttribute('x')).toBe('50');
    expect(svgRect.getAttribute('height')).toBe('280');
    expect(svgRect.getAttribute('width')).toBe('350');
  });

  it('renders source evidence badge with confidence and value', () => {
    render(
      <BoundingBoxOverlay
        evidence={mockEvidence}
        renderedWidth={500}
        renderedHeight={700}
      />
    );

    const badge = screen.getByTestId('bounding-box-badge');
    expect(badge).toBeTruthy();
    expect(badge.textContent).toContain('Biểu đồ Doanh Thu Hợp Nhất');
    expect(badge.textContent).toContain('95%');
    expect(badge.textContent).toContain('142.500 tỷ');
  });

  it('fires onClick callback when interactive bounding box frame is clicked', () => {
    const handleClick = vi.fn();

    render(
      <BoundingBoxOverlay
        evidence={mockEvidence}
        renderedWidth={500}
        renderedHeight={700}
        onClick={handleClick}
      />
    );

    const interactiveFrame = screen.getByTestId('bounding-box-interactive-frame');
    fireEvent.click(interactiveFrame);

    expect(handleClick).toHaveBeenCalledTimes(1);
    expect(handleClick).toHaveBeenCalledWith(mockEvidence);
  });

  it('positions badge inside frame when box is near top of viewport', () => {
    const topEvidence: GroundedEvidenceDTO = {
      ...mockEvidence,
      bounding_box: {
        ymin: 10, // top = 7px (< 28px)
        xmin: 100,
        ymax: 200,
        xmax: 500,
      },
    };

    render(
      <BoundingBoxOverlay
        evidence={topEvidence}
        renderedWidth={500}
        renderedHeight={700}
      />
    );

    const badge = screen.getByTestId('bounding-box-badge');
    expect(badge.className).toContain('top-1 left-1');
  });
});
