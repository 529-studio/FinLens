# S11-02: Automated Financial Ratio Calculation Engine & Cash Flow Health Screener Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a robust, decoupled financial ratio engine and cash flow health screener in `packages/core-engine/src/ratio_engine.py` exposed via `POST /api/v1/analysis/ratios`, supporting 14 standard ratios, DuPont 3-stage decomposition, cash flow health grading, and 100% visual grounding.

**Architecture:**
A decoupled domain service and endpoint pipeline:
1. `packages/core-engine/src/contracts.py`: Defines request/response models (`FinancialStatementInputs`, `FinancialRatioRequest`, `FinancialRatioResponse`, `RatioCategoryGroup`, `RatioItem`, `DuPontAnalysis`, `CashFlowHealthScore`).
2. `packages/core-engine/src/ratio_engine.py`: Implements `FinancialRatioEngine` encapsulating pure ratio calculations (liquidity, solvency, profitability), DuPont 3-stage decomposition, cash flow health grading (`STRONG`, `MODERATE`, `CAUTION`, `DISTRESS`), zero-division safety, and automated line item visual extraction.
3. `packages/core-engine/src/main.py`: Mounts `POST /api/v1/analysis/ratios` with RBAC authorization (`Permission.DOC_READ`), strict path traversal defense (`^[a-zA-Z0-9_\-]+$`), and audit integration.

**Tech Stack:**
- Backend: Python 3.12, FastAPI, Pydantic v2, LanceDB, MLX / LiteLLM, Pytest.
- Standards: AGENTS.md Rules 1, 2, 3, 11, 12, 13B, 14, 15.

**Spec:** `docs/superpowers/specs/2026-11-24-s11-02-financial-ratio-cash-flow-engine-design.md`

---

## Global Constraints

- **Git Flow (Rule 12):** Active branch is `feat/s11-02-financial-ratio-cash-flow-engine` targeting `dev`. Merge commit required.
- **Security & Path Traversal (Rule 13B):** `document_id` strictly validated against regex `^[a-zA-Z0-9_\-]+$`.
- **Zero-Leak Policy (Rule 2):** Zero credentials or private tokens exposed in debug logs or response payloads.
- **Zero Raw Emojis in UI / Output (Rule 15):** 0 raw emojis in narrative summaries, benchmarks, or code comments. Clean vector/text formatting only.
- **Visual Grounding Standard (ADR-003):** Every grounded evidence must specify `document_id`, `page_number`, and normalized `BoundingBox` $[0, 1000]$ with `ymax > ymin` and `xmax > xmin`.
- **Arithmetic Safety:** Strict zero-division handling and negative denominator checks. All floats normalized via `round((val + 1e-9), 4)`.

---

## Review Focus

1. **Path Traversal Across Document IDs:** Supplying `../../etc/passwd` must immediately trigger HTTP 400 Bad Request or 422 Unprocessable Entity.
2. **Missing Document Handling:** If the requested document is not indexed in LanceDB, return HTTP 404 cleanly.
3. **Division-by-Zero Safety:** When denominators are zero or `None` (e.g. Current Liabilities = 0, Equity = 0, Interest Expense = 0), ratio calculation must return `None` rather than crashing with `ZeroDivisionError` or returning `Infinity` / `NaN`.
4. **DuPont Consistency:** Product of Net Margin, Asset Turnover, and Financial Leverage must mathematically reconcile with ROE.
5. **Cash Flow Quality Logic:** A company with high positive Net Income but negative Operating Cash Flow ($OCF < 0$) must be classified as `DISTRESS` with clear warning signals.

---

### Task 1: Financial Ratio Data Contracts (`packages/core-engine/src/contracts.py`)

**Files:**
- Modify: `packages/core-engine/src/contracts.py`
- Test: `packages/core-engine/tests/test_ratio_engine.py`

**Interfaces:**
- `FinancialStatementInputs`: Line items for Income Statement, Balance Sheet, Cash Flow Statement.
- `FinancialRatioRequest`: `document_id: str`, `raw_inputs_override: Optional[FinancialStatementInputs]`, `include_dupont: bool`, `include_cash_flow_screening: bool`, `inference_mode: str`.
- `RatioCategory(str, Enum)`: `"liquidity"`, `"solvency"`, `"profitability"`, `"efficiency"`.
- `BenchmarkStatus(str, Enum)`: `"optimal"`, `"adequate"`, `"warning"`, `"critical"`, `"not_applicable"`.
- `RatioItem`: `code: str`, `name: str`, `category: RatioCategory`, `value: Optional[float]`, `unit: str`, `benchmark_status: BenchmarkStatus`, `formula_description: str`, `evidences: List[GroundedEvidence]`.
- `RatioCategoryGroup`: `category: RatioCategory`, `ratios: List[RatioItem]`.
- `DuPontAnalysis`: `net_profit_margin: Optional[float]`, `asset_turnover: Optional[float]`, `equity_multiplier: Optional[float]`, `roe: Optional[float]`, `formula_narrative: str`, `evidences: List[GroundedEvidence]`.
- `CashFlowHealthGrade(str, Enum)`: `"STRONG"`, `"MODERATE"`, `"CAUTION"`, `"DISTRESS"`.
- `CashFlowHealthScore`: `grade: CashFlowHealthGrade`, `earnings_quality_ratio: Optional[float]`, `free_cash_flow: Optional[float]`, `ocf_to_current_debt: Optional[float]`, `health_summary: str`, `warning_signals: List[str]`, `evidences: List[GroundedEvidence]`.
- `FinancialRatioResponse`: `document_id: str`, `ratio_groups: List[RatioCategoryGroup]`, `dupont_analysis: Optional[DuPontAnalysis]`, `cash_flow_health: Optional[CashFlowHealthScore]`, `raw_inputs_used: FinancialStatementInputs`, `evidences: List[GroundedEvidence]`, `latency_ms: float`, `engine_used: str`.

