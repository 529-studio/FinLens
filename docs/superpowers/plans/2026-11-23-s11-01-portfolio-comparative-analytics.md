# S11-01: Multi-Document Portfolio Synthesis & Cross-Filing Comparative Analytics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable financial analysts to synthesize and compare multi-document portfolios across corporate filings, computing deterministic financial metrics (YoY deltas, CAGR, margin trajectories, peer rankings) and preserving 100% visual grounding citations.

**Architecture:**
A decoupled domain service and endpoint pipeline:
1. `packages/core-engine/src/contracts.py`: Defines request/response models (`PortfolioDocumentTarget`, `PortfolioSynthesisRequest`, `PortfolioSynthesisResponse`, `EntityMetricSeries`, `PeerRankingItem`, `PortfolioSummary`).
2. `packages/core-engine/src/comparative_query.py`: Implements `PortfolioSynthesisEngine` encapsulating metadata resolution (explicit with regex/store fallback), financial mathematics (CAGR, YoY, Gross/Net Margins with IEEE-754 rounding), partitioned retrieval, and peer group ranking.
3. `packages/core-engine/src/main.py`: Mounts `POST /api/v1/portfolio/synthesize` with RBAC authorization (`Permission.DOC_READ`), strict path traversal defense (`^[a-zA-Z0-9_\-]+$`), and audit integration.

**Tech Stack:**
- Backend: Python 3.12, FastAPI, Pydantic v2, LanceDB, MLX / LiteLLM, Pytest.
- Standards: AGENTS.md Rules 1, 2, 3, 11, 12, 13, 14, 15.

**Spec:** `docs/superpowers/specs/2026-11-23-s11-01-portfolio-comparative-analytics-design.md`

---

## Global Constraints

- **Git Flow (Rule 12):** Active branch is `feat/s11-01-portfolio-comparative-analytics` targeting `dev`. Merge commit required.
- **Security & Path Traversal (Rule 13B):** Every `document_id` strictly validated against regex `^[a-zA-Z0-9_\-]+$`.
- **Zero-Leak Policy (Rule 2):** Zero credentials or private tokens exposed in debug logs or response payloads.
- **Zero Raw Emojis in UI / Output (Rule 15):** 0 raw emojis in narrative summaries, responses, or code comments. Clean vector/text formatting only.
- **Visual Grounding Standard (ADR-003):** Every grounded evidence must specify `document_id`, `page_number`, and normalized `BoundingBox` $[0, 1000]$ with `ymax > ymin` and `xmax > xmin`.
- **Memory Ceiling:** Maintain $< 6.0\text{ GB}$ Unified Memory usage during batch partitioned retrieval.

---

## Review Focus

1. **Path Traversal Across Document IDs:** Supplying `["../../etc/passwd", "valid_doc"]` must immediately trigger HTTP 400 Bad Request.
2. **Missing Document Handling in Portfolio:** If one or more documents in the portfolio are not indexed in LanceDB, return HTTP 404 with specific document IDs identified.
3. **CAGR Boundary Handling:** When base period value $V_0 \le 0$ or ending period value $V_n \le 0$, `cagr` must gracefully return `None` rather than raising a mathematical domain error or `NaN`.
4. **Metadata Fallback Robustness:** When `entity` or `period` are `None`, regex resolution correctly parses tokens like `VNM_2023_AUDITED` into entity `VNM` and period `2023`.
5. **Visual Citation Attribution:** Each calculated metric in time series or peer ranking must link back to its corresponding `GroundedEvidence` matching the exact `document_id` and page.

---

### Task 1: Portfolio Data Contracts (`packages/core-engine/src/contracts.py`)

**Files:**
- Modify: `packages/core-engine/src/contracts.py`
- Test: `packages/core-engine/tests/test_portfolio_synthesis.py`

**Interfaces:**
- `BenchmarkRole(str, Enum)`: `"target"`, `"peer"`, `"benchmark"`
- `PortfolioDocumentTarget`: `document_id: str`, `entity: Optional[str]`, `period: Optional[str]`, `role: BenchmarkRole`
- `PortfolioSynthesisRequest`: `documents: List[PortfolioDocumentTarget]`, `query_text: Optional[str]`, `metrics_requested: List[str]`, `inference_mode: str`
- `TimeSeriesDataPoint`: `period: str`, `value: Optional[float]`, `unit: str`, `yoy_growth: Optional[float]`, `evidence: Optional[GroundedEvidence]`
- `EntityMetricSeries`: `entity: str`, `metric: str`, `series: List[TimeSeriesDataPoint]`, `cagr: Optional[float]`
- `PeerRankingItem`: `rank: int`, `entity: str`, `period: str`, `metric_value: float`, `metric_name: str`, `growth_rate: Optional[float]`, `evidence: Optional[GroundedEvidence]`
- `PortfolioSummary`: `total_entities: int`, `total_periods: int`, `portfolio_revenue_aggregate: Optional[float]`, `weighted_net_margin: Optional[float]`, `fastest_growing_entity: Optional[str]`, `highest_margin_entity: Optional[str]`
- `PortfolioSynthesisResponse`: `portfolio_summary: PortfolioSummary`, `time_series_metrics: List[EntityMetricSeries]`, `peer_rankings: List[PeerRankingItem]`, `synthesis_narrative: str`, `evidences: List[GroundedEvidence]`, `retrieved_pages: Dict[str, List[int]]`, `latency_ms: float`, `engine_used: str`

