"""
TDD Test Suite for Multi-Document Comparative Visual RAG (Sprint 7 Task S7-02)
Tests comparative retrieval, multi-document grounding, YoY synthesis, and path traversal defense.
Governed by AGENTS.md Rules 1, 13, and 14.
"""

import pytest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from main import app
from contracts import ComparativeQueryRequest, ComparativeQueryResponse

client = TestClient(app)

REPO_ROOT = Path(__file__).resolve().parents[3]
SAMPLE_PDF = str(REPO_ROOT / "benchmarks" / "data" / "VNM_BCTC_2023_AUDITED.pdf")


@pytest.fixture(scope="module", autouse=True)
def setup_comparative_documents():
    """Ingest two fiscal documents for multi-document comparative testing."""
    for doc_id in ["VNM_2022_COMP", "VNM_2023_COMP"]:
        payload = {
            "file_path": SAMPLE_PDF,
            "document_id": doc_id,
            "render_dpi": 150,
        }
        res = client.post("/api/v1/documents/ingest", json=payload)
        assert res.status_code == 200, f"Failed to ingest setup document {doc_id}: {res.text}"


def test_comparative_query_success():
    """Verify multi-document retrieval, YoY synthesis, and multi-document visual grounding."""
    req_payload = {
        "document_ids": ["VNM_2022_COMP", "VNM_2023_COMP"],
        "query_text": "So sánh cơ cấu doanh thu nội địa và xuất khẩu giữa hai năm tài chính",
        "top_k_per_doc": 1,
        "inference_mode": "auto",
    }
    res = client.post("/api/v1/query/comparative", json=req_payload)
    assert res.status_code == 200, f"Comparative query failed: {res.text}"
    data = res.json()

    assert data["document_ids"] == ["VNM_2022_COMP", "VNM_2023_COMP"]
    assert "retrieved_pages" in data
    assert "VNM_2022_COMP" in data["retrieved_pages"]
    assert "VNM_2023_COMP" in data["retrieved_pages"]
    assert 1 in data["retrieved_pages"]["VNM_2022_COMP"]
    assert 1 in data["retrieved_pages"]["VNM_2023_COMP"]

    # Verify evidences contain citations from BOTH documents
    evidences = data["evidences"]
    assert len(evidences) >= 2, "Must contain at least 1 evidence per document"
    doc_ids_in_evidence = {ev.get("document_id") for ev in evidences}
    assert "VNM_2022_COMP" in doc_ids_in_evidence
    assert "VNM_2023_COMP" in doc_ids_in_evidence

    # Verify bounding box validity on 0-1000 scale
    for ev in evidences:
        bbox = ev["bounding_box"]
        assert 0 <= bbox["ymin"] < bbox["ymax"] <= 1000
        assert 0 <= bbox["xmin"] < bbox["xmax"] <= 1000
        assert ev["confidence"] >= 0.8

    # Verify answer contains comparative synthesis
    assert len(data["answer"]) > 50
    assert any(w in data["answer"].lower() for w in ["so sánh", "tăng trưởng", "doanh thu", "vnm_2022", "vnm_2023", "2022", "2023"])

    # Verify metrics structure
    assert isinstance(data["comparative_metrics"], list)
    assert len(data["comparative_metrics"]) >= 1
    metric = data["comparative_metrics"][0]
    assert "metric" in metric
    assert "VNM_2022_COMP" in metric or "doc_values" in metric
    assert data["latency_ms"] > 0


def test_comparative_query_cloud_inference_mode():
    """Verify that comparative query works in cloud inference mode."""
    payload = {
        "document_ids": ["VNM_2022_COMP", "VNM_2023_COMP"],
        "query_text": "So sánh doanh thu thuần và cơ cấu thị trường",
        "top_k_per_doc": 1,
        "inference_mode": "cloud",
    }
    res = client.post("/api/v1/query/comparative", json=payload)
    assert res.status_code == 200, f"Cloud comparative query failed: {res.text}"
    res_data = res.json()
    assert res_data["document_ids"] == ["VNM_2022_COMP", "VNM_2023_COMP"]
    assert len(res_data["comparative_metrics"]) >= 2
    assert len(res_data["evidences"]) >= 2
    for ev in res_data["evidences"]:
        assert ev["document_id"] in ["VNM_2022_COMP", "VNM_2023_COMP"]



def test_comparative_query_traversal_rejection():
    """Verify that path traversal in document_ids list is rejected with 400/422."""
    payload = {
        "document_ids": ["../../evil_escape", "VNM_2023_COMP"],
        "query_text": "So sánh doanh thu",
    }
    res = client.post("/api/v1/query/comparative", json=payload)
    assert res.status_code in [400, 422]


def test_comparative_query_insufficient_documents():
    """Verify that specifying fewer than 2 documents is rejected with 400/422."""
    payload = {
        "document_ids": ["VNM_2023_COMP"],
        "query_text": "So sánh doanh thu",
    }
    res = client.post("/api/v1/query/comparative", json=payload)
    assert res.status_code in [400, 422]


def test_comparative_query_duplicate_documents():
    """Verify that duplicate document IDs in comparison are rejected."""
    payload = {
        "document_ids": ["VNM_2023_COMP", "VNM_2023_COMP"],
        "query_text": "So sánh doanh thu",
    }
    res = client.post("/api/v1/query/comparative", json=payload)
    assert res.status_code in [400, 422]


def test_comparative_query_missing_document():
    """Verify that referencing non-existent document ID returns 404."""
    payload = {
        "document_ids": ["NON_EXISTENT_DOC_9999", "VNM_2023_COMP"],
        "query_text": "So sánh doanh thu",
    }
    res = client.post("/api/v1/query/comparative", json=payload)
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_cloud_router_analyze_comparative_direct():
    """Verify that CloudRouter analyze_comparative works offline/without keys."""
    import asyncio
    from cloud_router import CloudRouter
    cr = CloudRouter()
    doc_pages = {
        "DOC_A": [("/tmp/fake_page1.png", 1)],
        "DOC_B": [("/tmp/fake_page2.png", 2)],
    }
    with patch("cloud_router.is_path_safe", return_value=True):
        res = asyncio.run(cr.analyze_comparative(doc_pages, "So sánh doanh thu và lợi nhuận"))
    assert "answer" in res
    assert "comparative_metrics" in res
    assert len(res["comparative_metrics"]) >= 2
    assert "evidences" in res
    for ev in res["evidences"]:
        assert "document_id" in ev
        assert ev["document_id"] in ["DOC_A", "DOC_B"]


