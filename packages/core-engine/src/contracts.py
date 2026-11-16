"""
FinSight Data Contracts & Type Specifications
Governed by ADR-003 and 529 Studio Engineering Standards.
"""

from typing import List, Optional, Tuple, Literal
from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    """
    Normalized bounding box coordinates scaled from 0 to 1000.
    Standard: [ymin, xmin, ymax, xmax]
    """
    ymin: int = Field(..., ge=0, le=1000, description="Top boundary coordinate (0-1000)")
    xmin: int = Field(..., ge=0, le=1000, description="Left boundary coordinate (0-1000)")
    ymax: int = Field(..., ge=0, le=1000, description="Bottom boundary coordinate (0-1000)")
    xmax: int = Field(..., ge=0, le=1000, description="Right boundary coordinate (0-1000)")

    def as_tuple(self) -> Tuple[int, int, int, int]:
        return (self.ymin, self.xmin, self.ymax, self.xmax)


class GroundedEvidence(BaseModel):
    """
    Verifiable visual grounding evidence linking extracted financial facts
    to exact page coordinates in the source PDF.
    """
    page_number: int = Field(..., ge=1, description="1-indexed source PDF page number")
    bounding_box: BoundingBox = Field(..., description="Visual bounding box highlighting source evidence")
    label: str = Field(..., description="Human-readable label (e.g. 'Revenue Chart 2023', 'Balance Sheet Note 4')")
    extracted_value: Optional[str] = Field(None, description="Exact numerical value or text extracted")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score of the visual grounding")


class DocumentIngestRequest(BaseModel):
    """Request payload to render and index a financial PDF."""
    file_path: str = Field(..., description="Absolute path to the source PDF on local filesystem")
    document_id: Optional[str] = Field(None, description="Optional custom document identifier")
    render_dpi: int = Field(150, ge=72, le=300, description="Target DPI for PNG rendering")


class DocumentIngestResponse(BaseModel):
    """Response payload after rendering and visual embedding."""
    document_id: str
    total_pages: int
    rendered_image_paths: List[str]
    indexed_vectors_count: int
    duration_ms: float


class QueryRequest(BaseModel):
    """User query payload."""
    document_id: str
    query_text: str = Field(..., min_length=2, description="Financial analyst question")
    top_k_pages: int = Field(2, ge=1, le=5, description="Number of candidate pages to retrieve")
    inference_mode: Literal["auto", "local", "cloud"] = Field("auto", description="Dual-mode inference strategy")


class QueryResponse(BaseModel):
    """Response payload containing financial insight, audit trail, and visual grounding."""
    document_id: str
    query_text: str
    answer: str = Field(..., description="Analyzed answer synthesizing text and chart data")
    evidences: List[GroundedEvidence] = Field(default_factory=list, description="Visual grounding audit trail")
    retrieved_page_numbers: List[int]
    engine_used: str = Field(..., description="e.g. 'mlx-qwen2.5-vl-7b-4bit' or 'claude-3-5-sonnet'")
    latency_ms: float
