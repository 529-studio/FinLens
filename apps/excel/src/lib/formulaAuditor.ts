/**
 * FinSight Excel Add-in Formula Auditor & Dependency Graph Traversal
 * Analyzes cell formula precedents/dependents, detects circular references,
 * evaluates financial model formulas deterministically (Zero eval),
 * and executes dynamic sensitivity recalculation.
 * Governed by ADR-001, Sprint 10 Task S10-05, and AGENTS.md Rules 1, 13, 15.
 */

/* global Excel */

export interface CellReference {
  raw: string;
  normalized: string;
  col: string;
  row: number;
}

export interface CellFormulaNode {
  address: string;
  formula?: string;
  value: number | string;
  precedents: string[];
  dependents: string[];
  isDriver: boolean;
  depth: number;
  label?: string;
  auditStatus: 'verified' | 'unverified' | 'formula_error' | 'circular_ref';
  annotation?: string;
}

export interface DependencyGraph {
  nodes: Map<string, CellFormulaNode>;
  circularReferences: string[][];
  hasCycles: boolean;
  topologicalOrder: string[];
}

export interface SensitivityScenario {
  id: string;
  name: string;
  driverValue: number;
  deltaPercentage: number;
  isBase?: boolean;
}

export interface MetricImpact {
  address: string;
  label: string;
  baseValue: number;
  stressedValue: number;
  delta: number;
  percentChange: number;
}

export interface SensitivityResult {
  driverAddress: string;
  baseValue: number;
  currentValue: number;
  deltaValue: number;
  deltaPercent: number;
  recalculatedCells: Record<string, number>;
  impactedKeyMetrics: MetricImpact[];
}

// ---------------------------------------------------------------------------
// Address Parsing & Normalization
// ---------------------------------------------------------------------------

const CELL_REGEX = /^\$?([A-Z]{1,3})\$?([1-9][0-9]{0,6})$/i;
const RANGE_REGEX = /^\$?([A-Z]{1,3})\$?([1-9][0-9]{0,6}):\$?([A-Z]{1,3})\$?([1-9][0-9]{0,6})$/i;

/**
 * Normalizes an Excel cell address (e.g. "$B$5" -> "B5", "b5" -> "B5").
 */
export function normalizeAddress(addr: string): string {
  const clean = addr.trim().replace(/\$/g, '').toUpperCase();
  return clean;
}

/**
 * Parses an Excel cell address into column and row components.
 */
export function parseCellAddress(addr: string): CellReference | null {
  const match = addr.trim().match(CELL_REGEX);
  if (!match) return null;
  const col = match[1].toUpperCase();
  const row = parseInt(match[2], 10);
  return {
    raw: addr,
    normalized: `${col}${row}`,
    col,
    row,
  };
}

/**
 * Converts column letter to 0-based column index (A -> 0, B -> 1, Z -> 25, AA -> 26).
 */
export function colToIndex(col: string): number {
  let index = 0;
  for (let i = 0; i < col.length; i++) {
    index = index * 26 + (col.charCodeAt(i) - 64);
  }
  return index - 1;
}

/**
 * Converts 0-based column index to column letter (0 -> A, 1 -> B, 26 -> AA).
 */
export function indexToCol(index: number): string {
  let temp = index;
  let letter = '';
  while (temp >= 0) {
    letter = String.fromCharCode((temp % 26) + 65) + letter;
    temp = Math.floor(temp / 26) - 1;
  }
  return letter;
}

/**
 * Expands an Excel range string (e.g. "B2:B4" or "A1:B2") into individual cell addresses.
 */
export function expandCellRange(rangeStr: string): string[] {
  const match = rangeStr.trim().match(RANGE_REGEX);
  if (!match) {
    const single = parseCellAddress(rangeStr);
    return single ? [single.normalized] : [];
  }

  const startCol = match[1].toUpperCase();
  const startRow = parseInt(match[2], 10);
  const endCol = match[3].toUpperCase();
  const endRow = parseInt(match[4], 10);

  const startColIdx = Math.min(colToIndex(startCol), colToIndex(endCol));
  const endColIdx = Math.max(colToIndex(startCol), colToIndex(endCol));
  const minRow = Math.min(startRow, endRow);
  const maxRow = Math.max(startRow, endRow);

  const cells: string[] = [];
  for (let c = startColIdx; c <= endColIdx; c++) {
    const colName = indexToCol(c);
    for (let r = minRow; r <= maxRow; r++) {
      cells.push(`${colName}${r}`);
    }
  }
  return cells;
}

