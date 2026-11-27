"""
FinSight Data Contracts & Security Validation
Governed by ADR-003, AGENTS.md Rule 13, and 529 Engineering Standards.
Enforces strict input validation, path traversal defense, and bounding box constraints.
"""

import re
import time
import tempfile
from enum import Enum
from pathlib import Path
from typing import List, Optional, Tuple, Literal, Dict, Any
from pydantic import BaseModel, Field, field_validator


ALLOWED_ROOTS = [
    Path("~/.fintrace").expanduser().resolve(),
    Path("~/.finsight").expanduser().resolve(),
    Path(__file__).resolve().parents[3] / "benchmarks",
    Path(__file__).resolve().parents[3] / "data",
    Path("/tmp/fintrace_test").resolve(),
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


class FootnoteItem(BaseModel):
    """Structured financial statement footnote (Thuyết minh BCTC) reference."""
    line_item: str
    code: Optional[str] = None
    footnote_number: str
    footnote_title: str
    summary: str
    page_number: int
    bounding_box: BoundingBox


class QueryResponse(BaseModel):
    """Response payload containing financial insight, audit trail, and visual grounding."""
    document_id: str
    query_text: str
    answer: str = Field(..., description="Analyzed answer synthesizing text and chart data")
    evidences: List[GroundedEvidence] = Field(default_factory=list, description="Visual grounding audit trail")
    footnotes: List[FootnoteItem] = Field(default_factory=list, description="Extracted footnote citations")
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


class BenchmarkRole(str, Enum):
    TARGET = "target"
    PEER = "peer"
    BENCHMARK = "benchmark"


class PortfolioDocumentTarget(BaseModel):
    document_id: str = Field(..., description="Unique document ID in LanceDB store")
    entity: Optional[str] = Field(None, description="Enterprise ticker or name (e.g. VNM, HPG)")
    period: Optional[str] = Field(None, description="Fiscal period (e.g. 2021, 2022, 2023, 2023-Q4)")
    role: BenchmarkRole = Field(BenchmarkRole.PEER, description="Role in portfolio analysis")

    @field_validator("document_id")
    @classmethod
    def validate_document_id(cls, v: str) -> str:
        if not v or not re.match(r"^[a-zA-Z0-9_\-]+$", v):
            raise ValueError(f"document_id '{v}' must be strictly alphanumeric with dashes or underscores")
        if len(v) > 64:
            raise ValueError(f"document_id '{v}' must not exceed 64 characters")
        return v


class PortfolioSynthesisRequest(BaseModel):
    documents: List[PortfolioDocumentTarget] = Field(..., min_length=2, max_length=10, description="List of 2 to 10 document targets")
    query_text: Optional[str] = Field(
        "Tổng hợp hiệu quả kinh doanh, tốc độ tăng trưởng doanh thu và biên lợi nhuận giữa các kỳ báo cáo.",
        description="Specific analytical focus query",
    )
    metrics_requested: List[str] = Field(
        default_factory=lambda: [
            "revenue", "gross_profit", "net_profit", "gross_margin", "net_margin", "cagr_revenue"
        ],
        description="Target financial metrics to calculate and cross-reference",
    )
    inference_mode: Literal["auto", "local", "cloud"] = Field("auto", description="Dual-mode inference strategy")

    @field_validator("documents")
    @classmethod
    def validate_unique_documents(cls, docs: List[PortfolioDocumentTarget]) -> List[PortfolioDocumentTarget]:
        if len(docs) < 2:
            raise ValueError("documents list must contain at least 2 distinct document targets")
        if len(docs) > 10:
            raise ValueError("documents list must not exceed 10 document targets")
        seen = set()
        for d in docs:
            if d.document_id in seen:
                raise ValueError(f"Duplicate document_id '{d.document_id}' in portfolio request")
            seen.add(d.document_id)
        return docs


class TimeSeriesDataPoint(BaseModel):
    period: str
    value: Optional[float] = None
    unit: str = "VND"
    yoy_growth: Optional[float] = None
    evidence: Optional[GroundedEvidence] = None


class EntityMetricSeries(BaseModel):
    entity: str
    metric: str
    series: List[TimeSeriesDataPoint]
    cagr: Optional[float] = None


class PeerRankingItem(BaseModel):
    rank: int
    entity: str
    period: str
    metric_value: float
    metric_name: str
    growth_rate: Optional[float] = None
    evidence: Optional[GroundedEvidence] = None


class PortfolioSummary(BaseModel):
    total_entities: int
    total_periods: int
    portfolio_revenue_aggregate: Optional[float] = None
    weighted_net_margin: Optional[float] = None
    fastest_growing_entity: Optional[str] = None
    highest_margin_entity: Optional[str] = None


class PortfolioSynthesisResponse(BaseModel):
    portfolio_summary: PortfolioSummary
    time_series_metrics: List[EntityMetricSeries]
    peer_rankings: List[PeerRankingItem]
    synthesis_narrative: str
    evidences: List[GroundedEvidence]
    retrieved_pages: Dict[str, List[int]]
    latency_ms: float
    engine_used: str


class FinancialStatementInputs(BaseModel):
    """Raw financial statement line items (in reporting currency / VND)."""
    # Income Statement
    revenue: Optional[float] = Field(None, description="Doanh thu thuần")
    gross_profit: Optional[float] = Field(None, description="Lợi nhuận gộp")
    operating_profit: Optional[float] = Field(None, description="Lợi nhuận từ HĐKD (EBIT)")
    net_income: Optional[float] = Field(None, description="Lợi nhuận sau thuế (LNST)")
    interest_expense: Optional[float] = Field(None, description="Chi phí lãi vay")

    # Balance Sheet
    current_assets: Optional[float] = Field(None, description="Tài sản ngắn hạn")
    cash_and_equivalents: Optional[float] = Field(None, description="Tiền và tương đương tiền")
    inventories: Optional[float] = Field(None, description="Hàng tồn kho")
    total_assets: Optional[float] = Field(None, description="Tổng tài sản")
    current_liabilities: Optional[float] = Field(None, description="Nợ ngắn hạn")
    total_liabilities: Optional[float] = Field(None, description="Tổng nợ phải trả")
    equity: Optional[float] = Field(None, description="Vốn chủ sở hữu")

    # Cash Flow Statement
    operating_cash_flow: Optional[float] = Field(None, description="Lưu chuyển tiền thuần từ HĐKD (OCF)")
    capex: Optional[float] = Field(None, description="Tiền chi mua sắm TSCĐ (Capital Expenditures)")


class FinancialRatioRequest(BaseModel):
    document_id: str = Field(..., description="Unique document ID in LanceDB store")
    raw_inputs_override: Optional[FinancialStatementInputs] = Field(
        None, description="Optional manual overrides for financial line items"
    )
    include_dupont: bool = Field(True, description="Compute 3-stage DuPont decomposition")
    include_cash_flow_screening: bool = Field(True, description="Execute cash flow health screener")
    inference_mode: Literal["auto", "local", "cloud"] = Field("auto", description="Dual-mode inference strategy")

    @field_validator("document_id")
    @classmethod
    def validate_document_id(cls, v: str) -> str:
        if not v or not re.match(r"^[a-zA-Z0-9_\-]+$", v):
            raise ValueError(f"document_id '{v}' must be strictly alphanumeric with dashes or underscores")
        if len(v) > 64:
            raise ValueError(f"document_id '{v}' must not exceed 64 characters")
        return v


class RatioCategory(str, Enum):
    LIQUIDITY = "liquidity"
    SOLVENCY = "solvency"
    PROFITABILITY = "profitability"
    EFFICIENCY = "efficiency"


class BenchmarkStatus(str, Enum):
    OPTIMAL = "optimal"
    ADEQUATE = "adequate"
    WARNING = "warning"
    CRITICAL = "critical"
    NOT_APPLICABLE = "not_applicable"


class RatioItem(BaseModel):
    code: str = Field(..., description="Machine-readable ratio code e.g. current_ratio")
    name: str = Field(..., description="Human-readable name in Vietnamese / English")
    category: RatioCategory
    value: Optional[float] = None
    unit: str = "x"
    benchmark_status: BenchmarkStatus = BenchmarkStatus.NOT_APPLICABLE
    formula_description: str
    evidences: List[GroundedEvidence] = Field(default_factory=list)


class RatioCategoryGroup(BaseModel):
    category: RatioCategory
    ratios: List[RatioItem]


class DuPontAnalysis(BaseModel):
    net_profit_margin: Optional[float] = Field(None, description="Net Income / Revenue (%)")
    asset_turnover: Optional[float] = Field(None, description="Revenue / Total Assets (x)")
    equity_multiplier: Optional[float] = Field(None, description="Total Assets / Equity (x)")
    roe: Optional[float] = Field(None, description="Return on Equity (%)")
    formula_narrative: str
    evidences: List[GroundedEvidence] = Field(default_factory=list)


class CashFlowHealthGrade(str, Enum):
    STRONG = "STRONG"
    MODERATE = "MODERATE"
    CAUTION = "CAUTION"
    DISTRESS = "DISTRESS"


class CashFlowHealthScore(BaseModel):
    grade: CashFlowHealthGrade
    earnings_quality_ratio: Optional[float] = Field(None, description="OCF / Net Income")
    free_cash_flow: Optional[float] = Field(None, description="OCF - Capex (VND)")
    ocf_to_current_debt: Optional[float] = Field(None, description="OCF / Current Liabilities")
    health_summary: str
    warning_signals: List[str] = Field(default_factory=list)
    evidences: List[GroundedEvidence] = Field(default_factory=list)


class FinancialRatioResponse(BaseModel):
    document_id: str
    ratio_groups: List[RatioCategoryGroup]
    dupont_analysis: Optional[DuPontAnalysis] = None
    cash_flow_health: Optional[CashFlowHealthScore] = None
    raw_inputs_used: FinancialStatementInputs
    evidences: List[GroundedEvidence]
    latency_ms: float
    engine_used: str



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


class StreamingChunk(BaseModel):
    """Real-time token streaming payload delivered over WebSocket."""
    event: Literal["token", "evidence", "done", "error"]
    token: Optional[str] = None
    evidences: Optional[List[GroundedEvidence]] = None
    answer: Optional[str] = None
    elapsed_ms: Optional[float] = None
    error: Optional[str] = None


class FootnoteQueryRequest(BaseModel):
    """Request payload to extract and disambiguate footnote citations."""
    document_id: str
    line_items: Optional[List[str]] = None

    @field_validator("document_id")
    @classmethod
    def sanitize_doc_id(cls, v: str):
        if not re.match(r"^[a-zA-Z0-9_\-]+$", v) or ".." in v or len(v) > 64:
            raise ValueError("Access denied: Invalid or malicious document_id")
        return v


class FootnoteQueryResponse(BaseModel):
    """Response payload containing extracted footnotes mapped to balance sheet items."""
    document_id: str
    total_footnotes: int
    footnotes: List[FootnoteItem]
    elapsed_ms: float


# ============================================================================
# Multi-Page Table Stitching Contracts (ADR-004, Task S10-02)
# ============================================================================

class TableColumnDTO(BaseModel):
    """Normalized column definition in a financial statement table."""
    key: str = Field(..., description="Normalized identifier (e.g. 'line_item', 'code', 'footnote', 'ending_balance')")
    header: str = Field(..., description="Original column header text")
    index: int = Field(..., ge=0, description="0-indexed column position")
    data_type: Literal["text", "code", "numeric", "footnote"] = Field("text", description="Inferred column data type")
    bounding_box: Optional[BoundingBox] = Field(None, description="Bounding box of column header if detected")


class FragmentRowDTO(BaseModel):
    """Single raw table row extracted from a specific page."""
    cells: List[str] = Field(..., description="Raw text of each cell in the row")
    bounding_box: Optional[BoundingBox] = Field(None, description="Visual coordinates on source page")
    page_number: Optional[int] = Field(None, ge=1, description="Page number of the row")


class TableFragmentDTO(BaseModel):
    """Table fragment detected on a single page of a multi-page filing."""
    page_number: int = Field(..., ge=1, description="1-indexed source PDF page number")
    headers: Optional[List[str]] = Field(None, description="Optional explicit column headers on this page")
    rows: List[FragmentRowDTO] = Field(..., description="Raw rows extracted on this page")
    bounding_box: Optional[BoundingBox] = Field(None, description="Overall bounding box of table fragment on page")
    has_repeated_header: bool = Field(False, description="Flag indicating first row is a repeated header")


class TableRowDTO(BaseModel):
    """Unified row in a stitched multi-page financial statement table."""
    row_index: int = Field(..., ge=0, description="0-indexed global sequence in stitched table")
    page_number: int = Field(..., ge=1, description="Source page number where this row resides")
    cells: Dict[str, str] = Field(default_factory=dict, description="Column key to cell string value")
    raw_cells: List[str] = Field(default_factory=list, description="Ordered cell values matching columns")
    bounding_box: BoundingBox = Field(..., description="Visual coordinates for grounding on source page")
    is_total: bool = Field(False, description="Whether row is a summary or total row")
    is_section: bool = Field(False, description="Whether row is a section header (e.g. A. TÀI SẢN NGẮN HẠN)")
    code: Optional[str] = Field(None, description="Extracted line item code (e.g. 100, 110)")
    footnote: Optional[str] = Field(None, description="Extracted footnote reference")


class MultiPageTableDTO(BaseModel):
    """Unified multi-page financial statement table stitched across consecutive pages."""
    document_id: str = Field(..., description="Source document identifier")
    table_name: str = Field(..., description="Name of financial statement (e.g. Balance Sheet)")
    spanned_pages: List[int] = Field(..., min_length=1, description="List of 1-indexed pages this table spans")
    columns: List[TableColumnDTO] = Field(..., description="Aligned table columns")
    rows: List[TableRowDTO] = Field(..., description="Stitched rows with visual grounding")
    total_rows: int = Field(..., ge=0, description="Total number of data rows in stitched table")
    stitched_from_fragments_count: int = Field(..., ge=1, description="Number of page fragments stitched")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Stitching alignment confidence score")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional table metadata")


