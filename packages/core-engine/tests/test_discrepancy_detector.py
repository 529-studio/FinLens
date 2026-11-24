"""
TDD Test Suite for Multi-Document Anomaly & Discrepancy Detection Engine (Sprint 12 Task S12-01)
Governed by AGENTS.md Rules 1, 2, 3, 11, 12, 13B, 14, 15 and ADR-003.
"""

import sys
from pathlib import Path
import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from contracts import (
    BenchmarkRole,
    PortfolioDocumentTarget,
    BoundingBox,
    GroundedEvidence,
    DiscrepancyType,
    DiscrepancySeverity,
    DiscrepancyItem,
    DiscrepancySummary,
    DiscrepancyAuditRequest,
    DiscrepancyAuditResponse,
)


def test_discrepancy_contracts_instantiation_and_validation():
    """Verify DTO instantiation, enum mappings, and default values."""
    evidence = GroundedEvidence(
        page_number=2,
        bounding_box=BoundingBox(ymin=120, xmin=80, ymax=280, xmax=920),
        label="Tài sản ngắn hạn",
        extracted_value="35,000 tỷ VND",
        confidence=0.99,
        document_id="VNM_2023_AUDITED",
    )

    item = DiscrepancyItem(
        id="disc-bs-001",
        discrepancy_type=DiscrepancyType.BALANCE_SHEET_IMBALANCE,
        severity=DiscrepancySeverity.CRITICAL,
        metric_name="balance_sheet_equality",
        description="Total Assets (50,000) do not equal Liabilities (20,000) + Equity (29,500). Imbalance: 500.",
        expected_value=49500.0,
        reported_value=50000.0,
        variance_absolute=500.0,
        variance_percentage=1.01,
        period="2023",
        source_document_id="VNM_2023_AUDITED",
        evidences=[evidence],
        resolution_hint="Review footnote disclosures on asset revaluation reserves or restated liabilities.",
    )

    assert item.discrepancy_type == DiscrepancyType.BALANCE_SHEET_IMBALANCE
    assert item.severity == DiscrepancySeverity.CRITICAL
    assert item.variance_absolute == 500.0
    assert len(item.evidences) == 1
    assert item.evidences[0].bounding_box.ymin == 120

    summary = DiscrepancySummary(
        total_checks=25,
        discrepancies_found=1,
        critical_count=1,
        warning_count=0,
        info_count=0,
        health_score=75.0,
    )
    assert summary.health_score == 75.0
    assert summary.critical_count == 1

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

    req = DiscrepancyAuditRequest(
        documents=[doc1, doc2],
        variance_threshold_pct=25.0,
        check_restatements=True,
        check_accounting_equations=True,
        check_internal_calculations=True,
        check_segment_consolidation=True,
        tolerance_absolute=1.0,
    )
    assert len(req.documents) == 2
    assert req.variance_threshold_pct == 25.0
    assert req.tolerance_absolute == 1.0

    res = DiscrepancyAuditResponse(
        summary=summary,
        discrepancies=[item],
        audited_documents=["VNM_2022_AUDITED", "VNM_2023_AUDITED"],
        execution_time_ms=45.2,
        audit_narrative="Cross-filing audit identified 1 critical balance sheet imbalance.",
    )
    assert len(res.discrepancies) == 1
    assert res.execution_time_ms == 45.2


def test_discrepancy_contracts_bounds_and_path_traversal():
    """Verify validation boundaries and path traversal rejection in request contracts."""
    # Test path traversal in document_id
    with pytest.raises(ValidationError):
        PortfolioDocumentTarget(
            document_id="../../etc/shadow",
            entity="EVIL",
            period="2023",
        )

    # Test empty document list
    with pytest.raises(ValidationError):
        DiscrepancyAuditRequest(documents=[])

    # Test negative tolerance
    with pytest.raises(ValidationError):
        doc = PortfolioDocumentTarget(document_id="VNM_2023_AUDITED", entity="VNM", period="2023")
        DiscrepancyAuditRequest(documents=[doc], tolerance_absolute=-5.0)

    # Test negative variance threshold
    with pytest.raises(ValidationError):
        doc = PortfolioDocumentTarget(document_id="VNM_2023_AUDITED", entity="VNM", period="2023")
        DiscrepancyAuditRequest(documents=[doc], variance_threshold_pct=-10.0)


# ============================================================================
# Task 2 Tests: Pure Financial Discrepancy Functions and Engine
# ============================================================================

from discrepancy_detector import (
    check_balance_sheet_equation,
    check_gross_profit_equation,
    check_operating_profit_equation,
    check_net_profit_equation,
    check_restatement,
    check_unexpected_variance,
    check_segment_consolidation,
    compute_audit_health_score,
    DiscrepancyDetector,
)


