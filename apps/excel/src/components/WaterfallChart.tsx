/**
 * FinTrace Scenario Comparison Waterfall Chart Component for Excel Add-in
 * Renders interactive SVG waterfall variance decomposition across Base, Bull, and Bear scenarios,
 * with footnote grounding chips and one-click PDF audit report export.
 * Governed by Sprint 11 Task S11-05, AGENTS.md Rule 13, Rule 15 (Zero Emoji),
 * and frontend-4file-and-resilient-ui (3 UI states, >=48px touch targets).
 */

import React, { useState, useMemo, useCallback } from 'react';
import {
  BarChart3,
  TrendingUp,
  TrendingDown,
  Download,
  RefreshCw,
  FileText,
  CheckCircle2,
  AlertCircle,
  Eye,
  Layers,
} from 'lucide-react';
import {
  FinancialScenario,
  WaterfallDriverInput,
  WaterfallStep,
  GroundingCitation,
  WaterfallExportReport,
} from '../types/waterfall.types';
import {
  DEFAULT_VNM_WATERFALL_DRIVERS,
  SCENARIO_CONFIGS,
  applyScenarioToDrivers,
  computeWaterfallSteps,
  exportWaterfallToPdfOrPrint,
} from '../lib/excel/waterfallExporter';

export interface WaterfallChartProps {
  initialDrivers?: WaterfallDriverInput[];
  companyName?: string;
  reportingPeriod?: string;
  isLoading?: boolean;
  errorMessage?: string | null;
  onRetry?: () => void;
  onCitationClick?: (citation: GroundingCitation) => void;
}

