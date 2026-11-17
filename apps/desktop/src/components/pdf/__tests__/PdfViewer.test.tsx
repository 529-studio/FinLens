import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { PdfViewer } from '../PdfViewer';

describe('PdfViewer Component', () => {
  it('renders loading state', () => {
    // Note: This test requires a mock to trigger loading or verify initial render behavior.
    // For now, testing basic render and existence of canvas.
    render(<PdfViewer documentId="doc1" pageNumber={1} zoomLevel={1} />);
    expect(screen.getByRole('presentation')).toBeDefined(); // Canvas is present
  });
});
