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
    ModelStatusResponse,
    ModelDownloadRequest,
    ModelDownloadResponse,
    StoreStatsResponse,
    DocumentListResponse,
)
from renderer import PdfRenderer
from retriever import VisualRetriever
from vlm_router import VlmRouter
from store import StoreSecurityError
from model_manager import (
    ModelManager,
    DEFAULT_MODEL_ID,
    UnconfirmedDownloadError,
    ModelSecurityError,
    ModelOfflineError,
)
from mlx_engine import MLXEngine

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
model_manager = ModelManager()
mlx_engine = MLXEngine(model_manager=model_manager)
router = VlmRouter(mlx_engine=mlx_engine)


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "FinSight Core Daemon",
        "hardware_detected": router.detect_hardware_capability(),
        "timestamp": time.time(),
    }


@app.get("/api/v1/models/mlx/status", response_model=ModelStatusResponse)
def get_mlx_model_status():
    """Returns local Apple Silicon MLX model status, caching state, and memory metrics."""
    info = model_manager.get_model_info(mlx_engine.model_id)
    mem = mlx_engine.get_memory_usage()
    hw = router.detect_hardware_capability()
    return ModelStatusResponse(
        model_id=info["model_id"],
        quantization=info["quantization"],
        estimated_size_gb=info["estimated_size_gb"],
        memory_ceiling_gb=info["memory_ceiling_gb"],
        is_cached=info["is_cached"],
        is_loaded=mlx_engine.is_loaded,
        cache_dir=info["cache_dir"],
        hardware_capability=hw,
        memory_usage=mem,
    )


@app.post("/api/v1/models/mlx/download", response_model=ModelDownloadResponse)
def download_mlx_model(req: ModelDownloadRequest):
    """
    Downloads MLX model weights into local cache.
    Requires explicit user confirmation (confirm=True) to prevent surprise downloads.
    """
    mid = req.model_id or mlx_engine.model_id
    try:
        target_path = model_manager.download_model(mid, confirmed=req.confirm)
        return ModelDownloadResponse(
            model_id=mid,
            status="cached" if model_manager.is_cached(mid) else "downloaded",
            cache_dir=str(target_path),
            message=f"Model '{mid}' is ready in local cache.",
        )
    except UnconfirmedDownloadError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except (ModelSecurityError, ValueError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ModelOfflineError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Download error: {str(e)}")


@app.get("/api/v1/store/stats", response_model=StoreStatsResponse)
def get_store_stats():
    """Returns disk footprint and record counts for persistent LanceDB store."""
    stats = retriever.store.get_stats()
    return StoreStatsResponse(**stats)


@app.get("/api/v1/documents", response_model=DocumentListResponse)
def list_indexed_documents():
    """Lists all indexed documents currently persisted in LanceDB."""
    docs = retriever.store.list_documents()
    return DocumentListResponse(documents=docs, total=len(docs))


@app.delete("/api/v1/documents/{doc_id}")
def delete_indexed_document(doc_id: str):
    """Deletes all page vectors and metadata for a document from LanceDB."""
    try:
        deleted = retriever.store.delete_document(doc_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Document '{doc_id}' not found")
        return {"document_id": doc_id, "deleted": True, "message": f"Document '{doc_id}' successfully removed"}
    except StoreSecurityError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))




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
