# S12 Handoff & Sprint 13 Horizon

**Document**: `docs/HANDOFF-s12.md`  
**Date**: 2026-11-25  
**Repository**: `529-studio/FinTrace`  
**Charter**: Transition ledger documenting Sprint 12 completion state, delivered capabilities, settled architecture decisions, pitfalls, and next tasks for a fresh conversation.

---

## 1. Branch & Commit Status

- **Active branch**: `dev` (transitioning via `docs/s12-handoff`)
- **Head commit**: `590f18e` (`Merge pull request #106 from 529-studio/feat/s12-05-excel-audited-cell-drawer`)
- **Worktree**: clean (all 5 feature branches merged via PR merge commits into `dev`)
- **Merged in this sprint**:
  - PR #98 (`feat/s12-01-discrepancy-detector`): Multi-Document Anomaly & Discrepancy Detection Engine (Issue #97).
  - PR #100 (`feat/s12-02-audit-package-generator`): Automated Audit Trail Exporter & Regulatory Package Generator (Issue #99).
  - PR #102 (`feat/s12-03-pdf-annotation-canvas`): Desktop Native PDF Highlight Annotation Layer & Visual Comment Pinning (Issue #101).
  - PR #104 (`feat/s12-04-workspace-isolation`): Multi-Tenant Enterprise Workspace Isolation & Cryptographic Data Encryption at Rest (Issue #103).
  - PR #106 (`feat/s12-05-excel-audited-cell-drawer`): Excel Add-in Live Linked Footnote Citation Drawer & In-Sheet Audited Cell Tags (Issue #105).

---

## 2. Merged Deliverables

| PR | Task | Subsystem | Delivered capability |
| :--- | :--- | :-------- | :------------------- |
| **#98** | **S12-01** (#97) | `core-engine` | Multi-document anomaly & discrepancy engine (`discrepancy_detector.py`), absolute/relative variance calculation, anomaly categorization (`RESTATEMENT`, `UNEXPECTED_SIGN_FLIP`, `MATERIAL_VARIANCE`, `UNEXPLAINED_DRIFT`), severity thresholding, and `POST /api/v1/audit/discrepancies` endpoint with dual-document bounding box preservation (`[0, 1000]`). |
| **#100** | **S12-02** (#99) | `core-engine` | Regulatory compliance packager (`audit_packager.py`), Inline XBRL (iXBRL) generator with financial taxonomy tags, PDF/A-3 ISO 19005-3 container, cryptographic SHA-256 tamper-evident event chaining per ADR-007, BUNDLE ZIP assembly, and `POST /api/v1/audit/export-package` endpoint. |
| **#102** | **S12-03** (#101) | `apps/desktop` | Interactive native PDF annotation layer (`AnnotationCanvas.tsx`), drag-to-select spatial bounding box creation clamped to `[0, 1000]` coordinates per ADR-003, visual comment pinning popover, 3 resilient UI states, touch targets $\ge 48\text{px}$, and Rule 15 zero-emoji compliance. Verified live via Playwright MCP in `docs/proofs/sprint12/desktop_annotation_canvas.png`. |
| **#104** | **S12-04** (#103) | `core-engine` | Multi-tenant cryptographic workspace sandboxing (`workspace_security.py`), PBKDF2-HMAC-SHA256 tenant key derivation, AES-256-GCM authenticated encryption at rest, POSIX `0o700`/`0o600` access restrictions, cross-tenant isolation enforcement (`403 Forbidden`), and REST endpoints under `/api/v1/workspaces/`. |
| **#106** | **S12-05** (#105) | `apps/excel` | Live linked footnote citation drawer (`AuditedCellDrawer.tsx`), footnote code and section title display (`VI.24`), verification status badges, confidence scoring, `Xem tài liệu nguồn` desktop bridge trigger, `Gắn ghi chú kiểm toán` cell comment insertion, 3 UI states, kiosk touch targets $\ge 48\text{px}$, and Rule 15 compliance. |

---

## 3. Open Issues & Backlog

- **All active milestone issues for Sprint 12 are CLOSED**:
  - Issue #97 (S12-01): Closed via PR #98.
  - Issue #99 (S12-02): Closed via PR #100.
  - Issue #101 (S12-03): Closed via PR #102.
  - Issue #103 (S12-04): Closed via PR #104.
  - Issue #105 (S12-05): Closed via PR #106.
- Repository issue backlog count: 0 open issues.

---

## 4. Settled Architectural Decisions

