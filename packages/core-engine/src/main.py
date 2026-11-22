"""
FinSight Core Engine Local Daemon
Serves REST and WebSocket endpoints for Desktop App (Tauri v2) and Excel Add-in (Office.js).
Governed by ADR-001, ADR-004, and AGENTS.md Rule 13 (Security & Injection Defense).
"""

import re
import time
import os
import json
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, status, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

logger = logging.getLogger("finsight.main")

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
    CloudStatusResponse,
    CloudProviderDetail,
    CloudKeyUpdateRequest,
    CloudKeyUpdateResponse,
    CacheStatsResponse,
    CacheClearRequest,
    ComparativeQueryRequest,
    ComparativeQueryResponse,
    FootnoteQueryRequest,
    FootnoteQueryResponse,
    FootnoteItem,
)
from renderer import PdfRenderer
from retriever import VisualRetriever
from vlm_router import VlmRouter
from cloud_router import CloudRouter
from store import StoreSecurityError
from cache_manager import cache_manager
from model_manager import (
    ModelManager,
    DEFAULT_MODEL_ID,
    UnconfirmedDownloadError,
    ModelSecurityError,
    ModelOfflineError,
)
from mlx_engine import MLXEngine

app = FastAPI(
    title="FinTrace Visual Financial RAG Daemon",
    version="1.0.0",
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
cloud_router = CloudRouter()
router = VlmRouter(mlx_engine=mlx_engine, cloud_router=cloud_router)


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "FinTrace Core Daemon",
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


@app.get("/api/v1/models/cloud/status", response_model=CloudStatusResponse)
def get_cloud_model_status():
    """Returns available and configured cloud providers (Rule 2: Zero-Leak)."""
    status_dict = cloud_router.get_provider_status()
    providers_detail = {
        p: CloudProviderDetail(
            configured=info["configured"],
            model=info["model"],
            api_base_configured=info.get("api_base_configured"),
        )
        for p, info in status_dict.items()
    }
    return CloudStatusResponse(
        available_providers=list(cloud_router.PROVIDER_MODELS.keys()),
        providers=providers_detail,
        default_model="claude-3-5-sonnet-20241022",
    )


@app.post("/api/v1/models/cloud/keys", response_model=CloudKeyUpdateResponse)
def update_cloud_key(req: CloudKeyUpdateRequest):
    """Updates cloud BYOK API key in memory session (Rule 2: Zero-Leak)."""
    try:
        cloud_router.set_api_key(req.provider, req.api_key, api_base=req.api_base)
        return CloudKeyUpdateResponse(
            provider=req.provider,
            status="configured",
            message=f"API key for provider '{req.provider}' successfully updated in session.",
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


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
    """Deletes all page vectors and metadata for a document from LanceDB and clears associated caches."""
    try:
        deleted = retriever.store.delete_document(doc_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Document '{doc_id}' not found")
        # Invalidate caches for this document
        cache_manager.clear(scope="all", document_id=doc_id)
        return {"document_id": doc_id, "deleted": True, "message": f"Document '{doc_id}' successfully removed"}
    except StoreSecurityError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


class ConnectionManager:
    """Manages active WebSocket connections and broadcasts IPC citation events between Excel and Desktop."""
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str, sender: WebSocket):
        for connection in list(self.active_connections):
            if connection != sender:
                try:
                    await connection.send_text(message)
                except Exception:
                    self.disconnect(connection)


ws_manager = ConnectionManager()

UPLOAD_DIR = Path("~/.finsight/uploads").expanduser().resolve()
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@app.post("/api/v1/documents/upload", response_model=DocumentIngestResponse)
async def upload_document(
    file: UploadFile = File(...),
    render_dpi: int = Form(150),
    document_id: Optional[str] = Form(None),
):
    start_time = time.time()

    # 1. Filename sanitization & path traversal check (Rule 13B)
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing filename in uploaded file")

    raw_filename = file.filename
    if ".." in raw_filename or "/" in raw_filename or "\\" in raw_filename or "\0" in raw_filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename: path traversal or invalid characters detected",
        )

    if not raw_filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must be a valid PDF format (.pdf)",
        )

    clean_stem = re.sub(r"[^a-zA-Z0-9_\-]", "_", Path(raw_filename).stem)[:64]
    if not clean_stem:
        clean_stem = f"doc_{int(time.time())}"
    sanitized_filename = f"{clean_stem}.pdf"

    target_path = (UPLOAD_DIR / sanitized_filename).resolve()
    if target_path.parent != UPLOAD_DIR:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid target path: traversal detected",
        )

    # 2. Magic byte check & safe streaming
    header = await file.read(1024)
    if not header:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty (0 bytes)")

    if not header.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must be a valid PDF format (missing %PDF- header)",
        )

    with open(target_path, "wb") as f_out:
        f_out.write(header)
        while True:
            chunk = await file.read(64 * 1024)
            if not chunk:
                break
            f_out.write(chunk)

    # 3. Determine doc_id & execute rendering and indexing
    raw_id = document_id or clean_stem
    doc_id = re.sub(r"[^a-zA-Z0-9_\-]", "_", raw_id)[:64]

    try:
        pages = renderer.render_document(str(target_path), doc_id, dpi=render_dpi)
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Render error: {str(e)}")

    indexed_count = retriever.index_document(doc_id, pages)
    cache_manager.query_cache.invalidate_document(doc_id)

    duration_ms = (time.time() - start_time) * 1000.0

    return DocumentIngestResponse(
        document_id=doc_id,
        total_pages=len(pages),
        rendered_image_paths=[str(p[1]) for p in pages],
        indexed_vectors_count=indexed_count,
        duration_ms=round(duration_ms, 2),
        from_cache=renderer.last_render_from_cache,
    )



