import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { TornadoChart } from '../TornadoChart';
import { buildDependencyGraph, computeTornadoSensitivity } from '../../lib/formulaAuditor';

describe('TornadoChart & computeTornadoSensitivity', () => {
  it('ranks drivers accurately by absolute impact spread using zero-eval AST evaluation', () => {
    const graph = buildDependencyGraph({
      B2: { value: 1000, label: 'Revenue' },
      B3: { value: 0.6, label: 'COGS %' },
      B4: { value: 0.2, label: 'Tax Rate' },
      B5: { formula: '=B2*(1-B3)*(1-B4)', value: 320, label: 'Net Income' },
    });
    const baseValues = { B2: 1000, B3: 0.6, B4: 0.2, B5: 320 };
    const drivers = [
      { address: 'B4', label: 'Tax Rate' },
      { address: 'B3', label: 'COGS %' },
      { address: 'B2', label: 'Revenue' },
    ];

    const ranked = computeTornadoSensitivity(drivers, 'B5', graph, baseValues, 10);
    expect(ranked).toHaveLength(3);
    // COGS % (±10% of 0.6 -> ±0.06 on 1000 * 0.8 = ±48, spread=96) > Revenue (spread=64) > Tax Rate (spread=16)
    expect(ranked[0].address).toBe('B3');
    expect(ranked[0].spread).toBeCloseTo(96, 4);
    expect(ranked[1].address).toBe('B2');
    expect(ranked[1].spread).toBeCloseTo(64, 4);
    expect(ranked[2].address).toBe('B4');
    expect(ranked[2].spread).toBeCloseTo(16, 4);
    expect(ranked[0].dependents).toContain('B5');
  });

  it('switches swing percentage and highlights live formula dependency path on driver click', () => {
    render(<TornadoChart />);

    expect(screen.getByTestId('tornado-svg')).toBeTruthy();

    const swing20 = screen.getByTestId('tornado-swing-20');
    expect(swing20.className).toContain('min-h-[48px]');
    fireEvent.click(swing20);
    expect(swing20.getAttribute('aria-pressed')).toBe('true');

    const driverBtn = screen.getByTestId('tornado-driver-btn-B2');
    expect(driverBtn.className).toContain('min-h-[48px]');
    fireEvent.click(driverBtn);

    const depPanel = screen.getByTestId('tornado-dependency-panel');
    expect(depPanel.textContent).toContain('Chuỗi phụ thuộc: B2');
    expect(depPanel.textContent).toContain('Dependents (B2):');
  });

  it('renders all 3 resilient UI states (Skeleton, Error with Retry, Empty)', () => {
    const onRetry = vi.fn();
    const onReset = vi.fn();

    const { rerender } = render(<TornadoChart isLoading={true} />);
    expect(screen.getByTestId('tornado-skeleton')).toBeTruthy();

    rerender(<TornadoChart errorMessage="Lỗi đọc công thức" onRetry={onRetry} />);
    expect(screen.getByTestId('tornado-error')).toBeTruthy();
    fireEvent.click(screen.getByTestId('tornado-retry-btn'));
    expect(onRetry).toHaveBeenCalledTimes(1);

    rerender(<TornadoChart drivers={[]} onResetModel={onReset} />);
    expect(screen.getByTestId('tornado-empty')).toBeTruthy();
    fireEvent.click(screen.getByTestId('tornado-empty-action-btn'));
    expect(onReset).toHaveBeenCalledTimes(1);
  });
});
