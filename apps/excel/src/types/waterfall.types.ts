/**
 * FinTrace Scenario Waterfall Chart & PDF Export Types
 * Governed by Sprint 11 Task S11-05, AGENTS.md Rule 13, and frontend-4file-and-resilient-ui.
 */

export type WaterfallDriverType = 'total' | 'positive_delta' | 'negative_delta' | 'subtotal';
export type FinancialScenario = 'base' | 'bull' | 'bear';

export interface GroundingCitation {
  documentId: string;
  pageNumber: number;
  footnoteId?: string;
  lineItemText: string;
  boundingBox?: [number, number, number, number]; // [ymin, xmin, ymax, xmax] in [0, 1000]
}

export interface WaterfallDriverInput {
  id: string;
  label: string;
  type: WaterfallDriverType;
  value: number; // In billions VND
  citation?: GroundingCitation;
}

export interface WaterfallStep extends WaterfallDriverInput {
  startValue: number; // Computed accumulator start for rendering
  endValue: number;   // Computed accumulator end for rendering
  signedValue: number; // Normalized signed magnitude
  variancePercent?: number; // Optional variance percentage vs. base scenario
}

export interface ScenarioDefinition {
  id: FinancialScenario;
  label: string;
  revenueGrowthMultiplier: number; // e.g. 1.0 for Base, 1.10 for Bull (+10%), 0.90 for Bear (-10%)
  costEfficiencyMultiplier: number; // e.g. 1.0 for Base, 0.97 for Bull (-3% costs), 1.05 for Bear (+5% costs)
  description: string;
}

export interface WaterfallExportReport {
  title: string;
  companyName: string;
  reportingPeriod: string;
  scenario: FinancialScenario;
  scenarioLabel: string;
  steps: WaterfallStep[];
  citations: GroundingCitation[];
  exportedAt: string;
  netIncomeValue: number;
}
