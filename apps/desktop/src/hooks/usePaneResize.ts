/**
 * Hook: usePaneResize
 * Governed by 529 Engineering Standards:
 * - Resizable dual-pane layout with pointer events & pointer capture
 * - Clamping with minLeftWidth and minRightWidth (default 350px)
 * - Persistent split ratio in localStorage across app restarts
 * - Keyboard navigation support (ArrowLeft / ArrowRight)
 */

import { useState, useRef, useCallback, useEffect, type CSSProperties } from 'react';

export interface UsePaneResizeOptions {
  /** Initial split ratio between 0 and 1. Defaults to 0.5 (50/50). */
  initialRatio?: number;
  /** Minimum width for the left pane in pixels. Defaults to 350. */
  minLeftWidth?: number;
  /** Minimum width for the right pane in pixels. Defaults to 350. */
  minRightWidth?: number;
  /** Key used for persisting split ratio/width in localStorage. */
  storageKey?: string;
  /** Divider width in pixels. Defaults to 6. */
  dividerWidth?: number;
}

export interface UsePaneResizeReturn {
  splitRatio: number;
  isDragging: boolean;
  containerRef: React.RefObject<HTMLDivElement | null>;
  handlePointerDown: (e: React.PointerEvent<HTMLElement>) => void;
  handlePointerMove: (e: React.PointerEvent<HTMLElement>) => void;
  handlePointerUp: (e: React.PointerEvent<HTMLElement>) => void;
  handleKeyDown: (e: React.KeyboardEvent<HTMLElement>) => void;
  resetRatio: () => void;
  leftPaneStyle: CSSProperties;
  rightPaneStyle: CSSProperties;
}

