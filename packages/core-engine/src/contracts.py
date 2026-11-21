"""
FinSight Data Contracts & Security Validation
Governed by ADR-003, AGENTS.md Rule 13, and 529 Engineering Standards.
Enforces strict input validation, path traversal defense, and bounding box constraints.
"""

import re
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple, Literal, Dict, Any
from pydantic import BaseModel, Field, field_validator


ALLOWED_ROOTS = [
    Path("~/.finsight").expanduser().resolve(),
    Path(__file__).resolve().parents[3] / "benchmarks",
    Path(__file__).resolve().parents[3] / "data",
    Path("/tmp/finsight_test").resolve(),
    Path(tempfile.gettempdir()).resolve(),
]


def is_path_safe(raw_path: str) -> bool:
    """Verifies that a filesystem path does not escape authorized boundaries."""
    try:
        resolved = Path(raw_path).expanduser().resolve()
        # Ensure no null bytes
        if "\0" in str(raw_path):
            return False
        # Check against approved root directories
        return any(
            resolved == root or root in resolved.parents
            for root in ALLOWED_ROOTS
        )
    except Exception:
        return False


class BoundingBox(BaseModel):
    """
    Normalized bounding box coordinates scaled from 0 to 1000.
    Standard: [ymin, xmin, ymax, xmax]
    """
    ymin: int = Field(..., ge=0, le=1000, description="Top boundary coordinate (0-1000)")
    xmin: int = Field(..., ge=0, le=1000, description="Left boundary coordinate (0-1000)")
    ymax: int = Field(..., ge=0, le=1000, description="Bottom boundary coordinate (0-1000)")
    xmax: int = Field(..., ge=0, le=1000, description="Right boundary coordinate (0-1000)")

    @field_validator("ymax")
    @classmethod
    def validate_vertical(cls, ymax: int, info):
        ymin = info.data.get("ymin", 0)
        if ymax <= ymin:
            raise ValueError(f"ymax ({ymax}) must be strictly greater than ymin ({ymin})")
        return ymax

    @field_validator("xmax")
    @classmethod
    def validate_horizontal(cls, xmax: int, info):
        xmin = info.data.get("xmin", 0)
        if xmax <= xmin:
            raise ValueError(f"xmax ({xmax}) must be strictly greater than xmin ({xmin})")
        return xmax

    def as_tuple(self) -> Tuple[int, int, int, int]:
        return (self.ymin, self.xmin, self.ymax, self.xmax)


class GroundedEvidence(BaseModel):
    """
    Verifiable visual grounding evidence linking extracted financial facts
    to exact page coordinates in the source PDF.
    """
    page_number: int = Field(..., ge=1, description="1-indexed source PDF page number")
    bounding_box: BoundingBox = Field(..., description="Visual bounding box highlighting source evidence")
    label: str = Field(..., min_length=2, max_length=150, description="Human-readable label")
    extracted_value: Optional[str] = Field(None, max_length=100, description="Exact numerical value or text extracted")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score of visual grounding")
    document_id: Optional[str] = Field(None, description="Document identifier linking evidence to specific PDF")


class DocumentIngestRequest(BaseModel):
    """Request payload to render and index a financial PDF."""
    file_path: str = Field(..., description="Path to source PDF on filesystem")
    document_id: Optional[str] = Field(None, description="Alphanumeric document identifier")
    render_dpi: int = Field(150, ge=72, le=300, description="Target DPI for PNG rendering")

    @field_validator("document_id")
    @classmethod
    def sanitize_doc_id(cls, v: Optional[str]):
        if v is not None:
            if not re.match(r"^[a-zA-Z0-9_\-]+$", v):
                raise ValueError("document_id must be strictly alphanumeric (letters, digits, _, -)")
            if len(v) > 64:
                raise ValueError("document_id must not exceed 64 characters")
        return v

    @field_validator("file_path")
    @classmethod
    def validate_traversal(cls, v: str):
        if not is_path_safe(v):
            raise ValueError("Access denied: file_path must reside within authorized project/storage boundaries")
        return v


class DocumentIngestResponse(BaseModel):
    """Response payload after rendering and visual embedding."""
    document_id: str
    total_pages: int
    rendered_image_paths: List[str]
    indexed_vectors_count: int
    duration_ms: float
    from_cache: bool = Field(False, description="Whether rendered pages were loaded directly from local cache")


class QueryRequest(BaseModel):
    """User query payload."""
    document_id: str = Field(..., description="Document identifier")
    query_text: str = Field(..., min_length=2, max_length=1000, description="Financial analyst question")
    top_k_pages: int = Field(2, ge=1, le=5, description="Number of candidate pages to retrieve")
    inference_mode: Literal["auto", "local", "cloud"] = Field("auto", description="Dual-mode inference strategy")

    @field_validator("document_id")
    @classmethod
    def sanitize_doc_id(cls, v: str):
        if not re.match(r"^[a-zA-Z0-9_\-]+$", v):
            raise ValueError("document_id must be strictly alphanumeric (letters, digits, _, -)")
        return v

    @field_validator("query_text")
    @classmethod
    def sanitize_query(cls, v: str):
        # Prevent prompt injection markers and control characters
        cleaned = v.replace("\0", "").strip()
        if not cleaned:
            raise ValueError("query_text cannot be empty after trimming")
        return cleaned


