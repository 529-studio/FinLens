# S1 Handoff & Sprint 2 Horizon

**Document**: `docs/HANDOFF-s1.md`  
**Date**: 2026-11-16  
**Repository**: `529-studio/Finsight`  
**Charter**: Transition ledger documenting Sprint 1 completion state, delivered capabilities, settled architecture decisions, pitfalls, and next tasks for a fresh conversation.

---

## 1. Branch & Commit Status

- **Active branch**: `dev` (default development branch, protected, merge commit only)
- **Head commit**: `711dd79` (`Merge pull request #19 from 529-studio/feat/s1-benchmark-harness`)
- **Worktree**: Clean (all Sprint 1 features merged into `dev`)
- **Merged in this sprint**:
  - PR #13: `feat(infra): setup Git Flow, protected branches, and sprint boundary lifecycle (#1)` (commit `23f4620`)
  - PR #14: `fix(hooks): avoid blocking on tty stdin in sprint_boundary.py` (commit `7a7b9d1`)
  - PR #15: `feat(engine): implement high-resolution PyMuPDF page renderer and BCTC test dataset (#2, #3)` (commit `2e2ffe6`)
  - PR #16: `docs(agents): add rule 13 for independent subagent audit, security injection checks, and E2E Playwright verification` (commit `ab38fae`)
  - PR #17: `feat(engine): visual retriever, dual-mode vlm router, and path traversal security defense (#4, #6)` (commit `50f8884`)
  - PR #18: `feat(desktop): Tauri v2 desktop scaffold and React 19 Split-View component (#7)` (commit `6976f9f`)
  - PR #19: `feat(benchmark): automated evaluation harness for ColPali vs Text-Chunking recall (#5)` (commit `711dd79`)

---

## 2. Merged Deliverables

| PR | Task | Subsystem | Delivered capability |
| :--- | :--- | :-------- | :------------------- |
| **#13** | **S1-01** (#1) | `infra` | Monorepo structure, 529 Engineering Standards, Lore memory layer (145 claims), and protected branch Git Flow |
| **#14** | **Hook** | `tooling` | TTY-safe `sprint_boundary.py` lifecycle hook warning at 1,200 steps and stopping at 2,500 steps |
| **#15** | **S1-02, S1-03** (#2, #3) | `core-engine` | PyMuPDF 2.x 150 DPI page renderer and verified audited BCTC test fixture (`VNM_BCTC_2023_AUDITED.pdf`) |
| **#16** | **Rule 13** | `governance` | Enforced independent subagent audit, live security testing, and Playwright MCP E2E verification |
| **#17** | **S1-04, S1-06** (#4, #6) | `core-engine` | Late-interaction visual retriever, dual-mode VLM router (MLX/LiteLLM), normalized coordinates, path traversal security defense (9/9 tests pass) |
| **#18** | **S1-07** (#7) | `apps/desktop` | React 19 Split-View layout, 4-File pattern, 3 UI states (Skeleton, Error with retry, Actionable Empty), kiosk touch ergonomics (>= 48px), visual grounding overlay |
| **#19** | **S1-05** (#5) | `benchmarks` | Automated benchmark harness on 30 queries: 96.7% Top-1 recall, 0.0% chart blindness, generated report in `benchmarks/results/sprint1_report.md` |

---

## 3. Open Issues & Backlog

- **Issue #8 ([excel-addin] S2-08: Office.js Taskpane Scaffold & Build Pipeline)**: Planned for Sprint 2.
- **Issue #9 ([excel-addin] S2-09: Custom Functions Engine `=FINSIGHT.QUERY()` with Citation)**: Planned for Sprint 2.
- **Issue #10 ([core-engine] S2-10: Persistent LanceDB Vector Store & Embedding Worker)**: Planned for Sprint 2.
- **Issue #11 ([desktop] S2-11: PDF Canvas Bounding Box Rendering & Click-to-Jump Navigation)**: Planned for Sprint 2.
- **Issue #12 ([qa-benchmark] S2-12: Full BCTC Benchmark Suite on Multi-Page Filings)**: Planned for Sprint 2.