export function usePaneResize({
  initialRatio = 0.5,
  minLeftWidth = 350,
  minRightWidth = 350,
  storageKey = 'finsight:split-view:ratio',
  dividerWidth = 6,
}: UsePaneResizeOptions = {}): UsePaneResizeReturn {
  const [splitRatio, setSplitRatio] = useState<number>(() => {
    if (typeof window === 'undefined') return initialRatio;
    try {
      const saved = localStorage.getItem(storageKey);
      if (saved !== null) {
        const parsed = parseFloat(saved);
        if (!isNaN(parsed) && parsed > 0.05 && parsed < 0.95) {
          return parsed;
        }
      }
    } catch {
      // Safe fallback if localStorage is disabled or throws
    }
    return initialRatio;
  });

  const [isDragging, setIsDragging] = useState<boolean>(false);
  const containerRef = useRef<HTMLDivElement | null>(null);

  const updateRatioFromPointer = useCallback(
    (clientX: number) => {
      if (!containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const containerWidth = rect.width;
      if (containerWidth <= 0) return;

      const pointerOffset = clientX - rect.left;
      const safeMinLeft = Math.min(minLeftWidth, containerWidth / 2);
      const safeMaxLeft = Math.max(containerWidth - minRightWidth, safeMinLeft);
      const clampedX = Math.min(Math.max(pointerOffset, safeMinLeft), safeMaxLeft);

      const newRatio = Math.max(0.05, Math.min(0.95, clampedX / containerWidth));
      setSplitRatio(newRatio);

      try {
        localStorage.setItem(storageKey, newRatio.toFixed(4));
        localStorage.setItem(`${storageKey}:left-width`, Math.round(clampedX).toString());
      } catch {
        // Safe ignore
      }
    },
    [minLeftWidth, minRightWidth, storageKey]
  );

  const handlePointerDown = useCallback((e: React.PointerEvent<HTMLElement>) => {
    e.preventDefault();
    setIsDragging(true);
    try {
      e.currentTarget.setPointerCapture(e.pointerId);
    } catch {
      // Safe fallback
    }
  }, []);

  const handlePointerMove = useCallback(
    (e: React.PointerEvent<HTMLElement>) => {
      if (!isDragging) return;
      e.preventDefault();
      updateRatioFromPointer(e.clientX);
    },
    [isDragging, updateRatioFromPointer]
  );

  const handlePointerUp = useCallback(
    (e: React.PointerEvent<HTMLElement>) => {
      if (!isDragging) return;
      setIsDragging(false);
      try {
        e.currentTarget.releasePointerCapture(e.pointerId);
      } catch {
        // Safe fallback
      }
    },
    [isDragging]
  );

  const resetRatio = useCallback(() => {
    setSplitRatio(initialRatio);
    try {
      localStorage.setItem(storageKey, initialRatio.toString());
      if (containerRef.current) {
        const defaultWidth = Math.round(containerRef.current.getBoundingClientRect().width * initialRatio);
        localStorage.setItem(`${storageKey}:left-width`, defaultWidth.toString());
      }
    } catch {
      // Safe ignore
    }
  }, [initialRatio, storageKey]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLElement>) => {
      if (e.key === 'ArrowLeft') {
        e.preventDefault();
        setSplitRatio((prev) => {
          if (!containerRef.current) return prev;
          const containerWidth = containerRef.current.getBoundingClientRect().width;
          if (containerWidth <= 0) {
            const fallbackNext = Math.max(0.1, prev - 0.02);
            try {
              localStorage.setItem(storageKey, fallbackNext.toFixed(4));
            } catch {}
            return fallbackNext;
          }
          const currentLeft = prev * containerWidth;
          const targetLeft = Math.max(minLeftWidth, currentLeft - 20);
          const next = Math.max(0.05, Math.min(0.95, targetLeft / containerWidth));
          try {
            localStorage.setItem(storageKey, next.toFixed(4));
            localStorage.setItem(`${storageKey}:left-width`, Math.round(targetLeft).toString());
          } catch {}
          return next;
        });
      } else if (e.key === 'ArrowRight') {
        e.preventDefault();
        setSplitRatio((prev) => {
          if (!containerRef.current) return prev;
          const containerWidth = containerRef.current.getBoundingClientRect().width;
          if (containerWidth <= 0) {
            const fallbackNext = Math.min(0.9, prev + 0.02);
            try {
              localStorage.setItem(storageKey, fallbackNext.toFixed(4));
            } catch {}
            return fallbackNext;
          }
          const currentLeft = prev * containerWidth;
          const targetLeft = Math.min(containerWidth - minRightWidth, currentLeft + 20);
          const next = Math.max(0.05, Math.min(0.95, targetLeft / containerWidth));
          try {
            localStorage.setItem(storageKey, next.toFixed(4));
            localStorage.setItem(`${storageKey}:left-width`, Math.round(targetLeft).toString());
          } catch {}
          return next;
        });
      } else if (e.key === 'Home') {
        e.preventDefault();
        resetRatio();
      }
    },
    [minLeftWidth, minRightWidth, resetRatio, storageKey]
  );

  // Global safety fallback for pointer release outside component
  useEffect(() => {
    if (!isDragging) return;
    const handleGlobalUp = () => setIsDragging(false);
    window.addEventListener('pointerup', handleGlobalUp);
    window.addEventListener('pointercancel', handleGlobalUp);
    return () => {
      window.removeEventListener('pointerup', handleGlobalUp);
      window.removeEventListener('pointercancel', handleGlobalUp);
    };
  }, [isDragging]);

  const halfDivider = dividerWidth / 2;
  const safeRatio = Number.isFinite(splitRatio) ? Math.max(0.05, Math.min(0.95, splitRatio)) : 0.5;

  const leftPaneStyle: CSSProperties = {
    width: `calc(${safeRatio * 100}% - ${halfDivider}px)`,
    minWidth: `${minLeftWidth}px`,
    flexShrink: 0,
  };

  const rightPaneStyle: CSSProperties = {
    width: `calc(${(1 - safeRatio) * 100}% - ${halfDivider}px)`,
    minWidth: `${minRightWidth}px`,
    flexShrink: 0,
  };

  return {
    splitRatio,
    isDragging,
    containerRef,
    handlePointerDown,
    handlePointerMove,
    handlePointerUp,
    handleKeyDown,
    resetRatio,
    leftPaneStyle,
    rightPaneStyle,
  };
}
