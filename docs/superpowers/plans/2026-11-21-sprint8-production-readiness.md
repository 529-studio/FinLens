# Sprint 8: Production Readiness, Golden Dataset Benchmarks, Signing/Notarization & Streaming Inference Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Elevate FinSight from an internal beta to an enterprise-grade production-ready platform by establishing rigorous 100+ BCTC golden dataset retrieval benchmarks, configuring macOS/Windows hardened runtime signing and notarization, implementing real-time WebSocket token streaming across Desktop and Excel Taskpane, and delivering automated footnote (Thuyết minh BCTC) disambiguation.

**Architecture:** Visual RAG Core with late-interaction ColPali and LanceDB; FastAPI daemon with asynchronous WebSocket token streaming; Tauri v2 desktop client with hardened runtime entitlements and Rust-supervised Python daemon; Office.js taskpane with direct formula and footnote export.

**Tech Stack:** Python 3.10+, PyMuPDF, LanceDB, FastAPI, WebSockets, MLX-VLM / LiteLLM, Tauri v2, Rust 1.80+, React 19, TypeScript, Tailwind CSS, Office.js, Vitest, Pytest.

**Spec:** `docs/HANDOFF-s7.md`, `docs/PRD_ARCH_FINSIGHT.md`, `AGENTS.md`

## Global Constraints

- Default branch is `dev`; all work MUST merge into `dev` via Pull Requests with merge commits (`gh pr merge --merge`).
- Strict zero-emoji UI policy (Rule 15): 100% free-licensed Lucide React SVG icons.
- Kiosk touch ergonomics: All interactive targets $\ge 48\text{px}$.
- 3 UI States mandate: Skeleton loading, localized Error state with retry, and Actionable Empty state.
- Zero-leak security policy: 0 plain API keys or secrets in source code, logs, or git.
- Path traversal defense: All document IDs and file paths validated via `^[a-zA-Z0-9_\-]+$` and resolved strictly within approved directories.
- Independent Subagent Audit sign-off (`APPROVED 🟢`) required before closing any task or merging PRs.

## Review Focus

1. **Gatekeeper & Hardened Runtime Block**: Unsigned/un-notarized macOS binaries failing with "App is damaged" on client machines outside development environments.
2. **WebSocket Connection Drop / Reconnection**: Network interruptions or daemon restarts during long comparative streaming inference resulting in hanging UI spinners.
3. **Vietnamese Diacritics & Footnote OCR Noise**: Scanned or skewed PDF tables misidentifying footnote references (e.g. "TM 15", "Thuyết minh số 15") resulting in broken cell citations.
4. **Memory Exhaustion on Large Benchmarks**: Batch-evaluating 100+ financial filings exhausting host RAM due to unclosed PyMuPDF document handles or lingering MLX tensor caches.
5. **Path Traversal Probing**: Injection of directory traversal patterns (`../../etc/passwd`, absolute host paths) into document IDs or footnote export endpoints.

---

### Task 1: S8-01 - Golden Dataset Comprehensive Evaluation & Retrieval Accuracy Benchmarks

**Owner:** `qa-benchmark-engineer`, `rag-ml-engineer`  
**GitHub Issue:** To be created as S8-01  
**Target Branch:** `feat/s8-golden-dataset-benchmark` targeting `dev`  

**Files:**
- Create: `benchmarks/data/manifest_golden_100.json`
- Create: `benchmarks/eval_golden_suite.py`
- Create: `packages/core-engine/tests/test_golden_benchmark.py`
- Modify: `benchmarks/eval_retrieval.py`
- Modify: `package.json` (add `bench:golden` script)

