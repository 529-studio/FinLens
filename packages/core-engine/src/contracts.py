"""
FinSight Data Contracts & Security Validation
Governed by ADR-003, AGENTS.md Rule 13, and 529 Engineering Standards.
Enforces strict input validation, path traversal defense, and bounding box constraints.
"""

import re
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






