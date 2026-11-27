# Sprint 13 Technical Verification Report

**Date**: 2026-11-27  
**Repository**: `529-studio/FinTrace`  
**Target Branch**: `dev` (`aedc647`)  
**Wave Audit Verdict**: `APPROVED 🟢` (Independent subagent `4eb73129`)

---

## 1. Sprint 13 Deliverables Summary

| PR | Task | Subsystem | Delivered Capability |
| :--- | :--- | :-------- | :------------------- |
| **#116** | **S13-01** | `fullstack` | Real PDF page rendering (`PdfViewer.tsx` + backend `/api/v1/documents/{doc_id}/pages/{page_number}`), bounding box alignment, and bridge stability. |
| **#117** | **S13-02** | `fullstack` | Desktop PDF upload (`POST /api/v1/documents/upload`), document switcher (`DocumentPickerModal`), comparative picker, and Excel indexed selector. |
| **#118** | **S13-03** | `excel` | Local Tailwind build fix, responsive Waterfall SVG, formula baseline, and live bridge/audit note integration. |
| **#119** | **S13-04** | `core-engine` | Cross-sectional industry peer benchmarking engine (`peer_benchmark.py`), equal & market-cap weighted means, linear percentiles (`P10`–`P90`), z-scores, and `POST /api/v1/analysis/peer-benchmark`. |
| **#120** | **S13-05** | `core-engine` | Direct-to-Indirect Operating Cash Flow reconciliation engine (`cashflow_reconciler.py`), working capital delta sign handling, materiality thresholds, `[0, 1000]` citations, and `POST /api/v1/analysis/cashflow-reconcile`. |
| **#121** | **S13-06** | `apps/desktop` | Multi-document tabbed split-screen PDF viewer (`TabbedSplitViewer.tsx`) with `Đồng bộ trang` (page & scroll lock) and `SplitView.component.tsx` integration. |
| **#122** | **S13-07** | `core-engine` | Hierarchical RBAC engine (`rbac_policy.py`), Deny-Takes-Precedence `fnmatch` policies, salted PBKDF2-HMAC-SHA256 login hardening, privilege escalation blocking, and `/api/v1/rbac/*` endpoints. |
| **#123** | **S13-08** | `apps/excel` | OAT Tornado sensitivity engine (`computeTornadoSensitivity` in `formulaAuditor.ts`), responsive `TornadoChart.tsx` SVG with live `Precedents / Dependents` visualizer, and `Sidebar.tsx` integration. |

---

## 2. Verified Quantitative Scorecard (Post-Wave Audit)

| Package | Command | Result |
| :--- | :--- | :--- |
| **Core Engine** | `packages/core-engine/.venv/bin/pytest packages/core-engine/tests -q` | **202 passed** (7.38s) |
| **Desktop App** | `npm run --prefix apps/desktop test && npm run --prefix apps/desktop build` | **16 files, 68 passed** (2.61s); `tsc && vite build` OK (1.08s) |
| **Excel Add-in** | `npm run --prefix apps/excel test && npm run --prefix apps/excel build` | **9 files, 56 passed** (1.59s); `tsc && vite build` OK (912ms) |
| **Rule 15 (Zero Emoji)** | Automated scan of Sprint 13 frontend components | **0 raw emojis** |
| **Cleanliness & Security** | `console.log` & `eval(`/`exec(` scan | **0 violations** |

---

## 3. Empirical Reality Checks

- **Core Engine Live Daemon (`127.0.0.1:8765`)**:
  - `POST /api/v1/analysis/cashflow-reconcile` returned `200 OK` (`reconciled`, `0.108ms`) and rejected `../../etc/passwd` with `422`.
  - `POST /api/v1/auth/login` rejected arbitrary passwords with `401 Unauthorized`, blocked privilege escalation with `403 Forbidden`, and `POST /api/v1/rbac/evaluate` returned `200 OK` (`pol-deny-guest-delete`).
- **Playwright MCP Visual Proofs (`docs/proofs/sprint13/`)**:
  - `docs/proofs/sprint13/desktop_tabbed_split_viewer.png`: Dual-pane (`PANE A` / `PANE B`) tabbed split viewer verified at `1440x900`.
  - `docs/proofs/sprint13/excel_tornado_chart.png`: Responsive Tornado SVG & `Chuỗi phụ thuộc: B2` dependency panel verified at `420x900` taskpane viewport.
