"""
TDD Test Suite for Automated Audit Trail Exporter & Regulatory Package Generator (Sprint 12 Task S12-02)
Governed by AGENTS.md Rules 1, 2, 3, 11, 12, 13B, 14, 15 and ADR-003, ADR-007.
"""

import sys
import zipfile
import io
import xml.etree.ElementTree as ET
from pathlib import Path
import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from contracts import (
    BenchmarkRole,
    PortfolioDocumentTarget,
    RegulatoryPackageFormat,
    PackageManifestItem,
    AuditPackageRequest,
    AuditPackageResponse,
)


def test_regulatory_packager_contracts_validation():
    """Verify contracts instantiation, enum mappings, and validation bounds."""
    doc = PortfolioDocumentTarget(
        document_id="VNM_2023_AUDITED",
        entity="VNM",
        period="2023",
        role=BenchmarkRole.TARGET,
    )

    manifest_item = PackageManifestItem(
        document_id="VNM_2023_AUDITED",
        period="2023",
        file_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        grounded_citations_count=12,
        discrepancies_count=0,
    )
    assert manifest_item.document_id == "VNM_2023_AUDITED"
    assert manifest_item.grounded_citations_count == 12

    req = AuditPackageRequest(
        documents=[doc],
        format=RegulatoryPackageFormat.BUNDLE,
        taxonomy_standard="US-GAAP-2024",
        include_discrepancy_report=True,
        include_grounding_manifest=True,
        auditor_notes="Full annual filing regulatory package.",
    )
    assert req.format == RegulatoryPackageFormat.BUNDLE
    assert req.taxonomy_standard == "US-GAAP-2024"

    res = AuditPackageResponse(
        package_id="pkg-test-001",
        format=RegulatoryPackageFormat.BUNDLE,
        file_name="audit_package_VNM_2023.zip",
        file_bytes_base64="UEsDBBQAAAAIA...",
        file_size_bytes=1024,
        sha256_checksum="abc1234567890",
        tamper_evident_root_hash="def0987654321",
        manifest_items=[manifest_item],
        total_citations=12,
        created_at=1732490000.0,
        execution_time_ms=35.5,
    )
    assert res.package_id == "pkg-test-001"
    assert len(res.manifest_items) == 1


def test_regulatory_packager_contracts_path_traversal():
    """Verify path traversal rejection on document IDs in request."""
    with pytest.raises(ValidationError):
        PortfolioDocumentTarget(document_id="../../etc/shadow", entity="EVIL", period="2023")

    with pytest.raises(ValidationError):
        AuditPackageRequest(documents=[])


# ============================================================================
# Task 2 Tests: Pure Package Generator Functions
# ============================================================================

from audit_packager import (
    generate_ixbrl_xml,
    generate_pdfa3_container,
    generate_bundle_zip,
    compute_tamper_evident_chain,
    AuditPackager,
)


def test_generate_ixbrl_xml_structure():
    """Verify that generated XBRL document is valid XML with expected namespace tags."""
    metrics = {
        "VNM_2023_AUDITED": {
            "entity": "VNM",
            "period": "2023",
            "revenue": 60478.0,
            "net_profit": 9020.0,
            "total_assets": 52673.0,
            "total_liabilities": 17625.0,
            "total_equity": 35048.0,
        }
    }
    xml_str = generate_ixbrl_xml(
        metrics_by_doc=metrics,
        taxonomy_standard="US-GAAP-2024",
        discrepancies=[],
    )

    # Validate XML parsing
    root = ET.fromstring(xml_str)
    assert "xbrl" in root.tag.lower()
    assert len(root.findall(".//{http://fasb.org/us-gaap/2024}Revenues")) > 0
    assert len(root.findall(".//{http://fasb.org/us-gaap/2024}Assets")) > 0


def test_generate_pdfa3_container_structure():
    """Verify PDF/A-3 container bytes, header, and embedded file relationship dictionaries."""
    manifest_data = {"package_id": "pkg-001", "entity": "VNM", "period": "2023"}
    pdf_bytes = generate_pdfa3_container(
        title="FinTrace Regulatory Compliance Audit Report",
        entity="VNM",
        period="2023",
        manifest_data=manifest_data,
        discrepancies=[],
    )

    assert pdf_bytes.startswith(b"%PDF-1.7")
    assert b"/AFRelationship /Data" in pdf_bytes
    assert b"/Type /Filespec" in pdf_bytes
    assert b"%%EOF" in pdf_bytes


def test_generate_bundle_zip():
    """Verify multi-format bundle zip contains all required regulatory artifacts."""
    ixbrl_content = "<xbrl><test>data</test></xbrl>"
    pdf_content = b"%PDF-1.7 test content %%EOF"
    manifest_json = '{"package_id": "pkg-001"}'

    zip_bytes = generate_bundle_zip(
        package_id="pkg-001",
        ixbrl_content=ixbrl_content,
        pdf_content=pdf_content,
        manifest_json=manifest_json,
    )

    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as z:
        names = z.namelist()
        assert "manifest.json" in names
        assert "regulatory_filing.xbrl" in names
        assert "audit_report.pdf" in names
        assert "sha256_checksums.txt" in names

        # Verify content
        assert z.read("manifest.json").decode("utf-8") == manifest_json


