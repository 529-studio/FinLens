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
