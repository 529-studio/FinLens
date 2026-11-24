# S12-05: Excel Add-in Live Linked Footnote Citation Drawer & In-Sheet Audited Cell Tags Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the live linked footnote citation drawer and in-sheet audited cell tag manager (`AuditedCellDrawer.tsx`) for the Excel Add-in, providing instant provenance verification, "Jump to PDF Source" bridge triggers, 3 UI states, $\ge 48$px touch targets, and zero raw emojis.

**Architecture:**
- Component: `apps/excel/src/components/AuditedCellDrawer.tsx`
- Test Suite: `apps/excel/src/components/__tests__/AuditedCellDrawer.test.tsx`
- Integration: `apps/excel/src/components/Sidebar.tsx`
- Standards: 3 UI states (Skeleton, Error with retry, Actionable Empty), $\ge 48$px touch targets, Rule 15 Zero Emojis (Lucide React), ADR-003 Grounding.

**Tech Stack:**
- React 19, TypeScript, Lucide React, Vitest, Testing Library.

---

## Global Constraints

- **Git Flow (Rule 12):** Active branch is `feat/s12-05-excel-audited-cell-drawer` targeting `dev`. PR merge commit required.
- **Rule 15 Zero-Emoji Policy:** 0 raw Unicode emojis. Use Lucide React vector icons (`FileText`, `ExternalLink`, `CheckCircle2`, `AlertCircle`, `RefreshCw`, `Tag`, `BookOpen`, `X`).
- **Resilient UI (Kiosk & 3 States):** Skeleton loading, Error state with retry, Actionable Empty state. All interactive touch targets $\ge 48$px.
- **Bridge Navigation:** Transmits citation payload to desktop daemon via `bridge.sendCitation`.

---

### Task 1: AuditedCellDrawer Unit Tests (`AuditedCellDrawer.test.tsx`)
- Write tests covering:
  - Rendering cell address, line item, footnote disclosure, and confidence badge.
  - "Jump to PDF Source" button trigger with citation ID.
  - 3 UI States: Skeleton loading, Error state with retry, Actionable Empty state.
  - $\ge 48$px touch target verification on interactive buttons.

### Task 2: Implement `AuditedCellDrawer.tsx`
- Implement component adhering to design standards.
- Run `npx vitest run --root apps/excel` to verify all tests pass.

### Task 3: Integrate with `Sidebar.tsx`
- Connect drawer toggle and audited cell selection into Excel Add-in sidebar.
- Verify complete Excel test suite passes.

### Task 4: PR Creation, Independent Subagent Audit & Merge
- Push branch, create PR targeting `dev`, dispatch independent subagent audit.
- Merge PR with `--merge`.