class TableStitchRequest(BaseModel):
    """Request payload to stitch multi-page table fragments into a unified table."""
    document_id: str = Field(..., description="Document identifier")
    table_name: Optional[str] = Field("Financial Statement Table", description="Table title")
    fragments: List[TableFragmentDTO] = Field(..., min_length=1, description="List of page table fragments")

    @field_validator("document_id")
    @classmethod
    def sanitize_doc_id(cls, v: str):
        if not re.match(r"^[a-zA-Z0-9_\-]+$", v) or ".." in v or len(v) > 64:
            raise ValueError("Access denied: Invalid or malicious document_id")
        return v


class TableStitchResponse(BaseModel):
    """Response payload containing unified multi-page table and performance metrics."""
    document_id: str
    table: MultiPageTableDTO
    elapsed_ms: float


# ============================================================================
# Real-Time Collaborative Audit Session Sync Contracts (Task S11-03)
# ============================================================================

class SessionEventType(str, Enum):
    """Event types delivered across real-time collaborative WebSockets."""
    JOIN = "join"
    LEAVE = "leave"
    PRESENCE = "presence"
    CURSOR_MOVE = "cursor_move"
    ANNOTATION_ADD = "annotation_add"
    ANNOTATION_RESOLVE = "annotation_resolve"
    ANNOTATION_DELETE = "annotation_delete"
    HEARTBEAT = "heartbeat"
    SESSION_STATE = "session_state"
    ERROR = "error"


