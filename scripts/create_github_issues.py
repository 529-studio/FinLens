#!/usr/bin/env python3
"""
Creates comprehensive GitHub issues for FinSight following 529 Engineering Standards.
Each issue includes Context, Technical Details, Out of Scope, and Definition of Done.
"""

import subprocess
import json

ISSUES = [
    {
        "title": "[architect] S1-01: Scaffolding Monorepo, ADRs, Lore Memory & 529 Standards Setup",
        "labels": ["sprint-1", "role:architect"],
        "body": """## Context
FinSight requires a robust, polyglot monorepo structure housing Tauri v2 Desktop (Rust + React 19), Python Visual RAG Engine, and Office.js Add-in with strict blackbox module boundaries.
Governed by `docs/PRD_ARCH_FINSIGHT.md` and ADR-001 through ADR-004.

## Depends on
None (Tier 0 foundation).

## Technical Details
- File paths to create/verify:
  - `apps/desktop/` (Tauri v2 + React 19)
  - `packages/core-engine/` (Python Visual RAG)
  - `packages/office-addin/` (Office.js Add-in)
  - `benchmarks/` (Test dataset & recall harness)
  - `docs/adr/` (ADR-001 to ADR-004)
  - `docs/lesson_learn.md` (Two-way sync hook to 529-engineering-skills)
  - `lore.ontology.yml` & `.agents/mcp_config.json`
- Interfaces & contracts:
  - Ingest foundational architectural claims into Lore.
  - Expose `package.json` workspace scripts: `dev:desktop`, `dev:engine`, `dev:addin`, `bench:recall`.

## Out of Scope
- Do not implement production UI styling or full Office.js cell writing logic here.
- Do not commit secrets or live API keys to `.env`.

## Definition of Done
- [ ] Monorepo workspace directories cleanly initialized.
- [ ] ADR-001 through ADR-004 approved and indexed in Lore.
- [ ] `lore status` reports 0 stale claims, valid ontology.
- [ ] `npm run harvest:lessons` executes successfully.
- [ ] PR created against `dev` with merge commit.
"""
    },
    {
        "title": "[qa-benchmark] S1-02: Curate Ground Truth Dataset of 10 Audited Financial Statements",
        "labels": ["sprint-1", "role:qa-benchmark"],
        "body": """## Context
To evaluate Visual RAG against text-based chunking, we need real-world audited financial reports (BCTC) containing complex charts (pie, waterfall, margin trends) and multi-column balance sheets.

## Depends on
S1-01 (Repository Scaffolding).

## Technical Details
- File paths:
  - `benchmarks/manifest.json`: Metadata catalog for 10 audited financial reports:
    1. Vinamilk (VNM) 2023 Audited
    2. Hoa Phat Group (HPG) 2023 Annual Report
    3. Vietcombank (VCB) 2023 Audited
    4. Apple Inc. (AAPL) 2023 10-K
    5. Microsoft (MSFT) 2023 10-K
    6. FPT Corporation 2023 Audited
    7. Mobile World Group (MWG) 2023 Audited
    8. Novaland (NVL) 2023 Reviewed
    9. Tesla Inc. (TSLA) 2023 10-K
    10. PV GAS (GAS) 2023 Audited
  - For each document, define 3 target queries focusing specifically on visual charts and footnotes.

## Out of Scope
- Do not download non-financial marketing brochures.
- Do not evaluate text-only PDF documents.

## Definition of Done
- [ ] `benchmarks/manifest.json` contains complete document metadata and challenge descriptions.
- [ ] Ground truth page numbers annotated for each visual challenge.
- [ ] PR created against `dev` with merge commit.
"""
    },
    {
        "title": "[rag-ml] S1-03: Implement High-Resolution PDF Page Renderer (PyMuPDF 150-200 DPI)",
        "labels": ["sprint-1", "role:rag-ml"],
        "body": """## Context
Visual RAG requires converting each PDF page into a high-fidelity PNG image (150-200 DPI) preserving all visual axes, legends, fonts, and table grids for ColPali patch indexing.

## Depends on
S1-01.

## Technical Details
- File paths:
  - `packages/core-engine/src/renderer.py`
  - `packages/core-engine/tests/test_renderer.py`
- Core Class: `PdfRenderer(output_base_dir: str)`
  - `render_document(pdf_path: str, document_id: str, dpi: int = 150) -> List[Tuple[int, Path, int, int]]`
  - Safe path handling via `Path.resolve()` conforming to `env-and-auth-ops-debugging`.
  - Matrix scaling: `zoom = dpi / 72.0; mat = fitz.Matrix(zoom, zoom)`.

## Out of Scope
- Do not run OCR (tesseract) or text stripping; keep raw PNGs intact.
- Do not upload rendered images to cloud S3; store in local cache `~/.finsight/cache`.

## Definition of Done
- [ ] `PdfRenderer` successfully renders multi-page PDF into PNG files.
- [ ] Unit tests pass verifying image dimensions and existence.
- [ ] Output resolution matches 150-200 DPI specification.
- [ ] PR created against `dev` with merge commit.
"""
    },
    {
        "title": "[rag-ml] S1-04: Build ColPali Visual Patch Retrieval & LanceDB Multi-Vector Store",
        "labels": ["sprint-1", "role:rag-ml"],
        "body": """## Context
ColPali processes document page images into multi-vector visual patch embeddings. LanceDB serves as our local, serverless vector database capable of indexing and querying ColPali embeddings via MaxSim late interaction.

## Depends on
S1-03 (PDF Renderer).

## Technical Details
- File paths:
  - `packages/core-engine/src/retriever.py`
  - `packages/core-engine/src/contracts.py`
- Integration:
  - `byaldi` / ColPali engine wrapping Vision-Transformer patch representations.
  - LanceDB table schema storing `(doc_id, page_number, multi_vector, image_path)`.
  - Retrieval method: `search(query: str, top_k: int = 2) -> List[SearchResult]`.

## Out of Scope
- Do not use cloud vector databases (Pinecone / Milvus).
- Do not chunk pages into text fragments.

## Definition of Done
- [ ] Visual multi-vector embeddings generated from rendered PNG pages.
- [ ] LanceDB indices created locally without external daemon dependency.
- [ ] Late interaction query executes in < 600ms on local machine.
- [ ] PR created against `dev` with merge commit.
"""
    },
    {
        "title": "[qa-benchmark] S1-05: Automated Benchmark Harness: ColPali vs Text-Chunking Recall",
        "labels": ["sprint-1", "role:qa-benchmark"],
        "body": """## Context
We must validate our core value proposition: that Visual RAG eliminates the "chart blindness" that cripples traditional text chunking RAG in financial reports.
Governed by `evidence-based-dod-and-llm-guardrails`.

## Depends on
S1-02, S1-04.

## Technical Details
- File paths:
  - `benchmarks/eval_retrieval.py`
  - `benchmarks/results/sprint1_report.md`
- Metrics evaluated:
  - Top-1 Retrieval Recall
  - Top-3 Retrieval Recall
  - Chart Blindness rate (Zero-data error rate on visual queries)
  - Average Query Latency (ms)

## Out of Scope
- Do not mock the benchmark output; execute actual queries against manifest.
- Do not accept assertions without terminal logs.

## Definition of Done
- [ ] `eval_retrieval.py` executes successfully.
- [ ] ColPali Top-1 Recall exceeds 85% (vs Text-Chunking < 40%).
- [ ] Chart blindness rate on visual charts is 0.0% for ColPali.
- [ ] Empirical report generated in `benchmarks/results/sprint1_report.md`.
- [ ] PR created against `dev` with merge commit.
"""
    },
    {
        "title": "[rag-ml] S1-06: Dual-Engine VLM Router & Normalized Bounding Box Coordinate Extraction",
        "labels": ["sprint-1", "role:rag-ml"],
        "body": """## Context
VLM must extract financial figures while providing exact bounding box coordinates `[ymin, xmin, ymax, xmax]` (scale 0-1000) for visual grounding.
Dual-Engine architecture: MLX local Qwen2.5-VL vs Cloud LiteLLM.
Governed by ADR-002 and ADR-003.

## Depends on
S1-03, S1-04.

## Technical Details
- File paths:
  - `packages/core-engine/src/vlm_router.py`
  - `packages/core-engine/src/contracts.py`
  - `packages/core-engine/src/main.py`
- Pydantic DTOs:
  - `BoundingBox`: `ymin, xmin, ymax, xmax` (0-1000 integer range).
  - `GroundedEvidence`: `page_number, bounding_box, label, extracted_value, confidence`.
  - `QueryResponse`: `document_id, query_text, answer, evidences, engine_used, latency_ms`.
- Router logic:
  - Detect Apple Silicon (`Darwin` + `arm`) -> default to `mlx-vlm`.
  - Cloud BYOK router via `litellm` (Claude 3.5 Sonnet / Azure OpenAI).

## Out of Scope
- Do not return un-normalized pixel coordinates.
- Do not hardcode API keys in source code (Zero-Leak).

## Definition of Done
- [ ] VLM outputs structured JSON conforming to `QueryResponse`.
- [ ] Bounding boxes accurately cover chart and table source regions.
- [ ] FastAPI daemon exposes `/api/v1/query` and `/health` endpoints.
- [ ] PR created against `dev` with merge commit.
"""
    },
    {
        "title": "[frontend] S1-07: Tauri v2 Desktop Scaffold & React 19 4-File Split-View Component",
        "labels": ["sprint-1", "role:frontend"],
        "body": """## Context
Desktop application shell using Tauri v2, React 19, TypeScript, and Tailwind CSS.
Enforces 529 Engineering Standard `frontend-4file-and-resilient-ui`:
DTO types -> Fetcher -> Custom hook -> SplitView component with 3 UI states.

## Depends on
S1-01, S1-06.

## Technical Details
- File paths:
  - `apps/desktop/src/types/visual_rag.types.ts`
  - `apps/desktop/src/api/visual_rag.fetch.ts`
  - `apps/desktop/src/hooks/useVisualRag.hook.ts`
  - `apps/desktop/src/components/layout/SplitView.component.tsx`
- Requirements:
  - 3 Mandatory UI States: Skeleton loading, Error with Retry, Empty State with Action.
  - Kiosk Ergonomics: Interactive touch targets >= 48px.
  - Visual Bounding Box SVG overlay rendered on top of PDF viewport.
  - Click-to-source interactive chip focusing evidence.

## Out of Scope
- Do not bundle heavy native PDF rendering in node_modules; use webview PDF.js or native canvas.
- Do not bypass fetcher error handling.

## Definition of Done
- [ ] 4-File pattern strictly implemented without cross-contamination.
- [ ] All 3 UI states visually verified.
- [ ] Touch/click targets meet >= 48px requirement.
- [ ] PR created against `dev` with merge commit.
"""
    },
    {
        "title": "[frontend] S2-01: Resizable Split-View Layout & Responsive Panes",
        "labels": ["sprint-2", "role:frontend"],
        "body": """## Context
Sprint 2 UI milestone: Financial analysts need a split-screen workspace with a draggable divider to adjust the proportion of the PDF viewer vs financial chat panel.

## Depends on
S1-07.

## Technical Details
- File paths:
  - `apps/desktop/src/components/layout/ResizableSplitView.tsx`
  - `apps/desktop/src/hooks/usePaneResize.ts`
- Behavior:
  - Default 50/50 split ratio, persisted in localStorage.
  - Min width 350px for each pane.
  - Smooth dragging with pointer events and divider styling.

## Out of Scope
- Do not implement multiple floating windows; single dual-pane split view only.

## Definition of Done
- [ ] Resizable divider allows smooth pane adjustment.
- [ ] Width persisted across desktop restarts.
- [ ] PR created against `dev` with merge commit.
"""
    },
    {
        "title": "[frontend] S2-03: Dynamic Canvas/SVG Bounding Box Overlay for Visual Grounding",
        "labels": ["sprint-2", "role:frontend"],
        "body": """## Context
When VLM returns coordinates `[ymin, xmin, ymax, xmax]` (0-1000 scale), the PDF viewer must draw an animated red highlight box `#EF4444` directly over the chart or table.

## Depends on
S1-06, S1-07.

## Technical Details
- File paths:
  - `apps/desktop/src/components/pdf/BoundingBoxOverlay.tsx`
  - `apps/desktop/src/utils/coordinate_math.ts`
- Coordinate scaling:
  - `top = (ymin / 1000) * renderedHeight`
  - `left = (xmin / 1000) * renderedWidth`
  - `height = ((ymax - ymin) / 1000) * renderedHeight`
  - `width = ((xmax - xmin) / 1000) * renderedWidth`
- Animation: 2.5s gentle pulse with red box shadow `0 0 15px rgba(239, 68, 68, 0.5)`.

## Out of Scope
- Do not mutate the underlying PDF binary; overlay is rendered strictly in the presentation layer.

## Definition of Done
- [ ] Bounding box overlays accurately at any zoom level or DPI.
- [ ] Pulse animation highlights source evidence clearly.
- [ ] PR created against `dev` with merge commit.
"""
    },
    {
        "title": "[rag-ml] S3-01: Local Apple Silicon MLX Qwen2.5-VL-7B 4-Bit Inference Engine",
        "labels": ["sprint-3", "role:rag-ml"],
        "body": """## Context
Provide complete offline privacy and zero API token cost for Mac users by embedding `mlx-vlm` running 4-bit quantized `Qwen2.5-VL-7B-Instruct`.

## Depends on
S1-06.

## Technical Details
- File paths:
  - `packages/core-engine/src/mlx_engine.py`
  - `packages/core-engine/src/model_manager.py`
- Quantization: 4-bit MLX weights.
- Memory ceiling: < 6GB unified memory consumption.
- Response latency target: < 5 seconds per financial page analysis on M2/M3/M4.

## Out of Scope
- Do not run 70B models locally on 16GB laptops.
- Do not download weights without user confirmation.

## Definition of Done
- [ ] `mlx_engine.py` executes 100% offline with Wi-Fi disabled.
- [ ] Memory consumption measured and logged below 6GB.
- [ ] PR created against `dev` with merge commit.
"""
    },
    {
        "title": "[excel] S4-01: Office.js Web Add-in Manifest & React Fluent UI Sidebar",
        "labels": ["sprint-4", "role:excel"],
        "body": """## Context
Phase 2 major capability: Excel Add-in allowing analysts to work directly inside Microsoft Excel (Windows, Mac, Web).

## Depends on
S1-06.

## Technical Details
- File paths:
  - `packages/office-addin/manifest.xml`
  - `packages/office-addin/src/taskpane.tsx`
  - `packages/office-addin/src/components/ExcelSidebar.tsx`
- Technology: Office.js + Fluent UI React v9.
- Connects to FinSight Core Daemon at `http://127.0.0.1:8765`.

## Out of Scope
- Do not support legacy VSTO / VBA add-ins; modern Office.js web add-in only.

## Definition of Done
- [ ] Add-in loads cleanly inside Excel desktop and web sidepane.
- [ ] Sidebar communicates with local daemon.
- [ ] PR created against `dev` with merge commit.
"""
    },
    {
        "title": "[excel] S4-03: 1-Click Financial Table Export & Auto Formula Generation",
        "labels": ["sprint-4", "role:excel"],
        "body": """## Context
Extract parsed financial tables and charts from PDF, inserting them into selected cells with native Excel formulas and Audit Trail comments.

## Depends on
S4-01.

## Technical Details
- File paths:
  - `packages/office-addin/src/taskpane.ts`
  - `packages/office-addin/src/formula_synthesizer.ts`
- Core operations:
  - `Excel.run(async (context) => { ... })`
  - `sheet.getRangeByIndexes(...)` writes 2D value matrix.
  - Header formatting: Bold, dark background `#1E293B`, white font.
  - Automatically append `=SUM(...)` or `=AVERAGE(...)` formula on total rows.
  - Insert Audit Trail comment pointing to source document ID and page number.

## Out of Scope
- Do not overwrite existing non-empty sheet cells without user prompt confirmation.

## Definition of Done
- [ ] 1-Click table export populates cells accurately.
- [ ] Formulas calculate correctly in Excel engine.
- [ ] Audit trail comment affixed to origin cell.
- [ ] PR created against `dev` with merge commit.
"""
    }
]

def main():
    print(f"Creating {len(ISSUES)} structured issues in 529-studio/Finsight...")
    for idx, issue in enumerate(ISSUES, 1):
        cmd = [
            "gh", "issue", "create",
            "--repo", "529-studio/Finsight",
            "--title", issue["title"],
            "--body", issue["body"],
        ]
        for label in issue.get("labels", []):
            cmd.extend(["--label", label])
        
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            print(f"  [{idx}/{len(ISSUES)}] Created: {issue['title']} -> {res.stdout.strip()}")
        else:
            print(f"  [{idx}/{len(ISSUES)}] Error: {res.stderr.strip()}")

if __name__ == "__main__":
    main()
