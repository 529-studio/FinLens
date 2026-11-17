# S3-03: LanceDB Persistent Multi-Vector Store Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement persistent disk-backed storage using LanceDB at `~/.finsight/lancedb` for indexing, searching, and managing ColPali multi-vector page tensors and document visual metadata.

**Architecture:** `LanceDBStore` acts as the persistent database layer for the Visual RAG engine. It persists page image paths, dimensions, cryptographic hashes, layout tokens, and multi-dimensional vector embeddings into local Lance tables (`document_pages`). It replaces the volatile in-memory dictionary in `VisualRetriever`, exposes document listing and deletion capabilities, and provides disk metrics for enterprise audits.

**Tech Stack:** Python 3.12, LanceDB (`lancedb`), PyArrow (`pyarrow`), NumPy, FastAPI, Pydantic v2.

**Spec:** PRD §2, ADR-001, S2 Handoff §6 Task 3, AGENTS.md (Rules 1, 11, 12, 13, 15).

## Global Constraints

- Default database directory: `~/.finsight/lancedb` (configurable via `FINSIGHT_LANCEDB_DIR`).
- Strict Path Traversal Defense: database path and document IDs must validate against `is_path_safe` / `ALLOWED_ROOTS` and alphanumeric sanitization.
- Support schema with: `doc_id` (str), `page_number` (int), `image_path` (str), `width` (int), `height` (int), `signature` (str), `vector` (list of float), `metadata` (str), `indexed_at` (float).
- Multi-vector search: return top-k matching candidate pages with similarity scores.
- Zero raw emojis in code, responses, logs, or comments (Rule 15).
- Resilient fallback: graceful operation in mock / test environments.

## Review Focus

1. **Path Traversal in DB Path & Document IDs:** Ensure directory breakout attempts (`../../etc/passwd` or `doc/../../breakout`) are blocked immediately with `StoreSecurityError`.
2. **Persistence Across Process Restarts:** Verify that pages indexed in one session remain queryable and discoverable after re-instantiating `LanceDBStore`.
3. **Idempotent Upsert:** Re-indexing an existing document must update or replace existing records rather than producing duplicate pages.
4. **Document Deletion:** `delete_document(doc_id)` must cleanly remove all page vectors and metadata for that document without corrupting neighboring files.
5. **Storage Metrics Accuracy:** `get_stats()` must accurately reflect page counts, document counts, and disk size in bytes.

---

### Task 1: LanceDB Storage Engine Core (`store.py`)

**Files:**
- Create: `packages/core-engine/src/store.py`
- Test: `packages/core-engine/tests/test_store.py`

**Interfaces:**
- Produces:
  - `class LanceDBStore`
    - `connect() -> None`
    - `upsert_pages(doc_id: str, pages: List[Dict[str, Any]]) -> int`
    - `get_pages(doc_id: str) -> List[Dict[str, Any]]`
    - `search(doc_id: str, query_vector: List[float], top_k: int = 2) -> List[Dict[str, Any]]`
    - `delete_document(doc_id: str) -> bool`
    - `list_documents() -> List[str]`
    - `get_stats() -> Dict[str, Any]`

- [ ] **Step 1: Write failing tests for `LanceDBStore`**
  Cover initialization, path traversal defense, page upsert, vector similarity search, persistence, and deletion.

- [ ] **Step 2: Run test to verify it fails**
  Run: `packages/core-engine/.venv/bin/pytest packages/core-engine/tests/test_store.py -v`
  Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `LanceDBStore` in `packages/core-engine/src/store.py`**
  Connect to LanceDB, create `document_pages` table with PyArrow schema, implement vector search with metadata filtering, document listing, and deletion.

- [ ] **Step 4: Run test to verify it passes**
  Run: `packages/core-engine/.venv/bin/pytest packages/core-engine/tests/test_store.py -v`
  Expected: PASS

- [ ] **Step 5: Commit**
  ```bash
  git add packages/core-engine/src/store.py packages/core-engine/tests/test_store.py
  git commit -m "feat(core-engine): implement persistent LanceDB multi-vector store"
  ```

---

### Task 2: Wire `LanceDBStore` into `VisualRetriever` and Daemon API

**Files:**
- Modify: `packages/core-engine/src/retriever.py`
- Modify: `packages/core-engine/src/contracts.py`
- Modify: `packages/core-engine/src/main.py`
- Test: `packages/core-engine/tests/test_api_and_security.py`

**Interfaces:**
- Consumes: `LanceDBStore` from `store.py`.
- Produces:
  - `VisualRetriever(store: Optional[LanceDBStore] = None)`
  - `GET /api/v1/store/stats` -> returns store disk metrics and counts.
  - `GET /api/v1/documents` -> returns list of all indexed documents and page counts.
  - `DELETE /api/v1/documents/{doc_id}` -> deletes document from vector store.

- [ ] **Step 1: Write integration tests in `test_api_and_security.py`**
  Test store stats endpoint, document listing, and document deletion.

- [ ] **Step 2: Run test to verify it fails**
  Run: `packages/core-engine/.venv/bin/pytest packages/core-engine/tests/test_api_and_security.py -k "store or documents" -v`
  Expected: FAIL with 404 Not Found.

- [ ] **Step 3: Update `retriever.py`, `contracts.py`, and `main.py`**
  Wire `LanceDBStore` into `VisualRetriever`, add contracts for store stats and document lists, expose FastAPI routes.

- [ ] **Step 4: Run test to verify it passes**
  Run: `packages/core-engine/.venv/bin/pytest packages/core-engine/tests -v`
  Expected: All 35+ tests PASS.

- [ ] **Step 5: Commit**
  ```bash
  git add packages/core-engine/src/ packages/core-engine/tests/
  git commit -m "feat(core-engine): connect VisualRetriever to LanceDB and expose document management APIs"
  ```

---

### Task 3: Empirical Verification, Independent Subagent Audit & PR

**Files:**
- Documentation: `docs/lesson_learn.md`

- [ ] **Step 1: Live cURL verification of LanceDB store endpoints**
  Launch daemon, verify `GET /api/v1/store/stats`, `GET /api/v1/documents`, and verify persistent files on disk in `~/.finsight/lancedb`.

- [ ] **Step 2: Record post-mortem and lessons learned in `docs/lesson_learn.md`**
  Document LanceDB PyArrow table schemas, partition filtering, and persistent vector storage patterns.

- [ ] **Step 3: Push branch and open Pull Request against `dev`**
  Push `feat/s3-lancedb-store` and create PR via `gh pr create`.

- [ ] **Step 4: Dispatch independent subagent audit (Rule 13 / 14)**
  Audit PR diff against security, memory, and persistence standards.

- [ ] **Step 5: Merge PR with merge commit (`gh pr merge --merge`)**
  Merge the PR cleanly into `dev`.