**Steps:**
- [ ] Write failing test `packages/core-engine/tests/test_golden_benchmark.py` validating metrics schema (Top-1 recall $\ge 85\%$, Top-3 recall $\ge 95\%$, chart blindness $\le 0.0\%$, IoU $\ge 0.80$).
- [ ] Run test to verify it fails (`pytest packages/core-engine/tests/test_golden_benchmark.py`).
- [ ] Create `benchmarks/data/manifest_golden_100.json` defining ground truth queries, chart queries, multi-level balance sheet tables, and footnote references across major Vietnamese filings (VNM, HPG, VCB, FPT, VIC, MSN, MWG, VHM, MBB, TCB).
- [ ] Implement `benchmarks/eval_golden_suite.py` supporting batch evaluation, memory recycling, IoU calculation, and JSON results output at `benchmarks/results/sprint8_golden_benchmark.json`.
- [ ] Run tests and benchmark suite to verify pass status (`python benchmarks/eval_golden_suite.py --dry-run`).
- [ ] Dispatch independent subagent audit and verify 100% test pass.
- [ ] Commit and open PR targeting `dev`.

---

### Task 2: S8-02 - Production Installer Signing, Hardened Runtime & Notarization Pipeline

**Owner:** `lead-architect`, `frontend-engineer`  
**GitHub Issue:** To be created as S8-02  
**Target Branch:** `feat/s8-installer-signing-notarization` targeting `dev`  

**Files:**
- Create: `apps/desktop/src-tauri/entitlements.plist`
- Create: `scripts/notarize-macos.sh`
- Modify: `apps/desktop/src-tauri/tauri.conf.json`
- Modify: `.github/workflows/desktop-release.yml` (or create if missing)
- Create: `apps/desktop/src/hooks/__tests__/useCodeSigningStatus.test.ts`

**Steps:**
- [ ] Write unit test in `apps/desktop` verifying entitlements and signing verification utilities.
- [ ] Run test to verify initial failure.
- [ ] Create `apps/desktop/src-tauri/entitlements.plist` specifying hardened runtime capabilities (`com.apple.security.cs.allow-jit`, `com.apple.security.cs.allow-unsigned-executable-memory`, `com.apple.security.network.client`, `com.apple.security.network.server`).
- [ ] Update `tauri.conf.json` to link `bundle.macOS.entitlements` and configure Apple Developer ID certificate env placeholders (`APPLE_SIGNING_IDENTITY`, `APPLE_CERTIFICATE`, `APPLE_CERTIFICATE_PASSWORD`).
- [ ] Create `scripts/notarize-macos.sh` executing Apple `notarytool` submission and stapling with fallback for dry-run/local test validation.
- [ ] Run Tauri build validation (`npm --prefix apps/desktop run tauri:build -- --no-bundle` or dry run check).
- [ ] Dispatch independent subagent audit.
- [ ] Commit and open PR targeting `dev`.

---

### Task 3: S8-03 - Real-Time WebSocket Streaming Inference to Taskpane & Desktop

**Owner:** `rag-ml-engineer`, `frontend-engineer`, `excel-addin-engineer`  
**GitHub Issue:** To be created as S8-03  
**Target Branch:** `feat/s8-websocket-streaming-inference` targeting `dev`  

**Files:**
- Modify: `packages/core-engine/src/contracts.py` (add `StreamingChunk`, `StreamingStatus`)
- Modify: `packages/core-engine/src/main.py` (implement `/ws/query/stream`)
- Modify: `packages/core-engine/src/vlm_router.py` (add `stream_analyze`)
- Modify: `packages/core-engine/src/cloud_router.py` (add async streaming generator)
- Modify: `packages/core-engine/src/mlx_engine.py` (add token generator)
- Create: `packages/core-engine/tests/test_streaming_inference.py`
- Create: `apps/desktop/src/hooks/useStreamingQuery.ts`
- Create: `apps/desktop/src/hooks/__tests__/useStreamingQuery.test.ts`
- Modify: `apps/desktop/src/components/chat/ChatPanel.component.tsx` (progressive text rendering)
- Modify: `apps/excel/src/components/Sidebar.tsx` (progressive text rendering)

