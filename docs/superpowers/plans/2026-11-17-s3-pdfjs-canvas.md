# S3-Canvas: PDF.js Interactive Canvas Implementation Plan

**Goal:** Integrate `pdfjs-dist` to render real PDF pages on a canvas, supporting interactive zoom, pan, and smooth scroll-to-evidence based on VLM bounding boxes.

**Architecture:**
- Use `pdfjs-dist` for high-fidelity PDF rendering.
- `PdfViewer.tsx` manages document loading and canvas orchestration.
- `usePdfViewer.hook.ts` handles canvas state (scale, scroll position, evidence focusing).

**Implementation Steps:**

- [ ] **Step 1: Install `pdfjs-dist` (verified in package.json)**
- [ ] **Step 2: Create `apps/desktop/src/components/pdf/PdfViewer.tsx`**
  - Implement canvas rendering, zoom/pan interaction.
- [ ] **Step 3: Wire into `SplitView.component.tsx`**
  - Replace simulation canvas with `PdfViewer`.
- [ ] **Step 4: Implement scroll-to-evidence logic**
  - Smooth scroll to normalized coordinates.
- [ ] **Step 5: E2E Verification & Audit**
  - Run Playwright, audit via subagent, merge.
