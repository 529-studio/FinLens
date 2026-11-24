import { describe, it, expect } from 'vitest';
import {
  DEFAULT_VNM_WATERFALL_DRIVERS,
  applyScenarioToDrivers,
  computeWaterfallSteps,
  generateWaterfallHtmlReport,
} from '../waterfallExporter';
import { WaterfallDriverInput, WaterfallExportReport } from '../../../types/waterfall.types';

describe('waterfallExporter Utility', () => {
  it('correctly calculates waterfall step accumulators and signed delta normalization', () => {
    const sampleDrivers: WaterfallDriverInput[] = [
      { id: 'rev', label: 'Doanh thu thuần', type: 'total', value: 100 },
      { id: 'cogs', label: 'Giá vốn', type: 'negative_delta', value: 40 }, // unsigned input marked negative
      { id: 'gp', label: 'Lợi nhuận gộp', type: 'subtotal', value: 0 },
      { id: 'fin', label: 'Thu nhập tài chính', type: 'positive_delta', value: 10 },
      { id: 'sga', label: 'Chi phí SG&A', type: 'negative_delta', value: -20 }, // signed negative input
      { id: 'np', label: 'Lợi nhuận sau thuế', type: 'total', value: 50 },
    ];

    const steps = computeWaterfallSteps(sampleDrivers);

    // 1. Revenue Total Pillar: from 0 to 100
    expect(steps[0].startValue).toBe(0);
    expect(steps[0].endValue).toBe(100);
    expect(steps[0].signedValue).toBe(100);

    // 2. COGS Negative Delta: from 100 down to 60
    expect(steps[1].startValue).toBe(100);
    expect(steps[1].endValue).toBe(60);
    expect(steps[1].signedValue).toBe(-40);

    // 3. Gross Profit Subtotal Pillar: from 0 to 60
    expect(steps[2].startValue).toBe(0);
    expect(steps[2].endValue).toBe(60);

    // 4. Financial Income Positive Delta: from 60 up to 70
    expect(steps[3].startValue).toBe(60);
    expect(steps[3].endValue).toBe(70);
    expect(steps[3].signedValue).toBe(10);

    // 5. SG&A Negative Delta: from 70 down to 50
    expect(steps[4].startValue).toBe(70);
    expect(steps[4].endValue).toBe(50);
    expect(steps[4].signedValue).toBe(-20);

    // 6. Net Profit Total Pillar: from 0 to 50
    expect(steps[5].startValue).toBe(0);
    expect(steps[5].endValue).toBe(50);
  });

  it('applies Bull and Bear scenario stress multipliers accurately', () => {
    const base = DEFAULT_VNM_WATERFALL_DRIVERS;

    // Base scenario
    const baseApplied = applyScenarioToDrivers(base, 'base');
    expect(baseApplied[0].value).toBe(50617);
    expect(baseApplied[1].value).toBe(-30016);

    // Bull scenario: Revenue * 1.10 = 55679; COGS -30016 * 0.97 = -29116
    const bullApplied = applyScenarioToDrivers(base, 'bull');
    expect(bullApplied[0].value).toBe(Math.round(50617 * 1.1));
    expect(bullApplied[1].value).toBe(-Math.round(30016 * 0.97));

    // Bear scenario: Revenue * 0.90 = 45555; COGS -30016 * 1.05 = -31517
    const bearApplied = applyScenarioToDrivers(base, 'bear');
    expect(bearApplied[0].value).toBe(Math.round(50617 * 0.9));
    expect(bearApplied[1].value).toBe(-Math.round(30016 * 1.05));
  });

  it('computes variance percentages against base drivers', () => {
    const base = DEFAULT_VNM_WATERFALL_DRIVERS;
    const bull = applyScenarioToDrivers(base, 'bull');

    const bullSteps = computeWaterfallSteps(bull, base);
    const revStep = bullSteps.find((s) => s.id === 'revenue');
    expect(revStep?.variancePercent).toBe(10); // +10%
  });

  it('generates compliant print-ready HTML report with visual grounding citations and zero raw emojis', () => {
    const steps = computeWaterfallSteps(DEFAULT_VNM_WATERFALL_DRIVERS);
    const citations = DEFAULT_VNM_WATERFALL_DRIVERS.map((d) => d.citation).filter(Boolean) as any[];

    const report: WaterfallExportReport = {
      title: 'Báo Cáo Cầu Nối Lợi Nhuận',
      companyName: 'Vinamilk (VNM)',
      reportingPeriod: 'Năm 2023',
      scenario: 'base',
      scenarioLabel: 'Cơ sở (0%)',
      steps,
      citations,
      exportedAt: '2026-11-24 21:00:00',
      netIncomeValue: 11286,
    };

    const html = generateWaterfallHtmlReport(report);

    expect(html).toContain('Báo Cáo Cầu Nối Lợi Nhuận');
    expect(html).toContain('Vinamilk (VNM)');
    expect(html).toContain('11.286 Tỷ VNĐ');
    expect(html).toContain('TM 24');
    expect(html).toContain('[120, 50, 160, 950]');

    // Rule 15 check: Zero raw emojis
    const emojiRegex = /\p{Extended_Pictographic}/u;
    expect(emojiRegex.test(html)).toBe(false);
  });
});