@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Broadcast raw message payload (e.g. JSON citation event) to peer clients
            await ws_manager.broadcast(data, sender=websocket)
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)


@app.websocket("/ws/query/stream")
async def websocket_query_stream(websocket: WebSocket):
    """
    Real-time WebSocket streaming endpoint for progressive VLM token generation.
    Enforces strict path traversal defense (Rule 13B) and emits token/evidence/done events.
    """
    await websocket.accept()
    try:
        while True:
            raw_data = await websocket.receive_text()
            try:
                payload = json.loads(raw_data)
            except Exception:
                await websocket.send_text(json.dumps({"event": "error", "error": "Invalid JSON format"}))
                continue

            doc_id = payload.get("document_id")
            query_text = payload.get("query_text")
            mode = payload.get("inference_mode", "auto")

            # Path traversal & input security validation (Rule 13)
            if not doc_id or not re.match(r"^[a-zA-Z0-9_\-]+$", doc_id) or ".." in str(doc_id):
                await websocket.send_text(json.dumps({
                    "event": "error",
                    "error": "Access denied: Invalid or malicious document_id (path traversal rejected)"
                }))
                continue

            if not query_text or not isinstance(query_text, str) or not query_text.strip():
                await websocket.send_text(json.dumps({
                    "event": "error",
                    "error": "query_text must be a non-empty string"
                }))
                continue

            # Retrieve candidate pages
            candidate_pages = retriever.search(doc_id, query_text, top_k=2)
            if not candidate_pages:
                candidate_pages = [1]

            page_tuples = [
                (f"~/.finsight/cache/rendered_pages/{doc_id}/page_{p:04d}.png", p)
                for p in candidate_pages
            ]

            async for chunk in router.stream_analyze_pages(page_tuples, query_text, mode):
                await websocket.send_text(json.dumps(chunk))

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error("Error in streaming websocket: %s", e)
        try:
            await websocket.send_text(json.dumps({"event": "error", "error": str(e)}))
        except Exception:
            pass




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

    # Invalidate prior query cache entries for this document
    cache_manager.query_cache.invalidate_document(doc_id)

    duration_ms = (time.time() - start_time) * 1000.0

    return DocumentIngestResponse(
        document_id=doc_id,
        total_pages=len(pages),
        rendered_image_paths=[str(p[1]) for p in pages],
        indexed_vectors_count=indexed_count,
        duration_ms=round(duration_ms, 2),
        from_cache=renderer.last_render_from_cache,
    )


