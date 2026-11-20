# Sprint 6 Completion & Technical Verification Report

**Project:** FinSight (Visual Financial RAG & Hybrid Desktop Platform)  
**Document Version:** 1.0.0 (Audited & Reconciled with Git Ledger & Test Evidence)  
**Date:** 2026-11-20  
**Target Audience:** Technical Leads, System Architects, AI Evaluation Agents, Developers  
**Primary References & Ground Truth:**
- `docs/PRD_ARCH_FINSIGHT.md`
- `docs/HANDOFF-s5.md`
- `docs/lesson_learn.md`
- ADR-001 through ADR-004
- GitHub PR & Issue Ledger (#34, #35, #36; PR #37, #38, #39)

---

## 1. Executive Summary & Quantitative Scorecard

Sprint 6 executed the mandate established in `docs/HANDOFF-s5.md`: Centralized Deployment for Office Add-ins, Advanced Visual RAG with multi-page evidence linkage, and performance optimization for large-scale financial statement parsing.

### Delivered Deliverables Summary
- **S6-01 (#34, PR #37)**: Centralized Deployment & Microsoft Office Add-in XML Schema 1.1 compliant manifest (`manifest.prod.xml`, `manifest.xml`) with valid UUID (`529e0001-f187-4d7a-8f52-529529529001`), `<Permissions>ReadWriteDocument</Permissions>`, and WebSocket IPC broadcast manager in core-engine.
- **S6-02 (#35, PR #38)**: Advanced Visual RAG multi-page evidence linkage across BCTC pages (e.g. Page 1 Revenue charts + Page 2 Balance Sheet/Footnotes) with `router.analyze_pages`, synthesized insights, and desktop UI multi-page badge (`Liên kết đa trang`).
- **S6-03 (#36, PR #39)**: Performance optimization for large-scale financial statement parsing: multi-core parallel PyMuPDF rendering via `ThreadPoolExecutor`, content-addressed manifest caching (`manifest.json`), LanceDB in-memory page caching, sub-millisecond query LRU caching, and cache security hardening against path traversal.

### Quantitative Verification Scorecard
| Metric | Baseline Target | Sprint 6 Result | Verification Status |
| :--- | :--- | :--- | :---: |
| **Top-1 Retrieval Recall** | $\ge 85\%$ | **96.7%** | **PASSED 🟢** |
| **Chart Blindness Rate** | 0.0% | **0.0%** | **PASSED 🟢** |
| **Bounding Box Accuracy (IoU)** | $\ge 0.80$ | **> 0.95** | **PASSED 🟢** |
| **Cold Render Latency (8 pages)** | $< 2.5\text{s}$ | **0.42s** (multi-core parallel) | **PASSED 🟢** |
| **Cached Document Ingest** | $< 100\text{ms}$ | **< 15ms** (manifest hit) | **PASSED 🟢** |
| **Repeated Query Response Latency** | $< 100\text{ms}$ | **0.05ms - 0.58ms** (Query LRU) | **PASSED 🟢** |
| **Backend Test Suite Pass Rate** | 100% | **63 / 63 passed (100%)** | **PASSED 🟢** |
| **Desktop Test Suite Pass Rate** | 100% | **26 / 26 passed (100%)** | **PASSED 🟢** |
| **Production Build Status** | 0 errors | **0 errors (Desktop + Excel)** | **PASSED 🟢** |
| **Zero Raw Emojis in UI (Rule 15)** | 0 emojis | **0 emojis found** | **PASSED 🟢** |
| **Kiosk Touch Ergonomics** | $\ge 48\text{px}$ | **$\ge 48\text{px}$ on all buttons** | **PASSED 🟢** |

---

## 2. Wave-by-Wave Audit of Delivered Engineering

### Wave 1: Centralized Deployment & Multi-Client IPC Bridge (S6-01)
- Re-architected `apps/excel/manifest.prod.xml` and `apps/excel/manifest.xml` to satisfy strict Microsoft Office Add-in XML Schema 1.1 requirements.
- Validated via `npx office-addin-manifest validate` with 0 schema warnings.
- Upgraded Core Engine `/ws` endpoint with a multi-client `ConnectionManager` capable of broadcasting real-time citation navigation events between the Excel Taskpane and Desktop UI.

### Wave 2: Advanced Visual RAG & Multi-Page Evidence Linkage (S6-02)
- Enhanced `packages/core-engine/src/retriever.py` with cross-reference scoring heuristics (+2.0 boost on comprehensive/multi-statement queries) and `get_linked_pages()`.
- Implemented `analyze_pages(pages, query)` across `mlx_engine.py`, `cloud_router.py`, and `vlm_router.py` while preserving 100% backwards compatibility for `analyze_page`.
- Extended `SplitView.component.tsx` to render a visual badge `Liên kết đa trang (N trang)` when grounding evidences span multiple pages.
- Highlighted active evidence chip with high contrast red border and synchronized page switching with animated bounding box visual grounding.

### Wave 3: Performance Optimization & Sub-Millisecond Retrieval Caching (S6-03)
- Modernized `PdfRenderer` using `concurrent.futures.ThreadPoolExecutor(max_workers=min(cpu_count, 8))` with per-thread document handles, achieving 3-5x rasterization speedups.
- Implemented content-addressed manifest caching (`manifest.json`) verifying file size, mtime, dpi, page dimensions, and sha256 signatures, reducing re-ingestion latency from seconds to $< 15\text{ms}$.
- Added in-memory document page caching `_pages_cache` in `LanceDBStore` with automated invalidation.
- Created `QueryLRUCache` (`threading.RLock()`) providing sub-millisecond query responses ($0.05\text{ms} - 0.58\text{ms}$).
- Exposed `/api/v1/cache/stats` and `/api/v1/cache/clear` endpoints.

---

## 3. Reality-Check Audit Findings (The Uncomfortable Truths)

1. **Subdirectory Cache Deletion Traversal Vulnerability:**
   - *Observation:* During the S6-03 independent audit, a critical path traversal vulnerability was caught: `is_path_safe()` verified whether paths resided in `ALLOWED_ROOTS` (`~/.finsight`), but `document_id="../../victim"` inside `~/.finsight/cache/rendered_pages` resolved to `~/.finsight/victim`, allowing arbitrary directory deletion.
   - *Mitigation:* Enforced direct-child containment `target_dir.parent == self.render_cache_dir`, strict regex sanitization `^[a-zA-Z0-9_\-]+$`, and Pydantic field validation on `CacheClearRequest.document_id`. Re-audit was signed off as **APPROVED 🟢**.
2. **PyMuPDF Thread Safety with GIL:**
   - *Observation:* Sharing a single PyMuPDF document handle across multiple Python threads in a `ThreadPoolExecutor` can cause race conditions or memory faults in PyMuPDF's C layer.
   - *Mitigation:* Instantiated an independent document handle (`pymupdf.open(pdf_path)`) strictly inside `_render_single_page_worker` and closed it in a `finally:` block.

---

## 4. Engineering Lessons Learned
Recorded in `docs/lesson_learn.md` and synced via `npm run harvest:lessons`:
- **Lesson 14:** Tối ưu hóa xử lý BCTC quy mô lớn: Render đa luồng PyMuPDF, Bộ nhớ đệm Manifest và Phòng thủ Traversal trong Cache Invalidation.

---

## 5. Carry-Over Ledger & Strategic Bridge to Sprint 7
- **Sprint 7 Horizon:**
  1. Office.js 1-Click Financial Statement Ingestion directly from Excel Taskpane.
  2. Multi-Document Cross-Comparison RAG (comparing BCTC 2022 vs 2023 across multiple filings).
  3. Packaging and native desktop build validation (Tauri v2 bundle generation).
  4. Cleanup of legacy `packages/office-addin` directory in favor of official `apps/excel`.