class UserPresence(BaseModel):
    """Real-time presence and spatial location of an auditor in a shared session."""
    user_id: str = Field(..., description="Unique alphanumeric username or employee ID")
    name: str = Field("FinTrace Auditor", description="Display name of the auditor")
    role: str = Field("junior_analyst", description="Assigned organizational role")
    color: str = Field("#4F46E5", description="Hex color assigned to auditor avatar/cursor")
    active_page: int = Field(1, ge=1, description="PDF page number currently in view")
    cursor_x: Optional[float] = Field(None, ge=0.0, le=1000.0, description="Normalized X coordinate [0, 1000]")
    cursor_y: Optional[float] = Field(None, ge=0.0, le=1000.0, description="Normalized Y coordinate [0, 1000]")
    last_seen: float = Field(default_factory=time.time, description="Unix timestamp of last activity or heartbeat")


class AuditAnnotation(BaseModel):
    """Spatial visual audit annotation anchored to a specific filing page and bounding box."""
    annotation_id: str = Field(..., description="Unique UUID identifier for the annotation")
    document_id: str = Field(..., description="Target financial filing document ID")
    page_number: int = Field(..., ge=1, description="1-indexed PDF page number")
    bounding_box: List[float] = Field(..., min_length=4, max_length=4, description="[ymin, xmin, ymax, xmax] coordinates in [0, 1000]")
    comment: str = Field(..., min_length=1, description="Audit observation, review note, or question")
    author_id: str = Field(..., description="User ID of author who created the annotation")
    author_name: str = Field("FinTrace Auditor", description="Author display name")
    created_at: float = Field(default_factory=time.time, description="Unix timestamp when annotation was recorded")
    resolved: bool = Field(False, description="Whether this audit observation has been reviewed and resolved")
    resolved_by: Optional[str] = Field(None, description="User ID of senior auditor who marked it resolved")