def test_check_balance_sheet_equation_balanced():
    """Verify that a balanced balance sheet returns no discrepancy."""
    res = check_balance_sheet_equation(
        assets=10000.0,
        liabilities=4000.0,
        equity=6000.0,
        doc_id="VNM_2023_AUDITED",
        period="2023",
        tolerance=1.0,
    )
    assert res is None


def test_check_balance_sheet_equation_imbalance():
    """Verify that an imbalance exceeding tolerance is flagged as CRITICAL."""
    res = check_balance_sheet_equation(
        assets=10000.0,
        liabilities=4000.0,
        equity=5500.0,  # 500 imbalance
        doc_id="VNM_2023_AUDITED",
        period="2023",
        tolerance=1.0,
    )
    assert res is not None
    assert res.discrepancy_type == DiscrepancyType.BALANCE_SHEET_IMBALANCE
    assert res.severity == DiscrepancySeverity.CRITICAL
    assert res.variance_absolute == 500.0
    assert res.expected_value == 9500.0
    assert res.reported_value == 10000.0
    assert "Balance Sheet identity violation" in res.description


def test_check_gross_profit_equation():
    """Verify calculation consistency for Gross Profit = Revenue - COGS."""
    # Balanced case
    assert check_gross_profit_equation(
        revenue=1000.0, cogs=600.0, gross_profit=400.0,
        doc_id="VNM_2023_AUDITED", period="2023", tolerance=0.5
    ) is None

    # Inconsistent case
    disc = check_gross_profit_equation(
        revenue=1000.0, cogs=600.0, gross_profit=450.0,
        doc_id="VNM_2023_AUDITED", period="2023", tolerance=0.5
    )
    assert disc is not None
    assert disc.discrepancy_type == DiscrepancyType.CALCULATION_INCONSISTENCY
    assert disc.severity == DiscrepancySeverity.CRITICAL
    assert disc.variance_absolute == 50.0
    assert disc.expected_value == 400.0


def test_check_net_profit_equation():
    """Verify Net Profit = PreTax - Tax."""
    disc = check_net_profit_equation(
        pretax_profit=500.0, tax_expense=100.0, net_profit=380.0,
        doc_id="VNM_2023_AUDITED", period="2023", tolerance=1.0
    )
    assert disc is not None
    assert disc.variance_absolute == 20.0
    assert disc.severity == DiscrepancySeverity.CRITICAL


def test_check_cross_filing_restatement():
    """Verify detection of comparative figure restatement across two filings."""
    # 2022 filing reported 2022 Revenue as 50,000.
    # 2023 filing reported 2022 Comparative Revenue as 48,000.
    disc = check_restatement(
        metric_name="revenue",
        original_val=50000.0,
        comparative_val=48000.0,
        period="2022",
        original_doc="VNM_2022_AUDITED",
        comparative_doc="VNM_2023_AUDITED",
        tolerance=5.0,
    )
    assert disc is not None
    assert disc.discrepancy_type == DiscrepancyType.RESTATEMENT
    assert disc.severity == DiscrepancySeverity.CRITICAL
    assert disc.variance_absolute == 2000.0
    assert disc.variance_percentage == -4.0
    assert disc.comparative_document_id == "VNM_2023_AUDITED"


def test_check_unexpected_variance():
    """Verify unexpected YoY variance flagging when movement exceeds threshold."""
    # 35% growth vs 20% threshold -> flagged
    disc = check_unexpected_variance(
        metric_name="inventories",
        val_prev=1000.0,
        val_curr=1350.0,
        period_prev="2022",
        period_curr="2023",
        doc_prev="VNM_2022_AUDITED",
        doc_curr="VNM_2023_AUDITED",
        threshold_pct=20.0,
    )
    assert disc is not None
    assert disc.discrepancy_type == DiscrepancyType.UNEXPECTED_VARIANCE
    assert disc.severity == DiscrepancySeverity.WARNING
    assert disc.variance_percentage == 35.0

    # 10% growth vs 20% threshold -> not flagged
    assert check_unexpected_variance(
        metric_name="inventories",
        val_prev=1000.0,
        val_curr=1100.0,
        period_prev="2022",
        period_curr="2023",
        doc_prev="VNM_2022_AUDITED",
        doc_curr="VNM_2023_AUDITED",
        threshold_pct=20.0,
    ) is None


def test_check_segment_consolidation():
    """Verify segment consolidation sum vs consolidated total."""
    # Segments sum to 950, consolidated total is 1000 -> mismatch
    disc = check_segment_consolidation(
        segment_name="geographical_revenue",
        segment_values=[400.0, 300.0, 250.0],
        total_value=1000.0,
        doc_id="VNM_2023_AUDITED",
        period="2023",
        tolerance=1.0,
    )
    assert disc is not None
    assert disc.discrepancy_type == DiscrepancyType.SEGMENT_CONSOLIDATION_MISMATCH
    assert disc.severity == DiscrepancySeverity.WARNING
    assert disc.variance_absolute == 50.0
    assert disc.expected_value == 1000.0
    assert disc.reported_value == 950.0