class QueryResponse(BaseModel):
    """Response payload containing financial insight, audit trail, and visual grounding."""
    document_id: str
    query_text: str
    answer: str = Field(..., description="Analyzed answer synthesizing text and chart data")
    evidences: List[GroundedEvidence] = Field(default_factory=list, description="Visual grounding audit trail")
    retrieved_page_numbers: List[int]
    engine_used: str = Field(..., description="e.g. 'mlx-qwen2.5-vl-7b-4bit' or 'claude-3-5-sonnet'")
    latency_ms: float
    cached: bool = Field(False, description="Whether query response was retrieved from in-memory LRU cache")


class ComparativeQueryRequest(BaseModel):
    """User comparative query payload across multiple fiscal documents."""
    document_ids: List[str] = Field(..., min_length=2, max_length=5, description="List of 2 to 5 document identifiers to compare")
    query_text: str = Field(..., min_length=2, max_length=1000, description="Comparative financial analyst question")
    top_k_per_doc: int = Field(1, ge=1, le=5, description="Number of candidate pages to retrieve per document")
    inference_mode: Literal["auto", "local", "cloud"] = Field("auto", description="Dual-mode inference strategy")

    @field_validator("document_ids")
    @classmethod
    def validate_doc_ids(cls, ids: List[str]):
        if len(ids) < 2:
            raise ValueError("document_ids must contain at least 2 distinct document identifiers for comparison")
        if len(ids) > 5:
            raise ValueError("document_ids must not exceed 5 documents per comparative query")
        seen = set()
        for doc_id in ids:
            if not doc_id or not re.match(r"^[a-zA-Z0-9_\-]+$", doc_id):
                raise ValueError(f"document_id '{doc_id}' must be strictly alphanumeric (letters, digits, _, -)")
            if len(doc_id) > 64:
                raise ValueError(f"document_id '{doc_id}' must not exceed 64 characters")
            if doc_id in seen:
                raise ValueError(f"Duplicate document_id '{doc_id}' in comparison list")
            seen.add(doc_id)
        return ids

    @field_validator("query_text")
    @classmethod
    def sanitize_query(cls, v: str):
        cleaned = v.replace("\0", "").strip()
        if not cleaned:
            raise ValueError("query_text cannot be empty after trimming")
        return cleaned


class ComparativeQueryResponse(BaseModel):
    """Response payload containing YoY comparison, delta metrics, and multi-document visual grounding."""
    document_ids: List[str]
    query_text: str
    answer: str
    comparative_metrics: List[Dict[str, Any]] = Field(default_factory=list, description="Extracted YoY comparison metrics")
    evidences: List[GroundedEvidence]
    retrieved_pages: Dict[str, List[int]]
    engine_used: str
    latency_ms: float



class CacheStatsResponse(BaseModel):
    """Cache performance statistics for local rendering and in-memory queries."""
    total_cached_documents: int
    total_cached_pages: int
    rendered_cache_bytes: int
    in_memory_query_cache_entries: int
    query_cache_hits: int
    query_cache_misses: int
    hit_ratio: float


class CacheClearRequest(BaseModel):
    """Request payload to clear memory or disk caches."""
    scope: Literal["all", "queries", "documents"] = Field("all", description="Cache clearing scope")
    document_id: Optional[str] = Field(None, description="Optional document ID to clear specific document cache")

    @field_validator("document_id")
    @classmethod
    def sanitize_doc_id(cls, v: Optional[str]):
        if v is not None:
            if not re.match(r"^[a-zA-Z0-9_\-]+$", v):
                raise ValueError("document_id must be strictly alphanumeric (letters, digits, _, -)")
            if len(v) > 64:
                raise ValueError("document_id must not exceed 64 characters")
        return v


class ModelStatusResponse(BaseModel):
    """Status payload for local Apple Silicon MLX VLM engine."""
    model_id: str
    quantization: str
    estimated_size_gb: float
    memory_ceiling_gb: float
    is_cached: bool
    is_loaded: bool
    cache_dir: str
    hardware_capability: str
    memory_usage: dict


class ModelDownloadRequest(BaseModel):
    """Request payload to initiate model weight download."""
    model_id: Optional[str] = None
    confirm: bool = Field(False, description="Explicit user confirmation required before download")


class ModelDownloadResponse(BaseModel):
    """Response payload for model download operation."""
    model_id: str
    status: str
    cache_dir: str
    message: str


class StoreStatsResponse(BaseModel):
    """Storage statistics payload for persistent LanceDB multi-vector store."""
    db_path: str
    total_documents: int
    total_pages: int
    disk_size_bytes: int
    vector_dimension: int


class DocumentListResponse(BaseModel):
    """List of indexed documents in persistent storage."""
    documents: List[str]
    total: int


class CloudProviderDetail(BaseModel):
    """Status details for a cloud frontier model provider (Zero-Leak: no keys)."""
    configured: bool
    model: str
    api_base_configured: Optional[bool] = None


class CloudStatusResponse(BaseModel):
    """Status response for Cloud BYOK router (Rule 2: Zero-Leak)."""
    available_providers: List[str]
    providers: Dict[str, CloudProviderDetail]
    default_model: str


class CloudKeyUpdateRequest(BaseModel):
    """Request payload to update cloud BYOK API key in session."""
    provider: Literal["anthropic", "azure", "openai"]
    api_key: str = Field(..., min_length=1, description="BYOK API key (never returned in responses)")
    api_base: Optional[str] = Field(None, description="Optional custom base URL or Azure endpoint")


class CloudKeyUpdateResponse(BaseModel):
    """Zero-Leak response confirming API key update without exposing credentials."""
    provider: str
    status: str
    message: str



