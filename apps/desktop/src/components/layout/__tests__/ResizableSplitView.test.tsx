/**
 * Component tests for ResizableSplitView
 * Governed by 529 Engineering Standards
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ResizableSplitView } from '../ResizableSplitView';

describe('ResizableSplitView Component', () => {
  const STORAGE_KEY = 'test:resizable-split-view';

  beforeEach(() => {
    localStorage.clear();
  });

  it('renders left and right pane content', () => {
    render(
      <ResizableSplitView
        storageKey={STORAGE_KEY}
        leftPane={<div data-testid="left-content">Left PDF Content</div>}
        rightPane={<div data-testid="right-content">Right Chat Content</div>}
      />
    );

    expect(screen.getByTestId('left-content')).toBeTruthy();
    expect(screen.getByTestId('right-content')).toBeTruthy();
  });

  it('renders divider with accessible separator role and 50% default', () => {
    render(
      <ResizableSplitView
        storageKey={STORAGE_KEY}
        leftPane={<div>Left</div>}
        rightPane={<div>Right</div>}
      />
    );

    const divider = screen.getByRole('separator');
    expect(divider).toBeTruthy();
    expect(divider.getAttribute('aria-valuenow')).toBe('50');
    expect(divider.getAttribute('aria-orientation')).toBe('vertical');
  });

  it('resets ratio on double click', () => {
    localStorage.setItem(STORAGE_KEY, '0.75');

    render(
      <ResizableSplitView
        storageKey={STORAGE_KEY}
        initialRatio={0.5}
        leftPane={<div>Left</div>}
        rightPane={<div>Right</div>}
      />
    );

    const divider = screen.getByRole('separator');
    expect(divider.getAttribute('aria-valuenow')).toBe('75');

    fireEvent.doubleClick(divider);

    expect(divider.getAttribute('aria-valuenow')).toBe('50');
    expect(localStorage.getItem(STORAGE_KEY)).toBe('0.5');
  });

  it('supports keyboard navigation via arrow keys without crashing', () => {
    render(
      <ResizableSplitView
        storageKey={STORAGE_KEY}
        initialRatio={0.5}
        leftPane={<div>Left</div>}
        rightPane={<div>Right</div>}
      />
    );

    const divider = screen.getByRole('separator');
    divider.focus();

    // Arrow Left adjusts left pane
    fireEvent.keyDown(divider, { key: 'ArrowLeft' });
    expect(divider).toBeTruthy();
    expect(divider.getAttribute('aria-valuenow')).toBe('48');

    // Arrow Right adjusts right pane
    fireEvent.keyDown(divider, { key: 'ArrowRight' });
    expect(divider.getAttribute('aria-valuenow')).toBe('50');
  });
});