@app.post("/api/v1/query", response_model=QueryResponse)
async def query_financial_document(req: QueryRequest):
    start_time = time.time()

    # Fast LRU query cache lookup (reduces latency to < 5ms for repeated queries)
    cached_resp = cache_manager.query_cache.get(
        doc_id=req.document_id,
        query_text=req.query_text,
        top_k=req.top_k_pages,
        mode=req.inference_mode,
    )
    if cached_resp is not None:
        duration_ms = (time.time() - start_time) * 1000.0
        return QueryResponse(
            document_id=req.document_id,
            query_text=req.query_text,
            answer=cached_resp["answer"],
            evidences=cached_resp["evidences"],
            retrieved_page_numbers=cached_resp["retrieved_page_numbers"],
            engine_used=cached_resp["engine_used"],
            latency_ms=round(duration_ms, 2),
            cached=True,
        )

    # Step 1: Visual Late-Interaction candidate page retrieval (with multi-page evidence linkage)
    candidate_pages = retriever.search(req.document_id, req.query_text, top_k=req.top_k_pages)
    if not candidate_pages:
        candidate_pages = [1]

    # Step 2: Multi-page VLM visual grounding and cross-page reasoning
    page_tuples = [
        (f"~/.finsight/cache/rendered_pages/{req.document_id}/page_{p:04d}.png", p)
        for p in candidate_pages
    ]
    vlm_result = await router.analyze_pages(
        pages=page_tuples,
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

    # Cache response in memory LRU cache
    cache_manager.query_cache.put(
        doc_id=req.document_id,
        query_text=req.query_text,
        top_k=req.top_k_pages,
        mode=req.inference_mode,
        response_data={
            "answer": vlm_result.get("answer", "Chưa có câu trả lời."),
            "evidences": evidences,
            "retrieved_page_numbers": candidate_pages,
            "engine_used": vlm_result.get("engine", "unknown"),
        },
    )

    duration_ms = (time.time() - start_time) * 1000.0

    return QueryResponse(
        document_id=req.document_id,
        query_text=req.query_text,
        answer=vlm_result.get("answer", "Chưa có câu trả lời."),
        evidences=evidences,
        retrieved_page_numbers=candidate_pages,
        engine_used=vlm_result.get("engine", "unknown"),
        latency_ms=round(duration_ms, 2),
        cached=False,
    )


@app.post("/api/v1/query/comparative", response_model=ComparativeQueryResponse)
async def query_comparative_documents(req: ComparativeQueryRequest):
    """
    Executes cross-document comparative analysis across multiple fiscal statements (e.g. BCTC 2022 vs 2023).
    Extracts multi-index candidate pages, synthesizes YoY growth and margin shifts, and grounds evidence per document.
    """
    start_time = time.time()

    # 1. Verify all target documents exist in LanceDB store
    for doc_id in req.document_ids:
        pages = retriever.store.get_pages(doc_id)
        if not pages:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document '{doc_id}' not found in index. Please ingest it first."
            )

    # 2. Multi-Index Retrieval across all target document IDs
    retrieved_pages_map = retriever.comparative_search(
        req.document_ids,
        req.query_text,
        top_k_per_doc=req.top_k_per_doc
    )

    # 3. Assemble document pages mapping with image paths
    doc_pages: Dict[str, List[Tuple[str, int]]] = {}
    for doc_id, page_nums in retrieved_pages_map.items():
        stored_pages = retriever.store.get_pages(doc_id)
        page_dict = {p["page_number"]: p["image_path"] for p in stored_pages}
        doc_pages[doc_id] = []
        for p_num in page_nums:
            img_path = page_dict.get(p_num)
            if img_path:
                doc_pages[doc_id].append((img_path, p_num))

    # 4. Dispatch comparative visual inference to router
    try:
        vlm_res = await router.analyze_comparative(
            doc_pages=doc_pages,
            query=req.query_text,
            preferred_mode=req.inference_mode,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Comparative inference failed: {str(e)}")

    duration_ms = (time.time() - start_time) * 1000.0

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
            document_id=e.get("document_id"),
        )
        for e in vlm_res.get("evidences", [])
    ]

    return ComparativeQueryResponse(
        document_ids=req.document_ids,
        query_text=req.query_text,
        answer=vlm_res["answer"],
        comparative_metrics=vlm_res.get("comparative_metrics", []),
        evidences=evidences,
        retrieved_pages=retrieved_pages_map,
        engine_used=vlm_res["engine"],
        latency_ms=round(duration_ms, 2),
    )


@app.post("/api/v1/query/footnotes", response_model=FootnoteQueryResponse)
async def query_footnotes(req: FootnoteQueryRequest):
    """
    Extracts and disambiguates Thuyết minh BCTC citations for financial balance sheet items.
    Enforces strict path traversal defense (Rule 13B).
    """
    start_time = time.time()
    if not req.document_id or not re.match(r"^[a-zA-Z0-9_\-]+$", req.document_id) or ".." in req.document_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Access denied: Invalid or malicious document_id (path traversal rejected)"
        )

    raw_items = router.extract_footnotes(req.document_id, req.line_items)
    items = [
        FootnoteItem(
            line_item=it["line_item"],
            code=it.get("code"),
            footnote_number=it["footnote_number"],
            footnote_title=it["footnote_title"],
            summary=it["summary"],
            page_number=it["page_number"],
            bounding_box=BoundingBox(**it["bounding_box"])
        )
        for it in raw_items
    ]

    duration_ms = (time.time() - start_time) * 1000.0
    return FootnoteQueryResponse(
        document_id=req.document_id,
        total_footnotes=len(items),
        footnotes=items,
        elapsed_ms=round(duration_ms, 2)
    )





@app.get("/api/v1/cache/stats", response_model=CacheStatsResponse)
def get_cache_statistics():
    """Returns comprehensive cache metrics across memory query cache and disk render cache."""
    stats = cache_manager.get_stats()
    return CacheStatsResponse(**stats)


@app.post("/api/v1/cache/clear")
def clear_application_cache(req: Optional[CacheClearRequest] = None):
    """Clears query memory cache and/or disk rendered page cache."""
    scope = req.scope if req else "all"
    doc_id = req.document_id if req else None
    try:
        res = cache_manager.clear(scope=scope, document_id=doc_id)
        retriever.store.clear_memory_cache()
        return res
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("FINTRACE_DAEMON_HOST", os.getenv("FINSIGHT_DAEMON_HOST", "127.0.0.1"))
    port = int(os.getenv("FINTRACE_DAEMON_PORT", os.getenv("FINSIGHT_DAEMON_PORT", 8765)))
    uvicorn.run("main:app", host=host, port=port, reload=True)