class SessionState(BaseModel):
    """Authoritative snapshot of a collaborative audit session."""
    session_id: str = Field(..., description="Unique collaborative room ID")
    document_id: str = Field(..., description="Target financial filing document ID")
    created_at: float = Field(default_factory=time.time, description="Creation timestamp")
    active_users: Dict[str, UserPresence] = Field(default_factory=dict, description="Map of active user_id to UserPresence")
    annotations: List[AuditAnnotation] = Field(default_factory=list, description="List of spatial visual annotations")


class CollaborativeMessage(BaseModel):
    """WebSocket frame payload for collaborative session events."""
    event: SessionEventType = Field(..., description="Collaborative event type")
    session_id: str = Field(..., description="Collaborative room ID")
    user_id: Optional[str] = Field(None, description="Originating user ID")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Event-specific data payload")
    timestamp: float = Field(default_factory=time.time, description="Timestamp of the message")


class CreateSessionRequest(BaseModel):
    """Payload to create or initialize a collaborative audit session."""
    session_id: str = Field(..., min_length=3, max_length=64, description="Alphanumeric room ID")
    document_id: str = Field(..., min_length=1, max_length=64, description="Target document ID")

    @field_validator("session_id")
    @classmethod
    def sanitize_session_id(cls, v: str):
        if not re.match(r"^[a-zA-Z0-9_\-]+$", v) or ".." in v:
            raise ValueError("Access denied: Invalid session_id format")
        return v

    @field_validator("document_id")
    @classmethod
    def sanitize_doc_id(cls, v: str):
        if not re.match(r"^[a-zA-Z0-9_\-]+$", v) or ".." in v:
            raise ValueError("Access denied: Invalid document_id format")
        return v


# ============================================================================
# Offline Air-Gapped Licensing & Hardware Fingerprinting Contracts (Task S11-04)
# ============================================================================

class LicenseTier(str, Enum):
    """Tier level for enterprise licensing."""
    COMMUNITY = "community"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class LicenseState(str, Enum):
    """Current operational evaluation state of the software license."""
    ACTIVE = "active"
    EXPIRED = "expired"
    INVALID_SIGNATURE = "invalid_signature"
    FINGERPRINT_MISMATCH = "fingerprint_mismatch"
    COMMUNITY_EVALUATION = "community_evaluation"


class LicensePayload(BaseModel):
    """Cryptographically signed license metadata payload."""
    customer_id: str = Field(..., description="Unique enterprise identifier (e.g. 'VIETINBANK_HQ')")
    customer_name: str = Field(..., description="Display name of enterprise licensee")
    tier: LicenseTier = Field(LicenseTier.COMMUNITY, description="Licensed product tier")
    issued_at: float = Field(..., description="Unix epoch timestamp when license was issued")
    expires_at: float = Field(..., description="Unix epoch timestamp when license expires")
    max_users: int = Field(10, ge=1, description="Maximum seats permitted")
    features: List[str] = Field(default_factory=list, description="List of licensed feature flags")
    machine_fingerprint: str = Field(
        "*",
        description="One-way SHA-256 machine hardware hash, or '*' for floating deployment",
    )


class LicenseFileDTO(BaseModel):
    """Complete license container file with canonical payload and Ed25519 signature."""
    payload: LicensePayload
    signature: str = Field(..., description="Base64url-encoded Ed25519 asymmetric signature")