**Steps:**
- [ ] Write failing backend streaming tests in `packages/core-engine/tests/test_streaming_inference.py`.
- [ ] Write failing React hook tests in `apps/desktop/src/hooks/__tests__/useStreamingQuery.test.ts`.
- [ ] Implement WebSocket endpoint `/ws/query/stream` in `main.py` emitting token chunks and completed bounding box evidence payloads.
- [ ] Implement `stream_analyze` in `vlm_router.py` and `cloud_router.py`.
- [ ] Implement `useStreamingQuery.ts` in desktop and integrate progressive display into `ChatPanel.component.tsx` and `apps/excel/src/components/Sidebar.tsx` adhering to 3 UI states and zero raw emojis.
- [ ] Run backend tests (`pytest packages/core-engine/tests/test_streaming_inference.py`) and frontend tests (`npm run test:desktop`).
- [ ] Verify live rendering with Playwright MCP and save screenshot proof.
- [ ] Dispatch independent subagent audit.
- [ ] Commit and open PR targeting `dev`.

---

### Task 4: S8-04 - Consolidated Financial Statement Footnote Disambiguation & Formula Extraction

**Owner:** `rag-ml-engineer`, `excel-addin-engineer`  
**GitHub Issue:** To be created as S8-04  
**Target Branch:** `feat/s8-footnote-disambiguation` targeting `dev`  

**Files:**
- Modify: `packages/core-engine/src/contracts.py` (add `FootnoteReference`, `FootnoteDisambiguationResult`)
- Modify: `packages/core-engine/src/vlm_router.py` (enhanced prompt template for Thuyết minh BCTC)
- Modify: `packages/core-engine/src/main.py` (endpoint `/api/v1/query/footnotes`)
- Create: `packages/core-engine/tests/test_footnote_disambiguation.py`
- Modify: `apps/excel/src/lib/excel/table-export.ts` (attach footnote hyperlink and cross-sheet notes)
- Modify: `apps/excel/src/lib/excel/__tests__/table-export.test.ts`

**Steps:**
- [ ] Write failing test in `packages/core-engine/tests/test_footnote_disambiguation.py` asserting regex and VLM extraction of "Thuyết minh số X" into structured objects.
- [ ] Write failing test in `apps/excel/src/lib/excel/__tests__/table-export.test.ts` testing footnote comment embedding and hyperlink generation.
- [ ] Implement footnote extraction logic and prompt templates in `vlm_router.py` and endpoint in `main.py`.
- [ ] Enhance `table-export.ts` in `apps/excel` to write footnote references as dedicated column or rich cell comments.
- [ ] Run backend and excel test suites to verify 100% pass.
- [ ] Verify live Excel rendering with Playwright MCP.
- [ ] Dispatch independent subagent audit.
- [ ] Commit and open PR targeting `dev`.

---

### Task 5: S8-05 - Wave Audit, Security Traversal Probe & Sprint 8 Close Ritual

**Owner:** `lead-architect`, `qa-benchmark-engineer`  
**GitHub Issue:** To be created as S8-05 (or Sprint Close PR)  
**Target Branch:** `docs/s8-handoff` targeting `dev`  

**Files:**
- Create: `docs/reports/sprint8_report.md`
- Create: `docs/HANDOFF-s8.md`
- Modify: `docs/lesson_learn.md`

**Steps:**
- [ ] Execute comprehensive backend security probes (Rule 13B: path traversal on all new endpoints `/ws/query/stream`, `/api/v1/query/footnotes`).
- [ ] Execute live UI inspection via Playwright MCP (Rule 13C & Rule 15: 0 raw emojis, Kiosk $\ge 48\text{px}$).
- [ ] Run full test matrix: `pytest packages/core-engine/tests`, `npm run test:desktop`, `npm run test:excel`, `cargo test`.
- [ ] Generate `docs/reports/sprint8_report.md` and scaffold `docs/HANDOFF-s8.md` via `tools/sprint/close.sh --init`.
- [ ] Record lessons learned and harvest to central hub via `npm run harvest:lessons`.
- [ ] Dispatch external subagent for final sign-off (`APPROVED 🟢`).
- [ ] Open PR for `docs/s8-handoff` and merge with merge commit.
