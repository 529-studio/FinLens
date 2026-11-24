# Implementation Plan — S11-05: Excel Add-in Scenario Comparison Waterfall Chart & PDF Grounding Export

## Phase 1: Types, Math & Exporter
- [ ] Step 1.1: Define TypeScript contracts in `apps/excel/src/types/waterfall.types.ts`:
  - `WaterfallDriverType`, `FinancialScenario`, `GroundingCitation`, `WaterfallStep`, `ScenarioDefinition`, `WaterfallExportReport`.
- [ ] Step 1.2: Implement `waterfallExporter.ts` in `apps/excel/src/lib/excel/waterfallExporter.ts`:
  - Mathematical step accumulator computation (`computeWaterfallSteps`).
  - Scenario variance generator (`applyScenarioToSteps`).
  - Standalone print-to-PDF / HTML report generator with visual citation footnotes.

## Phase 2: UI Component & Component Test Suite
- [ ] Step 2.1: Implement `WaterfallChart.tsx` in `apps/excel/src/components/WaterfallChart.tsx`:
  - Responsive SVG canvas with total pillars (slate/indigo), positive variance (emerald), negative variance (rose), connector lines.
  - Scenario switcher chips (Base, Bull, Bear) with `min-h-[48px]`.
  - PDF export button with `min-h-[48px]`.
  - 3 UI States: Skeleton pulse, Error state with retry (`min-h-[48px]`), Empty state.
  - Rule 15 Zero-Emoji compliance: 100% Lucide React SVG icons.
- [ ] Step 2.2: Author component unit tests in `apps/excel/src/components/__tests__/WaterfallChart.test.tsx`:
  - Test 3 UI states (Skeleton, Error, Empty).
  - Test scenario switching and recalculation.
  - Test kiosk ergonomics (`min-h-[48px]` on all buttons).
  - Test Rule 15 zero raw emojis.
  - Test PDF export execution.

## Phase 3: Verification, Knowledge Sync & Independent Audit
- [ ] Step 3.1: Run all test suites across the monorepo (`npm --prefix apps/excel test`, `npm --prefix apps/desktop test`, `pytest`).
- [ ] Step 3.2: Build verification: `npm --prefix apps/excel run build` compiles with 0 errors.
- [ ] Step 3.3: Verify Zero-Emoji compliance on all modified files.
- [ ] Step 3.4: Record Lesson 34 in `docs/lesson_learn.md` and sync via `npm run harvest:lessons`.
- [ ] Step 3.5: Update Lore memory.
- [ ] Step 3.6: Dispatch independent subagent auditor for code & UI/UX sign-off.
- [ ] Step 3.7: Open PR against `dev`, verify GitHub Actions CI passes green, and merge with merge commit.