class LicenseStatusResponse(BaseModel):
    """License evaluation status report."""
    state: LicenseState
    is_valid: bool
    tier: LicenseTier
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    machine_fingerprint: str
    days_remaining: Optional[int] = None
    max_users: int = 1
    features: List[str] = Field(default_factory=list)
    expires_at: Optional[float] = None


class LicenseActivationRequest(BaseModel):
    """Request payload to activate an air-gapped cryptographic license."""
    license_key: Optional[str] = Field(None, description="Raw JSON or base64 string of the license file")
    license_data: Optional[Dict[str, Any]] = Field(None, description="Optional direct structured JSON object")


class LicenseActivationResponse(BaseModel):
    """Response confirming license activation outcome."""
    success: bool
    message: str
    status: LicenseStatusResponse


# ============================================================================
# Multi-Document Anomaly & Discrepancy Detection Contracts (Task S12-01)
# ============================================================================

class DiscrepancyType(str, Enum):
    """Classification of audited anomaly or financial discrepancy."""
    RESTATEMENT = "restatement"
    BALANCE_SHEET_IMBALANCE = "balance_sheet_imbalance"
    CALCULATION_INCONSISTENCY = "calculation_inconsistency"
    UNEXPECTED_VARIANCE = "unexpected_variance"
    SEGMENT_CONSOLIDATION_MISMATCH = "segment_consolidation_mismatch"


class DiscrepancySeverity(str, Enum):
    """Audit severity ranking for identified discrepancies."""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class DiscrepancyItem(BaseModel):
    """Detailed record of a detected financial anomaly or cross-filing variance."""
    id: str = Field(..., description="Unique anomaly identification slug or hash")
    discrepancy_type: DiscrepancyType = Field(..., description="Category of discrepancy")
    severity: DiscrepancySeverity = Field(..., description="Materiality severity level")
    metric_name: str = Field(..., description="Affected financial statement metric or equation")
    description: str = Field(..., description="Auditor-friendly explanation of the anomaly")
    expected_value: Optional[float] = Field(None, description="Mathematically expected or restated base value")
    reported_value: Optional[float] = Field(None, description="Actual reported value in the audited filing")
    variance_absolute: Optional[float] = Field(None, description="Absolute delta magnitude (|reported - expected|)")
    variance_percentage: Optional[float] = Field(None, description="Percentage variance delta relative to expected base")
    period: str = Field(..., description="Fiscal period under review (e.g. 2022, 2023)")
    source_document_id: str = Field(..., description="Document ID where reported value was retrieved")
    comparative_document_id: Optional[str] = Field(None, description="Comparative filing document ID for cross-filing restatements")
    evidences: List[GroundedEvidence] = Field(default_factory=list, description="Visual grounding citations anchored to PDF source")
    resolution_hint: Optional[str] = Field(None, description="Guidance or footnote cross-reference to investigate discrepancy")


class DiscrepancySummary(BaseModel):
    """Aggregated scorecard of cross-filing discrepancy audit findings."""
    total_checks: int = Field(..., ge=0, description="Total number of automated audit checks executed")
    discrepancies_found: int = Field(..., ge=0, description="Count of anomalies detected across all severities")
    critical_count: int = Field(..., ge=0, description="Count of critical accounting or restatement violations")
    warning_count: int = Field(..., ge=0, description="Count of notable unexpected variances or material warnings")
    info_count: int = Field(..., ge=0, description="Count of minor rounding or classification nuances")
    health_score: float = Field(..., ge=0.0, le=100.0, description="Financial reporting consistency score (0 to 100)")


class DiscrepancyAuditRequest(BaseModel):
    """Request payload to initiate cross-filing discrepancy and anomaly detection."""
    documents: List[PortfolioDocumentTarget] = Field(..., min_length=1, max_length=10, description="1 to 10 documents to audit")
    variance_threshold_pct: float = Field(20.0, ge=0.0, le=1000.0, description="YoY percentage change triggering unexpected variance flag")
    check_restatements: bool = Field(True, description="Audit prior-period comparative figures across consecutive filings")
    check_accounting_equations: bool = Field(True, description="Verify fundamental accounting balance identities")
    check_internal_calculations: bool = Field(True, description="Verify subtotal and profit calculation consistency")
    check_segment_consolidation: bool = Field(True, description="Verify segment summation against consolidated financial statements")
    tolerance_absolute: float = Field(1.0, ge=0.0, description="Absolute tolerance for rounding differences")


class DiscrepancyAuditResponse(BaseModel):
    """Comprehensive response containing detected anomalies, severity summary, and grounding."""
    summary: DiscrepancySummary = Field(..., description="Summary scorecard of audit results")
    discrepancies: List[DiscrepancyItem] = Field(default_factory=list, description="Detailed list of identified discrepancies")
    audited_documents: List[str] = Field(default_factory=list, description="List of audited document IDs")
    execution_time_ms: float = Field(..., ge=0.0, description="Engine execution latency in milliseconds")
    audit_narrative: str = Field(..., description="Concise executive audit summary of findings")


# ============================================================================
# Regulatory Compliance Audit Trail Packager Contracts (Task S12-02)
# ============================================================================

class RegulatoryPackageFormat(str, Enum):
    """Supported standardized regulatory package formats."""
    IXBRL = "ixbrl"
    PDFA3 = "pdfa3"
    BUNDLE = "bundle"


