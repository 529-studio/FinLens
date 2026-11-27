"""
FinSight Core Engine Local Daemon
Serves REST and WebSocket endpoints for Desktop App (Tauri v2) and Excel Add-in (Office.js).
Governed by ADR-001, ADR-004, and AGENTS.md Rule 13 (Security & Injection Defense).
"""

import re
import time
import os
import json
import uuid
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, status, UploadFile, File, Form, Depends, Query, Path as PathParam
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
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
    TableStitchRequest,
    TableStitchResponse,
    PortfolioSynthesisRequest,
    PortfolioSynthesisResponse,
    FinancialRatioRequest,
    FinancialRatioResponse,
    CreateSessionRequest,
    SessionEventType,
    LicenseActivationRequest,
    LicenseActivationResponse,
    LicenseStatusResponse,
    DiscrepancyAuditRequest,
    DiscrepancyAuditResponse,
    AuditPackageRequest,
    AuditPackageResponse,
    TenantWorkspaceCreateRequest,
    TenantWorkspaceResponse,
    TenantAccessVerificationRequest,
    TenantAccessVerificationResponse,
    DocumentInfoResponse,
    PeerBenchmarkRequest,
    PeerBenchmarkResponse,
    CashFlowReconcileRequest,
    CashFlowReconcileResponse,
    RBACPolicyEvaluateRequest,
    RBACPolicyEvaluateResponse,
    RBACPoliciesListResponse,
    is_path_safe,
)
from table_stitcher import TableStitcher
from comparative_query import PortfolioSynthesisEngine
from ratio_engine import FinancialRatioEngine
from peer_benchmark import PeerBenchmarkEngine
from cashflow_reconciler import CashFlowReconciler
from rbac_policy import HierarchicalRBACEngine
from discrepancy_detector import DiscrepancyDetector
from audit_packager import AuditPackager
from workspace_security import WorkspaceSecurityManager
from session_sync import AuditSessionManager
from licensing import LicenseManager
from auth import (
    Role,
    Permission,
    User,
    LoginRequest,
    LoginResponse,
    create_access_token,
    decode_access_token,
    RBAC_ENABLED,
    get_current_user,
    require_permission,
    require_role,
    ROLE_PERMISSIONS,
)
from audit_logger import audit_logger, AuditEvent
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
portfolio_engine = PortfolioSynthesisEngine(store=retriever.store, retriever=retriever, router=router)
ratio_engine = FinancialRatioEngine(store=retriever.store, retriever=retriever, router=router)
peer_benchmark_engine = PeerBenchmarkEngine()
cashflow_reconciler = CashFlowReconciler()
rbac_engine = HierarchicalRBACEngine()
discrepancy_detector = DiscrepancyDetector(retriever=retriever)
audit_packager = AuditPackager(retriever=retriever)
workspace_manager = WorkspaceSecurityManager()
audit_session_manager = AuditSessionManager()
license_manager = LicenseManager()


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "FinTrace Core Daemon",
        "hardware_detected": router.detect_hardware_capability(),
        "timestamp": time.time(),
    }


# ============================================================================
# Enterprise RBAC & Cryptographic Audit Endpoints (ADR-006, Task S10-03)
# ============================================================================

@app.post("/api/v1/auth/login", response_model=LoginResponse)
def login_user(req: LoginRequest):
    """
    Authenticates a user against salted PBKDF2-HMAC-SHA256 credential store (fail-closed)
    and issues an enterprise HS256 JWT access token.
    """
    ok, resolved_role, reason = rbac_engine.authenticate(
        username=req.username,
        password=req.password,
        requested_role=req.role,
    )
    if not ok or resolved_role is None:
        audit_logger.log_event(
            user_id=req.username,
            role="unauthenticated",
            action="AUTH_LOGIN_FAILED",
            details={"reason": reason},
        )
        if reason == "privilege_escalation_denied":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: requested role exceeds assigned privilege level",
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials: username or password rejected",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_role = resolved_role
    token = create_access_token(user_id=req.username, role=user_role, name=req.username.title())
    user = User(
        user_id=req.username,
        role=user_role,
        name=req.username.title(),
        permissions=set(ROLE_PERMISSIONS.get(user_role, set())),
    )

    audit_logger.log_event(
        user_id=req.username,
        role=user_role.value,
        action="AUTH_LOGIN_SUCCESS",
        details={"org": user.org},
    )

    return LoginResponse(
        access_token=token,
        token_type="Bearer",
        expires_in_seconds=28800,
        user=user,
    )


