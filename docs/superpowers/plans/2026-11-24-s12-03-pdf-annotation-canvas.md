# S12-03: Desktop Native PDF Highlight Annotation Layer & Visual Comment Pinning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the native desktop PDF highlight annotation overlay and visual comment pinning layer (`AnnotationCanvas.tsx`) adhering to the 4-file pattern, 3 UI states, $\ge 48$px touch targets, Rule 15 zero raw emojis, and ADR-003 normalized coordinate scaling.

**Architecture:**
- Component: `apps/desktop/src/components/pdf/AnnotationCanvas.tsx`
- Test Suite: `apps/desktop/src/components/pdf/__tests__/AnnotationCanvas.test.tsx`
- Types: `apps/desktop/src/types/session_sync.types.ts`
- E2E Verification: Playwright MCP live DOM snapshot and screenshot verification in `docs/proofs/sprint12/`.

**Tech Stack:**
- React 19, TypeScript, Tailwind CSS, Lucide React, Vitest, Testing Library, Playwright.

---

## Global Constraints

- **Git Flow (Rule 12):** Active branch is `feat/s12-03-pdf-annotation-canvas` targeting `dev`. Merge commit required.
- **Rule 15 Zero-Emoji Policy:** 0 raw Unicode emojis. Strictly use Lucide React icons (`Highlighter`, `MessageSquare`, `Pin`, `Check`, `Trash2`, `X`, `AlertCircle`, `RefreshCw`).
- **Resilient UI (Kiosk & 3 States):** Skeleton loading, Error state with retry, Empty state with actionable message. All interactive touch targets $\ge 48$px.
- **Visual Grounding Standard (ADR-003):** Annotations maintain normalized coordinates $[0, 1000]$ and never mutate underlying PDF binary.
- **Playwright E2E Verification (Rule 13C):** Empirical UI screenshot saved to `docs/proofs/sprint12/`.

---

### Task 1: Annotation Canvas Unit Tests (`AnnotationCanvas.test.tsx`)
- Write failing tests covering:
  - Rendering existing highlight annotations and comment pins on target page.
  - Interactive drag-to-select box creation.
  - 3 UI States: Skeleton loading, Error state with retry, Actionable Empty state.
  - $\ge 48$px touch target verification on action buttons.
  - Comment pin selection and popover actions (Resolve, Delete, Close).

### Task 2: Implement `AnnotationCanvas.tsx`
- Implement component in `apps/desktop/src/components/pdf/AnnotationCanvas.tsx`.
- Run `npm test --prefix apps/desktop` to verify all tests pass.

### Task 3: Playwright E2E UI Verification (Rule 13C)
- Spin up desktop preview / dev server.
- Capture screenshot proof to `docs/proofs/sprint12/desktop_annotation_canvas.png`.

### Task 4: PR Creation, Independent Subagent Audit & Merge
- Push branch, create PR targeting `dev`, dispatch independent subagent audit.
- Merge PR with `--merge`.
