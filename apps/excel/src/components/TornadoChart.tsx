/**
 * FinTrace Live Formula Dependency Visualizer & Sensitivity Tornado Chart
 * Governed by Sprint 13 Task S13-08 (Issue #115), AGENTS.md Rule 13 & Rule 15 (Zero Emoji),
 * and frontend-4file-and-resilient-ui (3 UI states, >=48px touch targets).
 */
import React, { useMemo, useState } from 'react';
import {
  Activity,
  AlertCircle,
  GitBranch,
  Layers,
  RefreshCw,
  TrendingDown,
  TrendingUp,
} from 'lucide-react';
import {
  buildDependencyGraph,
  computeTornadoSensitivity,
  type DependencyGraph,
  type TornadoBarResult,
  type TornadoDriverInput,
} from '../lib/formulaAuditor';

export interface TornadoChartProps {
  drivers?: TornadoDriverInput[];
  targetAddress?: string;
  targetLabel?: string;
  graph?: DependencyGraph;
  baseValues?: Record<string, number>;
  isLoading?: boolean;
  errorMessage?: string | null;
  onRetry?: () => void;
  onResetModel?: () => void;
}

const DEFAULT_BASE_VALUES: Record<string, number> = {
  B2: 1000, // Doanh thu thuần (tỷ VNĐ)
  B3: 0.58, // Tỷ lệ Giá vốn (COGS %)
  B4: 0.16, // Tỷ lệ Chi phí bán hàng & QLDN (SG&A %)
  B5: 0.2, // Thuế suất TNDN (Tax Rate)
  B6: 420, // Lợi nhuận gộp = B2 * (1 - B3)
  B7: 260, // EBIT = B6 - B2 * B4
  B8: 208, // Lợi nhuận ròng = B7 * (1 - B5)
};

const DEFAULT_DRIVERS: TornadoDriverInput[] = [
  { address: 'B2', label: 'Doanh thu thuần (B2)' },
  { address: 'B3', label: 'Tỷ lệ Giá vốn COGS % (B3)' },
  { address: 'B4', label: 'Tỷ lệ SG&A % (B4)' },
  { address: 'B5', label: 'Thuế suất TNDN (B5)' },
];

function createDefaultGraph(): DependencyGraph {
  return buildDependencyGraph({
    B2: { value: 1000, label: 'Doanh thu thuần' },
    B3: { value: 0.58, label: 'Tỷ lệ COGS %' },
    B4: { value: 0.16, label: 'Tỷ lệ SG&A %' },
    B5: { value: 0.2, label: 'Thuế suất TNDN' },
    B6: { formula: '=B2*(1-B3)', value: 420, label: 'Lợi nhuận gộp' },
    B7: { formula: '=B6-B2*B4', value: 260, label: 'Lợi nhuận hoạt động (EBIT)' },
    B8: { formula: '=B7*(1-B5)', value: 208, label: 'Lợi nhuận ròng' },
  });
}

const SWING_OPTIONS = [5, 10, 20] as const;

