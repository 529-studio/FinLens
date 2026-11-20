# S7-01: Office.js 1-Click Financial Statement Ingestion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable financial analysts in Excel to upload and index BCTC PDF statements in 1 click directly from the Office.js Taskpane, synchronizing document state with the local FinSight Core Engine daemon.

**Architecture:** 
A multipart upload endpoint on the FastAPI Core Daemon (`/api/v1/documents/upload`) with strict filename sanitization, PDF magic-byte validation, and path traversal defense; paired with a resilient 4-file frontend architecture in `apps/excel` (`DTO` -> `fetch` -> `hook` -> `UI component`) satisfying the 3 mandatory UI states (Skeleton, Error, Empty), Kiosk ergonomics ($\ge 48\text{px}$ touch targets), and strict zero-emoji SVG policy.

**Tech Stack:** 
- Backend: FastAPI, Pydantic v2, PyMuPDF, LanceDB, Python `multipart`.
- Frontend: Office.js, React 19, Vite, TanStack Query v5, Lucide React, Tailwind CSS.
- Verification: Pytest, Playwright MCP, independent subagent audit.

**Spec:** Issue S7-01 (#41), `docs/HANDOFF-s6.md` (Section 6: Sprint 7 Horizon), `AGENTS.md` (Rules 1, 11, 12, 13, 14, 15), and `frontend-4file-and-resilient-ui` skill.

---

## Global Constraints

- **Git Flow (Rule 12):** Active branch must be created as `feat/s7-office-ingest` from `dev`. Merge commit required into `dev`.
- **4-File Pattern (Rule 1):** Follow `src/types/api.ts` -> `src/lib/api/finsight.ts` -> `src/lib/hooks/use-ingest.ts` -> `src/components/`. No inline `fetch()` inside React components.
- **3 UI States (Rule 1):** Every data view must explicitly render Skeleton (loading), Error (with retry), and Empty (actionable) states.
- **Kiosk Ergonomics (Rule 1):** All interactive targets (buttons, drop zones, retry buttons) must have a minimum clickable area of $48\text{px} \times 48\text{px}$ (`min-h-[48px]`).
- **Security & Path Traversal (Rule 13B):** Sanitized filenames (`^[a-zA-Z0-9_\-\.]+$`), validated `%PDF-` header magic bytes, strict write boundaries restricted to `~/.finsight/uploads/`. Prohibit all directory traversal attacks (`../../`).
- **Zero-Emoji Policy (Rule 15):** Absolutely zero raw Unicode emojis in user interface components, buttons, badges, or headers. Use Lucide React vector SVGs exclusively.
- **Independent Audit (Rule 13A & 14):** PR cannot be merged without sign-off from an independent subagent (`research` or `self`).

---

## Review Focus

1. **Path Traversal via Uploaded Filename:** Probing `../../etc/passwd` or `../../../tmp/malicious.pdf` in multipart upload must be rejected with HTTP 400 without touching unauthorized filesystem locations.
2. **Invalid / Corrupted File Upload:** Uploading non-PDF files (e.g. `.exe`, `.sh`, or spoofed text files) must fail magic-byte verification with HTTP 400.
3. **Office.js Web Sandbox Compatibility:** In web browser / Office iframe environments where native filesystem paths cannot be accessed, multipart file stream upload must succeed and return complete page and vector metadata.
4. **Resilient UI State Transitions:** Switching between Empty -> Uploading (Skeleton/Progress) -> Success (Document Card) -> Error (Network Failure with Retry) must never crash or leave hanging state.
5. **Memory and Cache Hygiene:** After successful document upload and indexing, any stale query cache for the document must be invalidated, and uploaded temporary handles properly closed.

---

### Task 1: Backend Secure Multipart Upload Endpoint (`packages/core-engine`)

**Files:**
- Modify: `packages/core-engine/src/main.py`
- Modify: `packages/core-engine/requirements.txt`
- Test: `packages/core-engine/tests/test_api_and_security.py`

**Interfaces:**
- Produces:
  - `POST /api/v1/documents/upload`
    - Request: `multipart/form-data` with `file: UploadFile`, `render_dpi: int = 150`, `document_id: Optional[str] = None`
    - Validation:
      - Validates filename against `^[a-zA-Z0-9_\-\.]+$`
      - Validates `%PDF-` header magic bytes
      - Writes strictly to `~/.finsight/uploads/{sanitized_filename}`
    - Processing:
      - Renders pages via `renderer.render_document()`
      - Indexes vectors via `retriever.index_document()`
      - Invalidates cache via `cache_manager.query_cache.invalidate_document()`
    - Response: `DocumentIngestResponse`

- [ ] **Step 1: Write failing tests for `POST /api/v1/documents/upload`**
  Add unit tests in `packages/core-engine/tests/test_api_and_security.py`:
  - `test_upload_valid_pdf_success`: Upload valid sample PDF via multipart/form-data -> assert 200 OK, `total_pages > 0`, `indexed_vectors_count > 0`.
  - `test_upload_traversal_filename_rejected`: Upload with filename `../../evil.pdf` -> assert 400 Bad Request.
  - `test_upload_non_pdf_rejected`: Upload plain text or non-PDF binary -> assert 400 Bad Request.
  - `test_upload_empty_file_rejected`: Upload 0-byte file -> assert 400 Bad Request.

- [ ] **Step 2: Run tests to verify they fail**
  Run: `packages/core-engine/.venv/bin/pytest packages/core-engine/tests/test_api_and_security.py -k "test_upload" -v`
  Expected: FAIL with HTTP 404 / 405 (endpoint does not exist yet).

- [ ] **Step 3: Implement `POST /api/v1/documents/upload` in `packages/core-engine/src/main.py`**
  - Add `python-multipart>=0.0.9` to `requirements.txt`.
  - Ensure `~/.finsight/uploads` directory exists.
  - Implement validation (filename sanitization, magic byte check, size check).
  - Pipe to renderer, retriever, and cache invalidator.

- [ ] **Step 4: Run tests to verify they pass**
  Run: `packages/core-engine/.venv/bin/pytest packages/core-engine/tests/test_api_and_security.py -k "test_upload" -v`
  Expected: PASS 100%.

- [ ] **Step 5: Run full backend regression suite**
  Run: `packages/core-engine/.venv/bin/pytest packages/core-engine/tests/ -v`
  Expected: All tests pass.

---

### Task 2: Frontend 4-File Pattern & Resilient UI in `apps/excel`

**Files:**
- Modify: `apps/excel/src/types/api.ts`
- Modify: `apps/excel/src/lib/api/finsight.ts`
- Create: `apps/excel/src/lib/hooks/use-ingest.ts`
- Create: `apps/excel/src/components/DocumentUploader.tsx`
- Modify: `apps/excel/src/components/Sidebar.tsx`

**Interfaces:**
- `types/api.ts`:
  - `DocumentIngestResponseDTO`
  - `DocumentSummaryDTO`
  - `ActiveDocumentState`
- `lib/api/finsight.ts`:
  - `uploadFinancialDocument(file: File, dpi?: number, docId?: string): Promise<DocumentIngestResponseDTO>`
  - `fetchDocumentList(): Promise<{ documents: string[]; total: number }>`
- `lib/hooks/use-ingest.ts`:
  - `useDocumentUpload()` mutation
  - `useDocumentList()` query
- `components/DocumentUploader.tsx`:
  - Drag-and-drop zone and hidden `<input type="file" accept="application/pdf" />` triggered by button
  - Touch target $\ge 48\text{px}$
  - Zero raw emojis (use `UploadCloud`, `FileText`, `CheckCircle2`, `AlertCircle`, `Loader2` from Lucide React)
- `components/Sidebar.tsx`:
  - Integrate uploader with 3 UI states:
    - Skeleton state during upload/rendering.
    - Error state with localized Vietnamese message and retry button.
    - Empty state when no document is loaded.
    - Success state showing ingested document card, page count, and query input trigger.

- [ ] **Step 1: Update DTO types in `apps/excel/src/types/api.ts`**
  Define `DocumentIngestResponseDTO` matching backend schema.

- [ ] **Step 2: Implement pure fetch functions in `apps/excel/src/lib/api/finsight.ts`**
  Implement `uploadFinancialDocument` using `fetch` with FormData, `User-Agent: FinSight-Excel-Addin/1.0`, 60-second timeout, and clear error translation.

- [ ] **Step 3: Implement TanStack Query hook in `apps/excel/src/lib/hooks/use-ingest.ts`**
  Implement `useDocumentUpload` with cache invalidation on success.

- [ ] **Step 4: Implement `DocumentUploader.tsx` and integrate into `Sidebar.tsx`**
  - Implement responsive drag-and-drop file picker.
  - Render 3 UI states cleanly.
  - Enforce $48\text{px}$ minimum height for buttons.
  - Verify zero raw emojis.

- [ ] **Step 5: Verify frontend build**
  Run: `npm run --prefix apps/excel build`
  Expected: Successful compilation with zero TypeScript errors.

---

### Task 3: Security Live Probes, Playwright E2E Verification & Independent Subagent Audit

**Files:**
- Output proof: `docs/proofs/sprint7/s7-01-excel-ingestion.png`
- Audit report in PR description

- [ ] **Step 1: Live Security Probes against Backend Daemon**
  Execute live curl probes testing:
  - Traversal attempt: `curl -F "file=@sample.pdf;filename=../../evil.pdf" http://localhost:8000/api/v1/documents/upload` -> must return 400 Bad Request.
  - Non-PDF attempt: `curl -F "file=@test.txt" http://localhost:8000/api/v1/documents/upload` -> must return 400 Bad Request.

- [ ] **Step 2: Launch Dev Servers & Execute Playwright MCP E2E Verification**
  - Launch backend daemon on port 8000 and Excel dev server on port 3000.
  - Use Playwright MCP to navigate to taskpane:
    - Inspect Empty State (Verify Upload button, description, 48px touch target).
    - Upload sample BCTC PDF (`VNM_BCTC_2023_AUDITED.pdf`).
    - Capture Skeleton/Loading state.
    - Verify Success state (Document ID, total pages, indexed vectors).
    - Verify 0 console errors and 0 failed network requests.
    - Save screenshot to `docs/proofs/sprint7/s7-01-excel-ingestion.png`.

- [ ] **Step 3: Dispatch Independent Subagent Audit (Rules 13A & 14)**
  - Dispatch external subagent (`research` or `self`) with role `Independent Codebase & UI/UX Quality Auditor`.
  - Evaluate functional correctness, security compliance, 4-file architecture, and zero raw emojis.
  - Obtain formal verdict: `VERDICT: APPROVED 🟢`.

- [ ] **Step 4: Create Pull Request targeting `dev` with merge commit**