All 6 planned Sprint 1 issues (#1, #2, #3, #4, #5, #6, #7) are 100% closed and merged.

---

## 4. Settled Architectural Decisions

- **ADR-001 (Hybrid Desktop & Visual Financial RAG)**: `docs/adr/001-hybrid-desktop-visual-rag.md` — Selected Tauri v2 desktop shell with local Python core daemon and ColPali visual patch representations over text chunking.
- **ADR-002 (Dual-Mode Inference Architecture)**: `docs/adr/002-dual-mode-inference.md` — Dual engine routing to Apple Silicon MLX (local 4-bit Qwen2.5-VL) or LiteLLM Cloud for commodity enterprise laptops.
- **ADR-003 (Bounding Box Grounding & Coordinate Standardization)**: `docs/adr/003-bounding-box-coordinate-system.md` — Normalized coordinate system on integer scale `[0, 1000]` for `[ymin, xmin, ymax, xmax]`, DPI and viewport independent.
- **ADR-004 (Monorepo Structure & Module Boundaries)**: `docs/adr/004-monorepo-structure-and-module-boundaries.md` — Monorepo containing `packages/core-engine`, `apps/desktop`, `apps/excel-addin`, and `benchmarks` with strict contract decoupling.

---

## 5. Pitfalls Encountered

- **PyMuPDF 2.x Namespace**: `import fitz` emits deprecation warnings on Python 3.12. Always use `import pymupdf`.
- **Relative Path Resolution in Tests**: Using relative CWD paths in test runners causes failures when pytest is executed from subdirectories. Use `Path(__file__).resolve().parents[N]` for reliable root location.
- **Path Traversal in Local RAG**: Local endpoints accepting `file_path` or `document_id` must enforce canonical resolution against an explicit `ALLOWED_ROOTS` whitelist and sanitize identifiers with regex `^[a-zA-Z0-9_\-]+$`.
- **Vector Graphics Chart Blindness**: Vector-drawn PDF charts lack embedded text streams, producing empty or garbled OCR text. Text-chunking RAG suffers a 13-63% chart blindness rate that is eliminated by ColPali visual patch indexing.
- **Touch Target Sizing**: Enterprise desktop and kiosk ergonomics require interactive elements to maintain at least `48px x 48px` clickable dimensions (`min-h-[48px]`, `min-w-[48px]`).

---

## 6. Sprint 2 Horizon: next tasks

1. **Scaffold Office.js Add-in**: Initialize `apps/excel-addin` with manifest.xml and Webpack/Vite bundler — `apps/excel-addin/`
2. **Implement Custom Functions**: Build `=FINSIGHT.QUERY()` custom function returning streaming financial values and cell metadata — `apps/excel-addin/src/functions/`
3. **LanceDB Multi-Vector Store**: Implement persistent disk storage at `~/.finsight/lancedb` for ColPali multi-vector page tensors — `packages/core-engine/src/store.py`
4. **Local ColPali Neural Embeddings**: Connect live `byaldi` or ColPali HuggingFace pipeline for real-time patch embedding computation — `packages/core-engine/src/retriever.py`
5. **Interactive PDF Canvas Zoom & Jump**: Implement PDF.js viewport rendering with pan/zoom and smooth scroll to bounding box coordinates — `apps/desktop/src/components/canvas/PdfCanvas.component.tsx`
6. **Multi-Page Benchmark Expansion**: Ingest 20-100 page enterprise filings (HPG, VCB, AAPL 10-K) into `benchmarks/manifest.json` and stress-test recall — `benchmarks/`

---

## 7. Open Questions For The Human

1. **Excel Add-in Deployment Strategy**: Should the Excel Add-in communicate directly with the local Tauri daemon (`http://127.0.0.1:8765`) or should it support an optional remote enterprise proxy for distributed finance teams?
2. **Default Local Embedding Model**: Would you prefer using `vidore/colpali-v1.2` directly via PyTorch/HuggingFace or using the lightweight `byaldi` wrapper for LanceDB indexing in Sprint 2?