- [ ] **Step 1: Write failing tests for contracts**
  Create `packages/core-engine/tests/test_ratio_engine.py`:
  - `test_ratio_contracts_validation_success`: Construct valid request and verify field serialization.
  - `test_ratio_contracts_path_traversal_rejection`: Passing `../../etc/passwd` in `document_id` raises `ValidationError`.

- [ ] **Step 2: Run tests to verify they fail**
  Command: `packages/core-engine/.venv/bin/pytest packages/core-engine/tests/test_ratio_engine.py -v`
  Expected: FAIL (`ImportError` / missing classes).

- [ ] **Step 3: Implement contracts in `contracts.py`**
  Add the Pydantic models to `packages/core-engine/src/contracts.py`.

- [ ] **Step 4: Run tests to verify they pass**
  Command: `packages/core-engine/.venv/bin/pytest packages/core-engine/tests/test_ratio_engine.py -k "test_ratio_contracts" -v`
  Expected: PASS.

- [ ] **Step 5: Commit changes**
  Command: `git add packages/core-engine/src/contracts.py packages/core-engine/tests/test_ratio_engine.py && git commit -m "feat(contracts): add financial ratio and cash flow screener DTOs"`

---

### Task 2: Pure Ratio Mathematics & Cash Flow Screening Logic (`packages/core-engine/src/ratio_engine.py`)

**Files:**
- Create: `packages/core-engine/src/ratio_engine.py`
- Modify: `packages/core-engine/tests/test_ratio_engine.py`

**Interfaces:**
- `calculate_liquidity_ratios(inputs: FinancialStatementInputs, evidences_map: Dict[str, GroundedEvidence]) -> List[RatioItem]`
- `calculate_solvency_ratios(inputs: FinancialStatementInputs, evidences_map: Dict[str, GroundedEvidence]) -> List[RatioItem]`
- `calculate_profitability_ratios(inputs: FinancialStatementInputs, evidences_map: Dict[str, GroundedEvidence]) -> List[RatioItem]`
- `calculate_dupont_3stage(inputs: FinancialStatementInputs, evidences_map: Dict[str, GroundedEvidence]) -> Optional[DuPontAnalysis]`
- `screen_cash_flow_health(inputs: FinancialStatementInputs, evidences_map: Dict[str, GroundedEvidence]) -> Optional[CashFlowHealthScore]`

- [ ] **Step 1: Write failing tests for pure math functions**
  Add to `test_ratio_engine.py`:
  - `test_liquidity_ratios_calculation_and_benchmarks`: Test Current, Quick, Cash ratios and benchmark status assignment.
  - `test_solvency_and_leverage_ratios_edge_cases`: Test D/E, Debt-to-Assets, Financial Leverage, Interest Coverage, and zero denominator safety.
  - `test_profitability_and_dupont_decomposition`: Test Gross/Net Margin, ROA, ROE, and DuPont 3-stage reconciliation.
  - `test_cash_flow_health_screener_grades`: Test `STRONG`, `MODERATE`, `CAUTION`, `DISTRESS` grading based on OCF, Net Income, and Capex.
  - `test_zero_division_and_negative_equity_safety`: Ensure all divisions by zero return `None` gracefully without crashing.

- [ ] **Step 2: Run tests to verify they fail**
  Command: `packages/core-engine/.venv/bin/pytest packages/core-engine/tests/test_ratio_engine.py -k "test_liquidity or test_solvency or test_profitability or test_cash_flow or test_zero" -v`
  Expected: FAIL (`ModuleNotFoundError: No module named 'ratio_engine'`).

- [ ] **Step 3: Implement mathematical ratio calculations and screener**
  Implement in `packages/core-engine/src/ratio_engine.py`.

- [ ] **Step 4: Run tests to verify they pass**
  Command: `packages/core-engine/.venv/bin/pytest packages/core-engine/tests/test_ratio_engine.py -k "test_liquidity or test_solvency or test_profitability or test_cash_flow or test_zero" -v`
  Expected: PASS.

- [ ] **Step 5: Commit changes**
  Command: `git add packages/core-engine/src/ratio_engine.py packages/core-engine/tests/test_ratio_engine.py && git commit -m "feat(analytics): implement financial ratio math and cash flow screener in ratio_engine"`

