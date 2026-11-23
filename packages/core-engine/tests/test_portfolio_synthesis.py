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
from comparative_query import (
    resolve_target_metadata,
    calculate_yoy,
    calculate_cagr,
    calculate_margins,
    rank_entities_by_metric,
    compute_portfolio_summary,
    PortfolioSynthesisEngine,
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


def test_resolve_target_metadata_explicit():
    """Verify that explicitly provided entity and period are honored directly."""
    target = PortfolioDocumentTarget(
        document_id="CUSTOM_ID_001",
        entity="Vinamilk Corp",
        period="2023",
    )
    entity, period = resolve_target_metadata(target)
    assert entity == "Vinamilk Corp"
    assert period == "2023"


def test_resolve_target_metadata_regex_fallback():
    """Verify regex fallback extraction from document_id patterns."""
    cases = [
        ("VNM_2023_AUDITED", ("VNM", "2023")),
        ("HPG-2022-ANNUAL", ("HPG", "2022")),
        ("VIC_2021", ("VIC", "2021")),
        ("FPT_Q4_2023_REPORT", ("FPT", "2023")),
        ("UNKNOWNFILING", ("UNKNOWNFILING", "UNKNOWN")),
    ]
    for doc_id, expected in cases:
        target = PortfolioDocumentTarget(document_id=doc_id)
        entity, period = resolve_target_metadata(target)
        assert (entity, period) == expected, f"Failed on {doc_id}: got {(entity, period)}, expected {expected}"


def test_calculate_yoy_standard_and_edge_cases():
    """Verify YoY growth calculations and boundary handling."""
    # Standard positive growth: 100 -> 115 => +15.0%
    assert calculate_yoy(100.0, 115.0) == 15.0
    # Standard negative growth: 100 -> 85 => -15.0%
    assert calculate_yoy(100.0, 85.0) == -15.0
    # Floating point precision check: 50.0 -> 55.0 => +10.0%
    assert calculate_yoy(50.0, 55.0) == 10.0
    # Base is zero: division by zero returns None
    assert calculate_yoy(0.0, 100.0) is None
    # Base is negative: using |v_prev|
    assert calculate_yoy(-50.0, -40.0) == 20.0
    # None inputs
    assert calculate_yoy(None, 100.0) is None
    assert calculate_yoy(100.0, None) is None


def test_calculate_cagr_multi_year():
    """Verify Compound Annual Growth Rate (CAGR) formula and boundaries."""
    # 3-year CAGR: 100 -> 133.1 over 3 years => 10.0%
    cagr = calculate_cagr(100.0, 133.1, n_years=3)
    assert cagr is not None
    assert round(cagr * 100.0, 2) == 10.0

    # 1-year CAGR matches YoY: 100 -> 120 over 1 year => 20.0%
    cagr_1yr = calculate_cagr(100.0, 120.0, n_years=1)
    assert cagr_1yr is not None
    assert round(cagr_1yr * 100.0, 2) == 20.0

    # Non-positive starting or ending values return None
    assert calculate_cagr(0.0, 100.0, n_years=2) is None
    assert calculate_cagr(-50.0, 100.0, n_years=2) is None
    assert calculate_cagr(100.0, -20.0, n_years=2) is None
    assert calculate_cagr(100.0, 0.0, n_years=2) is None
    # Invalid years
    assert calculate_cagr(100.0, 120.0, n_years=0) is None
    assert calculate_cagr(100.0, 120.0, n_years=-1) is None


def test_calculate_margins():
    """Verify gross and net margin percentage calculations."""
    gross_m, net_m = calculate_margins(1000.0, 400.0, 150.0)
    assert gross_m == 40.0
    assert net_m == 15.0

    # Zero or None revenue returns None
    assert calculate_margins(0.0, 100.0, 50.0) == (None, None)
    assert calculate_margins(None, 100.0, 50.0) == (None, None)
    # Missing profits
    assert calculate_margins(1000.0, None, 150.0) == (None, 15.0)


def test_rank_entities_by_metric():
    """Verify peer group ranking ordering by specified metric."""
    p1 = TimeSeriesDataPoint(period="2023", value=60000.0)
    p2 = TimeSeriesDataPoint(period="2023", value=45000.0)
    p3 = TimeSeriesDataPoint(period="2023", value=90000.0)

    s1 = EntityMetricSeries(entity="VNM", metric="revenue", series=[p1])
    s2 = EntityMetricSeries(entity="QNS", metric="revenue", series=[p2])
    s3 = EntityMetricSeries(entity="HPG", metric="revenue", series=[p3])

    rankings = rank_entities_by_metric([s1, s2, s3], metric_name="revenue", target_period="2023")
    assert len(rankings) == 3
    assert rankings[0].entity == "HPG"
    assert rankings[0].rank == 1
    assert rankings[0].metric_value == 90000.0
    assert rankings[1].entity == "VNM"
    assert rankings[1].rank == 2
    assert rankings[2].entity == "QNS"
    assert rankings[2].rank == 3


def test_compute_portfolio_summary():
    """Verify portfolio aggregation and leader identification."""
    p1 = TimeSeriesDataPoint(period="2023", value=60000.0, yoy_growth=5.0)
    p2 = TimeSeriesDataPoint(period="2023", value=90000.0, yoy_growth=12.0)

    s1 = EntityMetricSeries(entity="VNM", metric="revenue", series=[p1])
    s2 = EntityMetricSeries(entity="HPG", metric="revenue", series=[p2])

    r1 = PeerRankingItem(rank=1, entity="HPG", period="2023", metric_name="revenue", metric_value=90000.0, growth_rate=12.0)
    r2 = PeerRankingItem(rank=2, entity="VNM", period="2023", metric_name="revenue", metric_value=60000.0, growth_rate=5.0)

    summary = compute_portfolio_summary([s1, s2], [r1, r2])
    assert summary.total_entities == 2
    assert summary.total_periods == 1
    assert summary.portfolio_revenue_aggregate == 150000.0
    assert summary.fastest_growing_entity == "HPG"


@pytest.mark.anyio
async def test_engine_synthesize_missing_doc_raises_error():
    """Verify that an unindexed document ID raises FileNotFoundError."""
    from unittest.mock import MagicMock

    store = MagicMock()
    store.get_pages.side_effect = lambda doc_id: [] if doc_id == "MISSING_DOC" else [{"page_number": 1, "image_path": "/tmp/1.png"}]
    retriever = MagicMock()
    retriever.store = store
    router = MagicMock()

    engine = PortfolioSynthesisEngine(store=store, retriever=retriever, router=router)
    req = PortfolioSynthesisRequest(
        documents=[
            PortfolioDocumentTarget(document_id="VNM_2022"),
            PortfolioDocumentTarget(document_id="MISSING_DOC"),
        ]
    )
    with pytest.raises(FileNotFoundError) as exc_info:
        await engine.synthesize(req)
    assert "MISSING_DOC" in str(exc_info.value)


@pytest.mark.anyio
async def test_engine_synthesize_success_mocked():
    """Verify end-to-end synthesis coordination with mock store, retriever, and router."""
    from unittest.mock import MagicMock, AsyncMock

    store = MagicMock()
    store.get_pages.side_effect = lambda doc_id: [
        {"page_number": 1, "image_path": f"/tmp/{doc_id}_p1.png", "text_preview": f"BCTC {doc_id}"}
    ]
    retriever = MagicMock()
    retriever.store = store
    retriever.comparative_search.return_value = {
        "VNM_2022": [1],
        "VNM_2023": [1],
    }

    mock_evidences = [
        {
            "page_number": 1,
            "ymin": 200,
            "xmin": 100,
            "ymax": 250,
            "xmax": 900,
            "label": "Doanh thu thuần",
            "extracted_value": "59,925",
            "confidence": 0.95,
            "document_id": "VNM_2022",
        },
        {
            "page_number": 1,
            "ymin": 210,
            "xmin": 110,
            "ymax": 260,
            "xmax": 910,
            "label": "Doanh thu thuần",
            "extracted_value": "60,478",
            "confidence": 0.97,
            "document_id": "VNM_2023",
        },
    ]

    mock_vlm_res = {
        "engine": "mock-mlx-engine",
        "answer": "Vinamilk duy trì tăng trưởng doanh thu 0.92% YoY.",
        "comparative_metrics": [
            {
                "metric": "Doanh thu thuần",
                "unit": "tỷ VNĐ",
                "doc_values": {"VNM_2022": "59,925", "VNM_2023": "60,478"},
                "yoy_growth": "+0.92%",
            }
        ],
        "evidences": mock_evidences,
    }

    router = MagicMock()
    router.analyze_comparative = AsyncMock(return_value=mock_vlm_res)

    engine = PortfolioSynthesisEngine(store=store, retriever=retriever, router=router)
    req = PortfolioSynthesisRequest(
        documents=[
            PortfolioDocumentTarget(document_id="VNM_2022", entity="VNM", period="2022"),
            PortfolioDocumentTarget(document_id="VNM_2023", entity="VNM", period="2023"),
        ],
        query_text="So sánh tăng trưởng doanh thu",
    )

    res = await engine.synthesize(req)
    assert res.engine_used == "mock-mlx-engine"
    assert res.portfolio_summary.total_entities == 1
    assert res.portfolio_summary.total_periods == 2
    assert len(res.time_series_metrics) >= 1
    assert len(res.evidences) == 2
    for ev in res.evidences:
        assert 0 <= ev.bounding_box.ymin < ev.bounding_box.ymax <= 1000
        assert 0 <= ev.bounding_box.xmin < ev.bounding_box.xmax <= 1000
        assert ev.document_id in ["VNM_2022", "VNM_2023"]


