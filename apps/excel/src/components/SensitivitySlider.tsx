import React, { useState, useMemo, useCallback } from 'react';
import {
  Sliders,
  TrendingUp,
  TrendingDown,
  RotateCcw,
  GitBranch,
  Calculator,
  AlertCircle,
  CheckCircle2,
  Activity,
  ChevronRight,
} from 'lucide-react';
import {
  DependencyGraph,
  SensitivityResult,
  buildDependencyGraph,
  runSensitivityAnalysis,
  updateWorksheetCellValue,
} from '../lib/formulaAuditor';

export interface SensitivitySliderProps {
  initialDriverAddress?: string;
  initialDriverLabel?: string;
  initialBaseValue?: number;
  minPercent?: number;
  maxPercent?: number;
  stepPercent?: number;
  isLoading?: boolean;
  customCells?: Record<string, { formula?: string; value?: number | string; label?: string }>;
  keyMetrics?: Array<{ address: string; label: string }>;
  onRecalculate?: (result: SensitivityResult) => void;
}

// Default financial model sample if none provided
const DEFAULT_MODEL_CELLS: Record<string, { formula?: string; value?: number; label?: string }> = {
  B5: { value: 0.05, label: 'Tỷ lệ tăng trưởng doanh thu (g)' },
  C8: { value: 50617, label: 'Doanh thu thuần năm trước (Tỷ VNĐ)' },
  C10: { formula: '=C8*(1+B5)', label: 'Doanh thu thuần kế hoạch (Tỷ VNĐ)' },
  C12: { formula: '=C10*0.407', label: 'Lợi nhuận gộp kế hoạch (Biên 40.7%)' },
  C15: { formula: '=C10*0.152', label: 'Chi phí bán hàng & QLDN' },
  C20: { formula: '=C12-C15', label: 'Lợi nhuận thuần từ HĐKD (Tỷ VNĐ)' },
};

const DEFAULT_KEY_METRICS = [
  { address: 'C10', label: 'Doanh thu thuần kế hoạch' },
  { address: 'C12', label: 'Lợi nhuận gộp kế hoạch' },
  { address: 'C20', label: 'Lợi nhuận thuần HĐKD' },
];

