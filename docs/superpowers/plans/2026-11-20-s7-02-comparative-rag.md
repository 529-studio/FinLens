# S7-02: Multi-Document Comparative Visual RAG Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable financial analysts to perform comparative queries cross-referencing multiple fiscal periods (e.g. BCTC 2022 vs BCTC 2023) across multiple document indices in LanceDB, synthesizing YoY growth metrics and side-by-side visual grounding.

**Architecture:**
A multi-document retrieval and synthesis pipeline across the core daemon and desktop client:
1. `packages/core-engine`: Multi-document vector retrieval in `VisualRetriever.comparative_search()` across multiple LanceDB document indices; comparative synthesis in `VlmRouter` / `MLXEngine` calculating YoY metrics; exposed via `POST /api/v1/query/comparative` with strict path traversal defense on all `document_ids`.
2. `apps/desktop`: 4-file pattern extension in Desktop client (`visual_rag.types.ts` -> `visual_rag.fetch.ts` -> `useVisualRag.hook.ts` -> `SplitView.component.tsx`) supporting comparative query mode, multi-document selection, YoY metric cards, and dual-document visual citation jumping.

**Tech Stack:** 
- Backend: Python 3.12, FastAPI, LanceDB, PyMuPDF, MLX / LiteLLM, Pydantic v2.
- Frontend: React 19, TypeScript, TanStack Query, Tailwind CSS, Lucide React.
- Verification: Pytest, Vitest, Playwright MCP, Independent Subagent Audit.

**Spec:** Issue #43 (`[rag-ml] S7-02: Multi-Document Comparative Visual RAG Across Multiple Fiscal Years`), `docs/HANDOFF-s6.md`, and AGENTS.md (Rules 1, 11, 12, 13, 14, 15).

---

## Global Constraints

- **Git Flow (Rule 12):** Active branch must be created as `feat/s7-comparative-rag` from `dev`. Merge commit required into `dev`.
- **Security & Path Traversal (Rule 13B):** Every item in `document_ids` must validate against regex `^[a-zA-Z0-9_\-]+$` and `is_path_safe`. Max 5 documents per query.
- **Visual Grounding Standards (ADR-003):** All bounding box coordinates must be normalized to integer scale $[0, 1000]$ with `ymax > ymin` and `xmax > xmin`. Each grounded evidence must specify its source `document_id` and `page_number`.
- **Frontend 4-File Pattern (Rule 1):** DTO -> pure fetch -> TanStack Query hook -> UI component.
- **Kiosk Ergonomics & Zero-Emoji (Rules 1 & 15):** Min $48\text{px}$ touch targets; zero raw Unicode emojis; Lucide React SVG iconography exclusively.
- **Independent Audit (Rule 13A & 14):** PR cannot be merged without sign-off from an independent subagent (`research` or `self`).

---

## Review Focus

1. **Path Traversal Across Document IDs:** Supplying `["../../etc/passwd", "valid_doc"]` must immediately trigger HTTP 400 Bad Request.
2. **Missing or Non-existent Document Handling:** If one of the requested document IDs is not found in LanceDB, the endpoint must return a clean 404 or structured error indicating the missing document ID.
3. **Multi-Document Citation Linkage:** When clicking a citation from Document A (e.g. 2022 Page 1), the PDF viewer must load Document A; when clicking a citation from Document B (e.g. 2023 Page 1), the PDF viewer must switch or split to Document B without UI state corruption.
4. **YoY Metric Calculation Precision:** The comparative synthesis must extract numerical values accurately from both documents and calculate the YoY percentage difference without sign inversion.
5. **Memory & Token Hygiene:** Memory ceiling (< 6GB Unified Memory) must be maintained when processing multi-document visual patches.

---

### Task 1: Backend Multi-Document Comparative RAG Pipeline (`packages/core-engine`)

**Files:**
- Modify: `packages/core-engine/src/contracts.py`
- Modify: `packages/core-engine/src/retriever.py`
- Modify: `packages/core-engine/src/mlx_engine.py`
- Modify: `packages/core-engine/src/cloud_router.py`
- Modify: `packages/core-engine/src/vlm_router.py`
- Modify: `packages/core-engine/src/main.py`
- Test: `packages/core-engine/tests/test_comparative_query.py`

**Interfaces:**
- `contracts.py`:
  - `GroundedEvidence`: add optional `document_id: Optional[str] = None`
  - `ComparativeQueryRequest(document_ids: List[str], query_text: str, top_k_per_doc: int = 1, inference_mode: str = "auto")`
  - `ComparativeQueryResponse(document_ids: List[str], query_text: str, answer: str, comparative_metrics: Dict[str, Any], evidences: List[GroundedEvidence], retrieved_pages: Dict[str, List[int]], engine_used: str, latency_ms: float)`
- `retriever.py`:
  - `comparative_search(document_ids: List[str], query: str, top_k_per_doc: int = 1) -> Dict[str, List[int]]`