@app.post("/api/v1/rbac/evaluate", response_model=RBACPolicyEvaluateResponse)
def evaluate_rbac_policy(
    req: RBACPolicyEvaluateRequest,
    user: User = Depends(require_permission(Permission.DOC_READ)),
):
    """
    Evaluates hierarchical RBAC permissions and explicit ALLOW/DENY policies
    (with deny-takes-precedence) for a target role, permission, and resource scope.
    """
    try:
        res = rbac_engine.evaluate(req)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    audit_logger.log_event(
        user_id=user.user_id,
        role=user.role.value,
        action="RBAC_POLICY_EVALUATE",
        details={
            "target_role": req.role,
            "permission": req.permission,
            "resource": req.resource,
            "allowed": res.allowed,
        },
    )
    return res


@app.get("/api/v1/rbac/policies", response_model=RBACPoliciesListResponse)
def list_rbac_policies(
    user: User = Depends(require_permission(Permission.AUDIT_READ)),
):
    """Lists active scoped RBAC policies and inherited role permission hierarchy."""
    audit_logger.log_event(
        user_id=user.user_id,
        role=user.role.value,
        action="RBAC_POLICIES_LIST",
        details={},
    )
    return rbac_engine.list_policies()


@app.get("/api/v1/auth/me", response_model=User)
def get_user_profile(user: User = Depends(get_current_user)):
    """Returns active user identity, role, and granted permissions."""
    return user


@app.get("/api/v1/audit/events")
def list_audit_events(
    limit: int = 50,
    offset: int = 0,
    action: Optional[str] = None,
    user_id: Optional[str] = None,
    document_id: Optional[str] = None,
    user: User = Depends(require_permission(Permission.AUDIT_READ)),
):
    """Lists tamper-evident audit records. Requires AUDIT_READ permission."""
    events, total = audit_logger.get_events(
        limit=limit,
        offset=offset,
        action=action,
        user_id=user_id,
        document_id=document_id,
    )
    return {"events": [e.model_dump() for e in events], "total": total}


@app.get("/api/v1/audit/verify")
def verify_audit_log_chain(user: User = Depends(require_permission(Permission.AUDIT_READ))):
    """
    Cryptographically verifies the entire SHA-256 event chain from Genesis.
    Fails closed if any historical record was altered or tampered with.
    """
    is_valid, count, err = audit_logger.verify_chain()
    return {
        "valid": is_valid,
        "total_records": count,
        "error": err,
        "status": "[PASS] VERIFIED" if is_valid else "[FAIL] TAMPERED",
    }


@app.post("/api/v1/audit/export")
def export_compliance_audit_log(
    destination_path: Optional[str] = None,
    user: User = Depends(require_permission(Permission.AUDIT_READ)),
):
    """Exports cryptographic audit logs for banking regulatory compliance."""
    target_p = None
    if destination_path:
        from contracts import is_path_safe
        if not is_path_safe(destination_path):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Access denied: Destination path outside authorized boundaries",
            )
        target_p = Path(destination_path)

    exported = audit_logger.export_events(target_p)
    audit_logger.log_event(
        user_id=user.user_id,
        role=user.role.value,
        action="AUDIT_EXPORT",
        details={"export_path": str(exported)},
    )
    return {
        "status": "SUCCESS",
        "export_path": str(exported),
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
def download_mlx_model(req: ModelDownloadRequest, user: User = Depends(require_permission(Permission.ADMIN_CONFIG))):
    """
    Downloads MLX model weights into local cache.
    Requires explicit user confirmation (confirm=True) to prevent surprise downloads.
    """
    mid = req.model_id or mlx_engine.model_id
    try:
        target_path = model_manager.download_model(mid, confirmed=req.confirm)
        audit_logger.log_event(
            user_id=user.user_id,
            role=user.role.value,
            action="ADMIN_CONFIG",
            details={"action": "model_download", "model_id": mid},
        )
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


def _resolve_safe_doc_dir(doc_id: str) -> Path:
    """Validates doc_id strictly and resolves its rendered page cache directory."""
    if not doc_id or "\0" in doc_id or ".." in doc_id or not re.match(r"^[a-zA-Z0-9_\-]+$", doc_id) or len(doc_id) > 64:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid document_id: must be alphanumeric with '_' or '-' (<= 64 chars)",
        )
    base_dir = renderer.output_base_dir.resolve()
    doc_dir = (base_dir / doc_id).resolve()
    if doc_dir.parent != base_dir:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Access denied: document_id escapes rendered cache directory",
        )
    return doc_dir


