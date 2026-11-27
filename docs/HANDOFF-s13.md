# S13 Handoff & Sprint 14 Horizon

**Document**: `docs/HANDOFF-s13.md`  
**Date**: 2026-11-27  
**Repository**: `529-studio/FinTrace`  
**Charter**: Transition ledger documenting Sprint 13 completion state, delivered capabilities, settled architecture decisions, pitfalls, and next tasks for a fresh conversation.

---

## 1. Branch & Commit Status

- **Active branch**: `dev` (transitioning via `docs/s13-handoff`)
- **Head commit**: `aedc647` (`Merge pull request #123 from 529-studio/feat/s13-08-excel-tornado-chart`)
- **Worktree**: clean (all 8 Sprint 13 feature/fix branches merged via PR merge commits into `dev`)
- **Merged in this sprint**:
  - PR #116 (`feat/s13-01-pdf-viewer-rendering`): Real PDF page rendering, bounding box alignment, and bridge stability.
  - PR #117 (`feat/s13-02-doc-upload-switcher`): Desktop PDF upload, document switcher, comparative picker, and Excel indexed selector.
  - PR #118 (`fix/110-excel-production-bridge`): Excel local Tailwind build, responsive Waterfall SVG, formula baseline, and bridge/audit note.
  - PR #119 (`feat/s13-04-peer-benchmark`, Issue #111): Cross-sectional industry peer benchmarking engine.
  - PR #120 (`feat/s13-05-cashflow-reconciler`, Issue #112): Cash flow direct-to-indirect reconciliation engine.
  - PR #121 (`feat/s13-06-tabbed-split-viewer`, Issue #113): Desktop multi-document tabbed split-screen PDF viewer with sync page/scroll.
  - PR #122 (`feat/s13-07-rbac-policy`, Issue #114): Enterprise hierarchical RBAC policy engine & fail-closed PBKDF2 login hardening.
  - PR #123 (`feat/s13-08-excel-tornado-chart`, Issue #115): Excel Add-in live formula dependency visualizer & sensitivity tornado chart.

---

## 2. Merged Deliverables

| PR | Task | Subsystem | Delivered capability |
| :--- | :--- | :-------- | :------------------- |
| **#116** | **S13-01** | `fullstack` | Backend `/api/v1/documents/{doc_id}/pages/{page_number}` + `PdfViewer.tsx` real canvas rendering & `[0, 1000]` overlay alignment. |
| **#117** | **S13-02** | `fullstack` | `POST /api/v1/documents/upload`, `DocumentPickerModal`, comparative picker, and Excel indexed document selector. |
| **#118** | **S13-03** | `excel` | Local Tailwind v3 build pipeline for Excel taskpane, responsive Waterfall SVG, and bridge/audit note fixes. |
| **#119** | **S13-04** (#111) | `core-engine` | `PeerBenchmarkEngine` (`peer_benchmark.py`) with equal & market-cap weighting, `P10`–`P90` percentiles, z-scores, and `POST /api/v1/analysis/peer-benchmark`. |
| **#120** | **S13-05** (#112) | `core-engine` | `CashFlowReconciler` (`cashflow_reconciler.py`) reconciling Direct vs Indirect CFO with `-ΔAR`/`-ΔInv`/`+ΔAP` sign conventions, zero-denominator safety, and `POST /api/v1/analysis/cashflow-reconcile`. |
| **#121** | **S13-06** (#113) | `apps/desktop` | `TabbedSplitViewer.tsx` multi-tab dual-pane PDF viewer with `Đồng bộ trang` (page & scroll lock) integrated into `SplitView.component.tsx`. |
| **#122** | **S13-07** (#114) | `core-engine` | `HierarchicalRBACEngine` (`rbac_policy.py`), Deny-Takes-Precedence `fnmatch` policies, salted PBKDF2-HMAC-SHA256 login hardening, and `/api/v1/rbac/evaluate` + `/api/v1/rbac/policies`. |
| **#123** | **S13-08** (#115) | `apps/excel` | `computeTornadoSensitivity` (`formulaAuditor.ts`) + responsive `TornadoChart.tsx` SVG with live `Precedents / Dependents` dependency panel in `Sidebar.tsx`. |