- `main.py`:
  - `POST /api/v1/query/comparative`

- [ ] **Step 1: Write failing tests for comparative RAG**
  Create `packages/core-engine/tests/test_comparative_query.py`:
  - `test_comparative_query_success`: Ingest 2 sample documents, run comparative query, verify both documents retrieved, YoY synthesis present, and evidences tagged with correct `document_id`.
  - `test_comparative_query_traversal_rejection`: Supplying malicious `document_ids` returns 400.
  - `test_comparative_query_insufficient_documents`: Supplying 1 document ID returns 400.
  - `test_comparative_query_missing_document`: Supplying non-existent document ID returns 404.

- [ ] **Step 2: Run tests to verify they fail**
  Run: `packages/core-engine/.venv/bin/pytest packages/core-engine/tests/test_comparative_query.py -v`
  Expected: FAIL.

- [ ] **Step 3: Implement data contracts and multi-index retrieval**
  - Add `ComparativeQueryRequest` and `ComparativeQueryResponse` to `contracts.py`.
  - Update `VisualRetriever.comparative_search` to query multiple document tables in LanceDB.

- [ ] **Step 4: Implement comparative VLM synthesis and endpoint in `main.py`**
  - Wire `analyze_comparative_documents` into `VlmRouter` / `MLXEngine` / `CloudRouter`.
  - Expose `POST /api/v1/query/comparative`.

- [ ] **Step 5: Run tests to verify they pass**
  Run: `packages/core-engine/.venv/bin/pytest packages/core-engine/tests/test_comparative_query.py -v`
  Expected: PASS 100%.

- [ ] **Step 6: Run full backend regression suite**
  Run: `packages/core-engine/.venv/bin/pytest packages/core-engine/tests/ -v`
  Expected: All tests pass.

---

### Task 2: Frontend Desktop Multi-Document Comparative UI (`apps/desktop`)

**Files:**
- Modify: `apps/desktop/src/types/visual_rag.types.ts`
- Modify: `apps/desktop/src/api/visual_rag.fetch.ts`
- Modify: `apps/desktop/src/hooks/useVisualRag.hook.ts`
- Modify: `apps/desktop/src/components/layout/SplitView.component.tsx`
- Modify: `apps/desktop/src/App.tsx`
- Test: `apps/desktop/src/components/layout/__tests__/ComparativeQuery.test.tsx`

**Interfaces:**
- `visual_rag.types.ts`:
  - `ComparativeQueryRequestDTO`
  - `ComparativeQueryResponseDTO`
  - `ComparativeMetricDTO`
- `visual_rag.fetch.ts`:
  - `fetchComparativeQuery(payload: ComparativeQueryRequestDTO): Promise<ComparativeQueryResponseDTO>`
- `useVisualRag.hook.ts`:
  - `useComparativeQuery()` mutation
- UI:
  - Multi-document selector chip group (allowing analyst to pick 2 documents).
  - Mode toggle: "Truy vấn đơn lẻ" vs "So sánh đa BCTC (YoY)".
  - Comparative Metric Cards showing YoY delta (e.g. Doanh thu: 2022 vs 2023, Tăng trưởng: +X%).
  - Grounded evidence badges highlighting source document and page.

- [ ] **Step 1: Update DTOs in `apps/desktop/src/types/visual_rag.types.ts`**
- [ ] **Step 2: Add fetch function in `apps/desktop/src/api/visual_rag.fetch.ts`**
- [ ] **Step 3: Add mutation hook in `apps/desktop/src/hooks/useVisualRag.hook.ts`**
- [ ] **Step 4: Implement comparative UI controls and result cards in `SplitView.component.tsx`**
- [ ] **Step 5: Run desktop unit and component test suite**
  Run: `npm --prefix apps/desktop test`
  Expected: PASS 100%.

---

### Task 3: Security Probes, Playwright E2E Verification & Independent Subagent Audit

**Files:**
- Output proof: `docs/proofs/sprint7/s7-02-comparative-rag.png`
- Audit report in PR description

- [ ] **Step 1: Live Security Probes**
  Probe `POST /api/v1/query/comparative` with path traversal payloads.
- [ ] **Step 2: Launch Dev Server & Run Playwright MCP E2E Test**
  - Launch core daemon & desktop dev server.
  - Select 2 documents (`VNM_2022` and `VNM_2023`).
  - Submit comparative query: "So sánh cơ cấu doanh thu và số dư tiền giữa 2 năm".
  - Verify YoY metric card rendering, evidence badges, and 0 console errors.
  - Capture screenshot to `docs/proofs/sprint7/s7-02-comparative-rag.png`.
- [ ] **Step 3: Dispatch Independent Subagent Audit (Rules 13A & 14)**
  - Require formal `VERDICT: APPROVED 🟢`.
- [ ] **Step 4: Open Pull Request targeting `dev` with merge commit, verify GitHub Actions CI**
