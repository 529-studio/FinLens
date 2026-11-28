# S14 Handoff & Sprint 15 Horizon

**Document**: `docs/HANDOFF-s14.md`  
**Date**: 2026-11-28  
**Repository**: `529-studio/FinTrace`  
**Charter**: Transition ledger documenting Sprint 14 completion state, delivered capabilities, settled architecture decisions, pitfalls, and next tasks for a fresh conversation.

---

## 1. Branch & Commit Status

- **Active branch**: `dev` (transitioning via `docs/s14-handoff`)
- **Head commit**: `c43dbc6` (`Merge pull request #132 from 529-studio/feat/s14-04-multiworker-audit-cache`)
- **Worktree**: clean (all 4 Sprint 14 feature branches merged via PR merge commits into `dev`; `docs/real_pdfs/` ignored via `.gitignore`)
- **Merged in this sprint**:
  - PR #129 (`feat/s14-01-colpali-lancedb-retriever`, Issue #125): ColPali 8x8 multi-vector patch embedding, MaxSim late-interaction scoring, LanceDB `document_patches` table, and epoch-guarded cache invalidation.
  - PR #130 (`feat/s14-02-async-mlx-offload`, Issue #126): Dedicated 1-worker `ThreadPoolExecutor` offload for synchronous `MLXEngine` inference in `VlmRouter` + warm-cache ANN skip in `retriever.py`.
  - PR #131 (`feat/s14-03-hardware-aesgcm`, Issue #127): Hardware-accelerated NIST SP 800-38D `AESGCM` encryption at rest in `workspace_security.py`.
  - PR #132 (`feat/s14-04-multiworker-audit-cache`, Issue #128): Multi-worker `fcntl.flock` + SQLite WAL backends for `AuditLogger` and `QueryLRUCache` + idempotent `VisualRetriever.index_document` skip.

---

## 2. Merged Deliverables

| PR | Task | Subsystem | Delivered capability |
| :--- | :--- | :-------- | :------------------- |
| **#129** | **S14-01** (#125) | `core-engine` | `ColPaliPatchEmbedder` (64 spatial patches/page, 128-dim) & MaxSim (`retriever.py`), `document_patches` table & `_cache_epoch` (`store.py`), `.gitignore` rule for `docs/real_pdfs/`. |
| **#130** | **S14-02** (#126) | `core-engine` | `VlmRouter._run_mlx_offloaded` (`ThreadPoolExecutor(max_workers=1)`) serializing Metal inference off the asyncio loop + warm `<=100`p cache fast path in `retriever.py`. |
| **#131** | **S14-03** (#127) | `core-engine` | `cryptography` `AESGCM` (256-bit key, 96-bit nonce, 128-bit tag, AAD, `InvalidTag` tamper rejection) in `workspace_security.py`. |
| **#132** | **S14-04** (#128) | `core-engine` | Cross-process `fcntl.flock` + SQLite WAL `BEGIN IMMEDIATE` in `AuditLogger`, shared SQLite WAL `QueryLRUCache`, and signature-based idempotent skip in `VisualRetriever.index_document`. |

---

## 3. Open Issues & Backlog

- **All Sprint 14 milestone issues are CLOSED**:
  - Issue #125 (`S14-01`): Closed via PR #129.
  - Issue #126 (`S14-02`): Closed via PR #130.
  - Issue #127 (`S14-03`): Closed via PR #131.
  - Issue #128 (`S14-04`): Closed via PR #132.
- Repository issue backlog count: **0 open issues**.

---

## 4. Settled Architectural Decisions

- **ADR-001 through ADR-010**: All prior ADRs remain in full effect.
- **Epoch-Guarded Multi-Vector LanceDB Cache (S14-01)**: `LanceDBStore._cache_epoch` increments on every mutation/clear (`upsert_pages`, `upsert_page_patches`, `delete_document`, `clear_memory_cache`), and `VisualRetriever._np_patch_cache` validates the epoch on read to prevent stale matrix hits.
- **Single-Worker Metal Inference Serialization (S14-02)**: `VlmRouter` uses a 1-worker `ThreadPoolExecutor` so Apple Silicon Metal memory stays bounded under the 6GB ceiling while FastAPI `/health` and WebSocket loops remain non-blocking.
- **Standard AES-256-GCM at Rest (S14-03)**: Custom HMAC-CTR stream cipher removed in favor of `cryptography.hazmat.primitives.ciphers.aead.AESGCM`.
- **SQLite WAL Multi-Worker Coordination (S14-04)**: `AuditLogger` and `QueryLRUCache` support `sqlite` WAL mode with `BEGIN IMMEDIATE` + bounded retry on `OperationalError` (`"locked"`), while preserving `jsonl` (with `fcntl.flock`) and `memory` defaults.

---

## 5. Pitfalls Encountered

- **Redundant LanceDB ANN Scans on Warm Small-Doc Cache**: Running `store.search` + `store.search_patches` on every query for `<= 100`-page documents pushed `ubuntu-latest` CI average latency to `10.55 ms` (tripping the `> 10.0 ms` regression gate in `test_benchmark_regression.py`). Skipping the disk ANN scan when `_np_patch_cache` is already epoch-valid keeps latency `< 4 ms`.
- **Concurrent `PRAGMA journal_mode=WAL` Race**: Spawning multiple OS worker processes simultaneously against an uninitialized SQLite file caused `sqlite3.OperationalError: database is locked` on `ubuntu-latest`. Moving `PRAGMA journal_mode=WAL` into `_init_sqlite()` with bounded retry and pre-initializing the DB before spawning workers resolved it.
- **Idempotent Re-Ingest Latency**: Re-ingesting a cached 2-page PDF exceeded `100 ms` on `ubuntu-latest` when `VisualRetriever.index_document` re-embedded and re-wrote `document_patches`. Matching `(page_number, signature)` pairs against `store.get_pages()` skips redundant LanceDB writes.

---

## 6. Sprint 15 Horizon: next tasks

1. `S15-01: Live ColPali Neural Weights Integration & E2E Quantization Benchmark` — wire `ColPaliPatchEmbedder._neural_model` inference path in `packages/core-engine/src/retriever.py` when `mlx-community/ColPali-v1.2-4bit` is cached.
2. `S15-02: Redis Shared Adapter for AuditLogger & QueryLRUCache` — add optional `redis` backend in `packages/core-engine/src/cache_manager.py` and `packages/core-engine/src/audit_logger.py` for multi-node LAN/cluster deployments.
3. `S15-03: Real-PDF Benchmark Suite & Regression Baseline Update` — add a reproducible public-domain PDF benchmark runner in `benchmarks/` using `ColPaliPatchEmbedder`.
4. `S15-04: Desktop & Excel E2E Integration for Multi-Worker Core Daemon` — validate `apps/desktop` and `apps/excel` against `uvicorn --workers 2` with `FINTRACE_SHARED_BACKEND=sqlite` and capture Playwright proofs.
5. `S15-05: Workspace Key Rotation & Audit Re-Encryption CLI` — add key rotation support in `packages/core-engine/src/workspace_security.py` using `AESGCM`.

---

## 7. Open Questions For The Human

- **Sprint 15 Focus**: Should Sprint 15 prioritize distributed `redis` cluster scaling (`S15-02`) + multi-worker Desktop/Excel E2E (`S15-04`), or live neural ColPali weight inference (`S15-01`) + key rotation (`S15-05`)?