@app.get("/api/v1/documents/{doc_id}/info", response_model=DocumentInfoResponse)
def get_document_info(doc_id: str, user: User = Depends(require_permission(Permission.DOC_READ))):
    """Returns total page count and available rendered page numbers for a document."""
    doc_dir = _resolve_safe_doc_dir(doc_id)
    page_nums = set()

    if doc_dir.exists() and doc_dir.is_dir():
        for png in doc_dir.glob("page_*.png"):
            match = re.match(r"^page_(\d+)\.png$", png.name)
            if match:
                page_nums.add(int(match.group(1)))

    try:
        stored_pages = retriever.store.get_pages(doc_id)
        for p in stored_pages:
            pnum = int(p.get("page_number", 0))
            if pnum >= 1:
                page_nums.add(pnum)
    except Exception:
        pass

    if not page_nums:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{doc_id}' not found",
        )

    sorted_pages = sorted(page_nums)
    return DocumentInfoResponse(
        document_id=doc_id,
        total_pages=max(len(sorted_pages), sorted_pages[-1]),
        available_pages=sorted_pages,
    )


@app.get("/api/v1/documents/{doc_id}/pages/{page_number}")
def get_document_page_image(
    doc_id: str,
    page_number: int = PathParam(..., ge=1, le=5000),
    user: User = Depends(require_permission(Permission.DOC_READ)),
):
    """Serves the rendered PNG image for a specific document page with path traversal defense."""
    doc_dir = _resolve_safe_doc_dir(doc_id)
    candidate = (doc_dir / f"page_{page_number:04d}.png").resolve()
    if candidate.parent != doc_dir:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Access denied: invalid page path",
        )

    if not candidate.is_file():
        # Check stored page image_path if indexed from an approved benchmark/cache directory
        try:
            stored_pages = retriever.store.get_pages(doc_id)
            for p in stored_pages:
                if int(p.get("page_number", 0)) == page_number and p.get("image_path"):
                    alt_path = Path(str(p["image_path"])).expanduser().resolve()
                    if is_path_safe(str(alt_path)) and alt_path.is_file():
                        candidate = alt_path
                        break
        except Exception:
            pass

    if not candidate.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rendered page {page_number} for document '{doc_id}' not found",
        )

    return FileResponse(
        path=str(candidate),
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=300"},
    )


@app.delete("/api/v1/documents/{doc_id}")
def delete_indexed_document(doc_id: str, user: User = Depends(require_permission(Permission.DOC_DELETE))):
    """Deletes all page vectors and metadata for a document from LanceDB and clears associated caches."""
    try:
        deleted = retriever.store.delete_document(doc_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Document '{doc_id}' not found")
        # Invalidate caches for this document
        cache_manager.clear(scope="all", document_id=doc_id)
        audit_logger.log_event(
            user_id=user.user_id,
            role=user.role.value,
            action="DOC_DELETE",
            document_id=doc_id,
        )
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
    user: User = Depends(require_permission(Permission.DOC_INGEST)),
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

            async for chunk in router.stream_analyze_pages(page_tuples, query_text, mode, document_id=doc_id):
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
async def ingest_document(req: DocumentIngestRequest, user: User = Depends(require_permission(Permission.DOC_INGEST))):
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
async def query_financial_document(req: QueryRequest, user: User = Depends(require_permission(Permission.DOC_READ))):
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

    raw_footnotes = router.extract_footnotes(req.document_id, [req.query_text])
    extracted_footnotes = [
        FootnoteItem(
            line_item=f["line_item"],
            code=f.get("code"),
            footnote_number=f["footnote_number"],
            footnote_title=f["footnote_title"],
            summary=f["summary"],
            page_number=f["page_number"],
            bounding_box=BoundingBox(**f["bounding_box"]),
        )
        for f in raw_footnotes
    ]

    return QueryResponse(
        document_id=req.document_id,
        query_text=req.query_text,
        answer=vlm_result.get("answer", "Chưa có câu trả lời."),
        evidences=evidences,
        footnotes=extracted_footnotes,
        retrieved_page_numbers=candidate_pages,
        engine_used=vlm_result.get("engine", "unknown"),
        latency_ms=round(duration_ms, 2),
        cached=False,
    )


@app.post("/api/v1/query/comparative", response_model=ComparativeQueryResponse)
async def query_comparative_documents(req: ComparativeQueryRequest, user: User = Depends(require_permission(Permission.DOC_READ))):
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


@app.post("/api/v1/portfolio/synthesize", response_model=PortfolioSynthesisResponse)
async def synthesize_portfolio_endpoint(
    req: PortfolioSynthesisRequest,
    user: User = Depends(require_permission(Permission.DOC_READ)),
):
    """
    Synthesizes multi-document financial portfolios, calculating YoY growth, CAGR, margin trajectories,
    and peer group rankings while preserving 100% visual grounding citations.
    Enforces path traversal defense and enterprise RBAC authorization.
    """
    for target in req.documents:
        if not re.match(r"^[a-zA-Z0-9_\-]+$", target.document_id) or ".." in target.document_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Access denied: Invalid or malicious document_id '{target.document_id}' (path traversal rejected)",
            )
        pages = retriever.store.get_pages(target.document_id)
        if not pages:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document '{target.document_id}' not found in index. Please ingest it first.",
            )

    try:
        return await portfolio_engine.synthesize(req)
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Portfolio synthesis failed: {str(e)}",
        )


