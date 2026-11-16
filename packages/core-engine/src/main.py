"""
FinSight Core Engine Local Daemon
Serves REST and WebSocket endpoints for Desktop App (Tauri v2) and Excel Add-in (Office.js).
Governed by ADR-001, ADR-004, and AGENTS.md Rule 13 (Security & Injection Defense).
"""

import re
import time
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Enforce relative path for .env (529 standard)
ENV_PATH = Path(__file__).resolve().parents[3] / ".env"
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)

from contracts import (
    DocumentIngestRequest,
    DocumentIngestResponse,
    QueryRequest,
    QueryResponse,
    GroundedEvidence,
    BoundingBox,
)
from renderer import PdfRenderer
from retriever import VisualRetriever
from vlm_router import VlmRouter

app = FastAPI(
    title="FinSight Visual Financial RAG Daemon",
    version="0.1.0",
    description="Local daemon serving visual search, VLM grounding, and financial analytics.",
)

# Enable CORS for localhost Tauri WebView and Excel Office.js
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

renderer = PdfRenderer()
retriever = VisualRetriever()
router = VlmRouter()


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "FinSight Core Daemon",
        "hardware_detected": router.detect_hardware_capability(),
        "timestamp": time.time(),
    }


@app.post("/api/v1/documents/ingest", response_model=DocumentIngestResponse)
async def ingest_document(req: DocumentIngestRequest):
    start_time = time.time()
    raw_id = req.document_id or Path(req.file_path).stem
    doc_id = re.sub(r"[^a-zA-Z0-9_\-]", "_", raw_id)[:64]

    try:
        pages = renderer.render_document(req.file_path, doc_id, dpi=req.render_dpi)
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Render error: {str(e)}")

    # Index into Visual Retriever
    indexed_count = retriever.index_document(doc_id, pages)

    duration_ms = (time.time() - start_time) * 1000.0

    return DocumentIngestResponse(
        document_id=doc_id,
        total_pages=len(pages),
        rendered_image_paths=[str(p[1]) for p in pages],
        indexed_vectors_count=indexed_count,
        duration_ms=round(duration_ms, 2),
    )


@app.post("/api/v1/query", response_model=QueryResponse)
async def query_financial_document(req: QueryRequest):
    start_time = time.time()

    # Step 1: Visual Late-Interaction candidate page retrieval
    candidate_pages = retriever.search(req.document_id, req.query_text, top_k=req.top_k_pages)
    primary_page = candidate_pages[0] if candidate_pages else 1

    # Step 2: VLM visual grounding and reasoning
    dummy_img_path = f"~/.finsight/cache/rendered_pages/{req.document_id}/page_{primary_page:04d}.png"
    vlm_result = await router.analyze_page(
        image_path=dummy_img_path,
        page_number=primary_page,
        query=req.query_text,
        preferred_mode=req.inference_mode,
    )

    evidences = [
        GroundedEvidence(
            page_number=e["page_number"],
            bounding_box=BoundingBox(
                ymin=e["ymin"],
                xmin=e["xmin"],
                ymax=e["ymax"],
                xmax=e["xmax"],
            ),
            label=e["label"],
            extracted_value=e.get("extracted_value"),
            confidence=e["confidence"],
        )
        for e in vlm_result.get("evidences", [])
    ]

    duration_ms = (time.time() - start_time) * 1000.0

    return QueryResponse(
        document_id=req.document_id,
        query_text=req.query_text,
        answer=vlm_result.get("answer", "Chưa có câu trả lời."),
        evidences=evidences,
        retrieved_page_numbers=candidate_pages,
        engine_used=vlm_result.get("engine", "unknown"),
        latency_ms=round(duration_ms, 2),
    )


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("FINSIGHT_DAEMON_HOST", "127.0.0.1")
    port = int(os.getenv("FINSIGHT_DAEMON_PORT", 8765))
    uvicorn.run("main:app", host=host, port=port, reload=True)
