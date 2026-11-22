/**
 * Comprehensive Unit Tests for Formula Auditor & Sensitivity Recalculation Engine
 * Governed by Sprint 10 Task S10-05, AGENTS.md Rule 3, Rule 13, Rule 15.
 */

import { describe, it, expect } from 'vitest';
import {
  normalizeAddress,
  parseCellAddress,
  colToIndex,
  indexToCol,
  expandCellRange,
  extractPrecedents,
  safeEvaluateFormula,
  buildDependencyGraph,
  recalculateModel,
  runSensitivityAnalysis,
  generateAuditAnnotation,
  updateWorksheetCellValue,
} from '../formulaAuditor';

describe('Formula Auditor - Address & Range Operations', () => {
  it('normalizes addresses by removing $ and converting to uppercase', () => {
    expect(normalizeAddress('$b$5')).toBe('B5');
    expect(normalizeAddress('c10')).toBe('C10');
    expect(normalizeAddress('  $aa$12  ')).toBe('AA12');
  });

  it('parses valid cell addresses into column and row components', () => {
    const res = parseCellAddress('$C$10');
    expect(res).not.toBeNull();
    expect(res?.col).toBe('C');
    expect(res?.row).toBe(10);
    expect(res?.normalized).toBe('C10');

    expect(parseCellAddress('invalid_cell')).toBeNull();
  });

  it('converts column letters to indices and back symmetrically', () => {
    expect(colToIndex('A')).toBe(0);
    expect(colToIndex('B')).toBe(1);
    expect(colToIndex('Z')).toBe(25);
    expect(colToIndex('AA')).toBe(26);

    expect(indexToCol(0)).toBe('A');
    expect(indexToCol(1)).toBe('B');
    expect(indexToCol(25)).toBe('Z');
    expect(indexToCol(26)).toBe('AA');
  });

  it('expands single column ranges into discrete cell lists', () => {
    const expanded = expandCellRange('B2:B4');
    expect(expanded).toEqual(['B2', 'B3', 'B4']);
  });

  it('expands multi-column 2D ranges into discrete cell lists', () => {
    const expanded = expandCellRange('A1:B2');
    expect(expanded).toEqual(['A1', 'A2', 'B1', 'B2']);
  });

  it('extracts unique precedent cells from arithmetic and function formulas', () => {
    expect(extractPrecedents('=C8*(1+B5)')).toEqual(['B5', 'C8']);
    expect(extractPrecedents('=SUM(B2:B4) + C10')).toEqual(['B2', 'B3', 'B4', 'C10']);
    expect(extractPrecedents('=AVERAGE($A$1:$A$3) * $B$1')).toEqual(['A1', 'A2', 'A3', 'B1']);
    expect(extractPrecedents('100')).toEqual([]);
  });
});

describe('Formula Auditor - Zero-eval Deterministic Formula Evaluator', () => {
  it('evaluates basic arithmetic expressions', () => {
    const ctx = { A1: 10, B1: 20, C1: 5 };
    expect(safeEvaluateFormula('=A1 + B1', ctx)).toBe(30);
    expect(safeEvaluateFormula('=B1 - A1', ctx)).toBe(10);
    expect(safeEvaluateFormula('=A1 * C1', ctx)).toBe(50);
    expect(safeEvaluateFormula('=B1 / C1', ctx)).toBe(4);
    expect(safeEvaluateFormula('=2 ^ 3', ctx)).toBe(8);
  });

  it('evaluates percentage operators correctly', () => {
    const ctx = { B5: 5 }; // 5%
    expect(safeEvaluateFormula('=100 * (1 + 5%)', ctx)).toBe(105);
  });

  it('evaluates financial functions (SUM, AVERAGE, MIN, MAX, ROUND)', () => {
    const ctx = { B2: 100, B3: 200, B4: 300, D1: 15.678 };
    expect(safeEvaluateFormula('=SUM(B2:B4)', ctx)).toBe(600);
    expect(safeEvaluateFormula('=AVERAGE(B2:B4)', ctx)).toBe(200);
    expect(safeEvaluateFormula('=MIN(B2:B4)', ctx)).toBe(100);
    expect(safeEvaluateFormula('=MAX(B2:B4)', ctx)).toBe(300);
    expect(safeEvaluateFormula('=ROUND(D1, 2)', ctx)).toBe(15.68);
  });

  it('handles division by zero safely by throwing an informative error', () => {
    const ctx = { A1: 10, A2: 0 };
    expect(() => safeEvaluateFormula('=A1 / A2', ctx)).toThrow('Division by zero');
  });
});