/**
 * Extracts all unique precedent cell addresses referenced in a formula string.
 * Handles ranges, absolute addresses, and multi-term expressions.
 */
export function extractPrecedents(formula: string): string[] {
  if (!formula || typeof formula !== 'string') return [];
  const cleanFormula = formula.startsWith('=') ? formula.slice(1) : formula;

  const precedents = new Set<string>();

  // 1. Match and expand all cell ranges: e.g. B2:B9, $A$1:$C$10
  const rangePattern = /\$?[A-Z]{1,3}\$?[1-9][0-9]{0,6}:\$?[A-Z]{1,3}\$?[1-9][0-9]{0,6}/gi;
  const ranges = cleanFormula.match(rangePattern) || [];
  for (const r of ranges) {
    const expanded = expandCellRange(r);
    for (const cell of expanded) {
      precedents.add(cell);
    }
  }

  // 2. Remove matched ranges from formula to prevent double matching single cells
  const formulaWithoutRanges = cleanFormula.replace(rangePattern, ' ');

  // 3. Match single cell references: e.g. B5, $C$10, AA2
  // Must not match function names (e.g. SUM, AVERAGE) or arbitrary words followed by '('
  const cellPattern = /\b(?![A-Z]+\()\$?([A-Z]{1,3})\$?([1-9][0-9]{0,6})\b/gi;
  let match: RegExpExecArray | null;
  while ((match = cellPattern.exec(formulaWithoutRanges)) !== null) {
    const cellRef = parseCellAddress(match[0]);
    if (cellRef) {
      precedents.add(cellRef.normalized);
    }
  }

  return Array.from(precedents).sort();
}

// ---------------------------------------------------------------------------
// Zero-eval Deterministic Formula Evaluator
// ---------------------------------------------------------------------------

type TokenType = 'NUMBER' | 'IDENTIFIER' | 'OPERATOR' | 'LPAREN' | 'RPAREN' | 'COMMA';

interface Token {
  type: TokenType;
  value: string;
}

function tokenizeFormula(input: string): Token[] {
  const clean = input.startsWith('=') ? input.slice(1).trim() : input.trim();
  const tokens: Token[] = [];
  let i = 0;

  while (i < clean.length) {
    const ch = clean[i];

    if (/\s/.test(ch)) {
      i++;
      continue;
    }

    if (ch === '(') {
      tokens.push({ type: 'LPAREN', value: '(' });
      i++;
      continue;
    }

    if (ch === ')') {
      tokens.push({ type: 'RPAREN', value: ')' });
      i++;
      continue;
    }

    if (ch === ',') {
      tokens.push({ type: 'COMMA', value: ',' });
      i++;
      continue;
    }

    if (ch === '+' || ch === '-' || ch === '*' || ch === '/' || ch === '^' || ch === '%') {
      tokens.push({ type: 'OPERATOR', value: ch });
      i++;
      continue;
    }

    // Number (including decimals e.g. 0.05, 100, .5)
    if (/[0-9]/.test(ch) || (ch === '.' && i + 1 < clean.length && /[0-9]/.test(clean[i + 1]))) {
      let numStr = '';
      while (i < clean.length && (/[0-9]/.test(clean[i]) || clean[i] === '.')) {
        numStr += clean[i];
        i++;
      }
      tokens.push({ type: 'NUMBER', value: numStr });
      continue;
    }

    // Identifiers: functions (SUM, AVG) or Cell references (B5, $B$5, B2:B4)
    if (/[A-Za-z$]/.test(ch)) {
      let ident = '';
      while (i < clean.length && /[A-Za-z0-9$:]/.test(clean[i])) {
        ident += clean[i];
        i++;
      }
      tokens.push({ type: 'IDENTIFIER', value: ident.toUpperCase() });
      continue;
    }

    // Skip unknown character safely
    i++;
  }

  return tokens;
}

class ExpressionParser {
  private tokens: Token[];
  private pos = 0;
  private context: Record<string, number>;

  constructor(tokens: Token[], context: Record<string, number>) {
    this.tokens = tokens;
    this.context = context;
  }

  private peek(): Token | undefined {
    return this.tokens[this.pos];
  }

  private consume(expectedType?: TokenType): Token {
    const token = this.tokens[this.pos];
    if (!token) {
      throw new Error('Unexpected end of formula');
    }
    if (expectedType && token.type !== expectedType) {
      throw new Error(`Expected token ${expectedType} but found ${token.type} ('${token.value}')`);
    }
    this.pos++;
    return token;
  }

  parse(): number {
    const val = this.parseExpression();
    if (this.pos < this.tokens.length) {
      throw new Error(`Unexpected trailing token: '${this.tokens[this.pos].value}'`);
    }
    return val;
  }

  // expr -> term (('+' | '-') term)*
  private parseExpression(): number {
    let result = this.parseTerm();

    while (this.peek() && this.peek()!.type === 'OPERATOR' && (this.peek()!.value === '+' || this.peek()!.value === '-')) {
      const op = this.consume('OPERATOR').value;
      const right = this.parseTerm();
      if (op === '+') result += right;
      else result -= right;
    }

    return result;
  }

  // term -> power (('*' | '/') power)*
  private parseTerm(): number {
    let result = this.parsePower();

    while (this.peek() && this.peek()!.type === 'OPERATOR' && (this.peek()!.value === '*' || this.peek()!.value === '/')) {
      const op = this.consume('OPERATOR').value;
      const right = this.parsePower();
      if (op === '*') {
        result *= right;
      } else {
        if (right === 0) throw new Error('Division by zero in financial formula');
        result /= right;
      }
    }

    return result;
  }

  // power -> unary ('^' power)?
  private parsePower(): number {
    const base = this.parseUnary();
    if (this.peek() && this.peek()!.type === 'OPERATOR' && this.peek()!.value === '^') {
      this.consume('OPERATOR');
      const exp = this.parsePower();
      return Math.pow(base, exp);
    }
    return base;
  }

  // unary -> ('+' | '-')? factor
  private parseUnary(): number {
    if (this.peek() && this.peek()!.type === 'OPERATOR') {
      const op = this.peek()!.value;
      if (op === '+') {
        this.consume('OPERATOR');
        return this.parseUnary();
      }
      if (op === '-') {
        this.consume('OPERATOR');
        return -this.parseUnary();
      }
    }
    return this.parseFactor();
  }

  // factor -> primary ('%')?
  private parseFactor(): number {
    let val = this.parsePrimary();
    if (this.peek() && this.peek()!.type === 'OPERATOR' && this.peek()!.value === '%') {
      this.consume('OPERATOR');
      val = val / 100.0;
    }
    return val;
  }

  // primary -> NUMBER | IDENTIFIER '(' args ')' | CELL_REF | '(' expr ')'
  private parsePrimary(): number {
    const token = this.peek();
    if (!token) throw new Error('Unexpected end of expression');

    if (token.type === 'NUMBER') {
      this.consume('NUMBER');
      return parseFloat(token.value);
    }

    if (token.type === 'LPAREN') {
      this.consume('LPAREN');
      const val = this.parseExpression();
      this.consume('RPAREN');
      return val;
    }

    if (token.type === 'IDENTIFIER') {
      this.consume('IDENTIFIER');
      const ident = token.value;

      // Function call: IDENTIFIER '(' ... ')'
      if (this.peek() && this.peek()!.type === 'LPAREN') {
        this.consume('LPAREN');
        const args: number[] = [];

        if (this.peek() && this.peek()!.type !== 'RPAREN') {
          while (true) {
            // Check if next token is a range identifier like "B2:B9"
            if (this.peek() && this.peek()!.type === 'IDENTIFIER' && this.peek()!.value.includes(':')) {
              const rangeToken = this.consume('IDENTIFIER').value;
              const expanded = expandCellRange(rangeToken);
              for (const cell of expanded) {
                args.push(this.context[cell] ?? 0);
              }
            } else {
              args.push(this.parseExpression());
            }

            if (this.peek() && this.peek()!.type === 'COMMA') {
              this.consume('COMMA');
            } else {
              break;
            }
          }
        }

        this.consume('RPAREN');
        return this.evaluateFunction(ident, args);
      }

      // Check if it's a range without function, e.g. error
      if (ident.includes(':')) {
        const expanded = expandCellRange(ident);
        const sum = expanded.reduce((acc, cell) => acc + (this.context[cell] ?? 0), 0);
        return sum;
      }

      // Cell reference lookup
      const normalizedCell = normalizeAddress(ident);
      if (normalizedCell in this.context) {
        return this.context[normalizedCell];
      }

      // Unknown cell defaults to 0.0 in financial recalculation
      return 0.0;
    }

    throw new Error(`Unexpected token: ${token.value}`);
  }

  private evaluateFunction(name: string, args: number[]): number {
    const fn = name.toUpperCase();
    switch (fn) {
      case 'SUM':
        return args.reduce((acc, v) => acc + v, 0);
      case 'AVERAGE':
      case 'AVG':
        if (args.length === 0) return 0;
        return args.reduce((acc, v) => acc + v, 0) / args.length;
      case 'MIN':
        if (args.length === 0) return 0;
        return Math.min(...args);
      case 'MAX':
        if (args.length === 0) return 0;
        return Math.max(...args);
      case 'ABS':
        return Math.abs(args[0] ?? 0);
      case 'ROUND': {
        const val = args[0] ?? 0;
        const decimals = args[1] ?? 0;
        const factor = Math.pow(10, decimals);
        return Math.round(val * factor) / factor;
      }
      case 'PRODUCT':
        if (args.length === 0) return 0;
        return args.reduce((acc, v) => acc * v, 1);
      default:
        throw new Error(`Unsupported financial formula function: ${name}`);
    }
  }
}

/**
 * Evaluates an Excel mathematical formula string safely and deterministically.
 * Zero eval, zero external dependencies.
 */
export function safeEvaluateFormula(formula: string, context: Record<string, number>): number {
  if (!formula || typeof formula !== 'string') return 0;
  const tokens = tokenizeFormula(formula);
  if (tokens.length === 0) return 0;
  const parser = new ExpressionParser(tokens, context);
  return parser.parse();
}

// ---------------------------------------------------------------------------
// Dependency Graph Builder & Cycle Detection
// ---------------------------------------------------------------------------

export interface CellInputSpec {
  formula?: string;
  value?: number | string;
  label?: string;
}

/**
 * Builds the bidirectional dependency graph across cells, detects cycles,
 * and computes topological evaluation order.
 */
export function buildDependencyGraph(
  cells: Record<string, CellInputSpec>
): DependencyGraph {
  const nodes = new Map<string, CellFormulaNode>();

  // 1. Initialize all nodes
  for (const [rawAddr, spec] of Object.entries(cells)) {
    const addr = normalizeAddress(rawAddr);
    const hasFormula = Boolean(spec.formula && spec.formula.trim().startsWith('='));
    const precedents = hasFormula ? extractPrecedents(spec.formula!) : [];

    nodes.set(addr, {
      address: addr,
      formula: spec.formula,
      value: spec.value ?? 0,
      precedents,
      dependents: [],
      isDriver: !hasFormula,
      depth: 0,
      label: spec.label,
      auditStatus: hasFormula ? 'verified' : 'unverified',
    });
  }

  // 2. Populate dependent (reverse) edges
  for (const [addr, node] of nodes.entries()) {
    for (const prec of node.precedents) {
      if (!nodes.has(prec)) {
        // Precedent cell exists outside configured range; register as driver input
        nodes.set(prec, {
          address: prec,
          value: 0,
          precedents: [],
          dependents: [addr],
          isDriver: true,
          depth: 0,
          auditStatus: 'unverified',
        });
      } else {
        const precNode = nodes.get(prec)!;
        if (!precNode.dependents.includes(addr)) {
          precNode.dependents.push(addr);
        }
      }
    }
  }

  // 3. Cycle Detection (DFS with 3 colors: 0=unvisited, 1=visiting, 2=visited)
  const circularReferences: string[][] = [];
  const visited = new Map<string, number>();
  const path: string[] = [];

  function dfsCycle(curr: string) {
    visited.set(curr, 1);
    path.push(curr);

    const node = nodes.get(curr);
    if (node) {
      for (const next of node.dependents) {
        const state = visited.get(next) ?? 0;
        if (state === 1) {
          // Cycle detected!
          const cycleStartIdx = path.indexOf(next);
          const cycle = path.slice(cycleStartIdx).concat(next);
          circularReferences.push(cycle);
          if (node) node.auditStatus = 'circular_ref';
        } else if (state === 0) {
          dfsCycle(next);
        }
      }
    }

    path.pop();
    visited.set(curr, 2);
  }

  for (const addr of nodes.keys()) {
    if ((visited.get(addr) ?? 0) === 0) {
      dfsCycle(addr);
    }
  }

  // 4. Topological Sort (Kahn's algorithm)
  const inDegree = new Map<string, number>();
  for (const [addr, node] of nodes.entries()) {
    inDegree.set(addr, node.precedents.length);
  }

  const queue: string[] = [];
  for (const [addr, deg] of inDegree.entries()) {
    if (deg === 0) {
      queue.push(addr);
    }
  }

  const topologicalOrder: string[] = [];
  while (queue.length > 0) {
    const curr = queue.shift()!;
    topologicalOrder.push(curr);

    const node = nodes.get(curr);
    if (node) {
      for (const dep of node.dependents) {
        const currentDeg = inDegree.get(dep) ?? 0;
        const newDeg = currentDeg - 1;
        inDegree.set(dep, newDeg);
        if (newDeg === 0) {
          queue.push(dep);
        }
      }
    }
  }

  return {
    nodes,
    circularReferences,
    hasCycles: circularReferences.length > 0,
    topologicalOrder,
  };
}

// ---------------------------------------------------------------------------
// Dynamic Model Sensitivity & Recalculation Engine
// ---------------------------------------------------------------------------

/**
 * Recalculates model cells downstream of a driver cell when its value changes.
 */
export function recalculateModel(
  driverAddress: string,
  driverValue: number,
  graph: DependencyGraph,
  baseValues: Record<string, number>
): Record<string, number> {
  const normDriver = normalizeAddress(driverAddress);
  const currentValues: Record<string, number> = { ...baseValues, [normDriver]: driverValue };

  // Traverse in topological order to ensure precedents are evaluated before dependents
  for (const addr of graph.topologicalOrder) {
    if (addr === normDriver) {
      currentValues[addr] = driverValue;
      continue;
    }

    const node = graph.nodes.get(addr);
    if (!node || !node.formula) continue;

    try {
      const recalculated = safeEvaluateFormula(node.formula, currentValues);
      // Normalize IEEE-754 precision to avoid 55000.00000000001
      currentValues[addr] = Math.round((recalculated + Number.EPSILON) * 1e9) / 1e9;
    } catch {
      // Retain previous value if calculation fails
      currentValues[addr] = baseValues[addr] ?? 0;
    }
  }

  return currentValues;
}

/**
 * Runs a complete sensitivity evaluation for a driver parameter, computing deltas
 * and percentage changes across selected financial metrics.
 */
export function runSensitivityAnalysis(
  driverAddress: string,
  driverValue: number,
  graph: DependencyGraph,
  baseValues: Record<string, number>,
  keyMetrics: Array<{ address: string; label: string }> = []
): SensitivityResult {
  const normDriver = normalizeAddress(driverAddress);
  const baseDriverVal = baseValues[normDriver] ?? 0;
  const deltaValue = driverValue - baseDriverVal;
  const deltaPercent = baseDriverVal !== 0 ? (deltaValue / Math.abs(baseDriverVal)) * 100 : 0;

  const recalculatedCells = recalculateModel(driverAddress, driverValue, graph, baseValues);

  const impactedKeyMetrics: MetricImpact[] = keyMetrics.map((metric) => {
    const normAddr = normalizeAddress(metric.address);
    const base = baseValues[normAddr] ?? 0;
    const stressed = recalculatedCells[normAddr] ?? base;
    const diff = stressed - base;
    const pct = base !== 0 ? (diff / Math.abs(base)) * 100 : 0;

    return {
      address: normAddr,
      label: metric.label,
      baseValue: base,
      stressedValue: stressed,
      delta: diff,
      percentChange: pct,
    };
  });

  return {
    driverAddress: normDriver,
    baseValue: baseDriverVal,
    currentValue: driverValue,
    deltaValue,
    deltaPercent,
    recalculatedCells,
    impactedKeyMetrics,
  };
}

/**
 * Generates an audit trail annotation string suitable for an Excel cell comment.
 * Conforms to AGENTS.md Rule 15 (zero raw emojis) and ADR-001.
 */
export function generateAuditAnnotation(
  address: string,
  node: CellFormulaNode,
  graph: DependencyGraph,
  sourceDoc?: string,
  sourcePage?: number
): string {
  const lines: string[] = [
    `[FinTrace Audit Trail: Cell ${address}]`,
    `Status: [${node.auditStatus.toUpperCase()}]`,
  ];

  if (node.label) {
    lines.push(`Line Item: ${node.label}`);
  }

  if (node.formula) {
    lines.push(`Formula: ${node.formula}`);
    lines.push(`Precedents (${node.precedents.length}): ${node.precedents.join(', ') || 'None'}`);
  } else {
    lines.push(`Driver Parameter: Base Value = ${node.value}`);
  }

  if (node.dependents.length > 0) {
    lines.push(`Dependents (${node.dependents.length}): ${node.dependents.join(', ')}`);
  }

  lines.push(`Model Graph: ${graph.nodes.size} nodes evaluated`);

  if (sourceDoc) {
    lines.push(`Verified Grounding: Doc ${sourceDoc}${sourcePage ? ` (Page ${sourcePage})` : ''}`);
  }

  return lines.join(' | ');
}

/**
 * Updates an Excel cell value in the active worksheet with graceful test-safe fallback.
 */
export async function updateWorksheetCellValue(
  address: string,
  value: number
): Promise<{ success: boolean; address: string; value: number }> {
  const norm = normalizeAddress(address);

  if (typeof Excel !== 'undefined' && Excel.run) {
    try {
      await Excel.run(async (context) => {
        const sheet = context.workbook.worksheets.getActiveWorksheet();
        const range = sheet.getRange(norm);
        range.values = [[value]];
        await context.sync();
      });
      return { success: true, address: norm, value };
    } catch {
      return { success: false, address: norm, value };
    }
  }

  // Graceful fallback when Office.js is not present (browser/test)
  return { success: true, address: norm, value };
}

// ---------------------------------------------------------------------------
// One-at-a-Time (OAT) Tornado Sensitivity Analysis (Sprint 13 S13-08)
// ---------------------------------------------------------------------------

export interface TornadoDriverInput {
  address: string;
  label: string;
  swingPct?: number;
}

export interface TornadoBarResult {
  address: string;
  label: string;
  baseDriverValue: number;
  lowDriverValue: number;
  highDriverValue: number;
  baseTargetValue: number;
  lowTargetValue: number;
  highTargetValue: number;
  lowDelta: number;
  highDelta: number;
  spread: number;
  precedents: string[];
  dependents: string[];
  formula?: string;
}

/**
 * Computes One-at-a-Time (OAT) Tornado sensitivity swings for a set of driver cells
 * against a target KPI cell using deterministic zero-eval AST evaluation,
 * sorted descending by absolute impact spread (max - min).
 */
export function computeTornadoSensitivity(
  drivers: TornadoDriverInput[],
  targetAddress: string,
  graph: DependencyGraph,
  baseValues: Record<string, number>,
  defaultSwingPct: number = 10
): TornadoBarResult[] {
  if (!drivers || drivers.length === 0) return [];

  const normTarget = normalizeAddress(targetAddress);
  const baseTargetValue = baseValues[normTarget] ?? 0;

  const results: TornadoBarResult[] = drivers.map((driver) => {
    const normDriver = normalizeAddress(driver.address);
    const pct = Math.max(0.1, driver.swingPct ?? defaultSwingPct);
    const baseDriverValue = baseValues[normDriver] ?? 0;
    const step = Math.abs(baseDriverValue) * (pct / 100);
    const lowDriverValue = baseDriverValue - step;
    const highDriverValue = baseDriverValue + step;

    const lowRecalc = recalculateModel(normDriver, lowDriverValue, graph, baseValues);
    const highRecalc = recalculateModel(normDriver, highDriverValue, graph, baseValues);

    const lowTargetValue = lowRecalc[normTarget] ?? baseTargetValue;
    const highTargetValue = highRecalc[normTarget] ?? baseTargetValue;

    const lowDelta = lowTargetValue - baseTargetValue;
    const highDelta = highTargetValue - baseTargetValue;
    const spread = Math.abs(highTargetValue - lowTargetValue);

    const driverNode = graph.nodes.get(normDriver);

    return {
      address: normDriver,
      label: driver.label,
      baseDriverValue,
      lowDriverValue,
      highDriverValue,
      baseTargetValue,
      lowTargetValue,
      highTargetValue,
      lowDelta,
      highDelta,
      spread,
      precedents: driverNode?.precedents ?? [],
      dependents: driverNode?.dependents ?? [],
      formula: driverNode?.formula,
    };
  });

  return results.sort((a, b) => b.spread - a.spread);
}
