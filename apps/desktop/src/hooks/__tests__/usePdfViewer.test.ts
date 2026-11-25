import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook } from '@testing-library/react';
import { usePdfViewer } from '../usePdfViewer.hook';

describe('usePdfViewer hook', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('initializes with idle state and default logical page dimensions', () => {
    const { result } = renderHook(() => usePdfViewer('doc1'));
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBe(null);
    expect(result.current.renderedSize).toEqual({ width: 560, height: 792 });
  });
});
