# S7 Handoff & Sprint 8 Horizon

**Document**: `docs/HANDOFF-s7.md`  
**Date**: 2026-11-21  
**Repository**: `529-studio/Finsight`  
**Charter**: Transition ledger documenting Sprint 7 completion state, delivered capabilities, settled architecture decisions, pitfalls, and next tasks for a fresh conversation.

---

## 1. Branch & Commit Status

- **Active branch**: `dev`
- **Head commit**: `8fcffc5` (`Merge pull request #48 from 529-studio/feat/s7-excel-table-export`)
- **Worktree**: clean (all 4 feature branches merged via PR merge commits into `dev`)
- **Merged in this sprint**:
  - PR #42 (`feat/s7-office-ingest`): S7-01 Office.js 1-Click Financial Statement Ingestion & Direct Local Bridge (Issue #41).
  - PR #46 (`feat/s7-comparative-rag`): S7-02 Multi-Document Comparative Visual RAG Across Multiple Fiscal Years (Issue #43).
  - PR #47 (`feat/s7-tauri-daemon-lifecycle`): S7-03 Native Desktop Packaging (Tauri v2 Bundle Generation) & Daemon Lifecycle Management (Issue #44).
  - PR #48 (`feat/s7-excel-table-export`): S7-04 1-Click Financial Table Export to Excel Sheet & Monorepo Cleanup (Issue #45, #11, #12).

---

## 2. Merged Deliverables

| PR | Task | Subsystem | Delivered capability |
| :--- | :--- | :-------- | :------------------- |
| **#42** | **S7-01** (#41) | `apps/excel`, `packages/core-engine` | Office.js Taskpane base64 ingestion (`/api/v1/documents/ingest-base64`) with 50MB file size checks, SHA256 integrity, drag-and-drop UI, full 3 UI states, and Kiosk touch ergonomics ($\ge 48\text{px}$). |
| **#46** | **S7-02** (#43) | `packages/core-engine`, `apps/desktop` | Multi-Document Comparative Visual RAG (`/api/v1/query/compare`), multi-doc selection in Desktop `SplitView.component.tsx`, cross-document evidence chips with document badges, and dynamic viewer switching. |
| **#47** | **S7-03** (#44) | `apps/desktop/src-tauri`, `apps/desktop` | Standalone native macOS desktop bundle (`FinSight.app` 10.4MB, `FinSight_0.1.0_aarch64.dmg` 3.67MB), Rust `DaemonManager` with automatic SIGTERM/SIGKILL lifecycle cleanup (zero zombie processes), and React `useDaemonLifecycle` polling hook. |
| **#48** | **S7-04** (#45, #11, #12) | `apps/excel`, root monorepo | Office.js `insertFinancialTableToSheet` with automated `=SUM(...)` total rows, audit trail cell comments, 1-Click UI export button, deletion of obsolete `packages/office-addin`, and automated vitest test suite. |

---

## 3. Open Issues & Backlog

- **All active milestone issues for Sprint 7 are CLOSED**:
  - Issue #41 (S7-01): Closed via PR #42.
  - Issue #43 (S7-02): Closed via PR #46.
  - Issue #44 (S7-03): Closed via PR #47.
  - Issue #45 (S7-04): Closed via PR #48.
  - Issue #11 (S4-01): Closed via PR #48.
  - Issue #12 (S4-03): Closed via PR #48.
- Repository issue backlog count: 0 open issues.

---

## 4. Settled Architectural Decisions

- **ADR-001 (Hybrid Desktop & Visual RAG Native)**: Visual RAG ColPali late-interaction indexing persists in LanceDB; multi-page and multi-document cross-referencing maintains normalized coordinates `[0, 1000]`.
- **ADR-002 (Dual-Mode Inference Architecture)**: Apple Silicon MLX local inference prioritized when hardware available; Cloud Router acts as BYOK frontier fallback. Extended in Sprint 7 with `analyze_comparative` multi-statement synthesis.
- **ADR-003 (Bounding Box Visual Grounding Protocol)**: Audited SVG overlay remains 100% immutable over source PDF; dynamic viewer switching in multi-document queries seamlessly transitions the active document while preserving evidence coordinates.
- **ADR-004 (Monorepo Blackbox Boundaries & IPC)**: Excel Add-in (`apps/excel`) and Desktop Client (`apps/desktop`) communicate with `packages/core-engine` daemon over REST and WebSocket broadcast. Legacy `packages/office-addin` removed.
- **ADR-005 (Zero-Zombie Native Desktop Daemon Lifecycle)**: Rust `DaemonManager` handles local Python daemon spawning, lightweight healthchecks, and lifecycle teardown (`Drop` trait) ensuring 0 orphan processes on app termination.

---

## 5. Pitfalls Encountered & Engineering Rules

1. **Comparative Inference Offline Fallback Alignment**:
   - `CloudRouter.analyze_comparative` failed in CI when invoking `_synthesize_offline_fallback` because the base class defined `_synthesize_fallback`.
   - *Rule:* Always maintain exact method name parity with parent router abstractions and alias legacy signatures to prevent subtle runtime exceptions during network outages.
2. **Office.js Comment Model Compatibility (Rule 15 & Sandbox Safety)**:
   - In Office.js type definitions, `Range.comments` is not a property; comments are managed workbook-wide via `context.workbook.comments.add(originCell, comment, 'Plain')`.
   - *Rule:* Always guard Office.js calls with `typeof Excel !== 'undefined'` fallbacks to ensure headless automated testing (Vitest/Playwright) executes without throwing reference errors.
3. **Tauri v2 Bundle Configuration Schema**:
   - Tauri v2 bundle configuration requires uppercase/camelcase `"macOS"` rather than lowercase `"macos"`.
   - *Rule:* Validate `tauri.conf.json` with `npm run tauri:build` or schema verification tools before committing build configurations.

---

## 6. Sprint 8 Horizon: next tasks

1. **S8-01: Golden Dataset Comprehensive Evaluation & Retrieval Accuracy Benchmarks** — `benchmarks/`, `packages/core-engine/`
   - Run automated evaluation benchmarks across 100+ Vietnamese audited financial statements (Vingroup, Masan, Vinamilk, FPT, Hoa Phat) measuring Top-1/Top-3 recall, chart blindness rate, and bounding box IoU accuracy.
2. **S8-02: End-to-End Production Installer Signing & Notarization** — `apps/desktop/src-tauri/`
   - Configure Apple Developer ID code signing and `notarytool` notarization for macOS `.dmg`/`.app` and prepare Windows Authenticode signing pipelines.
3. **S8-03: Real-Time WebSocket Streaming Inference to Taskpane & Desktop** — `packages/core-engine/src/`, `apps/desktop/`, `apps/excel/`
   - Implement token streaming over WebSocket from MLX Engine and Cloud Router, displaying progressive text generation in the Desktop chat and Excel Taskpane without blocking UI interaction.
4. **S8-04: Consolidated Financial Statement Footnote Disambiguation & Formula Extraction** — `packages/core-engine/src/`, `apps/excel/`
   - Enhance VLM prompt templates and OCR post-processing to automatically map balance sheet line items to corresponding footnote numbers (Thuyết minh BCTC) and generate linked Excel references.

---

## 7. Open Questions For The Human

- None. All Sprint 7 deliverables have been implemented, audited by an independent subagent (`cb8df475-63e3-45a6-8c6b-1e81e42abbce`), verified with 100% CI pass rate, merged into `dev` via merge commits, and recorded in project documentation. Sprint 8 is ready to launch in a fresh conversation.