---

## 3. Open Issues & Backlog

- **All active milestone issues for Sprint 13 are CLOSED**:
  - Issue #111 (S13-04): Closed via PR #119.
  - Issue #112 (S13-05): Closed via PR #120.
  - Issue #113 (S13-06): Closed via PR #121.
  - Issue #114 (S13-07): Closed via PR #122.
  - Issue #115 (S13-08): Closed via PR #123.
- Repository issue backlog count: **0 open issues**.

---

## 4. Settled Architectural Decisions

- **ADR-001 through ADR-010**: All prior ADRs remain in full effect (Visual RAG LanceDB, Dual-Mode MLX/LiteLLM, `[0, 1000]` Bounding Box Grounding, Monorepo IPC, Packaging/Signing, Docker LAN Box, Enterprise RBAC & AST Formula Engine, Ed25519 Licensing, Workspace AES-256-GCM Isolation, iXBRL/PDF-A-3).
- **Fail-Closed PBKDF2 Credential Store & Deny-Takes-Precedence RBAC (S13-07)**: `/api/v1/auth/login` verifies salted PBKDF2-HMAC-SHA256 hashes (100k rounds) in constant time (`hmac.compare_digest`), blocks privilege escalation (`403`), and evaluates `DENY` rules before `ALLOW` rules and hierarchical role inheritance.
- **Zero-Eval OAT Sensitivity & Tornado Visualization (S13-08)**: All sensitivity recalculations (`recalculateModel`, `computeTornadoSensitivity`) execute via deterministic recursive-descent `ExpressionParser` in topological order (`topologicalOrder`), never `eval()`.

---

## 5. Pitfalls Encountered

- **`buildDependencyGraph` Input Signature**: `buildDependencyGraph` in `apps/excel/src/lib/formulaAuditor.ts` expects `Record<string, { formula?: string; value?: number; label?: string }>` keyed by cell address (e.g. `{ B2: { value: 1000 } }`), NOT an array of cell objects. Passing an array causes `Object.entries` to index by `'0'`, `'1'`, silently yielding zero spread in `computeTornadoSensitivity`.
- **Testing-Library `getByText` Collisions in Multi-Pane Views**: Automatically activating `TabbedSplitViewer` in Comparative mode duplicated raw document ID strings (e.g. `VNM_2022_COMP`) in both the right-pane chips and left-pane tabs/toolbars, breaking `screen.getByText('VNM_2022_COMP')` in `ComparativeQuery.test.tsx`. Prefixing pane/tab labels (`PDF · ${id}`, `Tài liệu: ${id}`) keeps exact-match queries unambiguous.
- **Use `.venv/bin/pytest` Explicitly**: Always invoke `packages/core-engine/.venv/bin/pytest` rather than bare `pytest` to avoid environment/plugin mismatches.

---

## 6. Sprint 14 Horizon: next tasks

1. `S14-01: Neural ColPali Visual Patch Embedding & LanceDB Vector Search Integration` — replace keyword heuristics in `packages/core-engine/src/retriever.py` with real multi-vector patch scoring.
2. `S14-02: Non-Blocking Local MLX Inference Offload` — wrap synchronous `MLXEngine.analyze_pages` in `asyncio.to_thread` / dedicated 1-worker executor in `vlm_router.py` so `/health` and WebSocket sessions never stall during local inference.
3. `S14-03: Hardware-Accelerated AESGCM in Workspace Security` — migrate `workspace_security.py` `encrypt_data_at_rest` / `decrypt_data_at_rest` to `cryptography.hazmat.primitives.ciphers.aead.AESGCM`.
4. `S14-04: Multi-Worker Shared Audit & Cache Backend` — optional SQLite WAL / Redis adapter for `AuditLogger` and `QueryLRUCache` when scaling `uvicorn --workers > 1`.

---

## 7. Open Questions For The Human

- **Sprint 14 Focus**: Should Sprint 14 prioritize real neural ColPali embeddings (`S14-01`) + non-blocking MLX (`S14-02`), or production multi-worker hardening (`S14-03`, `S14-04`) first?
