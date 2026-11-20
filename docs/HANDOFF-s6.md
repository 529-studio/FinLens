# S6 Handoff & Sprint 7 Horizon

**Document**: `docs/HANDOFF-s6.md`  
**Date**: 2026-11-20  
**Repository**: `529-studio/Finsight`  
**Charter**: Transition ledger documenting Sprint 6 completion state, delivered capabilities, settled architecture decisions, pitfalls, and next tasks for a fresh conversation.

---

## 1. Branch & Commit Status

- **Active branch**: `dev`
- **Head commit**: `e5fa741` (`Merge pull request #39 from 529-studio/feat/s6-performance-optimization`)
- **Worktree**: clean (all feature branches merged via PR merge commits into `dev`)
- **Merged in this sprint**:
  - PR #37 (`feat/s6-centralized-deployment`): S6-01 Centralized Deployment & Schema-Valid Office Manifest.
  - PR #38 (`feat/s6-multipage-visual-rag`): S6-02 Advanced Visual RAG Multi-Page Evidence Linkage.
  - PR #39 (`feat/s6-performance-optimization`): S6-03 Large-Scale Financial Statement Parsing & Cache Performance Optimization.

---

## 2. Merged Deliverables

| PR | Task | Subsystem | Delivered capability |
| :--- | :--- | :-------- | :------------------- |
| **#37** | **S6-01** (#34) | `apps/excel`, `packages/core-engine` | Validated Microsoft Office Add-in XML Schema 1.1 manifest (`manifest.prod.xml`, `manifest.xml`) with valid UUID, `<Permissions>`, and multi-client WebSocket IPC broadcast manager. |
| **#38** | **S6-02** (#35) | `packages/core-engine`, `apps/desktop` | Multi-page visual evidence linkage and cross-page reasoning across BCTC pages with `router.analyze_pages`, active visual chip tracking, and desktop UI badge (`Liên kết đa trang`). |
| **#39** | **S6-03** (#36) | `packages/core-engine`, `apps/desktop` | Multi-core parallel PyMuPDF rendering via `ThreadPoolExecutor`, content-addressed manifest caching (`manifest.json`), LanceDB in-memory page caching, sub-millisecond query LRU caching (< 1ms), and cache security hardening. |

---

## 3. Open Issues & Backlog

- **#11 ([excel] S4-01: Office.js Web Add-in Setup & HTTPS Dev Server)**: Core functionality delivered via `apps/excel` in S4/S5/S6. Backlog item remaining is final packaging validation.
- **#12 ([excel] S4-03: 1-Click Financial Statement Ingestion & Query Trigger)**: Excel taskpane direct upload and ingestion flow to be implemented in Sprint 7.

---

## 4. Settled Architectural Decisions

- **ADR-001 (Hybrid Desktop & Visual RAG Native)**: Visual RAG ColPali late-interaction indexing persists in LanceDB; multi-page cross-referencing maintains normalized coordinates `[0, 1000]`.
- **ADR-002 (Dual-Mode Inference Architecture)**: Apple Silicon MLX local inference prioritized when hardware available; LiteLLM cloud router acts as BYOK frontier fallback.
- **ADR-003 (Bounding Box Visual Grounding Protocol)**: Audited SVG overlay remains 100% immutable over source PDF; multi-page citations jump across pages with visual flash highlight.
- **ADR-004 (Monorepo Blackbox Boundaries & IPC)**: Excel Add-in (`apps/excel`) and Desktop Client (`apps/desktop`) communicate asynchronously with `packages/core-engine` daemon over REST and WebSocket broadcast.

---

## 5. Pitfalls Encountered & Engineering Rules

1. **Subdirectory Cache Deletion Traversal Vulnerability (Rule 13B)**:
   - Verifying `is_path_safe()` against `ALLOWED_ROOTS` (`~/.finsight`) alone is insufficient for subdirectory operations (such as `~/.finsight/cache/rendered_pages`), because traversal paths like `../../victim_dir` remain within `ALLOWED_ROOTS`.
   - *Rule:* Always enforce direct-child containment (`target_dir.parent == self.render_cache_dir`) and Pydantic regex sanitization `^[a-zA-Z0-9_\-]+$` for all user-supplied identifiers.
2. **PyMuPDF Thread Safety with GIL**:
   - PyMuPDF objects must not be shared across worker threads in a `ThreadPoolExecutor`.
   - *Rule:* Open an independent document handle (`pymupdf.open(pdf_path)`) strictly inside worker functions and close it within a `finally:` block.
3. **Office Manifest Schema Enforcement**:
   - Microsoft Office Add-in XML Schema 1.1 strictly requires `<Id>` to be a valid uppercase/lowercase GUID/UUID, `<Permissions>ReadWriteDocument</Permissions>`, and HTTPS icon/support URLs. Always validate manifests with `npx office-addin-manifest validate`.

---

## 6. Sprint 7 Horizon: next tasks

1. **S7-01: Office.js 1-Click Financial Statement Ingestion** — `apps/excel/src/components/`, `apps/excel/src/lib/`
   - Implement direct PDF file picker in the Excel Taskpane to trigger backend ingestion (`/api/v1/documents/ingest`) and update local document state.
2. **S7-02: Multi-Document Comparative RAG** — `packages/core-engine/src/`, `apps/desktop/`
   - Support comparative queries cross-referencing multiple fiscal years (e.g. BCTC 2022 vs BCTC 2023) across multiple document indices.
3. **S7-03: Tauri v2 Native Desktop Bundle Verification** — `apps/desktop/src-tauri/`
   - Build and verify native DMG/app bundle on macOS with local daemon lifecycle management.
4. **S7-04: Legacy Monorepo Cleanup** — `packages/office-addin/`, `package.json`
   - Prune obsolete `packages/office-addin` directory in favor of official `apps/excel`.

---

## 7. Open Questions For The Human

- None. All Sprint 6 tasks have been implemented, audited, merged via PR merge commits into `dev`, and signed off with **VERDICT: APPROVED 🟢**. Sprint 7 is ready to launch in a fresh conversation.
