# S12-01: Multi-Document Anomaly & Discrepancy Detection Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an enterprise-grade multi-document anomaly & discrepancy detection engine (`Cross-Filing Variance Auditor`) capable of detecting cross-filing restatements, balance sheet equation imbalances, calculation inconsistencies, segment consolidation mismatches, and unexpected YoY variances with 100% visual grounding citations.

**Architecture:**
A modular analytical engine in `packages/core-engine`:
1. `packages/core-engine/src/contracts.py`: Defines DTOs (`DiscrepancyType`, `DiscrepancySeverity`, `DiscrepancyItem`, `DiscrepancySummary`, `DiscrepancyAuditRequest`, `DiscrepancyAuditResponse`).
2. `packages/core-engine/src/discrepancy_detector.py`: Pure financial auditing rules and `DiscrepancyDetector` engine with configurable tolerance, severity classification, and health scoring.
3. `packages/core-engine/src/main.py`: Exposes `POST /api/v1/audit/discrepancies` with enterprise RBAC (`Permission.DOC_READ`), strict path traversal validation (`^[a-zA-Z0-9_\-]+$`), and audit event logging.

**Tech Stack:**
- Python 3.13, FastAPI, Pydantic v2, Pytest, LanceDB.
- Standards: AGENTS.md Rules 1, 2, 3, 11, 12, 13, 14, 15 and ADR-003.

**Spec:** Issue #97 (`[rag-ml] S12-01: Multi-Document Anomaly & Discrepancy Detection Engine (Cross-Filing Variance Auditor)`).

---

## Global Constraints

- **Git Flow (Rule 12):** Active branch is `feat/s12-01-discrepancy-detector` targeting `dev`. PR merge commit required.
- **Security & Path Traversal (Rule 13B):** Every `document_id` strictly validated against regex `^[a-zA-Z0-9_\-]+$` and rejects any `..` path traversal attempt.
- **Zero-Leak Policy (Rule 2):** No sensitive keys, private tokens, or file paths leaked in responses.
- **Zero Raw Emojis in UI / Output (Rule 15):** Strict 0 raw emojis in narrative summaries, audit messages, and code comments.
- **Visual Grounding Standard (ADR-003):** Every discrepancy evidence citation includes `document_id`, `page_number`, and normalized `BoundingBox` $[0, 1000]$.
- **Deterministic Math:** Pure IEEE-754 precision normalization with `safe_divide` and configurable rounding tolerance.

---

## Review Focus

1. **Path Traversal Across Target Documents:** Malicious document IDs like `../../etc/passwd` must be immediately rejected with HTTP 400 Bad Request.
2. **Missing Document in Store:** If a requested document target is not found in the vector index, return HTTP 404 with specific document ID.
3. **Restatement Variance vs True Error:** Distinguish between restatements (historical figure updated in a later filing) and immediate mathematical imbalances ($Assets \neq Liabilities + Equity$).
4. **Tolerance Boundary Handling:** Rounding differences below `tolerance_absolute` must be classified as `INFO` or suppressed, while differences exceeding tolerance are flagged as `CRITICAL` or `WARNING`.
5. **Zero Division & None Safety:** Missing metrics or 0 base values in percentage variance calculation must not trigger runtime crashes or unhandled exceptions.

---

### Task 1: Discrepancy Data Contracts (`contracts.py`)

**Files:**
- Modify: `packages/core-engine/src/contracts.py`
- Test: `packages/core-engine/tests/test_discrepancy_detector.py`

**Interfaces:**
- `DiscrepancyType(str, Enum)`: `RESTATEMENT`, `BALANCE_SHEET_IMBALANCE`, `CALCULATION_INCONSISTENCY`, `UNEXPECTED_VARIANCE`, `SEGMENT_CONSOLIDATION_MISMATCH`
- `DiscrepancySeverity(str, Enum)`: `CRITICAL`, `WARNING`, `INFO`
- `DiscrepancyItem`: `id: str`, `discrepancy_type: DiscrepancyType`, `severity: DiscrepancySeverity`, `metric_name: str`, `description: str`, `expected_value: Optional[float]`, `reported_value: Optional[float]`, `variance_absolute: Optional[float]`, `variance_percentage: Optional[float]`, `period: str`, `source_document_id: str`, `comparative_document_id: Optional[str]`, `evidences: List[GroundedEvidence]`, `resolution_hint: Optional[str]`
- `DiscrepancySummary`: `total_checks: int`, `discrepancies_found: int`, `critical_count: int`, `warning_count: int`, `info_count: int`, `health_score: float`
- `DiscrepancyAuditRequest`: `documents: List[PortfolioDocumentTarget]`, `variance_threshold_pct: float = 20.0`, `check_restatements: bool = True`, `check_accounting_equations: bool = True`, `check_internal_calculations: bool = True`, `check_segment_consolidation: bool = True`, `tolerance_absolute: float = 1.0`
- `DiscrepancyAuditResponse`: `summary: DiscrepancySummary`, `discrepancies: List[DiscrepancyItem]`, `audited_documents: List[str]`, `execution_time_ms: float`, `audit_narrative: str`

- [ ] **Step 1: Write failing tests for contracts**
  Create `packages/core-engine/tests/test_discrepancy_detector.py` with tests for model instantiation, validation constraints, and path traversal rejection on document targets.
- [ ] **Step 2: Run test to verify failure**
  Run: `pytest packages/core-engine/tests/test_discrepancy_detector.py -v`
  Expected: FAIL (`ImportError` / `NameError` for missing contracts).