---

### Task 3: Financial Ratio Engine Coordination & Visual Extraction (`packages/core-engine/src/ratio_engine.py`)

**Files:**
- Modify: `packages/core-engine/src/ratio_engine.py`
- Modify: `packages/core-engine/tests/test_ratio_engine.py`

**Interfaces:**
- `FinancialRatioEngine`:
  - `__init__(self, store, retriever, router)`
  - `async def analyze(self, req: FinancialRatioRequest) -> FinancialRatioResponse`
  - `_extract_line_items_from_document(self, document_id: str, mode: str) -> Tuple[FinancialStatementInputs, Dict[str, GroundedEvidence]]`

- [ ] **Step 1: Write failing tests for FinancialRatioEngine**
  Add to `test_ratio_engine.py`:
  - `test_engine_analyze_with_override_inputs`: Passing manual inputs bypasses extraction and returns fully calculated response.
  - `test_engine_analyze_automated_extraction_mocked`: Mock store and router; verify extraction parses line items and computes ratios.
  - `test_engine_analyze_missing_document_raises_404`: Passing non-existent document ID raises `FileNotFoundError`.

- [ ] **Step 2: Run tests to verify they fail**
  Command: `packages/core-engine/.venv/bin/pytest packages/core-engine/tests/test_ratio_engine.py -k "test_engine_analyze" -v`
  Expected: FAIL.

- [ ] **Step 3: Implement `FinancialRatioEngine` coordination logic**
  Implement in `packages/core-engine/src/ratio_engine.py`.

- [ ] **Step 4: Run tests to verify they pass**
  Command: `packages/core-engine/.venv/bin/pytest packages/core-engine/tests/test_ratio_engine.py -k "test_engine_analyze" -v`
  Expected: PASS.

- [ ] **Step 5: Commit changes**
  Command: `git add packages/core-engine/src/ratio_engine.py packages/core-engine/tests/test_ratio_engine.py && git commit -m "feat(engine): implement FinancialRatioEngine coordinator in ratio_engine"`

---

### Task 4: API Endpoint Mounting & Security Integration (`packages/core-engine/src/main.py`)

**Files:**
- Modify: `packages/core-engine/src/main.py`
- Modify: `packages/core-engine/tests/test_ratio_engine.py`

**Interfaces:**
- Endpoint: `POST /api/v1/analysis/ratios`
  - Authorization: `Depends(require_permission(Permission.DOC_READ))`
  - Path traversal guard on `req.document_id`
  - Document existence check in LanceDB store
  - Returns: `FinancialRatioResponse`

- [ ] **Step 1: Write failing integration tests for endpoint**
  Add to `test_ratio_engine.py`:
  - `test_api_ratios_endpoint_success`: Valid request returns 200 and complete schema.
  - `test_api_ratios_endpoint_path_traversal`: Malicious `document_id` returns 400 or 422.
  - `test_api_ratios_endpoint_missing_document`: Unindexed document returns 404.
  - `test_api_ratios_endpoint_unauthorized`: Malformed/expired JWT returns 401.

- [ ] **Step 2: Run tests to verify they fail**
  Command: `packages/core-engine/.venv/bin/pytest packages/core-engine/tests/test_ratio_engine.py -k "test_api_ratios" -v`
  Expected: FAIL (404 on route `/api/v1/analysis/ratios`).

- [ ] **Step 3: Mount endpoint and wire engine in `main.py`**
  Initialize `ratio_engine = FinancialRatioEngine(...)` and wire `POST /api/v1/analysis/ratios`.

- [ ] **Step 4: Run full test suite to verify they pass**
  Command: `packages/core-engine/.venv/bin/pytest packages/core-engine/tests/test_ratio_engine.py -v && packages/core-engine/.venv/bin/pytest packages/core-engine/tests/ -v`
  Expected: ALL PASS.

- [ ] **Step 5: Commit changes**
  Command: `git add packages/core-engine/src/main.py packages/core-engine/tests/test_ratio_engine.py && git commit -m "feat(api): mount POST /api/v1/analysis/ratios endpoint with RBAC and security guards"`

---

### Task 5: Empirical Verification, Knowledge Sync & Independent Subagent Audit

- [ ] **Step 1: Run live empirical verification cURL test against active daemon**
  Test live endpoint with actual JSON payload and document citations on running host daemon.
- [ ] **Step 2: Sync Knowledge Hook & Zero-Emoji Check**
  Record Lesson 31 in `docs/lesson_learn.md`, sync via `npm run harvest:lessons`, and verify 0 raw emojis in code.
- [ ] **Step 3: Update Lore Shared Memory**
  Record `api:/api/v1/analysis/ratios` and `sym:packages/core-engine/src/ratio_engine.py#FinancialRatioEngine` in Lore.
- [ ] **Step 4: Dispatch Independent Subagent (`research`) for Audit (Rules 13A & 14)**
  Audit diff, path traversal defenses, zero-leak compliance, and zero raw emojis in source.
- [ ] **Step 5: Create PR targeting `dev` with merge commit and subagent sign-off**
