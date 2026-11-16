# S2 Handoff & Sprint 3 Horizon

**Document**: `docs/HANDOFF-s2.md`  
**Date**: 2026-11-16  
**Repository**: `529-studio/Finsight`  
**Charter**: Transition ledger documenting Sprint 2 completion state, delivered capabilities, settled architecture decisions, pitfalls, and next tasks for a fresh conversation.

---

## 1. Branch & Commit Status

- **Active branch**: `dev` (default development branch, protected, merge commit only)
- **Head commit**: `0bbd71c` (`Merge pull request #26 from 529-studio/feat/s2-zero-emoji-policy`)
- **Worktree**: Clean (all Sprint 2 features merged into `dev`)
- **Merged in this sprint**:
  - PR #21: `feat(desktop): Resizable Split-View Layout & Responsive Panes (#8)`
  - PR #22: `feat(desktop): Dynamic Canvas/SVG Bounding Box Overlay for Visual Grounding (#9)`
  - PR #23: `docs(agents): add Rule 14 for post-wave independent subagent audit and UI/UX quality gate`
  - PR #24: `feat(desktop): fix fullscreen viewport responsiveness and add monorepo Makefile`
  - PR #25: `fix(make): auto-clear ports before launching make dev`
  - PR #26: `docs(agents): add Rule 15 for zero-emoji UI policy and replace emojis with free SVG icons`

---

## 2. Merged Deliverables

| PR | Task | Subsystem | Delivered capability |
| :--- | :--- | :--- | :------------------- |
| **#21** | **S2-01** (#8) | `apps/desktop` | Resizable dual-pane layout (`ResizableSplitView.tsx`, `usePaneResize.ts`), clamped 350px min-width, localStorage persistence, 50/50 double-click reset, keyboard nav |
| **#22** | **S2-03** (#9) | `apps/desktop` | Dynamic SVG Bounding Box overlay (`BoundingBoxOverlay.tsx`, `coordinate_math.ts`), normalized [0, 1000] scaling, red #EF4444 drop-shadow glow, 2.5s pulse, top-clip avoidance |
| **#23** | **Rule 14** | `governance` | Enforced post-wave independent external subagent audit with dual-axis quality gate (correctness & user-friendly UI/UX) |
| **#24** | **Polish/Tooling**| `desktop/infra` | Fixed fullscreen flex shrinkage (100% 1920x1080 width), interactive zoom controls [60%, 180%], root monorepo Makefile with colorized help |
| **#25** | **Tooling** | `tooling` | Auto-clear lingering port listeners on :8765 and :5173 before launching `make dev` |
| **#26** | **Rule 15** | `governance/ui` | Zero-Emoji UI policy in AGENTS.md and substitution of raw emojis with Lucide React vector SVGs (`BarChart3`, `PieChart`) |

---

## 3. Open Issues & Backlog

- **Issue #10 ([rag-ml] S3-01: Local Apple Silicon MLX Qwen2.5-VL-7B 4-Bit Inference Engine)**: Open — Scheduled for Sprint 3.
- **Issue #11 ([excel] S4-01: Office.js Webpack Build & Excel Custom Function =FINSIGHT.QUERY())**: Open — Scheduled for Sprint 4.
- **Issue #12 ([excel] S4-03: 1-Click Financial Citation & Jump to Desktop Application)**: Open — Scheduled for Sprint 4.

All planned Sprint 2 frontend issues (#8, #9) are 100% completed and closed.

---

## 4. Settled Architectural Decisions

- **ADR-005 (Decoupled Visual Grounding Presentation Layer)**: Bounding box overlays are rendered strictly in presentation SVG/DOM layers above the PDF canvas; the underlying PDF binary remains 100% immutable and unaltered.
- **ADR-006 (Clamped Headless Resizing with Pointer Capture)**: Dual-pane proportion calculations are encapsulated in headless hook `usePaneResize`, using W3C pointer capture and global pointer cancel cleanup to prevent cursor detachment during rapid dragging.
- **Rule 14 (Post-Wave Quality Gate)**: Every milestone wave within a sprint must conclude with an independent external subagent audit evaluating both functional correctness and financial analyst usability.
- **Rule 15 (Zero-Emoji Enterprise Standard)**: UI presentation layers must strictly avoid raw Unicode emojis and mandate free-licensed vector SVGs (Lucide React / MIT).

---

## 5. Pitfalls Encountered

- **Flex Shrinkage on `#root`**: When `body` has `display: flex`, a child `#root` without explicit `flex: 1` and `width: 100%` will shrink-wrap to its content width (`1415px`), causing an empty void on wide displays. Always configure `html, body, #root { width: 100%; height: 100% }` and `#root { flex: 1 }`.
- **Division by Zero in Dynamic Layouts**: In unmounted, hidden, or zero-width containers, calculating split ratios via `pointerOffset / containerWidth` evaluates to `NaN` or `Infinity`, causing CSS `calc()` parsers to throw syntax errors. Always guard with `if (containerWidth <= 0) return;`.
- **Top-Edge Evidence Badge Clipping**: When a bounding box is positioned near the top of a page (`ymin < 28px`), an overlay badge positioned at `-top-6` clips outside the scroll container. The overlay must dynamically detect `top < 28px` and flip the badge inside (`top-1 left-1`).
- **Zsh Glob Qualifier Trap with Makefile Help**: Copy-pasting shell commands containing parentheses from Markdown tables (e.g. `make engine (:8765)`) triggers zsh glob qualifier errors (`zsh: no matches found: (:8765)`). Keep commands isolated in code blocks without inline parenthesis annotations.

---

## 6. Sprint 3 Horizon: next tasks

1. **Local Apple Silicon MLX Engine**: Implement `packages/core-engine/src/mlx_engine.py` loading 4-bit quantized `Qwen2.5-VL-7B-Instruct` under 6GB memory ceiling — `packages/core-engine/src/mlx_engine.py` (Issue #10)
2. **Model Manager & Weight Caching**: Implement `model_manager.py` with HuggingFace snapshot download confirmation, offline detection, and fallback routing — `packages/core-engine/src/model_manager.py` (Issue #10)
3. **LanceDB Multi-Vector Store**: Implement persistent disk storage at `~/.finsight/lancedb` for ColPali multi-vector page tensors — `packages/core-engine/src/store.py`
4. **Local ColPali Neural Embeddings**: Connect live `byaldi` or ColPali HuggingFace pipeline for real-time patch embedding computation — `packages/core-engine/src/retriever.py`
5. **Interactive PDF.js Canvas Integration**: Replace simulated PDF canvas with real `pdfjs-dist` page rendering supporting pan/zoom and smooth scroll to bounding box coordinates — `apps/desktop/src/components/canvas/PdfCanvas.component.tsx`
6. **Multi-Page Benchmark Stress Testing**: Ingest 20-100 page enterprise filings into `benchmarks/manifest.json` and stress-test recall — `benchmarks/`

---

## 7. Open Questions For The Human

1. **MLX Default Quantization vs Speed**: For Sprint 3 Issue #10, would you prefer 4-bit quantization (fastest, ~4.5GB RAM) or 8-bit quantization (higher OCR precision on dense footnotes, ~7.5GB RAM) as the default preset on 16GB+ Apple Silicon Macs?
2. **Local LanceDB Storage Location**: Should the local vector store default to `~/.finsight/lancedb/` (user home directory) or `data/cache/lancedb/` inside the repository directory?