- **ADR-001 (Hybrid Desktop & Visual RAG Native)**: Visual RAG ColPali late-interaction indexing in LanceDB; multi-document cross-referencing maintains normalized coordinates `[0, 1000]`.
- **ADR-002 (Dual-Mode Inference Architecture & Streaming)**: Apple Silicon MLX local inference prioritized; Cloud Router fallback; real-time WebSocket token streaming with bounding box emission.
- **ADR-003 (Bounding Box Visual Grounding Protocol)**: Audited SVG overlay remains 100% immutable over source PDF; multi-page stitched tables preserve origin page and coordinates.
- **ADR-004 (Monorepo Blackbox Boundaries & IPC)**: Desktop Client (`apps/desktop`) and Excel Add-in (`apps/excel`) communicate with `packages/core-engine` daemon over REST and WebSocket broadcast.
- **ADR-005 (Production Packaging, Notarization & Authenticode Signing)**: Dual-platform distribution pipeline supporting macOS Hardened Runtime (`notarytool` stapling) and Windows Authenticode.
- **ADR-006 (Enterprise On-Premises Docker LAN Box Architecture)**: Air-gapped multi-tenant deployment for enterprise banking accounting departments running on internal isolated networks.
- **ADR-007 (Enterprise RBAC, Cryptographic Audit Chaining & AST Formula Engine)**: Tamper-evident SHA-256 event chaining for audit trails, pure Python JWT authentication, and zero-eval recursive descent AST formula evaluation.
- **ADR-008 (Air-Gapped Ed25519 License Verification & Salted Hardware Fingerprinting)**: Offline license cryptographic validation using asymmetric Ed25519 signatures, irreversible SHA-256 salted hardware hashing, and atomic file replacement with `0o600` access controls.
- **ADR-009 (Multi-Tenant Workspace Isolation & Cryptographic Encryption at Rest)**: Per-tenant isolated filesystem trees (`~/.finsight/workspaces/{tenant_id}/{workspace_id}/`), PBKDF2-HMAC-SHA256 key derivation (100k rounds), AES-256-GCM encryption with random 12-byte IV and 16-byte tag, POSIX `0o700`/`0o600` permissions.
- **ADR-010 (Regulatory Packaging & Long-Term Preservation Standards)**: ISO 19005-3 PDF/A-3 container embedding machine-readable metadata, Inline XBRL (iXBRL) with GAAP/VAS taxonomy namespaces, and blockchain-style sequential SHA-256 hash chaining.

---

## 5. Pitfalls Encountered

- **Async Runner Marker Incompatibility (`anyio` vs `pytest-asyncio`)**: In Ubuntu CI environments where `anyio` is the active async test plugin, using `@pytest.mark.asyncio` triggers unhandled collection errors. Always decorate asynchronous test functions with `@pytest.mark.anyio` for cross-environment compatibility.
- **Python 3.12 Binary String Literal Prefix**: Syntax `bf"..."` is invalid in Python 3.12. Refactor raw binary assemblies by declaring explicit byte literals `b"..."` and joining them with `b"".join(...)`.
- **TypeScript Strict `noUnusedLocals` in CI Build Step**: While Vitest ignores unused variables during test compilation, the production build step `npm run build` (`tsc && vite build`) strictly fails if any imported variable is unused. Always run `npm run build` locally before pushing frontend commits.
- **Coordinate Normalization Clamping Invariants**: Mouse dragging outside canvas boundaries can generate negative coordinates or dimensions exceeding container bounds. Always apply `Math.max(0, Math.min(1000, Math.round(...)))` and enforce $x_{\min} < x_{\max}$ to preserve visual grounding integrity.

---

## 6. Sprint 13 Horizon: next tasks

1. `S13-01: Cross-Sectional Industry Peer Benchmarking Engine & Sector Percentile Scoring` — `packages/core-engine/src/peer_benchmark.py`
2. `S13-02: Advanced Cash Flow Statement Direct-to-Indirect Reconciliation Engine` — `packages/core-engine/src/cashflow_reconciler.py`
3. `S13-03: Desktop Multi-Document Tabbed Split-Screen & Synchronized Page Scrolling` — `apps/desktop/src/components/pdf/TabbedSplitViewer.tsx`
4. `S13-04: Enterprise Role-Based Access Control (RBAC) Hierarchical Permission Engine & Audit Policy Enforcement` — `packages/core-engine/src/rbac_policy.py`
5. `S13-05: Excel Add-in Live Formula Dependency Visualizer & Sensitivity Tornado Chart` — `apps/excel/src/components/TornadoChart.tsx`

---

## 7. Open Questions For The Human

- **Sector Percentile Weighting**: For Sprint 13 Task S13-01, should the cross-sectional industry peer benchmarking engine compute percentiles across equal-weighted metrics or market-cap weighted industry averages?