@app.post("/api/v1/analysis/ratios", response_model=FinancialRatioResponse)
async def analyze_financial_ratios_endpoint(
    req: FinancialRatioRequest,
    user: User = Depends(require_permission(Permission.DOC_READ)),
):
    """
    Computes 14 standard financial ratios, 3-stage DuPont decomposition, and cash flow health grading.
    Enforces path traversal defense and enterprise RBAC authorization.
    """
    if not re.match(r"^[a-zA-Z0-9_\-]+$", req.document_id) or ".." in req.document_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Access denied: Invalid or malicious document_id '{req.document_id}' (path traversal rejected)",
        )
    pages = retriever.store.get_pages(req.document_id)
    if not pages:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{req.document_id}' not found in index. Please ingest it first.",
        )

    try:
        return await ratio_engine.analyze(req)
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Financial ratio analysis failed: {str(e)}",
        )


@app.post("/api/v1/analysis/peer-benchmark", response_model=PeerBenchmarkResponse)
def peer_benchmark_endpoint(
    req: PeerBenchmarkRequest,
    user: User = Depends(require_permission(Permission.DOC_READ)),
):
    """
    Executes cross-sectional industry peer benchmarking with equal-weighted and
    market-cap weighted averages, linear percentiles (P10-P90), and z-scores.
    """
    res = peer_benchmark_engine.evaluate(req)
    audit_logger.log_event(
        user_id=user.user_id,
        role=user.role.value,
        action="PEER_BENCHMARK",
        document_id=req.target_document_id,
        details={"sector": req.sector_name, "weighting_mode": req.weighting_mode.value},
    )
    return res


@app.post("/api/v1/analysis/cashflow-reconcile", response_model=CashFlowReconcileResponse)
def cashflow_reconcile_endpoint(
    req: CashFlowReconcileRequest,
    user: User = Depends(require_permission(Permission.DOC_READ)),
):
    """
    Reconciles Direct Method Operating Cash Flow (CFO) against Indirect Method derivation
    with working capital sign handling, materiality classification, and [0, 1000] visual grounding.
    """
    try:
        res = cashflow_reconciler.reconcile(req)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    audit_logger.log_event(
        user_id=user.user_id,
        role=user.role.value,
        action="CASHFLOW_RECONCILE",
        document_id=req.document_id,
        details={"period": req.period_label, "status": res.status.value, "variance": res.reconciliation_variance},
    )
    return res


@app.post("/api/v1/audit/discrepancies", response_model=DiscrepancyAuditResponse)
async def audit_discrepancies_endpoint(
    req: DiscrepancyAuditRequest,
    user: User = Depends(require_permission(Permission.DOC_READ)),
):
    """
    Automated multi-document anomaly & discrepancy detection engine.
    Audits cross-filing restatements, accounting equation balance identities,
    profit & loss calculation consistency, segment consolidation gaps, and unexpected YoY variances.
    Enforces path traversal defense and enterprise RBAC authorization.
    """
    for target in req.documents:
        if not re.match(r"^[a-zA-Z0-9_\-]+$", target.document_id) or ".." in target.document_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Access denied: Invalid or malicious document_id '{target.document_id}' (path traversal rejected)",
            )
        pages = retriever.store.get_pages(target.document_id)
        if not pages:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document '{target.document_id}' not found in index. Please ingest it first.",
            )

    try:
        return await discrepancy_detector.audit(req)
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Discrepancy audit failed: {str(e)}",
        )