export const TornadoChart: React.FC<TornadoChartProps> = ({
  drivers = DEFAULT_DRIVERS,
  targetAddress = 'B8',
  targetLabel = 'Lợi nhuận ròng (B8)',
  graph: propGraph,
  baseValues = DEFAULT_BASE_VALUES,
  isLoading = false,
  errorMessage = null,
  onRetry,
  onResetModel,
}) => {
  const [swingPct, setSwingPct] = useState<number>(10);
  const [selectedDriverAddr, setSelectedDriverAddr] = useState<string | null>(null);

  const graph = useMemo(() => propGraph ?? createDefaultGraph(), [propGraph]);

  const bars: TornadoBarResult[] = useMemo(
    () => computeTornadoSensitivity(drivers, targetAddress, graph, baseValues, swingPct),
    [drivers, targetAddress, graph, baseValues, swingPct]
  );

  const activeDriver = useMemo(
    () => bars.find((b) => b.address === selectedDriverAddr) || bars[0] || null,
    [bars, selectedDriverAddr]
  );

  // 1. Loading Skeleton State
  if (isLoading) {
    return (
      <div
        data-testid="tornado-skeleton"
        className="p-3 bg-white border border-slate-200 rounded-xl space-y-3 animate-pulse"
      >
        <div className="h-4 bg-slate-200 rounded w-2/3" />
        <div className="h-12 bg-slate-100 rounded-lg" />
        <div className="h-32 bg-slate-100 rounded-lg" />
      </div>
    );
  }

  // 2. Error State with >=48px Retry
  if (errorMessage) {
    return (
      <div
        data-testid="tornado-error"
        className="p-4 bg-rose-50 border border-rose-200 rounded-xl text-rose-900 space-y-3"
      >
        <div className="flex items-center gap-2 text-xs font-semibold">
          <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
          <span>Không thể tính biểu đồ Tornado</span>
        </div>
        <p className="text-xs text-rose-700">{errorMessage}</p>
        {onRetry && (
          <button
            type="button"
            data-testid="tornado-retry-btn"
            onClick={onRetry}
            className="min-h-[48px] px-4 py-2 bg-rose-700 hover:bg-rose-800 text-white text-xs font-semibold rounded-lg flex items-center gap-2 transition cursor-pointer"
          >
            <RefreshCw className="w-4 h-4" />
            <span>Thử lại</span>
          </button>
        )}
      </div>
    );
  }

  // 3. Actionable Empty State
  if (bars.length === 0) {
    return (
      <div
        data-testid="tornado-empty"
        className="p-4 bg-slate-50 border border-slate-200 rounded-xl text-center space-y-3"
      >
        <Layers className="w-8 h-8 text-slate-400 mx-auto" />
        <p className="text-xs text-slate-600">
          Chưa có biến đầu vào (driver) nào để phân tích độ nhạy Tornado.
        </p>
        {onResetModel && (
          <button
            type="button"
            data-testid="tornado-empty-action-btn"
            onClick={onResetModel}
            className="min-h-[48px] px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-lg inline-flex items-center gap-2 transition cursor-pointer"
          >
            <RefreshCw className="w-4 h-4" />
            <span>Nạp mô hình mẫu</span>
          </button>
        )}
      </div>
    );
  }

  const maxAbsDelta = Math.max(
    1e-6,
    ...bars.flatMap((b) => [Math.abs(b.lowDelta), Math.abs(b.highDelta)])
  );
  const svgWidth = 340;
  const labelColWidth = 118;
  const chartHalfWidth = 96;
  const centerX = labelColWidth + chartHalfWidth;
  const rowHeight = 32;
  const svgHeight = bars.length * rowHeight + 24;

  const targetNode = graph.nodes.get(targetAddress.toUpperCase());

  return (
    <div
      data-testid="tornado-chart-container"
      className="p-3 bg-white border border-slate-200 rounded-xl space-y-3 shadow-sm"
    >
      {/* Header & Swing Selector */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5 min-w-0">
          <Activity className="w-4 h-4 text-indigo-600 shrink-0" />
          <span className="text-xs font-bold text-slate-800 truncate">
            Tornado: {targetLabel}
          </span>
        </div>
        <span className="text-[11px] font-mono text-slate-500 shrink-0">
          Base: {(bars[0]?.baseTargetValue ?? 0).toFixed(1)}
        </span>
      </div>

      {/* Swing % Selector (>=48px touch targets) */}
      <div className="grid grid-cols-3 gap-1.5" role="group" aria-label="Biên độ dao động driver">
        {SWING_OPTIONS.map((pct) => (
          <button
            key={pct}
            type="button"
            data-testid={`tornado-swing-${pct}`}
            onClick={() => setSwingPct(pct)}
            aria-pressed={swingPct === pct}
            className={`min-h-[48px] px-2 py-1.5 rounded-lg text-xs font-semibold border transition cursor-pointer ${
              swingPct === pct
                ? 'bg-indigo-600 border-indigo-600 text-white shadow-sm'
                : 'bg-slate-50 border-slate-200 text-slate-700 hover:bg-slate-100'
            }`}
          >
            ±{pct}%
          </button>
        ))}
      </div>

      {/* Responsive SVG Tornado Chart (zero horizontal overflow) */}
      <div className="w-full overflow-hidden">
        <svg
          data-testid="tornado-svg"
          viewBox={`0 0 ${svgWidth} ${svgHeight}`}
          className="w-full h-auto block"
          role="img"
          aria-label={`Biểu đồ Tornado phân tích độ nhạy ${targetLabel}`}
        >
          {/* Center Zero-Delta Baseline */}
          <line
            x1={centerX}
            y1={6}
            x2={centerX}
            y2={svgHeight - 12}
            stroke="#94a3b8"
            strokeDasharray="3 3"
            strokeWidth={1}
          />

          {bars.map((bar, idx) => {
            const y = idx * rowHeight + 10;
            const minDelta = Math.min(bar.lowDelta, bar.highDelta);
            const maxDelta = Math.max(bar.lowDelta, bar.highDelta);

            const leftW = Math.max(2, (Math.abs(Math.min(0, minDelta)) / maxAbsDelta) * chartHalfWidth);
            const rightW = Math.max(2, (Math.max(0, maxDelta) / maxAbsDelta) * chartHalfWidth);
            const isSelected = activeDriver?.address === bar.address;

            return (
              <g
                key={bar.address}
                data-testid={`tornado-bar-${bar.address}`}
                onClick={() => setSelectedDriverAddr(bar.address)}
                className="cursor-pointer"
              >
                <rect
                  x={0}
                  y={y - 2}
                  width={svgWidth}
                  height={rowHeight - 4}
                  rx={4}
                  fill={isSelected ? '#eef2ff' : 'transparent'}
                />
                <text
                  x={4}
                  y={y + 14}
                  fontSize={10}
                  fontWeight={isSelected ? 700 : 500}
                  fill={isSelected ? '#3730a3' : '#334155'}
                >
                  {bar.label.length > 18 ? `${bar.label.slice(0, 17)}…` : bar.label}
                </text>

                {/* Downside Bar (Rose) */}
                {minDelta < 0 && (
                  <rect
                    x={centerX - leftW}
                    y={y + 3}
                    width={leftW}
                    height={16}
                    rx={2}
                    fill="#f43f5e"
                  />
                )}

                {/* Upside Bar (Emerald) */}
                {maxDelta > 0 && (
                  <rect
                    x={centerX}
                    y={y + 3}
                    width={rightW}
                    height={16}
                    rx={2}
                    fill="#10b981"
                  />
                )}
              </g>
            );
          })}
        </svg>
      </div>

      {/* Interactive Driver Selection Buttons (>=48px) & Live Formula Dependency Path */}
      <div className="space-y-1.5">
        {bars.map((bar) => {
          const isSelected = activeDriver?.address === bar.address;
          return (
            <button
              key={bar.address}
              type="button"
              data-testid={`tornado-driver-btn-${bar.address}`}
              onClick={() => setSelectedDriverAddr(bar.address)}
              className={`w-full min-h-[48px] px-3 py-2 rounded-lg border text-left flex items-center justify-between gap-2 transition cursor-pointer ${
                isSelected
                  ? 'bg-indigo-50 border-indigo-400 text-indigo-950'
                  : 'bg-slate-50/70 border-slate-200 text-slate-700 hover:bg-slate-100'
              }`}
            >
              <span className="text-xs font-medium truncate">{bar.label}</span>
              <span className="text-[11px] font-mono text-slate-600 shrink-0">
                ±{(bar.spread / 2).toFixed(1)}
              </span>
            </button>
          );
        })}
      </div>

      {activeDriver && (
        <div
          data-testid="tornado-dependency-panel"
          className="p-3 bg-slate-50 border border-slate-200 rounded-lg space-y-2 text-xs"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5 font-semibold text-slate-800">
              <GitBranch className="w-3.5 h-3.5 text-indigo-600" />
              <span>Chuỗi phụ thuộc: {activeDriver.address}</span>
            </div>
            <span className="text-[11px] font-mono text-indigo-700">
              Spread: {activeDriver.spread.toFixed(2)}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-2 text-[11px]">
            <div className="flex items-center gap-1 text-rose-700">
              <TrendingDown className="w-3.5 h-3.5 shrink-0" />
              <span>Thấp: {Math.min(activeDriver.lowTargetValue, activeDriver.highTargetValue).toFixed(2)}</span>
            </div>
            <div className="flex items-center gap-1 text-emerald-700">
              <TrendingUp className="w-3.5 h-3.5 shrink-0" />
              <span>Cao: {Math.max(activeDriver.lowTargetValue, activeDriver.highTargetValue).toFixed(2)}</span>
            </div>
          </div>

          <div className="text-[11px] text-slate-600 space-y-1 pt-1 border-t border-slate-200">
            <div>
              <strong className="text-slate-700">Precedents ({activeDriver.address}):</strong>{' '}
              {activeDriver.precedents.length > 0 ? activeDriver.precedents.join(' → ') : 'Biến gốc (Input Driver)'}
            </div>
            <div>
              <strong className="text-slate-700">Dependents ({activeDriver.address}):</strong>{' '}
              {activeDriver.dependents.length > 0 ? activeDriver.dependents.join(' → ') : 'Không có'}
              {targetNode?.formula ? ` | ${targetAddress} = ${targetNode.formula}` : ''}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
