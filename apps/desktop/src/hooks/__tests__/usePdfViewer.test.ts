import { describe, it, expect, vi } from 'vitest';
import { renderHook } from '@testing-library/react';
import { usePdfViewer } from '../usePdfViewer.hook';

describe('usePdfViewer hook', () => {
  it('initializes with idle state', () => {
    const { result } = renderHook(() => usePdfViewer('doc1'));
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBe(null);
  });
});
