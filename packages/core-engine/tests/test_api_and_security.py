"""
TDD & Security Audit Test Suite for FinSight Core Daemon
Tests API endpoints, Visual RAG retrieval accuracy, Bounding Box normalization,
and actively attacks the daemon with path traversal and injection payloads.
Governed by AGENTS.md Rule 13.
"""

import pytest
from pathlib import Path
from fastapi.testclient import TestClient

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from main import app
from contracts import is_path_safe, BoundingBox

client = TestClient(app)

REPO_ROOT = Path(__file__).resolve().parents[3]
SAMPLE_PDF = str(REPO_ROOT / "benchmarks" / "data" / "VNM_BCTC_2023_AUDITED.pdf")


def test_health_endpoint():
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "mlx" in data["hardware_detected"] or "cpu" in data["hardware_detected"]


def test_ingest_and_query_chart_flow():
    """Verify full end-to-end flow: ingest BCTC PDF and query visual chart."""
    # 1. Ingest
    ingest_payload = {
        "file_path": SAMPLE_PDF,
        "document_id": "VNM_2023_TEST_FLOW",
        "render_dpi": 150,
    }
    ingest_res = client.post("/api/v1/documents/ingest", json=ingest_payload)
    assert ingest_res.status_code == 200
    ingest_data = ingest_res.json()
    assert ingest_data["total_pages"] == 2
    assert ingest_data["indexed_vectors_count"] == 2

    # 2. Query chart on Page 1
    query_payload = {
        "document_id": "VNM_2023_TEST_FLOW",
        "query_text": "Cơ cấu doanh thu theo biểu đồ thị trường năm 2023 thay đổi ra sao?",
        "top_k_pages": 1,
    }
    query_res = client.post("/api/v1/query", json=query_payload)
    assert query_res.status_code == 200
    query_data = query_res.json()

    # Visual retrieval must locate Page 1 (where the chart is)
    assert 1 in query_data["retrieved_page_numbers"]
    assert len(query_data["evidences"]) >= 1

    ev = query_data["evidences"][0]
    assert ev["page_number"] == 1
    assert "Biểu đồ" in ev["label"]

    # Verify Bounding Box coordinates are valid and normalized [0, 1000]
    bbox = ev["bounding_box"]
    assert 0 <= bbox["ymin"] < bbox["ymax"] <= 1000
    assert 0 <= bbox["xmin"] < bbox["xmax"] <= 1000


def test_query_footnote_flow():
    """Verify visual retrieval correctly routes footnote query to Page 2."""
    query_payload = {
        "document_id": "VNM_2023_TEST_FLOW",
        "query_text": "Thuyết minh số 4 về tiền gửi ngân hàng và lãi suất như thế nào?",
        "top_k_pages": 1,
    }
    query_res = client.post("/api/v1/query", json=query_payload)
    assert query_res.status_code == 200
    data = query_res.json()

    # Must retrieve Page 2
    assert 2 in data["retrieved_page_numbers"]
    ev = data["evidences"][0]
    assert ev["page_number"] == 2
    assert "Thuyết minh" in ev["label"]
    assert ev["confidence"] >= 0.95


# ==============================================================================
# SECURITY & INJECTION DEFENSE TESTS (AGENTS.md Rule 13)
# ==============================================================================

def test_security_path_traversal_in_file_path():
    """Attack: Attempt arbitrary host file read via path traversal."""
    traversal_payloads = [
        "/etc/passwd",
        "../../../../../../etc/shadow",
        "~/.ssh/id_rsa",
        "/var/run/docker.sock",
    ]
    for bad_path in traversal_payloads:
        res = client.post("/api/v1/documents/ingest", json={"file_path": bad_path})
        # Must fail closed with 422 Validation Error
        assert res.status_code == 422
        assert "Access denied" in res.text or "authorized" in res.text


def test_security_path_traversal_in_doc_id():
    """Attack: Attempt directory breakout via document_id parameter."""
    bad_doc_ids = [
        "../../malicious",
        "doc/sub/../../escape",
        "doc;rm -rf /",
        "doc\0nullbyte",
    ]
    for bad_id in bad_doc_ids:
        res = client.post("/api/v1/query", json={
            "document_id": bad_id,
            "query_text": "Hỏi đáp tài chính bình thường",
        })
        assert res.status_code == 422
        assert "strictly alphanumeric" in res.text


def test_security_bounding_box_invariants():
    """Verify Bounding Box enforces geometric invariants (ymax > ymin, xmax > xmin)."""
    # Inverted vertical
    with pytest.raises(ValueError):
        BoundingBox(ymin=500, xmin=100, ymax=400, xmax=300)

    # Inverted horizontal
    with pytest.raises(ValueError):
        BoundingBox(ymin=100, xmin=500, ymax=200, xmax=400)

    # Out of 0-1000 range
    with pytest.raises(ValueError):
        BoundingBox(ymin=-10, xmin=100, ymax=200, xmax=300)

    with pytest.raises(ValueError):
        BoundingBox(ymin=100, xmin=100, ymax=200, xmax=1050)