- [ ] **Step 3: Implement contracts in `contracts.py`**
  Add models with Pydantic v2 field validations.
- [ ] **Step 4: Run test to verify pass**
  Run: `pytest packages/core-engine/tests/test_discrepancy_detector.py -k "test_discrepancy_contracts" -v`
  Expected: PASS.
- [ ] **Step 5: Commit**
  Run: `git add packages/core-engine/src/contracts.py packages/core-engine/tests/test_discrepancy_detector.py && git commit -m "feat(contracts): add discrepancy detection and audit models"`

---

### Task 2: Pure Financial Discrepancy Engine (`discrepancy_detector.py`)

**Files:**
- Create: `packages/core-engine/src/discrepancy_detector.py`
- Modify: `packages/core-engine/tests/test_discrepancy_detector.py`

**Interfaces:**
- `check_balance_sheet_equation(assets, liabilities, equity, doc_id, period, tolerance, evidences) -> Optional[DiscrepancyItem]`
- `check_income_statement_math(revenue, cogs, gross_profit, doc_id, period, tolerance, evidences) -> Optional[DiscrepancyItem]`
- `check_operating_profit_math(gross_profit, operating_expenses, operating_profit, doc_id, period, tolerance, evidences) -> Optional[DiscrepancyItem]`
- `check_restatement(metric_name, original_val, comparative_val, period, orig_doc, comp_doc, tolerance, evidences) -> Optional[DiscrepancyItem]`
- `check_unexpected_variance(metric_name, val_prev, val_curr, period_prev, period_curr, doc_prev, doc_curr, threshold_pct, evidences) -> Optional[DiscrepancyItem]`
- `check_segment_consolidation(segment_name, segment_values, total_value, doc_id, period, tolerance, evidences) -> Optional[DiscrepancyItem]`
- `compute_audit_health_score(critical, warning, info, total_checks) -> float`
- `DiscrepancyDetector`: `audit(request: DiscrepancyAuditRequest, retriever=None) -> DiscrepancyAuditResponse`

- [ ] **Step 1: Write failing tests for mathematical detection rules**
  Add unit tests in `test_discrepancy_detector.py` covering balance sheet imbalance, restatement detection, unexpected YoY variances, calculation errors, and health scoring.
- [ ] **Step 2: Run test to verify failure**
  Run: `pytest packages/core-engine/tests/test_discrepancy_detector.py -k "test_detection" -v`
  Expected: FAIL (`ModuleNotFoundError` for `discrepancy_detector`).
- [ ] **Step 3: Implement `discrepancy_detector.py`**
  Implement auditing functions and `DiscrepancyDetector` with zero raw emojis, safe division, and precision rounding.
- [ ] **Step 4: Run test to verify pass**
  Run: `pytest packages/core-engine/tests/test_discrepancy_detector.py -k "test_detection" -v`
  Expected: PASS.
- [ ] **Step 5: Commit**
  Run: `git add packages/core-engine/src/discrepancy_detector.py packages/core-engine/tests/test_discrepancy_detector.py && git commit -m "feat(core-engine): implement discrepancy and variance detection engine"`

---

### Task 3: REST Endpoint Integration (`main.py`)

**Files:**
- Modify: `packages/core-engine/src/main.py`
- Modify: `packages/core-engine/tests/test_discrepancy_detector.py`

**Interfaces:**
- Endpoint: `POST /api/v1/audit/discrepancies`
- Consumes: `DiscrepancyAuditRequest`
- Produces: `DiscrepancyAuditResponse`
- Security: RBAC `Permission.DOC_READ`, path traversal regex verification `^[a-zA-Z0-9_\-]+$`

- [ ] **Step 1: Write failing tests for API endpoint**
  Add TestClient tests for `POST /api/v1/audit/discrepancies`:
  - Success with valid documents.
  - 400 Bad Request on path traversal (`../../etc/passwd`).
  - 404 Not Found on un-ingested document.
  - 401/403 on missing or invalid JWT bearer token.
- [ ] **Step 2: Run test to verify failure**
  Run: `pytest packages/core-engine/tests/test_discrepancy_detector.py -k "test_api" -v`
  Expected: FAIL (404 Not Found for missing endpoint).
- [ ] **Step 3: Implement endpoint in `main.py`**
  Wire `DiscrepancyDetector` instance, document path validation, RBAC dependency, and route handler.
- [ ] **Step 4: Run test to verify pass**
  Run: `pytest packages/core-engine/tests/test_discrepancy_detector.py -v`
  Expected: All tests PASS.
- [ ] **Step 5: Commit**
  Run: `git add packages/core-engine/src/main.py packages/core-engine/tests/test_discrepancy_detector.py && git commit -m "feat(api): mount discrepancy audit endpoint with RBAC and path traversal guards"`

---

### Task 4: Full Test Suite Verification & Independent Subagent Audit

**Files:**
- Test all: `packages/core-engine/tests/`

- [ ] **Step 1: Run complete core-engine test suite**
  Run: `pytest packages/core-engine/tests/ -v`
  Expected: 100% pass across all tests.
- [ ] **Step 2: Push branch and open Pull Request**
  Push `feat/s12-01-discrepancy-detector` and create PR targeting `dev`.
- [ ] **Step 3: Dispatch Independent Subagent Audit (Rule 13A)**
  Invoke `research` or `self` subagent to perform an independent audit of the PR diff against security and DoD criteria.
- [ ] **Step 4: Merge PR with merge commit**
  Run `gh pr merge <PR_NUMBER> --merge`.