def test_compute_audit_health_score():
    """Verify audit health score calculation and bounds."""
    # Perfect score: 0 discrepancies
    assert compute_audit_health_score(0, 0, 0, 20) == 100.0

    # 1 critical (20 pts), 1 warning (7.5 pts), 2 info (2 pts) = 100 - 29.5 = 70.5
    assert compute_audit_health_score(1, 1, 2, 20) == 70.5

    # Multiple critical issues should clamp at 0.0, never negative
    assert compute_audit_health_score(10, 5, 0, 20) == 0.0


@pytest.mark.anyio
async def test_discrepancy_detector_full_audit_mocked():
    """Verify complete DiscrepancyDetector engine run across two filings."""
    detector = DiscrepancyDetector()

    req = DiscrepancyAuditRequest(
        documents=[
            PortfolioDocumentTarget(document_id="VNM_2022_AUDITED", entity="VNM", period="2022"),
            PortfolioDocumentTarget(document_id="VNM_2023_AUDITED", entity="VNM", period="2023"),
        ],
        variance_threshold_pct=20.0,
        check_restatements=True,
        check_accounting_equations=True,
        check_internal_calculations=True,
        check_segment_consolidation=True,
        tolerance_absolute=1.0,
    )

    res = await detector.audit(req)
    assert isinstance(res, DiscrepancyAuditResponse)
    assert res.summary.total_checks > 0
    assert 0.0 <= res.summary.health_score <= 100.0
    assert len(res.audited_documents) == 2
    assert res.execution_time_ms > 0
    assert len(res.audit_narrative) > 0


# ============================================================================
# Task 3 Tests: REST Endpoint POST /api/v1/audit/discrepancies
# ============================================================================

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)
REPO_ROOT = Path(__file__).resolve().parents[3]
SAMPLE_PDF = str(REPO_ROOT / "benchmarks" / "data" / "VNM_BCTC_2023_AUDITED.pdf")


@pytest.fixture(scope="module")
def setup_discrepancy_documents():
    """Ingest test documents into vector store index for live endpoint test."""
    for doc_id in ["VNM_2022_DISC", "VNM_2023_DISC"]:
        payload = {
            "document_id": doc_id,
            "file_path": SAMPLE_PDF,
            "render_dpi": 150,
        }
        res = client.post("/api/v1/documents/ingest", json=payload)
        assert res.status_code == 200, f"Failed to ingest {doc_id}: {res.text}"


def test_api_audit_discrepancies_success(setup_discrepancy_documents):
    """Verify live endpoint POST /api/v1/audit/discrepancies returns 200 with full schema."""
    payload = {
        "documents": [
            {"document_id": "VNM_2022_DISC", "entity": "VNM", "period": "2022"},
            {"document_id": "VNM_2023_DISC", "entity": "VNM", "period": "2023"},
        ],
        "variance_threshold_pct": 20.0,
        "check_restatements": True,
        "check_accounting_equations": True,
        "check_internal_calculations": True,
        "check_segment_consolidation": True,
        "tolerance_absolute": 1.0,
    }
    res = client.post("/api/v1/audit/discrepancies", json=payload)
    assert res.status_code == 200, f"API failed: {res.text}"
    data = res.json()

    assert "summary" in data
    assert data["summary"]["total_checks"] > 0
    assert 0.0 <= data["summary"]["health_score"] <= 100.0
    assert "discrepancies" in data
    assert "audited_documents" in data
    assert len(data["audited_documents"]) == 2
    assert "audit_narrative" in data
    assert data["execution_time_ms"] > 0


def test_api_audit_discrepancies_path_traversal():
    """Verify strict path traversal defense rejects malicious document identifiers."""
    payload = {
        "documents": [
            {"document_id": "../../etc/passwd", "entity": "EVIL", "period": "2023"},
        ],
    }
    res = client.post("/api/v1/audit/discrepancies", json=payload)
    assert res.status_code in [400, 422]


def test_api_audit_discrepancies_missing_document(setup_discrepancy_documents):
    """Verify 404 is returned when a requested document target is not in the store."""
    payload = {
        "documents": [
            {"document_id": "VNM_2022_DISC"},
            {"document_id": "NOT_INGESTED_DOC_888"},
        ],
    }
    res = client.post("/api/v1/audit/discrepancies", json=payload)
    assert res.status_code == 404
    assert "NOT_INGESTED_DOC_888" in res.json()["detail"]


def test_api_audit_discrepancies_unauthorized():
    """Verify missing/invalid authorization token is rejected (401)."""
    payload = {
        "documents": [
            {"document_id": "VNM_2022_DISC"},
        ],
    }
    headers = {"Authorization": "Bearer malformed.invalid.token"}
    res = client.post("/api/v1/audit/discrepancies", json=payload, headers=headers)
    assert res.status_code == 401


