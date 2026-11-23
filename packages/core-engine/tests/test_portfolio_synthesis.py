"""
TDD Test Suite for Multi-Document Portfolio Synthesis & Cross-Filing Comparative Analytics (Sprint 11 Task S11-01)
Governed by AGENTS.md Rules 1, 2, 3, 11, 12, 13, 14, 15.
"""

import sys
from pathlib import Path
import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from contracts import (
    BenchmarkRole,
    PortfolioDocumentTarget,
    PortfolioSynthesisRequest,
    TimeSeriesDataPoint,
    EntityMetricSeries,
    PeerRankingItem,
    PortfolioSummary,
    PortfolioSynthesisResponse,
    BoundingBox,
    GroundedEvidence,
)


def test_portfolio_contracts_validation_success():
    """Verify construction and validation of PortfolioSynthesisRequest and models."""
    doc1 = PortfolioDocumentTarget(
        document_id="VNM_2022_AUDITED",
        entity="VNM",
        period="2022",
        role=BenchmarkRole.TARGET,
    )
    doc2 = PortfolioDocumentTarget(
        document_id="VNM_2023_AUDITED",
        entity="VNM",
        period="2023",
        role=BenchmarkRole.TARGET,
    )
    req = PortfolioSynthesisRequest(
        documents=[doc1, doc2],
        query_text="So sánh doanh thu và biên lợi nhuận giữa hai năm",
        metrics_requested=["revenue", "gross_profit", "net_profit", "cagr_revenue"],
        inference_mode="auto",
    )
    assert len(req.documents) == 2
    assert req.documents[0].document_id == "VNM_2022_AUDITED"
    assert req.documents[0].role == BenchmarkRole.TARGET
    assert req.inference_mode == "auto"

    # Test Response model assembly
    evidence = GroundedEvidence(
        page_number=1,
        bounding_box=BoundingBox(ymin=100, xmin=150, ymax=300, xmax=800),
        label="Doanh thu thuần",
        extracted_value="60,478 tỷ",
        confidence=0.98,
        document_id="VNM_2023_AUDITED",
    )
    point1 = TimeSeriesDataPoint(
        period="2022",
        value=59925.0,
        unit="tỷ VND",
        yoy_growth=None,
    )
    point2 = TimeSeriesDataPoint(
        period="2023",
        value=60478.0,
        unit="tỷ VND",
        yoy_growth=0.92,
        evidence=evidence,
    )
    series = EntityMetricSeries(
        entity="VNM",
        metric="revenue",
        series=[point1, point2],
        cagr=0.0092,
    )
    ranking = PeerRankingItem(
        rank=1,
        entity="VNM",
        period="2023",
        metric_name="revenue",
        metric_value=60478.0,
        growth_rate=0.92,
        evidence=evidence,
    )
    summary = PortfolioSummary(
        total_entities=1,
        total_periods=2,
        portfolio_revenue_aggregate=60478.0,
        weighted_net_margin=14.8,
        fastest_growing_entity="VNM",
        highest_margin_entity="VNM",
    )
    res = PortfolioSynthesisResponse(
        portfolio_summary=summary,
        time_series_metrics=[series],
        peer_rankings=[ranking],
        synthesis_narrative="Vinamilk duy trì đà tăng trưởng ổn định.",
        evidences=[evidence],
        retrieved_pages={"VNM_2022_AUDITED": [1], "VNM_2023_AUDITED": [1]},
        latency_ms=120.5,
        engine_used="mlx-qwen2.5-vl-7b-4bit",
    )
    assert res.portfolio_summary.total_entities == 1
    assert len(res.time_series_metrics) == 1
    assert res.time_series_metrics[0].cagr == 0.0092
    assert res.evidences[0].document_id == "VNM_2023_AUDITED"


def test_portfolio_contracts_path_traversal_rejection():
    """Verify that path traversal in document_id is strictly rejected (Rule 13B)."""
    with pytest.raises(ValidationError):
        PortfolioDocumentTarget(document_id="../../etc/passwd")

    with pytest.raises(ValidationError):
        PortfolioDocumentTarget(document_id="doc/with/slash")

    with pytest.raises(ValidationError):
        PortfolioDocumentTarget(document_id="doc;injection")


def test_portfolio_contracts_document_count_bounds():
    """Verify min_length=2 and max_length=10 boundary conditions."""
    doc = PortfolioDocumentTarget(document_id="VNM_2023")
    # < 2 documents
    with pytest.raises(ValidationError):
        PortfolioSynthesisRequest(documents=[doc])

    # > 10 documents
    excessive_docs = [PortfolioDocumentTarget(document_id=f"DOC_{i}") for i in range(11)]
    with pytest.raises(ValidationError):
        PortfolioSynthesisRequest(documents=excessive_docs)