describe('Formula Auditor - Dependency Graph & Sensitivity Analysis', () => {
  const modelCells = {
    B5: { value: 0.05, label: 'Tăng trưởng doanh thu' },
    C8: { value: 50000, label: 'Doanh thu năm trước' },
    C10: { formula: '=C8*(1+B5)', label: 'Doanh thu kế hoạch' },
    C12: { formula: '=C10*0.4', label: 'Lợi nhuận gộp' },
    C20: { formula: '=C12-5000', label: 'Lợi nhuận ròng' },
  };

  it('builds dependency graph with correct precedent and dependent edges', () => {
    const graph = buildDependencyGraph(modelCells);
    expect(graph.hasCycles).toBe(false);
    expect(graph.circularReferences.length).toBe(0);

    const b5 = graph.nodes.get('B5');
    expect(b5?.isDriver).toBe(true);
    expect(b5?.dependents).toContain('C10');

    const c10 = graph.nodes.get('C10');
    expect(c10?.precedents).toEqual(['B5', 'C8']);
    expect(c10?.dependents).toContain('C12');

    // Topological order guarantees B5 and C8 come before C10, and C10 before C12
    const b5Idx = graph.topologicalOrder.indexOf('B5');
    const c10Idx = graph.topologicalOrder.indexOf('C10');
    const c12Idx = graph.topologicalOrder.indexOf('C12');
    const c20Idx = graph.topologicalOrder.indexOf('C20');

    expect(b5Idx).toBeLessThan(c10Idx);
    expect(c10Idx).toBeLessThan(c12Idx);
    expect(c12Idx).toBeLessThan(c20Idx);
  });

  it('detects circular references cleanly and flags nodes', () => {
    const cyclicCells = {
      A1: { formula: '=B1 + 10' },
      B1: { formula: '=A1 * 2' },
    };
    const graph = buildDependencyGraph(cyclicCells);
    expect(graph.hasCycles).toBe(true);
    expect(graph.circularReferences.length).toBeGreaterThan(0);
  });

  it('recalculates model downstream when driver parameter changes', () => {
    const graph = buildDependencyGraph(modelCells);
    const baseValues = { B5: 0.05, C8: 50000, C10: 52500, C12: 21000, C20: 16000 };

    // Increase driver B5 from 5% (0.05) to 10% (0.10)
    const recalculated = recalculateModel('B5', 0.10, graph, baseValues);

    expect(recalculated.B5).toBe(0.10);
    expect(recalculated.C8).toBe(50000);
    expect(recalculated.C10).toBeCloseTo(55000, 2);
    expect(recalculated.C12).toBeCloseTo(22000, 2);
    expect(recalculated.C20).toBeCloseTo(17000, 2);
  });

  it('runs complete sensitivity analysis computing deltas and percentage changes', () => {
    const graph = buildDependencyGraph(modelCells);
    const baseValues = { B5: 0.05, C8: 50000, C10: 52500, C12: 21000, C20: 16000 };
    const keyMetrics = [
      { address: 'C10', label: 'Doanh thu kế hoạch' },
      { address: 'C20', label: 'Lợi nhuận ròng' },
    ];

    const result = runSensitivityAnalysis('B5', 0.10, graph, baseValues, keyMetrics);

    expect(result.driverAddress).toBe('B5');
    expect(result.baseValue).toBe(0.05);
    expect(result.currentValue).toBe(0.10);
    expect(result.deltaPercent).toBe(100); // from 0.05 to 0.10 is +100%

    expect(result.impactedKeyMetrics.length).toBe(2);
    const revMetric = result.impactedKeyMetrics.find((m) => m.address === 'C10');
    expect(revMetric?.baseValue).toBe(52500);
    expect(revMetric?.stressedValue).toBeCloseTo(55000, 2);
    expect(revMetric?.delta).toBeCloseTo(2500, 2);
    expect(revMetric?.percentChange).toBeCloseTo(4.7619, 2);
  });

  it('generates zero-emoji audit annotations compliant with Rule 15 and ADR-001', () => {
    const graph = buildDependencyGraph(modelCells);
    const c10Node = graph.nodes.get('C10')!;
    const annotation = generateAuditAnnotation('C10', c10Node, graph, 'VNM_BCTC_2023', 15);

    expect(annotation).toContain('[FinTrace Audit Trail: Cell C10]');
    expect(annotation).toContain('Status: [VERIFIED]');
    expect(annotation).toContain('Formula: =C8*(1+B5)');
    expect(annotation).toContain('Verified Grounding: Doc VNM_BCTC_2023 (Page 15)');

    // Rule 15 zero emojis check
    const emojiRegex = /\p{Extended_Pictographic}/u;
    expect(emojiRegex.test(annotation)).toBe(false);
  });

  it('executes updateWorksheetCellValue cleanly with fallback in test environment', async () => {
    const res = await updateWorksheetCellValue('B5', 0.075);
    expect(res.success).toBe(true);
    expect(res.address).toBe('B5');
    expect(res.value).toBe(0.075);
  });
});