- [ ] **Step 1: Write failing tests for contracts**
  Create `packages/core-engine/tests/test_portfolio_synthesis.py`:
  - `test_portfolio_contracts_validation_success`: Construct valid request and verify field serialization.
  - `test_portfolio_contracts_path_traversal_rejection`: Passing invalid characters in `document_id` raises `ValidationError`.
  - `test_portfolio_contracts_document_count_bounds`: Passing < 2 or > 10 documents raises `ValidationError`.

- [ ] **Step 2: Run tests to verify they fail**
  Command: `pytest packages/core-engine/tests/test_portfolio_synthesis.py -v`
  Expected: FAIL (`ImportError` / `NameError` for missing classes).

- [ ] **Step 3: Implement contracts in `contracts.py`**
  Add the Pydantic models with field validations to `packages/core-engine/src/contracts.py`.

- [ ] **Step 4: Run tests to verify they pass**
  Command: `pytest packages/core-engine/tests/test_portfolio_synthesis.py -k "test_portfolio_contracts" -v`
  Expected: PASS.

- [ ] **Step 5: Commit changes**
  Command: `git add packages/core-engine/src/contracts.py packages/core-engine/tests/test_portfolio_synthesis.py && git commit -m "feat(contracts): add portfolio synthesis and comparative analytics DTOs"`

---

### Task 2: Pure Financial Math & Metadata Resolution (`packages/core-engine/src/comparative_query.py`)

**Files:**
- Create: `packages/core-engine/src/comparative_query.py`
- Modify: `packages/core-engine/tests/test_portfolio_synthesis.py`

**Interfaces:**
- `resolve_target_metadata(target: PortfolioDocumentTarget, store_pages: Optional[List[Dict[str, Any]]] = None) -> Tuple[str, str]`
- `calculate_yoy(v_prev: Optional[float], v_curr: Optional[float]) -> Optional[float]`
- `calculate_cagr(v_start: Optional[float], v_end: Optional[float], n_years: int) -> Optional[float]`
- `calculate_margins(revenue: Optional[float], gross_profit: Optional[float], net_profit: Optional[float]) -> Tuple[Optional[float], Optional[float]]`
- `rank_entities_by_metric(series_list: List[EntityMetricSeries], metric_name: str, target_period: Optional[str] = None) -> List[PeerRankingItem]`
- `compute_portfolio_summary(time_series: List[EntityMetricSeries], peer_rankings: List[PeerRankingItem]) -> PortfolioSummary`

- [ ] **Step 1: Write failing tests for math & metadata functions**
  Add to `test_portfolio_synthesis.py`:
  - `test_resolve_target_metadata_explicit`: Explicit `entity` and `period` preserved.
  - `test_resolve_target_metadata_regex_fallback`: `VNM_2023_AUDITED` -> `("VNM", "2023")`.
  - `test_calculate_yoy_standard_and_edge_cases`: Normal calculation, zero previous, negative base, floating-point precision.
  - `test_calculate_cagr_multi_year`: Exact 3-year CAGR, 0 or negative base returns `None`, single-year handling.
  - `test_calculate_margins`: Revenue zero handling, gross margin, net margin.
  - `test_rank_entities_by_metric`: Correct ranking order and tie-breaking.

- [ ] **Step 2: Run tests to verify they fail**
  Command: `pytest packages/core-engine/tests/test_portfolio_synthesis.py -k "test_resolve or test_calculate or test_rank" -v`
  Expected: FAIL (`ModuleNotFoundError: No module named 'comparative_query'`).

- [ ] **Step 3: Implement math and metadata resolution functions**
  Implement in `packages/core-engine/src/comparative_query.py`.

- [ ] **Step 4: Run tests to verify they pass**
  Command: `pytest packages/core-engine/tests/test_portfolio_synthesis.py -k "test_resolve or test_calculate or test_rank" -v`
  Expected: PASS.

- [ ] **Step 5: Commit changes**
  Command: `git add packages/core-engine/src/comparative_query.py packages/core-engine/tests/test_portfolio_synthesis.py && git commit -m "feat(analytics): implement financial math and metadata resolution in comparative_query"`

---

### Task 3: Portfolio Synthesis Engine & Inference Coordination (`packages/core-engine/src/comparative_query.py`)

**Files:**
- Modify: `packages/core-engine/src/comparative_query.py`
- Modify: `packages/core-engine/tests/test_portfolio_synthesis.py`