def test_compute_tamper_evident_chain():
    """Verify deterministic SHA-256 event chaining (ADR-007)."""
    events1 = [
        {"id": "ev1", "action": "ingest", "doc": "VNM_2023"},
        {"id": "ev2", "action": "audit_discrepancy", "finding": "none"},
    ]
    events2 = [
        {"id": "ev1", "action": "ingest", "doc": "VNM_2023"},
        {"id": "ev2", "action": "audit_discrepancy", "finding": "none"},
    ]
    events_tampered = [
        {"id": "ev1", "action": "ingest", "doc": "VNM_2023"},
        {"id": "ev2", "action": "audit_discrepancy", "finding": "TAMPERED"},
    ]

    hash1 = compute_tamper_evident_chain(events1)
    hash2 = compute_tamper_evident_chain(events2)
    hash_tampered = compute_tamper_evident_chain(events_tampered)

    assert len(hash1) == 64
    assert hash1 == hash2
    assert hash1 != hash_tampered


@pytest.mark.anyio
async def test_audit_packager_full_export():
    """Verify end-to-end export execution in AuditPackager."""
    packager = AuditPackager()

    req = AuditPackageRequest(
        documents=[
            PortfolioDocumentTarget(document_id="VNM_2023_AUDITED", entity="VNM", period="2023"),
        ],
        format=RegulatoryPackageFormat.BUNDLE,
        taxonomy_standard="US-GAAP-2024",
    )

    res = await packager.export_package(req)
    assert isinstance(res, AuditPackageResponse)
    assert res.format == RegulatoryPackageFormat.BUNDLE
    assert res.file_size_bytes > 0
    assert len(res.sha256_checksum) == 64
    assert len(res.tamper_evident_root_hash) == 64
    assert len(res.manifest_items) == 1


# ============================================================================
# Task 3 Tests: REST Endpoint POST /api/v1/audit/export-package
# ============================================================================

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)
REPO_ROOT = Path(__file__).resolve().parents[3]
SAMPLE_PDF = str(REPO_ROOT / "benchmarks" / "data" / "VNM_BCTC_2023_AUDITED.pdf")


@pytest.fixture(scope="module")
def setup_packager_documents():
    """Ingest test document into vector store."""
    payload = {
        "document_id": "VNM_2023_PKG",
        "file_path": SAMPLE_PDF,
        "render_dpi": 150,
    }
    res = client.post("/api/v1/documents/ingest", json=payload)
    assert res.status_code == 200, f"Failed to ingest: {res.text}"


def test_api_export_package_success(setup_packager_documents):
    """Verify live endpoint POST /api/v1/audit/export-package returns 200 with valid package payload."""
    payload = {
        "documents": [
            {"document_id": "VNM_2023_PKG", "entity": "VNM", "period": "2023"},
        ],
        "format": "bundle",
        "taxonomy_standard": "US-GAAP-2024",
        "include_discrepancy_report": True,
        "include_grounding_manifest": True,
    }
    res = client.post("/api/v1/audit/export-package", json=payload)
    assert res.status_code == 200, f"Export package failed: {res.text}"
    data = res.json()

    assert data["format"] == "bundle"
    assert "file_bytes_base64" in data
    assert data["file_size_bytes"] > 0
    assert len(data["sha256_checksum"]) == 64
    assert len(data["tamper_evident_root_hash"]) == 64
    assert len(data["manifest_items"]) == 1


def test_api_export_package_path_traversal():
    """Verify path traversal attack in export package is blocked."""
    payload = {
        "documents": [
            {"document_id": "../../etc/passwd", "entity": "EVIL", "period": "2023"},
        ],
    }
    res = client.post("/api/v1/audit/export-package", json=payload)
    assert res.status_code in [400, 422]


def test_api_export_package_missing_document(setup_packager_documents):
    """Verify 404 is returned when target document does not exist."""
    payload = {
        "documents": [
            {"document_id": "MISSING_DOC_777"},
        ],
    }
    res = client.post("/api/v1/audit/export-package", json=payload)
    assert res.status_code == 404
    assert "MISSING_DOC_777" in res.json()["detail"]


def test_api_export_package_unauthorized():
    """Verify invalid JWT token returns 401 Unauthorized."""
    payload = {
        "documents": [
            {"document_id": "VNM_2023_PKG"},
        ],
    }
    headers = {"Authorization": "Bearer invalid.jwt.token"}
    res = client.post("/api/v1/audit/export-package", json=payload, headers=headers)
    assert res.status_code == 401