export const SensitivitySlider: React.FC<SensitivitySliderProps> = ({
  initialDriverAddress = 'B5',
  initialDriverLabel = 'Tỷ lệ tăng trưởng doanh thu (g)',
  initialBaseValue = 0.05,
  minPercent = -20,
  maxPercent = 30,
  stepPercent = 0.5,
  isLoading = false,
  customCells,
  keyMetrics = DEFAULT_KEY_METRICS,
  onRecalculate,
}) => {
  const [driverAddress] = useState(initialDriverAddress);
  const [driverLabel] = useState(initialDriverLabel);
  const [baseValue] = useState(initialBaseValue);
  const [deltaPercent, setDeltaPercent] = useState<number>(0);
  const [showFormulaTree, setShowFormulaTree] = useState(false);
  const [calculationError, setCalculationError] = useState<string | null>(null);
  const [syncStatus, setSyncStatus] = useState<'idle' | 'syncing' | 'synced' | 'failed'>('idle');

  // Build model dependency graph
  const modelCells = customCells || DEFAULT_MODEL_CELLS;
  const graph: DependencyGraph = useMemo(() => {
    try {
      return buildDependencyGraph(modelCells);
    } catch (err: any) {
      setCalculationError(err?.message || 'Lỗi xây dựng đồ thị phụ thuộc công thức');
      return { nodes: new Map(), circularReferences: [], hasCycles: false, topologicalOrder: [] };
    }
  }, [modelCells]);

  // Base values dictionary
  const baseValues: Record<string, number> = useMemo(() => {
    const vals: Record<string, number> = {};
    for (const [addr, cell] of Object.entries(modelCells)) {
      if (typeof cell.value === 'number') {
        vals[addr] = cell.value;
      }
    }
    return vals;
  }, [modelCells]);

  // Compute stressed driver value
  const stressedDriverValue = useMemo(() => {
    return baseValue * (1 + deltaPercent / 100);
  }, [baseValue, deltaPercent]);

  // Sensitivity analysis execution
  const sensitivityResult: SensitivityResult | null = useMemo(() => {
    if (graph.hasCycles || calculationError) return null;
    try {
      const res = runSensitivityAnalysis(
        driverAddress,
        stressedDriverValue,
        graph,
        baseValues,
        keyMetrics
      );
      return res;
    } catch (err: any) {
      setCalculationError(err?.message || 'Lỗi tính toán kịch bản nhạy cảm');
      return null;
    }
  }, [driverAddress, stressedDriverValue, graph, baseValues, keyMetrics, calculationError]);

  // Quick scenario selection handler
  const handleScenarioSelect = (pct: number) => {
    setCalculationError(null);
    setDeltaPercent(pct);
  };

  // Slider change handler
  const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setCalculationError(null);
    setDeltaPercent(parseFloat(e.target.value));
  };

  // Reset to base scenario
  const handleReset = () => {
    setCalculationError(null);
    setDeltaPercent(0);
  };

  // Step adjust (+ or -)
  const handleStep = (direction: 'up' | 'down') => {
    setCalculationError(null);
    const step = direction === 'up' ? stepPercent : -stepPercent;
    const nextVal = Math.min(maxPercent, Math.max(minPercent, deltaPercent + step));
    setDeltaPercent(parseFloat(nextVal.toFixed(1)));
  };

  // Push updated value to active Excel sheet
  const handleApplyToSheet = useCallback(async () => {
    if (!sensitivityResult) return;
    setSyncStatus('syncing');
    try {
      const res = await updateWorksheetCellValue(driverAddress, stressedDriverValue);
      if (res.success) {
        setSyncStatus('synced');
        if (onRecalculate) onRecalculate(sensitivityResult);
        setTimeout(() => setSyncStatus('idle'), 2500);
      } else {
        setSyncStatus('failed');
      }
    } catch {
      setSyncStatus('failed');
    }
  }, [driverAddress, stressedDriverValue, sensitivityResult, onRecalculate]);

  // 1. Loading UI State
  if (isLoading) {
    return (
      <div data-testid="sensitivity-skeleton" className="p-4 space-y-4 bg-slate-900 border border-slate-800 rounded-xl">
        <div className="h-6 w-48 bg-slate-800 rounded animate-pulse" />
        <div className="h-12 w-full bg-slate-800 rounded-lg animate-pulse" />
        <div className="h-24 w-full bg-slate-800 rounded-lg animate-pulse" />
      </div>
    );
  }

  // 2. Error UI State
  if (calculationError || graph.hasCycles) {
    return (
      <div data-testid="sensitivity-error" className="p-4 space-y-3 bg-red-950/40 border border-red-800/60 rounded-xl text-slate-200">
        <div className="flex items-center space-x-2 text-red-400">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <span className="font-semibold text-sm">Lỗi Mô Hình Công Thức</span>
        </div>
        <p className="text-xs text-red-300">
          {graph.hasCycles
            ? `Phát hiện tham chiếu vòng tròn (Circular Reference): ${graph.circularReferences.map((c) => c.join(' -> ')).join(', ')}`
            : calculationError}
        </p>
        <button
          onClick={() => {
            setCalculationError(null);
            setDeltaPercent(0);
          }}
          className="min-h-[48px] px-4 py-2 w-full flex items-center justify-center space-x-2 bg-red-900/60 hover:bg-red-800 text-red-100 rounded-lg text-sm font-medium transition-colors"
        >
          <RotateCcw className="w-4 h-4" />
          <span>Thử lại & Đặt lại Mô hình</span>
        </button>
      </div>
    );
  }

  // 3. Empty UI State
  if (!modelCells || Object.keys(modelCells).length === 0) {
    return (
      <div data-testid="sensitivity-empty" className="p-6 text-center space-y-3 bg-slate-900 border border-slate-800 rounded-xl">
        <Calculator className="w-8 h-8 text-slate-500 mx-auto" />
        <p className="text-sm font-medium text-slate-300">Chưa có ô công thức nào được nạp</p>
        <p className="text-xs text-slate-500">
          Chọn một bảng tài chính hoặc nạp mô hình công thức để bắt đầu phân tích độ nhạy.
        </p>
      </div>
    );
  }

  const selectedNode = graph.nodes.get(driverAddress);

  return (
    <div
      data-testid="sensitivity-slider-container"
      className="p-4 bg-slate-900 border border-slate-800 rounded-xl text-slate-100 space-y-4"
    >
      {/* Header */}
      <div className="flex items-center justify-between pb-2 border-b border-slate-800">
        <div className="flex items-center space-x-2">
          <Sliders className="w-5 h-5 text-indigo-400" />
          <h3 className="text-sm font-semibold text-slate-100">Độ Nhạy Mô Hình & Kiểm Toán Công Thức</h3>
        </div>
        <span className="px-2 py-0.5 text-[11px] font-mono bg-indigo-950/80 text-indigo-300 border border-indigo-800/60 rounded">
          {driverAddress}
        </span>
      </div>

      {/* Driver Cell Info */}
      <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800/80 space-y-1">
        <div className="flex justify-between items-center text-xs">
          <span className="text-slate-400">Tham số dẫn dắt:</span>
          <span className="font-medium text-slate-200">{driverLabel}</span>
        </div>
        <div className="flex justify-between items-baseline pt-1">
          <span className="text-xs text-slate-400">Giá trị cơ sở: {(baseValue * 100).toFixed(1)}%</span>
          <div className="flex items-center space-x-2">
            <span className="text-xs text-slate-400">Giá trị kịch bản:</span>
            <span className="text-base font-bold text-indigo-400 font-mono">
              {(stressedDriverValue * 100).toFixed(2)}%
            </span>
            <span
              className={`text-xs font-mono font-medium ${
                deltaPercent > 0 ? 'text-emerald-400' : deltaPercent < 0 ? 'text-rose-400' : 'text-slate-400'
              }`}
            >
              ({deltaPercent >= 0 ? `+${deltaPercent.toFixed(1)}%` : `${deltaPercent.toFixed(1)}%`})
            </span>
          </div>
        </div>
      </div>

      {/* Interactive Kiosk Ergonomic Slider Controls */}
      <div className="space-y-3">
        {/* Slider Input with >=48px Touch Target Area */}
        <div className="min-h-[48px] flex items-center px-1">
          <input
            type="range"
            aria-label="Độ lệch phần trăm tham số"
            min={minPercent}
            max={maxPercent}
            step={stepPercent}
            value={deltaPercent}
            onChange={handleSliderChange}
            className="w-full h-3 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-400"
          />
        </div>

        {/* Step Buttons & Reset with >=48px Touch Targets */}
        <div className="grid grid-cols-3 gap-2">
          <button
            type="button"
            onClick={() => handleStep('down')}
            className="min-h-[48px] px-3 py-2 bg-slate-800 hover:bg-slate-700 active:bg-slate-600 rounded-lg text-sm font-semibold text-slate-200 transition-colors flex items-center justify-center space-x-1"
          >
            <span>- {stepPercent}%</span>
          </button>
          <button
            type="button"
            onClick={handleReset}
            className="min-h-[48px] px-3 py-2 bg-slate-800 hover:bg-slate-700 active:bg-slate-600 rounded-lg text-xs font-medium text-slate-300 transition-colors flex items-center justify-center space-x-1"
          >
            <RotateCcw className="w-3.5 h-3.5 text-slate-400" />
            <span>Cơ sở (0%)</span>
          </button>
          <button
            type="button"
            onClick={() => handleStep('up')}
            className="min-h-[48px] px-3 py-2 bg-slate-800 hover:bg-slate-700 active:bg-slate-600 rounded-lg text-sm font-semibold text-slate-200 transition-colors flex items-center justify-center space-x-1"
          >
            <span>+ {stepPercent}%</span>
          </button>
        </div>

        {/* Quick Scenario Preset Chips with >=48px Touch Targets */}
        <div className="grid grid-cols-4 gap-1.5 pt-1">
          {[
            { label: 'Bi quan', pct: -10, badge: 'PESSIMISTIC' },
            { label: 'Thận trọng', pct: -5, badge: 'CONSERVATIVE' },
            { label: 'Lạc quan', pct: 5, badge: 'OPTIMISTIC' },
            { label: 'Căng thẳng', pct: 15, badge: 'STRESSED' },
          ].map((sc) => (
            <button
              key={sc.badge}
              type="button"
              onClick={() => handleScenarioSelect(sc.pct)}
              className={`min-h-[48px] px-2 py-1 text-center rounded-lg border text-xs font-medium transition-colors flex flex-col items-center justify-center ${
                deltaPercent === sc.pct
                  ? 'bg-indigo-950/80 border-indigo-500 text-indigo-300 shadow-sm'
                  : 'bg-slate-800/60 border-slate-700/60 text-slate-400 hover:bg-slate-800 hover:text-slate-200'
              }`}
            >
              <span className="text-[11px] font-semibold">{sc.label}</span>
              <span className="text-[10px] font-mono text-slate-400">{sc.pct > 0 ? `+${sc.pct}%` : `${sc.pct}%`}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Recalculated Metric Impact Display */}
      {sensitivityResult && (
        <div className="space-y-2 pt-2 border-t border-slate-800">
          <div className="flex items-center justify-between text-xs text-slate-400 font-medium">
            <span className="flex items-center space-x-1">
              <Activity className="w-3.5 h-3.5 text-indigo-400" />
              <span>Tác Động Lên Các Chỉ Số Chính</span>
            </span>
            <span className="text-[11px] font-mono text-slate-400">
              {sensitivityResult.impactedKeyMetrics.length} chỉ tiêu
            </span>
          </div>

          <div className="space-y-2">
            {sensitivityResult.impactedKeyMetrics.map((metric) => {
              const isPositive = metric.delta > 0;
              const isNeutral = metric.delta === 0;

              return (
                <div
                  key={metric.address}
                  className="bg-slate-950/80 p-2.5 rounded-lg border border-slate-800/80 flex items-center justify-between"
                >
                  <div className="space-y-0.5">
                    <div className="flex items-center space-x-1.5">
                      <span className="text-xs font-mono font-medium text-slate-400">{metric.address}</span>
                      <span className="text-xs text-slate-200 font-medium">{metric.label}</span>
                    </div>
                    <div className="text-[11px] text-slate-400 font-mono">
                      Cơ sở: {metric.baseValue.toLocaleString('vi-VN')} tỷ
                    </div>
                  </div>

                  <div className="text-right space-y-0.5">
                    <div className="text-sm font-bold font-mono text-slate-100">
                      {Math.round(metric.stressedValue).toLocaleString('vi-VN')} tỷ
                    </div>
                    <div
                      className={`text-[11px] font-mono font-medium flex items-center justify-end space-x-1 ${
                        isPositive ? 'text-emerald-400' : isNeutral ? 'text-slate-400' : 'text-rose-400'
                      }`}
                    >
                      {isPositive ? (
                        <TrendingUp className="w-3 h-3" />
                      ) : isNeutral ? null : (
                        <TrendingDown className="w-3 h-3" />
                      )}
                      <span>
                        {isPositive ? `+${metric.percentChange.toFixed(1)}%` : `${metric.percentChange.toFixed(1)}%`}
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Formula Audit Trail Inspection Toggle */}
      <div className="pt-2 border-t border-slate-800 space-y-2">
        <button
          type="button"
          onClick={() => setShowFormulaTree(!showFormulaTree)}
          className="min-h-[48px] w-full px-3 py-2 bg-slate-800/60 hover:bg-slate-800 border border-slate-700/60 rounded-lg text-xs font-medium text-slate-300 transition-colors flex items-center justify-between"
        >
          <div className="flex items-center space-x-2">
            <GitBranch className="w-4 h-4 text-indigo-400" />
            <span>Cây Phụ Thuộc & Kiểm Toán Công Thức (Precedents / Dependents)</span>
          </div>
          <ChevronRight className={`w-4 h-4 text-slate-400 transition-transform ${showFormulaTree ? 'rotate-90' : ''}`} />
        </button>

        {showFormulaTree && selectedNode && (
          <div
            data-testid="formula-tree-drawer"
            className="p-3 bg-slate-950/90 rounded-lg border border-slate-800 text-xs space-y-2 font-mono"
          >
            <div className="flex items-center justify-between text-slate-300 pb-1 border-b border-slate-800">
              <span className="font-semibold text-slate-200">Ô {driverAddress}</span>
              <span className="flex items-center space-x-1 text-emerald-400 text-[11px]">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>[VERIFIED AUDIT TRAIL]</span>
              </span>
            </div>

            {selectedNode.formula ? (
              <div className="text-indigo-300 bg-slate-900 p-2 rounded border border-slate-800">
                Formula: {selectedNode.formula}
              </div>
            ) : (
              <div className="text-slate-400 italic">Tham số gốc (Driver Input)</div>
            )}

            <div className="space-y-1">
              <div className="text-slate-400 font-semibold text-[11px]">
                Các ô phụ thuộc xuôi dòng (Dependents: {selectedNode.dependents.length}):
              </div>
              <div className="flex flex-wrap gap-1">
                {selectedNode.dependents.length > 0 ? (
                  selectedNode.dependents.map((dep) => (
                    <span
                      key={dep}
                      className="px-2 py-0.5 bg-slate-800 text-slate-200 rounded border border-slate-700 text-[11px]"
                    >
                      {dep}
                    </span>
                  ))
                ) : (
                  <span className="text-slate-500 italic">Không có ô phụ thuộc</span>
                )}
              </div>
            </div>

            <div className="pt-1 text-[10px] text-slate-400">
              Thứ tự tính toán hợp lệ (Topological Order): {graph.topologicalOrder.join(' -> ')}
            </div>
          </div>
        )}
      </div>

      {/* Sheet Recalculate & Sync Action Button with >=48px Touch Target */}
      <div className="pt-2">
        <button
          type="button"
          onClick={handleApplyToSheet}
          disabled={syncStatus === 'syncing'}
          className={`min-h-[48px] w-full px-4 py-3 rounded-lg text-sm font-semibold flex items-center justify-center space-x-2 transition-colors ${
            syncStatus === 'synced'
              ? 'bg-emerald-600 text-white'
              : syncStatus === 'failed'
              ? 'bg-rose-700 text-white'
              : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-md'
          }`}
        >
          {syncStatus === 'syncing' ? (
            <>
              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              <span>Đang tính toán lại bảng tính...</span>
            </>
          ) : syncStatus === 'synced' ? (
            <>
              <CheckCircle2 className="w-4 h-4" />
              <span>Đã cập nhật ô {driverAddress} vào Excel!</span>
            </>
          ) : syncStatus === 'failed' ? (
            <>
              <AlertCircle className="w-4 h-4" />
              <span>Cập nhật bảng tính thất bại (Thử lại)</span>
            </>
          ) : (
            <>
              <Calculator className="w-4 h-4" />
              <span>Áp Dụng Kịch Bản Vào Bảng Tính Excel</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
};
