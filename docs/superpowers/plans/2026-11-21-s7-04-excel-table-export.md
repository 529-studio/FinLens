# Implementation Plan: Sprint 7 Task S7-04 - 1-Click Financial Table Export to Excel Sheet & Monorepo Cleanup

## 1. Executive Summary & Goals
- **Issue Reference:**
  - [#45 - [excel] S7-04: 1-Click Financial Table Export to Excel Sheet & Monorepo Cleanup](https://github.com/529-studio/Finsight/issues/45)
  - Closes [#11 - [excel] S4-01: Office.js Web Add-in Manifest & React Fluent UI Sidebar](https://github.com/529-studio/Finsight/issues/11)
  - Closes [#12 - [excel] S4-03: 1-Click Financial Table Export & Auto Formula Generation](https://github.com/529-studio/Finsight/issues/12)
- **Target Branch:** `feat/s7-excel-table-export` targeting `dev`
- **Objective:**
  1. Complete the Phase 2 Excel integration by porting and modernizing `insertFinancialTableToSheet` into `apps/excel/src/lib/excel/table-export.ts` with auto-formula generation (`=SUM(...)`) and audit trail comments.
  2. Integrate an ergonomic 1-Click "Xuất Bảng Vào Excel" button ($\ge 48\text{px}$) into `apps/excel/src/components/Sidebar.tsx` with full 3 UI states.
  3. Clean up the obsolete skeleton directory `packages/office-addin/` and update root `package.json` scripts to eliminate monorepo technical debt.

---

## 2. Architectural Blueprint & File Map

```
apps/excel/
├── src/
│   ├── lib/
│   │   └── excel/
│   │       ├── table-export.ts             # Office.js Excel table export, =SUM() formula, audit comments
│   │       └── __tests__/
│   │           └── table-export.test.ts    # Unit tests for matrix formatting and formula generation
│   ├── components/
│   │   └── Sidebar.tsx                     # "Xuất Bảng Vào Excel" button with Kiosk >= 48px & 3 UI states
│   └── types/
│       └── api.ts                          # TableExportPayload interface
└── package.json                            # Test script and dependencies

Root:
├── package.json                            # Update dev:addin to apps/excel
└── packages/
    └── office-addin/                       # [DELETED] Obsolete skeleton directory removed
```

---

## 3. Detailed Technical Tasks

### Task 1: Excel Table Exporter (`apps/excel/src/lib/excel/table-export.ts`)
- Implement `insertFinancialTableToSheet(data: FinancialTableData)`:
  - Supports Office.js environment detection (`typeof Excel !== 'undefined'`).
  - Fallback for standalone web test runner (returns structured mock preview without throwing).
  - Retrieves active selection (`context.workbook.getSelectedRange()`).
  - Detects numeric columns in `data.rows` and appends an automated total row with `=SUM(colStart:colEnd)` formulas.
  - Formats header row: bold, `#1E293B` (slate-800) background, white text.
  - Automatically adjusts column width: `targetRange.format.autofitColumns()`.
  - Attaches Audit Trail comment to top-left origin cell:
    `[FinSight Audit Trail] Trích xuất từ tài liệu ${data.sourceDocId}, trang ${data.sourcePage}. Nhấp vào sidebar để xem ảnh gốc.`

### Task 2: UI Integration in Excel Taskpane (`apps/excel/src/components/Sidebar.tsx`)
- Add structured table data parser from `queryResult` (e.g. revenue breakdown by segment).
- Add 1-Click "Xuất Bảng Vào Excel" button:
  - Touch target meets Kiosk $\ge 48\text{px}$ standard (`min-h-[48px]`).
  - Displays export state: idle, exporting (spinner), success badge with checkmark, error with retry.
  - Uses 100% Lucide React SVGs (`Table`, `ArrowDownToLine`, `CheckCircle2`), 0 raw emojis.

### Task 3: Obsolete Directory Cleanup & Monorepo Maintenance
- Delete obsolete directory `packages/office-addin/`.
- Update root `package.json`:
  - Change `"dev:addin": "npm run --prefix packages/office-addin dev"` to `"dev:addin": "npm run --prefix apps/excel dev"`.
- Ensure `npm install` and all workspaces remain clean and valid.

### Task 4: Automated Testing & Verification
- Unit test `table-export.test.ts` verifying matrix building, formula generation, and fallback execution.
- Build verification:
  - `npm --prefix apps/excel run build` (`tsc && vite build`) exits 0.
  - `npm --prefix apps/desktop run build` exits 0.
  - `npm --prefix apps/desktop test` (32 tests) pass 100%.
  - `packages/core-engine/.venv/bin/pytest packages/core-engine/tests -q` (74 tests) pass 100%.
- E2E Playwright verification of `apps/excel` taskpane with screenshot saved to `docs/proofs/sprint7/s7-04-excel-export.png`.

### Task 5: Subagent Audit, CI & Merge
- Dispatch independent subagent `research` with role `Independent Codebase & UI/UX Quality Auditor`.
- Obtain `VERDICT: APPROVED 🟢`.
- Commit, push, create PR for Issue #45, monitor GitHub Actions CI, and merge into `dev`.

---

## 4. Definition of Done (DoD)
- [ ] `insertFinancialTableToSheet` implemented with Office.js integration, `=SUM()` formula row, and audit comment.
- [ ] 1-Click "Xuất Bảng Vào Excel" button added to `Sidebar.tsx` with $\ge 48\text{px}$ touch target and zero raw emojis.
- [ ] Obsolete directory `packages/office-addin/` completely removed.
- [ ] All test suites across monorepo pass 100%.
- [ ] Playwright screenshot proof in `docs/proofs/sprint7/s7-04-excel-export.png`.
- [ ] Subagent audit signed off with `APPROVED 🟢`.
- [ ] PR created and merged into `dev` with `--merge` commit.