export const WaterfallChart: React.FC<WaterfallChartProps> = ({
  initialDrivers = DEFAULT_VNM_WATERFALL_DRIVERS,
  companyName = 'Vinamilk (VNM)',
  reportingPeriod = 'Năm 2023',
  isLoading = false,
  errorMessage = null,
  onRetry,
  onCitationClick,
}) => {
  const [scenario, setScenario] = useState<FinancialScenario>('base');
  const [selectedStep, setSelectedStep] = useState<WaterfallStep | null>(null);
  const [exportNotice, setExportNotice] = useState<string | null>(null);

  // 1. Loading State: Skeleton Layout
  if (isLoading) {
    return (
      <div
        data-testid="waterfall-skeleton"
        className="w-full bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4 animate-pulse"
      >
        <div className="flex items-center justify-between">
          <div className="h-5 w-48 bg-slate-800 rounded" />
          <div className="h-8 w-24 bg-slate-800 rounded-lg" />
        </div>
        <div className="flex space-x-2">
          <div className="h-10 w-28 bg-slate-800 rounded-lg" />
          <div className="h-10 w-28 bg-slate-800 rounded-lg" />
          <div className="h-10 w-28 bg-slate-800 rounded-lg" />
        </div>
        <div className="h-64 w-full bg-slate-800/60 rounded-lg flex items-end justify-between p-4 space-x-3">
          <div className="h-4/5 w-12 bg-slate-700/80 rounded-t" />
          <div className="h-2/5 w-12 bg-slate-700/80 rounded-t" />
          <div className="h-3/5 w-12 bg-slate-700/80 rounded-t" />
          <div className="h-1/5 w-12 bg-slate-700/80 rounded-t" />
          <div className="h-1/3 w-12 bg-slate-700/80 rounded-t" />
          <div className="h-2/5 w-12 bg-slate-700/80 rounded-t" />
        </div>
      </div>
    );
  }

  // 2. Error State: Localized Banner with >=48px Retry Button
  if (errorMessage) {
    return (
      <div
        data-testid="waterfall-error"
        className="w-full bg-rose-950/50 border border-rose-800/80 rounded-xl p-5 space-y-3"
      >
        <div className="flex items-center space-x-3 text-rose-200">
          <AlertCircle className="w-5 h-5 text-rose-400 shrink-0" />
          <div>
            <div className="font-semibold text-sm">Lỗi tải mô hình thác nước kịch bản:</div>
            <div className="text-xs text-rose-300 mt-0.5">{errorMessage}</div>
          </div>
        </div>
        {onRetry && (
          <button
            type="button"
            data-testid="waterfall-retry-btn"
            onClick={onRetry}
            className="min-h-[48px] px-5 py-2.5 bg-rose-700 hover:bg-rose-600 active:bg-rose-800 text-white text-xs font-semibold rounded-lg flex items-center space-x-2 transition-colors cursor-pointer"
          >
            <RefreshCw className="w-4 h-4" />
            <span>Thử lại tải dữ liệu</span>
          </button>
        )}
      </div>
    );
  }

  // 3. Empty State: No Drivers Provided
  if (!initialDrivers || initialDrivers.length === 0) {
    return (
      <div
        data-testid="waterfall-empty"
        className="w-full bg-slate-900 border border-slate-800 rounded-xl p-8 text-center space-y-4"
      >
        <div className="w-12 h-12 rounded-full bg-slate-800 flex items-center justify-center mx-auto text-slate-400">
          <BarChart3 className="w-6 h-6" />
        </div>
        <div className="space-y-1">
          <h4 className="text-sm font-semibold text-slate-200">Chưa có dữ liệu phân tích biến động</h4>
          <p className="text-xs text-slate-400 max-w-sm mx-auto">
            Vui lòng chọn bảng kết quả kinh doanh từ tài liệu BCTC hoặc tải kịch bản mẫu để khởi tạo biểu đồ thác nước.
          </p>
        </div>
        {onRetry && (
          <button
            type="button"
            data-testid="waterfall-load-sample-btn"
            onClick={onRetry}
            className="min-h-[48px] px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-lg inline-flex items-center space-x-2 transition-colors cursor-pointer"
          >
            <RefreshCw className="w-4 h-4" />
            <span>Nạp kịch bản mẫu VNM</span>
          </button>
        )}
      </div>
    );
  }

  // Compute active scenario steps
  const activeScenarioConfig = SCENARIO_CONFIGS[scenario];
  const appliedDrivers = useMemo(() => {
    return applyScenarioToDrivers(initialDrivers, scenario);
  }, [initialDrivers, scenario]);

  const steps: WaterfallStep[] = useMemo(() => {
    return computeWaterfallSteps(appliedDrivers, initialDrivers);
  }, [appliedDrivers, initialDrivers]);

  const netIncomeStep = steps.find((s) => s.id === 'net_income') || steps[steps.length - 1];

  // SVG Dimension Math
  const svgWidth = 680;
  const svgHeight = 280;
  const marginTop = 30;
  const marginBottom = 50;
  const marginLeft = 30;
  const marginRight = 30;

  const chartWidth = svgWidth - marginLeft - marginRight;
  const chartHeight = svgHeight - marginTop - marginBottom;

  const maxVal = Math.max(...steps.map((s) => Math.max(s.startValue, s.endValue)), 100);
  const minVal = Math.min(...steps.map((s) => Math.min(s.startValue, s.endValue)), 0);
  const valueRange = maxVal - minVal || 1;

  const barCount = steps.length;
  const barSpacing = chartWidth / barCount;
  const barWidth = Math.min(barSpacing * 0.65, 56);

  const getY = (val: number) => {
    return marginTop + chartHeight - ((val - minVal) / valueRange) * chartHeight;
  };

  const zeroY = getY(0);

  const handleExportPdf = useCallback(() => {
    const citations: GroundingCitation[] = [];
    steps.forEach((s) => {
      if (s.citation) citations.push(s.citation);
    });

    const report: WaterfallExportReport = {
      title: 'Báo Cáo Phân Tích Cầu Nối Lợi Nhuận & So Sánh Kịch Bản',
      companyName,
      reportingPeriod,
      scenario,
      scenarioLabel: activeScenarioConfig.label,
      steps,
      citations,
      exportedAt: new Date().toLocaleString('vi-VN'),
      netIncomeValue: netIncomeStep?.signedValue || 0,
    };

    const ok = exportWaterfallToPdfOrPrint(report);
    if (ok) {
      setExportNotice('Đã xuất báo cáo kiểm toán PDF thành công');
      setTimeout(() => setExportNotice(null), 3000);
    }
  }, [steps, companyName, reportingPeriod, scenario, activeScenarioConfig, netIncomeStep]);

  return (
    <div
      data-testid="waterfall-chart-container"
      className="w-full bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4 select-none"
    >
      {/* 1. Header Bar: Title, Context, and Export PDF Button */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-3.5">
        <div className="flex items-center space-x-2.5">
          <div className="w-9 h-9 rounded-lg bg-indigo-950/80 border border-indigo-800/80 flex items-center justify-center text-indigo-400">
            <BarChart3 className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-100 flex items-center space-x-2">
              <span>Cầu Nối Lợi Nhuận & So Sánh Kịch Bản</span>
            </h3>
            <div className="text-xs text-slate-400">
              {companyName} • {reportingPeriod}
            </div>
          </div>
        </div>

        {/* PDF Export Button (>=48px kiosk ergonomic touch target) */}
        <button
          type="button"
          data-testid="waterfall-export-btn"
          onClick={handleExportPdf}
          title="Xuất báo cáo PDF kèm trích dẫn đối soát thị giác"
          className="min-h-[48px] px-4 py-2.5 bg-slate-800 hover:bg-slate-700 active:bg-slate-850 text-indigo-300 hover:text-indigo-200 border border-slate-700 rounded-lg text-xs font-semibold flex items-center space-x-2 transition-colors cursor-pointer shrink-0"
        >
          <Download className="w-4 h-4" />
          <span>Xuất Báo Cáo PDF</span>
        </button>
      </div>

      {exportNotice && (
        <div
          data-testid="waterfall-export-notice"
          className="px-3 py-2 bg-emerald-950/60 border border-emerald-800/80 rounded-lg text-xs text-emerald-300 flex items-center space-x-2"
        >
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          <span>{exportNotice}</span>
        </div>
      )}

      {/* 2. Scenario Switcher Chips (>=48px kiosk ergonomic touch target) */}
      <div className="space-y-2">
        <div className="text-xs font-semibold text-slate-400 flex items-center space-x-1.5">
          <Layers className="w-3.5 h-3.5 text-indigo-400" />
          <span>Chọn Kịch Bản Giả Lập:</span>
        </div>
        <div className="grid grid-cols-3 gap-2">
          {(['base', 'bull', 'bear'] as FinancialScenario[]).map((scKey) => {
            const sc = SCENARIO_CONFIGS[scKey];
            const isSelected = scenario === scKey;
            return (
              <button
                key={scKey}
                type="button"
                data-testid={`scenario-chip-${scKey}`}
                onClick={() => setScenario(scKey)}
                className={`min-h-[48px] px-3 py-2 rounded-lg border text-xs font-medium flex flex-col items-center justify-center transition-all cursor-pointer ${
                  isSelected
                    ? 'bg-indigo-600/20 border-indigo-500 text-indigo-200 shadow-sm'
                    : 'bg-slate-800/60 hover:bg-slate-800 border-slate-700 text-slate-300'
                }`}
              >
                <div className="flex items-center space-x-1">
                  {scKey === 'bull' && <TrendingUp className="w-3.5 h-3.5 text-emerald-400" />}
                  {scKey === 'bear' && <TrendingDown className="w-3.5 h-3.5 text-rose-400" />}
                  <span className="font-semibold">{sc.label}</span>
                </div>
              </button>
            );
          })}
        </div>
        <div className="text-[11px] text-slate-400 bg-slate-800/40 px-3 py-1.5 rounded-lg border border-slate-800/60">
          {activeScenarioConfig.description}
        </div>
      </div>

      {/* 3. SVG Waterfall Canvas */}
      <div className="relative w-full overflow-x-auto bg-slate-950/70 border border-slate-800 rounded-xl p-3">
        <svg
          data-testid="waterfall-svg"
          viewBox={`0 0 ${svgWidth} ${svgHeight}`}
          className="w-full h-auto min-w-[580px]"
        >
          {/* Zero baseline */}
          <line
            x1={marginLeft}
            y1={zeroY}
            x2={svgWidth - marginRight}
            y2={zeroY}
            stroke="#475569"
            strokeWidth="1"
          />

          {/* Render Bars and Connectors */}
          {steps.map((step, idx) => {
            const barX = marginLeft + idx * barSpacing + (barSpacing - barWidth) / 2;
            const topVal = Math.max(step.startValue, step.endValue);
            const bottomVal = Math.min(step.startValue, step.endValue);

            const barY = getY(topVal);
            const rawBarHeight = getY(bottomVal) - barY;
            const barHeight = Math.max(rawBarHeight, 2);

            let fillColor = '#6366f1'; // Indigo for total
            if (step.type === 'subtotal') fillColor = '#475569'; // Slate for subtotal
            if (step.type === 'positive_delta') fillColor = '#10b981'; // Emerald
            if (step.type === 'negative_delta') fillColor = '#f43f5e'; // Rose

            const isHovered = selectedStep?.id === step.id;

            return (
              <g
                key={step.id}
                className="cursor-pointer"
                onClick={() => setSelectedStep(step)}
              >
                {/* Horizontal connector from previous bar */}
                {idx > 0 && (
                  <line
                    x1={marginLeft + (idx - 1) * barSpacing + (barSpacing - barWidth) / 2 + barWidth}
                    y1={getY(steps[idx - 1].endValue)}
                    x2={barX}
                    y2={getY(steps[idx - 1].endValue)}
                    stroke="#475569"
                    strokeWidth="1"
                    strokeDasharray="3 3"
                  />
                )}

                {/* Waterfall Bar Rect */}
                <rect
                  data-testid={`waterfall-bar-${step.id}`}
                  x={barX}
                  y={barY}
                  width={barWidth}
                  height={barHeight}
                  rx="3"
                  fill={fillColor}
                  opacity={isHovered ? 1 : 0.88}
                  stroke={isHovered ? '#ffffff' : 'none'}
                  strokeWidth={isHovered ? 2 : 0}
                  className="transition-all"
                />

                {/* Value Label above/below bar */}
                <text
                  x={barX + barWidth / 2}
                  y={barY - 6}
                  textAnchor="middle"
                  fill="#cbd5e1"
                  fontSize="10"
                  fontFamily="monospace"
                  fontWeight="600"
                >
                  {step.type === 'negative_delta'
                    ? `-${Math.abs(step.signedValue).toLocaleString('vi-VN')}`
                    : step.type === 'positive_delta'
                    ? `+${step.signedValue.toLocaleString('vi-VN')}`
                    : step.signedValue.toLocaleString('vi-VN')}
                </text>

                {/* X-axis Label & Footnote */}
                <text
                  x={barX + barWidth / 2}
                  y={svgHeight - marginBottom + 18}
                  textAnchor="middle"
                  fill="#94a3b8"
                  fontSize="10.5"
                  fontWeight="500"
                >
                  {step.label.length > 12 ? `${step.label.slice(0, 10)}...` : step.label}
                </text>

                {step.citation?.footnoteId && (
                  <text
                    x={barX + barWidth / 2}
                    y={svgHeight - marginBottom + 32}
                    textAnchor="middle"
                    fill="#818cf8"
                    fontSize="9.5"
                    fontFamily="monospace"
                    fontWeight="700"
                  >
                    [{step.citation.footnoteId}]
                  </text>
                )}
              </g>
            );
          })}
        </svg>
      </div>

      {/* 4. Selected Step Drill-Down Drawer / Footnote Grounding */}
      {selectedStep && (
        <div
          data-testid="waterfall-detail-card"
          className="bg-slate-800/80 border border-slate-700/80 rounded-xl p-3.5 space-y-2"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <span className="text-xs font-semibold text-slate-200">{selectedStep.label}</span>
              {selectedStep.variancePercent !== undefined && (
                <span
                  className={`text-[10px] px-1.5 py-0.5 rounded font-mono font-bold ${
                    selectedStep.variancePercent >= 0
                      ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                      : 'bg-rose-950 text-rose-400 border border-rose-800'
                  }`}
                >
                  {selectedStep.variancePercent >= 0 ? '+' : ''}
                  {selectedStep.variancePercent}% vs Cơ sở
                </span>
              )}
            </div>
            <span className="font-mono text-xs font-bold text-slate-100">
              {selectedStep.signedValue.toLocaleString('vi-VN')} Tỷ VNĐ
            </span>
          </div>

          {selectedStep.citation ? (
            <div className="flex items-center justify-between text-xs text-slate-400 bg-slate-900/80 px-2.5 py-1.5 rounded-lg border border-slate-750">
              <div className="flex items-center space-x-2 truncate">
                <FileText className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
                <span className="truncate">
                  {selectedStep.citation.footnoteId || 'Thuyết minh'} • Trang{' '}
                  {selectedStep.citation.pageNumber} ({selectedStep.citation.documentId})
                </span>
              </div>
              {onCitationClick && (
                <button
                  type="button"
                  data-testid="view-citation-btn"
                  onClick={() => onCitationClick(selectedStep.citation!)}
                  className="min-h-[48px] px-3 py-1 text-xs font-semibold text-indigo-400 hover:text-indigo-300 flex items-center space-x-1 cursor-pointer shrink-0"
                >
                  <Eye className="w-3.5 h-3.5" />
                  <span>Xem BCTC</span>
                </button>
              )}
            </div>
          ) : (
            <div className="text-[11px] text-slate-500 italic">
              Chỉ tiêu trung gian được tính toán tự động từ mô hình biến động.
            </div>
          )}
        </div>
      )}
    </div>
  );
};