**Interfaces:**
- `PortfolioSynthesisEngine`:
  - `__init__(self, store, retriever, router)`
  - `async def synthesize(self, req: PortfolioSynthesisRequest) -> PortfolioSynthesisResponse`
  - Internal methods:
    * `_retrieve_portfolio_pages(self, document_ids: List[str], query: str) -> Dict[str, List[int]]`
    * `_assemble_image_payloads(self, retrieved_pages: Dict[str, List[int]]) -> Dict[str, List[Tuple[str, int]]]`
    * `_build_time_series(self, vlm_metrics: List[Dict[str, Any]], targets: List[PortfolioDocumentTarget], evidences: List[GroundedEvidence]) -> List[EntityMetricSeries]`

- [ ] **Step 1: Write failing tests for PortfolioSynthesisEngine**
  Add to `test_portfolio_synthesis.py`:
  - `test_engine_synthesize_success_mocked`: Mock store and router; verify response contains `portfolio_summary`, `time_series_metrics`, `peer_rankings`, `synthesis_narrative`, and valid `evidences`.
  - `test_engine_synthesize_grounding_preservation`: Verify all evidences have `document_id`, `page_number`, and normalized bounding box $[0, 1000]$.
  - `test_engine_synthesize_missing_doc_raises_404`: Passing non-existent document ID raises appropriate exception.

- [ ] **Step 2: Run tests to verify they fail**
  Command: `pytest packages/core-engine/tests/test_portfolio_synthesis.py -k "test_engine_synthesize" -v`
  Expected: FAIL (`AttributeError` / missing `PortfolioSynthesisEngine`).

- [ ] **Step 3: Implement `PortfolioSynthesisEngine`**
  Implement full coordination logic in `packages/core-engine/src/comparative_query.py`.

- [ ] **Step 4: Run tests to verify they pass**
  Command: `pytest packages/core-engine/tests/test_portfolio_synthesis.py -k "test_engine_synthesize" -v`
  Expected: PASS.

- [ ] **Step 5: Commit changes**
  Command: `git add packages/core-engine/src/comparative_query.py packages/core-engine/tests/test_portfolio_synthesis.py && git commit -m "feat(engine): implement PortfolioSynthesisEngine in comparative_query"`

---

### Task 4: API Endpoint Mounting & Security Integration (`packages/core-engine/src/main.py`)

**Files:**
- Modify: `packages/core-engine/src/main.py`
- Modify: `packages/core-engine/tests/test_portfolio_synthesis.py`

**Interfaces:**
- Endpoint: `POST /api/v1/portfolio/synthesize`
  - Authorization: `Depends(require_permission(Permission.DOC_READ))`
  - Path traversal check: Validate all `document_id`s in `req.documents`.
  - Existence check: Return 404 if any document ID is missing from `retriever.store`.
  - Returns: `PortfolioSynthesisResponse`

- [ ] **Step 1: Write failing integration tests for endpoint**
  Add to `test_portfolio_synthesis.py`:
  - `test_api_portfolio_synthesize_success`: Valid request with ingested test documents returns 200 and complete schema.
  - `test_api_portfolio_synthesize_unauthorized`: Request without valid JWT or insufficient role returns 401/403.
  - `test_api_portfolio_synthesize_path_traversal`: Request with `../../etc/passwd` returns 400 or 422.
  - `test_api_portfolio_synthesize_missing_document`: Request with `NON_EXISTENT_DOC` returns 404.

- [ ] **Step 2: Run tests to verify they fail**
  Command: `pytest packages/core-engine/tests/test_portfolio_synthesis.py -k "test_api_portfolio" -v`
  Expected: FAIL (404 Not Found on route `/api/v1/portfolio/synthesize`).

- [ ] **Step 3: Mount endpoint and wire engine in `main.py`**
  Initialize `PortfolioSynthesisEngine` and expose `POST /api/v1/portfolio/synthesize`.

- [ ] **Step 4: Run full test suite to verify they pass**
  Command: `pytest packages/core-engine/tests/test_portfolio_synthesis.py -v && pytest packages/core-engine/tests/ -v`
  Expected: ALL PASS (100% pass rate).

- [ ] **Step 5: Commit changes**
  Command: `git add packages/core-engine/src/main.py packages/core-engine/tests/test_portfolio_synthesis.py && git commit -m "feat(api): mount POST /api/v1/portfolio/synthesize endpoint with RBAC and security guards"`

---

### Task 5: Empirical Verification & Independent Subagent Audit

- [ ] **Step 1: Run live empirical verification cURL test against active daemon**
  Test live endpoint with actual JSON payload and document citations.
- [ ] **Step 2: Dispatch Independent Subagent (`research` or `self`) for Audit (Rules 13A & 14)**
  Audit diff, path traversal defenses, zero-leak compliance, and zero raw emojis in source.
- [ ] **Step 3: Create PR targeting `dev` with merge commit and subagent sign-off**