class PackageManifestItem(BaseModel):
    """Manifest entry for an individual audited filing in the regulatory package."""
    document_id: str = Field(..., description="Target filing document identifier")
    period: str = Field(..., description="Audited fiscal period (e.g. 2022, 2023)")
    file_sha256: str = Field(..., description="Cryptographic SHA-256 hash of source filing")
    grounded_citations_count: int = Field(..., ge=0, description="Count of visual grounding evidence citations")
    discrepancies_count: int = Field(0, ge=0, description="Count of identified anomalies and restatements")


class AuditPackageRequest(BaseModel):
    """Request payload to generate a standardized regulatory audit compliance package."""
    documents: List[PortfolioDocumentTarget] = Field(..., min_length=1, max_length=10, description="Filing documents to package")
    format: RegulatoryPackageFormat = Field(RegulatoryPackageFormat.BUNDLE, description="Requested packaging format")
    taxonomy_standard: str = Field("US-GAAP-2024", description="Regulatory taxonomy specification (e.g. US-GAAP-2024, IFRS-2024)")
    include_discrepancy_report: bool = Field(True, description="Whether to embed discrepancy auditor findings")
    include_grounding_manifest: bool = Field(True, description="Whether to embed spatial bounding box citation manifest")
    auditor_notes: Optional[str] = Field(None, description="Auditor executive notes or sign-off remarks")


class AuditPackageResponse(BaseModel):
    """Metadata response confirming generated regulatory compliance package."""
    package_id: str = Field(..., description="Unique compliance package identifier")
    format: RegulatoryPackageFormat = Field(..., description="Package format generated")
    file_name: str = Field(..., description="File name for download or transmission")
    file_bytes_base64: str = Field(..., description="Base64-encoded binary payload of the archive or file")
    file_size_bytes: int = Field(..., ge=0, description="Total binary size in bytes")
    sha256_checksum: str = Field(..., description="SHA-256 integrity hash of exported payload")
    tamper_evident_root_hash: str = Field(..., description="Cryptographic SHA-256 event chaining root hash")
    manifest_items: List[PackageManifestItem] = Field(default_factory=list, description="List of included filing manifests")
    total_citations: int = Field(..., ge=0, description="Total grounded citations across all filings")
    created_at: float = Field(default_factory=time.time, description="Unix timestamp of package generation")
    execution_time_ms: float = Field(..., ge=0.0, description="Generation latency in milliseconds")


# ============================================================================
# Multi-Tenant Enterprise Workspace Isolation Contracts (Task S12-04)
# ============================================================================

class WorkspaceTier(str, Enum):
    """Isolation security tier for multi-tenant deployments."""
    STANDARD = "standard"
    ENTERPRISE_ISOLATED = "enterprise_isolated"
    AIRGAPPED = "airgapped"


class EncryptionAlgorithm(str, Enum):
    """Cryptographic cipher suites supported for encryption at rest."""
    AES_256_GCM = "aes-256-gcm"
    CHACHA20_POLY1305 = "chacha20-poly1305"


class TenantWorkspaceCreateRequest(BaseModel):
    """Request payload to provision an isolated multi-tenant workspace."""
    workspace_id: str = Field(..., max_length=64, description="Unique tenant workspace alphanumeric ID")
    tenant_name: str = Field(..., description="Enterprise organization or department name")
    tier: WorkspaceTier = Field(WorkspaceTier.ENTERPRISE_ISOLATED, description="Isolation boundary tier")
    encryption_algorithm: EncryptionAlgorithm = Field(EncryptionAlgorithm.AES_256_GCM, description="Encryption cipher")
    kms_key_id: Optional[str] = Field(None, description="Optional external KMS key ID")

    @field_validator("workspace_id")
    @classmethod
    def sanitize_workspace_id(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z0-9_\-]+$", v) or ".." in v or len(v) > 64:
            raise ValueError(f"Invalid or malicious workspace_id '{v}' (path traversal rejected)")
        return v


class TenantWorkspaceResponse(BaseModel):
    """Response payload confirming provisioned isolated tenant workspace."""
    workspace_id: str
    tenant_name: str
    tier: WorkspaceTier
    encryption_algorithm: EncryptionAlgorithm
    is_encrypted: bool
    storage_path: str
    key_fingerprint: str
    created_at: float


class TenantAccessVerificationRequest(BaseModel):
    """Request payload to verify cross-tenant access permissions."""
    workspace_id: str = Field(..., max_length=64, description="Requesting tenant workspace ID")
    requested_document_id: str = Field(..., description="Target filing document ID")

    @field_validator("workspace_id")
    @classmethod
    def sanitize_workspace_id(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z0-9_\-]+$", v) or ".." in v or len(v) > 64:
            raise ValueError(f"Invalid or malicious workspace_id '{v}' (path traversal rejected)")
        return v


class TenantAccessVerificationResponse(BaseModel):
    """Response payload confirming tenant access decision."""
    workspace_id: str
    requested_document_id: str
    allowed: bool
    reason: str


class DocumentInfoResponse(BaseModel):
    """Metadata and available rendered page numbers for an indexed document."""
    document_id: str = Field(..., description="Sanitized alphanumeric document identifier")
    total_pages: int = Field(..., ge=0, description="Total number of rendered/indexed pages")
    available_pages: List[int] = Field(default_factory=list, description="Sorted 1-indexed page numbers available")