@app.post("/api/v1/audit/export-package", response_model=AuditPackageResponse)
async def export_audit_package_endpoint(
    req: AuditPackageRequest,
    user: User = Depends(require_permission(Permission.DOC_READ)),
):
    """
    Automated Audit Trail Exporter & Regulatory Package Generator.
    Produces standardized Inline XBRL (iXBRL), archival PDF/A-3 containers with embedded
    machine-readable metadata, or full ZIP compliance bundles with SHA-256 tamper-evident event chains.
    Enforces path traversal defense and enterprise RBAC authorization.
    """
    for target in req.documents:
        if not re.match(r"^[a-zA-Z0-9_\-]+$", target.document_id) or ".." in target.document_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Access denied: Invalid or malicious document_id '{target.document_id}' (path traversal rejected)",
            )
        pages = retriever.store.get_pages(target.document_id)
        if not pages:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document '{target.document_id}' not found in index. Please ingest it first.",
            )

    try:
        return await audit_packager.export_package(req)
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Regulatory audit package generation failed: {str(e)}",
        )


@app.post("/api/v1/workspaces/create", response_model=TenantWorkspaceResponse)
def create_workspace_endpoint(
    req: TenantWorkspaceCreateRequest,
    user: User = Depends(require_permission(Permission.DOC_READ)),
):
    """
    Provisions an isolated multi-tenant workspace with restricted 0o700 permissions
    and AES-256-GCM authenticated encryption at rest.
    Enforces path traversal defense and enterprise RBAC authorization.
    """
    if not re.match(r"^[a-zA-Z0-9_\-]+$", req.workspace_id) or ".." in req.workspace_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Access denied: Invalid or malicious workspace_id '{req.workspace_id}' (path traversal rejected)",
        )
    try:
        return workspace_manager.create_workspace(req)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to provision workspace: {str(e)}",
        )


@app.get("/api/v1/workspaces/{workspace_id}/status", response_model=TenantWorkspaceResponse)
def get_workspace_status_endpoint(
    workspace_id: str,
    user: User = Depends(require_permission(Permission.DOC_READ)),
):
    """
    Retrieves tenant workspace isolation metadata and non-reversible key fingerprint.
    Enforces path traversal defense.
    """
    if not re.match(r"^[a-zA-Z0-9_\-]+$", workspace_id) or ".." in workspace_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Access denied: Invalid or malicious workspace_id '{workspace_id}'",
        )
    status_resp = workspace_manager.get_workspace_status(workspace_id)
    if not status_resp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace '{workspace_id}' not found",
        )
    return status_resp


