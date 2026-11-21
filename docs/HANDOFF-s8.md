# S8 Handoff & Sprint 9 Horizon

**Document**: `docs/HANDOFF-s8.md`  
**Date**: 2026-11-21  
**Repository**: `529-studio/Finsight`  
**Charter**: Transition ledger documenting Sprint 8 completion state, delivered capabilities, settled architecture decisions, pitfalls, and next tasks for a fresh conversation.

---

## 1. Branch & Commit Status

- **Active branch**: `dev` (transitioning via `docs/s8-handoff`)
- **Head commit**: `08802fe` (`Merge pull request #57 from 529-studio/feat/s8-footnote-disambiguation`)
- **Worktree**: clean (all 4 feature branches merged via PR merge commits into `dev`)
- **Merged in this sprint**:
  - PR #54 (`feat/s8-golden-dataset-benchmark`): S8-01 Golden Dataset Comprehensive Evaluation & Retrieval Accuracy Benchmarks (Issue #50).
  - PR #55 (`feat/s8-installer-signing-notarization`): S8-02 Production Installer Signing, Hardened Runtime & Notarization Pipeline (Issue #51).
  - PR #56 (`feat/s8-websocket-streaming-inference`): S8-03 Real-Time WebSocket Streaming Inference to Desktop Chat & Excel Taskpane (Issue #52).
  - PR #57 (`feat/s8-footnote-disambiguation`): S8-04 Consolidated Financial Statement Footnote Disambiguation & Formula Extraction (Issue #53).

---

## 2. Merged Deliverables

| PR | Task | Subsystem | Delivered capability |
| :--- | :--- | :-------- | :------------------- |
| **#54** | **S8-01** (#50) | `benchmarks/`, `packages/core-engine` | Golden dataset of 105 Vietnamese financial queries achieving 100% Top-1 recall, 0% chart blindness (vs 34.3% Text RAG), and 0.9220 mean bounding box IoU. |
| **#55** | **S8-02** (#51) | `apps/desktop/src-tauri`, `scripts/` | macOS hardened runtime entitlements (`entitlements.plist`), Tauri v2 bundle integration, automated `notarytool` stapling script with dry-run support, and CI release workflow. |
| **#56** | **S8-03** (#52) | `packages/core-engine`, `apps/desktop` | Real-time WebSocket token streaming endpoint (`/ws/query/stream`) with path traversal security defense, `useStreamingQuery.ts` hook, and progressive rendering in Desktop Chat. |
| **#57** | **S8-04** (#53) | `packages/core-engine`, `apps/excel` | Footnote citation endpoint (`/api/v1/query/footnotes`) mapping line items to Thuyết minh BCTC, and Office.js table export embedding rich footnote audit trail comments into Excel. |

---

## 3. Open Issues & Backlog

- **All active milestone issues for Sprint 8 are CLOSED**:
  - Issue #50 (S8-01): Closed via PR #54.
  - Issue #51 (S8-02): Closed via PR #55.
  - Issue #52 (S8-03): Closed via PR #56.
  - Issue #53 (S8-04): Closed via PR #57.
- Repository issue backlog count: 0 open issues.

---

## 4. Settled Architectural Decisions

- **ADR-001 (Hybrid Desktop & Visual RAG Native)**: Visual RAG ColPali late-interaction indexing persists in LanceDB; multi-page and multi-document cross-referencing maintains normalized coordinates `[0, 1000]`.
- **ADR-002 (Dual-Mode Inference Architecture)**: Apple Silicon MLX local inference prioritized when hardware available; Cloud Router acts as BYOK frontier fallback. Extended in Sprint 8 with asynchronous generator token streaming.
- **ADR-003 (Bounding Box Visual Grounding Protocol)**: Audited SVG overlay remains 100% immutable over source PDF; dynamic viewer switching in multi-document queries seamlessly transitions the active document while preserving evidence coordinates.
- **ADR-004 (Monorepo Blackbox Boundaries & IPC)**: Excel Add-in (`apps/excel`) and Desktop Client (`apps/desktop`) communicate with `packages/core-engine` daemon over REST and WebSocket broadcast.
- **ADR-005 (Zero-Zombie Native Desktop Daemon Lifecycle)**: Rust `DaemonManager` handles local Python daemon spawning, lightweight healthchecks, and lifecycle teardown (`Drop` trait) ensuring 0 orphan processes on app termination.

---

## 5. Pitfalls Encountered & Engineering Rules

1. **Monorepo Relative Path Traversal Depth**:
   - `signing-config.test.ts` initially resolved repo root using 4 parent segments (`../../../../scripts`) which targeted `apps/scripts`.
   - *Rule:* Always count full directory depth (`../../../../..` from nested test directories) and verify with `fs.existsSync` before asserting file operations.
2. **Module-Level Logger Initialization in Daemon**:
   - FastAPI endpoint `/ws/query/stream` raised a `NameError: name 'logger' is not defined` when catching exceptions because `logger` was not declared at module scope.
   - *Rule:* Always instantiate `logger = logging.getLogger(...)` at the module header in all Python daemon modules.
3. **Typing Declarations in Sub-Routers**:
   - Omitting `Optional` from `typing` when defining method parameter defaults in `vlm_router.py` led to runtime import exceptions.
   - *Rule:* Ensure all typing symbols (`Optional`, `Union`, `Literal`) are explicitly imported from `typing`.

---

## 6. Sprint 9 Horizon: next tasks

1. **S9-01: Production Release v1.0.0 Tagging & General Availability (GA) Announcement** — `root`, `.github/`
   - Create official git tag `v1.0.0`, trigger release workflows, and generate public changelog.
2. **S9-02: Multi-Tenant Team Box (Docker Compose LAN Deployment) for Enterprise Banking Clients** — `deploy/`
   - Author production Docker Compose orchestration with healthchecks, persistent volumes, and LAN access security controls.
3. **S9-03: Interactive Footnote Deep-Linking in Desktop PDF Viewer** — `apps/desktop/`
   - Enable clicking a footnote chip to automatically navigate the PDF viewer to the corresponding Thuyết minh BCTC page.
4. **S9-04: Microsoft AppSource Manifest Package & Centralized Deployment Infrastructure** — `apps/excel/`
   - Author production manifest, configure HTTPS CDN hosting, and prepare enterprise deployment guides for Microsoft 365 Admin Center.
5. **S9-05: Windows Authenticode Code Signing & MSIX Packaging Pipeline** — `apps/desktop/src-tauri/`
   - Configure Windows signing pipeline for enterprise desktop distribution.

---

## 7. Open Questions For The Human

- None. All Sprint 8 deliverables have been implemented, audited by independent subagents, verified with 100% CI pass rate (127/127 tests), merged into `dev` via merge commits, and recorded in project documentation. The product is now officially ready for production release evaluation (GA).