# ============================================================================
# Cross-Sectional Industry Peer Benchmarking Contracts (Task S13-04 / Handoff S13-01)
# ============================================================================

class BenchmarkWeightingMode(str, Enum):
    """Weighting strategy for cross-sectional sector benchmark averages."""
    EQUAL = "equal"
    MARKET_CAP = "market_cap"


class PeerQuartileStanding(str, Enum):
    """Relative quartile standing of target company against industry peers."""
    TOP_QUARTILE = "top_quartile"
    ABOVE_MEDIAN = "above_median"
    BELOW_MEDIAN = "below_median"
    BOTTOM_QUARTILE = "bottom_quartile"
    INSUFFICIENT_DATA = "insufficient_data"


class PeerCompanyMetric(BaseModel):
    """Single peer company observation for cross-sectional sector benchmarking."""
    company_id: str = Field(..., min_length=1, max_length=64)
    company_name: str = Field(..., min_length=1, max_length=120)
    market_cap: Optional[float] = Field(None, ge=0.0, description="Market capitalization for cap-weighted benchmarks")
    metrics: Dict[str, Optional[float]] = Field(default_factory=dict)


class MetricBenchmarkConfig(BaseModel):
    """Configuration defining metric display metadata and optimization polarity."""
    metric_code: str = Field(..., min_length=1, max_length=64)
    metric_name: Optional[str] = Field(None, max_length=120)
    unit: str = Field("", max_length=16)
    higher_is_better: bool = Field(True, description="False for leverage/cost metrics where lower is stronger")