@app.post("/api/v1/workspaces/{workspace_id}/verify-access", response_model=TenantAccessVerificationResponse)
def verify_workspace_access_endpoint(
    workspace_id: str,
    req: TenantAccessVerificationRequest,
    user: User = Depends(require_permission(Permission.DOC_READ)),
):
    """
    Validates that a requested document resides strictly within tenant workspace boundaries.
    Prevents cross-tenant document and vector retrieval leakage.
    """
    if not re.match(r"^[a-zA-Z0-9_\-]+$", workspace_id) or ".." in workspace_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Access denied: Invalid or malicious workspace_id '{workspace_id}'",
        )
    is_allowed = workspace_manager.verify_tenant_access(workspace_id, req.requested_document_id)
    return TenantAccessVerificationResponse(
        workspace_id=workspace_id,
        requested_document_id=req.requested_document_id,
        allowed=is_allowed,
        reason="Access granted within tenant boundary" if is_allowed else "Cross-tenant access denied: Document is isolated to another workspace",
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





@app.post("/api/v1/table/stitch", response_model=TableStitchResponse)
async def stitch_table(request: TableStitchRequest, user: User = Depends(require_permission(Permission.TABLE_STITCH))):
    """
    Stitches multi-page table fragments into a unified MultiPageTableDTO.
    Maintains cross-page coordinate grounding and aligns shifted columns.
    """
    t0 = time.perf_counter()
    stitcher = TableStitcher()
    try:
        stitched = stitcher.stitch(request)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        audit_logger.log_event(
            user_id=user.user_id,
            role=user.role.value,
            action="TABLE_STITCH",
            document_id=request.document_id,
            details={"pages": stitched.spanned_pages, "rows": stitched.total_rows},
        )
        return TableStitchResponse(
            document_id=request.document_id,
            table=stitched,
            elapsed_ms=round(elapsed_ms, 2),
        )
    except Exception as e:
        logger.error(f"Table stitching failed: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Table stitching failed: {str(e)}")


@app.get("/api/v1/cache/stats", response_model=CacheStatsResponse)
def get_cache_statistics():
    """Returns comprehensive cache metrics across memory query cache and disk render cache."""
    stats = cache_manager.get_stats()
    return CacheStatsResponse(**stats)


@app.post("/api/v1/cache/clear")
def clear_application_cache(req: Optional[CacheClearRequest] = None, user: User = Depends(require_permission(Permission.ADMIN_CONFIG))):
    """Clears query memory cache and/or disk rendered page cache."""
    scope = req.scope if req else "all"
    doc_id = req.document_id if req else None
    try:
        res = cache_manager.clear(scope=scope, document_id=doc_id)
        retriever.store.clear_memory_cache()
        audit_logger.log_event(
            user_id=user.user_id,
            role=user.role.value,
            action="ADMIN_CONFIG",
            details={"action": "cache_clear", "scope": scope, "document_id": doc_id},
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============================================================================
# Real-Time Collaborative Audit Session Sync Endpoints (Task S11-03)
# ============================================================================

@app.post("/api/v1/sessions")
async def create_or_init_session(
    req: CreateSessionRequest,
    user: User = Depends(require_permission(Permission.DOC_READ)),
):
    """Initializes or retrieves an active collaborative audit session room."""
    try:
        session = await audit_session_manager.get_or_create_session(req.session_id, req.document_id)
        audit_logger.log_event(
            user_id=user.user_id,
            role=user.role.value,
            action="SESSION_CREATE",
            document_id=req.document_id,
            details={"session_id": req.session_id},
        )
        return {
            "session_id": session.session_id,
            "document_id": session.document_id,
            "created_at": session.created_at,
            "active_users_count": len(session.active_users),
            "annotations_count": len(session.annotations),
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@app.get("/api/v1/sessions/{session_id}")
def get_session_details(
    session_id: str,
    user: User = Depends(require_permission(Permission.DOC_READ)),
):
    """Retrieves metadata, active auditors, and visual annotations for a session."""
    try:
        clean_sid = AuditSessionManager.validate_session_id(session_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    snapshot = audit_session_manager.get_session_snapshot(clean_sid)
    if not snapshot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Session '{clean_sid}' not found")
    return snapshot


@app.websocket("/ws/v1/sessions/{session_id}")
async def websocket_session_sync(
    websocket: WebSocket,
    session_id: str,
    token: Optional[str] = Query(None),
    document_id: Optional[str] = Query(None),
    active_page: int = Query(1),
):
    """
    Real-time WebSocket endpoint for multi-auditor presence and spatial annotation sync.
    Enforces JWT authentication and strict session_id sanitization.
    """
    try:
        clean_sid = AuditSessionManager.validate_session_id(session_id)
    except ValueError as e:
        await websocket.close(code=1008, reason=str(e))
        return

    # Authenticate user from query token
    auth_user: Optional[User] = None
    if token:
        try:
            auth_user = decode_access_token(token)
        except Exception:
            await websocket.close(code=1008, reason="Invalid authentication token")
            return
    elif RBAC_ENABLED:
        await websocket.close(code=1008, reason="Authentication token required when RBAC is enabled")
        return
    else:
        # Default unauthenticated auditor in development mode
        anon_id = f"auditor_{uuid.uuid4().hex[:6]}"
        auth_user = User(
            user_id=anon_id,
            role=Role.JUNIOR_ANALYST,
            name="FinTrace Auditor",
            permissions=set(ROLE_PERMISSIONS.get(Role.JUNIOR_ANALYST, set())),
        )

    await websocket.accept()

    doc_id = document_id or "default_filing"
    try:
        clean_doc_id = AuditSessionManager.validate_document_id(doc_id)
    except ValueError:
        clean_doc_id = "default_filing"

    session = await audit_session_manager.register_connection(
        session_id=clean_sid,
        document_id=clean_doc_id,
        websocket=websocket,
        user_id=auth_user.user_id,
        name=auth_user.name,
        role=auth_user.role.value if hasattr(auth_user.role, "value") else str(auth_user.role),
        active_page=active_page,
    )

    # 1. Send authoritative snapshot to newly connected client
    snapshot_payload = {
        "event": SessionEventType.SESSION_STATE.value,
        "session_id": clean_sid,
        "payload": session.model_dump(),
        "timestamp": time.time(),
    }
    await websocket.send_text(json.dumps(snapshot_payload))

    # 2. Broadcast JOIN presence to existing peers
    join_payload = {
        "event": SessionEventType.JOIN.value,
        "session_id": clean_sid,
        "user_id": auth_user.user_id,
        "payload": session.active_users[auth_user.user_id].model_dump(),
        "timestamp": time.time(),
    }
    await audit_session_manager.broadcast(clean_sid, join_payload, exclude=websocket)

    try:
        while True:
            raw_text = await websocket.receive_text()
            response_or_broadcast = await audit_session_manager.handle_message(websocket, raw_text)
            if response_or_broadcast:
                event_type = response_or_broadcast.get("event")
                if event_type in (SessionEventType.HEARTBEAT.value, SessionEventType.ERROR.value):
                    await websocket.send_text(json.dumps(response_or_broadcast))
                elif event_type in (SessionEventType.PRESENCE.value, SessionEventType.CURSOR_MOVE.value):
                    # Do not echo presence/cursor events back to the sender
                    await audit_session_manager.broadcast(clean_sid, response_or_broadcast, exclude=websocket)
                else:
                    # Broadcast collaborative events (annotations, etc.) to all clients in room
                    await audit_session_manager.broadcast(clean_sid, response_or_broadcast)
    except WebSocketDisconnect:
        disc_res = await audit_session_manager.disconnect(websocket)
        if disc_res:
            _, disc_uid, _, user_removed = disc_res
            if user_removed:
                leave_payload = {
                    "event": SessionEventType.LEAVE.value,
                    "session_id": clean_sid,
                    "user_id": disc_uid,
                    "payload": {"user_id": disc_uid},
                    "timestamp": time.time(),
                }
                await audit_session_manager.broadcast(clean_sid, leave_payload)
    except Exception as e:
        logger.error(f"Error in collaborative websocket session {clean_sid}: {e}")
        await audit_session_manager.disconnect(websocket)


# ============================================================================
# Offline Air-Gapped Licensing Endpoints (Task S11-04)
# ============================================================================

@app.post("/api/v1/license/activate", response_model=LicenseActivationResponse)
def activate_license(
    req: LicenseActivationRequest,
    user: User = Depends(require_permission(Permission.ADMIN_CONFIG)),
):
    """
    Activates an air-gapped cryptographic enterprise license key.
    Enforces Ed25519 digital signature validation and hardware machine fingerprinting.
    """
    payload_input = req.license_data if req.license_data is not None else req.license_key
    if payload_input is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing license payload: license_key or license_data required",
        )

    success, message, status_resp = license_manager.activate(payload_input)
    audit_logger.log_event(
        user_id=user.user_id,
        role=user.role.value,
        action="LICENSE_ACTIVATE",
        details={
            "success": success,
            "tier": status_resp.tier.value,
            "customer_id": status_resp.customer_id,
            "state": status_resp.state.value,
        },
    )

    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

    return LicenseActivationResponse(
        success=success,
        message=message,
        status=status_resp,
    )


@app.get("/api/v1/license/status", response_model=LicenseStatusResponse)
def get_license_status(
    user: User = Depends(require_permission(Permission.DOC_READ)),
):
    """
    Returns current software license status, tier, features, and hardware fingerprint.
    Zero-Leak (Rule 2): Never exposes private keys or raw hardware serials.
    """
    return license_manager.get_status()


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("FINTRACE_DAEMON_HOST", os.getenv("FINSIGHT_DAEMON_HOST", "127.0.0.1"))
    port = int(os.getenv("FINTRACE_DAEMON_PORT", os.getenv("FINSIGHT_DAEMON_PORT", 8765)))
    uvicorn.run("main:app", host=host, port=port, reload=True)
