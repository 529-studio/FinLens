/**
 * Unit tests for usePaneResize hook
 * Governed by 529 Engineering Standards
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { usePaneResize } from '../usePaneResize';

describe('usePaneResize', () => {
  const STORAGE_KEY = 'test:split-ratio';

  beforeEach(() => {
    localStorage.clear();
  });

  it('initializes with default 0.5 split ratio', () => {
    const { result } = renderHook(() =>
      usePaneResize({ storageKey: STORAGE_KEY })
    );

    expect(result.current.splitRatio).toBe(0.5);
    expect(result.current.isDragging).toBe(false);
    expect(result.current.leftPaneStyle.width).toBe('calc(50% - 3px)');
    expect(result.current.rightPaneStyle.width).toBe('calc(50% - 3px)');
  });

  it('restores stored split ratio from localStorage', () => {
    localStorage.setItem(STORAGE_KEY, '0.6250');

    const { result } = renderHook(() =>
      usePaneResize({ storageKey: STORAGE_KEY })
    );

    expect(result.current.splitRatio).toBe(0.625);
    expect(result.current.leftPaneStyle.width).toBe('calc(62.5% - 3px)');
    expect(result.current.rightPaneStyle.width).toBe('calc(37.5% - 3px)');
  });

  it('resets ratio to initial 0.5 via resetRatio', () => {
    localStorage.setItem(STORAGE_KEY, '0.75');

    const { result } = renderHook(() =>
      usePaneResize({ storageKey: STORAGE_KEY, initialRatio: 0.5 })
    );

    expect(result.current.splitRatio).toBe(0.75);

    act(() => {
      result.current.resetRatio();
    });

    expect(result.current.splitRatio).toBe(0.5);
    expect(localStorage.getItem(STORAGE_KEY)).toBe('0.5');
  });

  it('respects minLeftWidth and minRightWidth constraints', () => {
    const { result } = renderHook(() =>
      usePaneResize({
        minLeftWidth: 350,
        minRightWidth: 350,
        storageKey: STORAGE_KEY,
      })
    );

    expect(result.current.leftPaneStyle.minWidth).toBe('350px');
    expect(result.current.rightPaneStyle.minWidth).toBe('350px');
  });
});