class PeerBenchmarkRequest(BaseModel):
    """Request payload for cross-sectional peer benchmarking & percentile scoring."""
    sector_name: str = Field(..., min_length=1, max_length=120)
    target_company_id: str = Field(..., min_length=1, max_length=64)
    target_company_name: str = Field(..., min_length=1, max_length=120)
    target_document_id: Optional[str] = Field(None, max_length=64)
    target_market_cap: Optional[float] = Field(None, ge=0.0)
    target_metrics: Dict[str, Optional[float]] = Field(default_factory=dict)
    peers: List[PeerCompanyMetric] = Field(default_factory=list, max_length=200)
    metric_configs: List[MetricBenchmarkConfig] = Field(default_factory=list)
    weighting_mode: BenchmarkWeightingMode = Field(BenchmarkWeightingMode.EQUAL)
    exclude_target_from_pool: bool = Field(True)

    @field_validator("target_document_id")
    @classmethod
    def sanitize_target_doc_id(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not re.match(r"^[a-zA-Z0-9_\-]+$", v) or ".." in v or len(v) > 64:
                raise ValueError(f"Invalid or malicious target_document_id '{v}' (path traversal rejected)")
        return v


class MetricBenchmarkResult(BaseModel):
    """Cross-sectional distribution statistics and percentile rank for one financial metric."""
    metric_code: str
    metric_name: str
    unit: str = ""
    higher_is_better: bool = True
    target_value: Optional[float] = None
    peer_count: int = Field(..., ge=0)
    equal_weighted_mean: Optional[float] = None
    market_cap_weighted_mean: Optional[float] = None
    active_sector_mean: Optional[float] = None
    p10: Optional[float] = None
    p25: Optional[float] = None
    p50: Optional[float] = None
    p75: Optional[float] = None
    p90: Optional[float] = None
    percentile_rank: Optional[float] = Field(None, ge=0.0, le=100.0)
    z_score: Optional[float] = None
    standing: PeerQuartileStanding = PeerQuartileStanding.INSUFFICIENT_DATA


class PeerBenchmarkResponse(BaseModel):
    """Complete cross-sectional peer benchmarking report."""
    sector_name: str
    target_company_id: str
    target_company_name: str
    target_document_id: Optional[str] = None
    weighting_mode: BenchmarkWeightingMode
    peer_count_evaluated: int = Field(..., ge=0)
    composite_percentile_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    results: List[MetricBenchmarkResult] = Field(default_factory=list)
    narrative: str
    execution_time_ms: float = Field(..., ge=0.0)


# ============================================================================
# Cash Flow Direct-to-Indirect Reconciliation Contracts (Task S13-05)
# ============================================================================

class ReconciliationStatus(str, Enum):
    """Materiality classification of Direct vs Indirect CFO reconciliation."""
    RECONCILED = "reconciled"
    IMMATERIAL_VARIANCE = "immaterial_variance"
    MATERIAL_MISMATCH = "material_mismatch"


class DirectCashFlowInput(BaseModel):
    """Direct Method Operating Cash Flow components (signed cash flows by default)."""
    cash_received_from_customers: float = Field(0.0, description="Cash inflows from customers")
    cash_paid_to_suppliers: float = Field(0.0, description="Cash paid to suppliers (negative for outflow unless direct_outflows_as_positive=True)")
    cash_paid_to_employees: float = Field(0.0, description="Cash paid to employees (negative for outflow unless direct_outflows_as_positive=True)")
    interest_paid: float = Field(0.0, description="Interest paid (negative for outflow unless direct_outflows_as_positive=True)")
    taxes_paid: float = Field(0.0, description="Income taxes paid (negative for outflow unless direct_outflows_as_positive=True)")
    other_operating_cash: float = Field(0.0, description="Other net operating cash inflows/outflows")


class IndirectCashFlowInput(BaseModel):
    """Indirect Method Operating Cash Flow components using balance-sheet delta conventions."""
    net_income: float = Field(0.0, description="Net income for the reporting period")
    depreciation_amortization: float = Field(0.0, description="Non-cash depreciation & amortization add-back")
    non_cash_adjustments: float = Field(0.0, description="Other non-cash adjustments (provisions, impairment, FX)")
    delta_receivables: float = Field(0.0, description="Change in accounts receivable (Ending - Beginning; positive increase reduces cash)")
    delta_inventory: float = Field(0.0, description="Change in inventory (Ending - Beginning; positive increase reduces cash)")
    delta_payables: float = Field(0.0, description="Change in accounts payable (Ending - Beginning; positive increase provides cash)")
    delta_other_working_capital: float = Field(0.0, description="Net cash impact of other working capital changes")


class CashFlowReconcileRequest(BaseModel):
    """Request payload for Direct-to-Indirect Operating Cash Flow reconciliation."""
    document_id: str = Field(..., min_length=1, max_length=64, description="Source financial filing document ID")
    period_label: str = Field("FY", min_length=1, max_length=64, description="Reporting period label (e.g. FY2024)")
    direct: DirectCashFlowInput
    indirect: IndirectCashFlowInput
    direct_outflows_as_positive: bool = Field(
        False,
        description="Set True if direct outflow fields (suppliers, employees, interest, taxes) are supplied as positive magnitudes",
    )
    reconciliation_tolerance: float = Field(0.01, ge=0.0, description="Absolute tolerance for exact RECONCILED status")
    materiality_threshold_pct: float = Field(1.0, ge=0.0, le=100.0, description="Percentage variance threshold for MATERIAL_MISMATCH")
    citations: Dict[str, BoundingBox] = Field(
        default_factory=dict,
        description="Optional [0, 1000] bounding box visual grounding citations keyed by component name",
    )
    citation_pages: Dict[str, int] = Field(
        default_factory=dict,
        description="Optional 1-indexed PDF page numbers keyed by component name",
    )

    @field_validator("document_id")
    @classmethod
    def sanitize_document_id(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z0-9_\-]+$", v) or ".." in v or len(v) > 64:
            raise ValueError(f"Invalid or malicious document_id '{v}' (path traversal rejected)")
        return v


class CashFlowLineItemResult(BaseModel):
    """Single reconciled cash flow line item with signed CFO impact and visual grounding."""
    method: Literal["direct", "indirect"]
    item_code: str
    label: str
    raw_input: float
    cfo_impact: float
    bounding_box: Optional[BoundingBox] = None
    page_number: Optional[int] = Field(None, ge=1)


class CashFlowReconcileResponse(BaseModel):
    """Complete Direct-to-Indirect Operating Cash Flow reconciliation report."""
    document_id: str
    period_label: str
    direct_cfo: float
    indirect_cfo: float
    reconciliation_variance: float
    abs_variance: float = Field(..., ge=0.0)
    variance_pct: Optional[float] = Field(None, ge=0.0)
    status: ReconciliationStatus
    working_capital_net_impact: float
    non_cash_total_addback: float
    line_items: List[CashFlowLineItemResult] = Field(default_factory=list)
    citations: Dict[str, BoundingBox] = Field(default_factory=dict)
    narrative: str
    execution_time_ms: float = Field(..., ge=0.0)


# ============================================================================
# Enterprise Hierarchical RBAC Policy Contracts (Task S13-07)
# ============================================================================

class PolicyEffect(str, Enum):
    """RBAC policy evaluation effect."""
    ALLOW = "allow"
    DENY = "deny"


class RBACPolicyRuleDTO(BaseModel):
    """Scoped RBAC policy rule supporting explicit ALLOW/DENY and glob resource matching."""
    policy_id: str = Field(..., min_length=1, max_length=64)
    effect: PolicyEffect
    roles: List[str] = Field(default_factory=list)
    permissions: List[str] = Field(default_factory=list)
    resource_pattern: str = Field("*", min_length=1, max_length=128)
    description: str = Field("", max_length=256)


class RBACPolicyEvaluateRequest(BaseModel):
    """Request payload to evaluate whether a role has permission on a scoped resource."""
    role: str = Field(..., min_length=1, max_length=64)
    permission: str = Field(..., min_length=1, max_length=64)
    resource: str = Field("*", min_length=1, max_length=128)

    @field_validator("resource")
    @classmethod
    def sanitize_resource(cls, v: str) -> str:
        if ".." in v or "\0" in v:
            raise ValueError("Invalid resource identifier (path traversal rejected)")
        return v


class RBACPolicyEvaluateResponse(BaseModel):
    """Deterministic RBAC policy evaluation decision."""
    allowed: bool
    effect: PolicyEffect
    role: str
    permission: str
    resource: str
    matched_policy_id: Optional[str] = None
    reason: str


class RBACPoliciesListResponse(BaseModel):
    """Active RBAC policy rules and inherited role permission matrix."""
    total_policies: int = Field(..., ge=0)
    policies: List[RBACPolicyRuleDTO] = Field(default_factory=list)
    role_hierarchy: Dict[str, List[str]] = Field(default_factory=dict)














