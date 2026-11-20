"""
TDD & Security Audit Test Suite for FinSight Core Daemon
Tests API endpoints, Visual RAG retrieval accuracy, Bounding Box normalization,
and actively attacks the daemon with path traversal and injection payloads.
Governed by AGENTS.md Rule 13.
"""

import pytest
from pathlib import Path
from unittest.mock import patch
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


# ==============================================================================
# S3-01: MLX LOCAL ENGINE & MODEL MANAGEMENT TESTS
# ==============================================================================

def test_mlx_model_status_endpoint():
    res = client.get("/api/v1/models/mlx/status")
    assert res.status_code == 200
    data = res.json()
    assert "model_id" in data
    assert "mlx-community/Qwen2.5-VL-7B-Instruct-4bit" in data["model_id"]
    assert "is_cached" in data
    assert "memory_usage" in data
    assert "hardware_capability" in data
    assert data["memory_ceiling_gb"] == 6.0


def test_mlx_model_download_unconfirmed_rejected():
    # Attempting to download without confirm=True must be rejected with 400 Bad Request
    res = client.post("/api/v1/models/mlx/download", json={
        "model_id": "mlx-community/Qwen2.5-VL-7B-Instruct-4bit",
        "confirm": False,
    })
    assert res.status_code == 400
    assert "confirmation" in res.json()["detail"].lower()


def test_mlx_model_download_confirmed():
    with patch("main.model_manager.download_model") as mock_dl:
        mock_dl.return_value = Path("/tmp/mock_mlx_model")
        res = client.post("/api/v1/models/mlx/download", json={
            "model_id": "mlx-community/Qwen2.5-VL-7B-Instruct-4bit",
            "confirm": True,
        })
        assert res.status_code == 200
        data = res.json()
        assert data["status"] in ("downloaded", "cached")
        assert "model_id" in data


# ==============================================================================
# S3-03: LANCEDB STORE & DOCUMENT MANAGEMENT ENDPOINTS
# ==============================================================================

def test_store_stats_endpoint():
    res = client.get("/api/v1/store/stats")
    assert res.status_code == 200
    data = res.json()
    assert "db_path" in data
    assert "total_documents" in data
    assert "total_pages" in data
    assert "disk_size_bytes" in data
    assert data["vector_dimension"] == 128


def test_documents_list_and_delete_endpoint():
    # 1. Ingest document first
    ingest_payload = {
        "file_path": SAMPLE_PDF,
        "document_id": "VNM_DELETE_FLOW",
        "render_dpi": 150,
    }
    client.post("/api/v1/documents/ingest", json=ingest_payload)

    # 2. List documents
    res_list = client.get("/api/v1/documents")
    assert res_list.status_code == 200
    data_list = res_list.json()
    assert "VNM_DELETE_FLOW" in data_list["documents"]
    assert data_list["total"] >= 1

    # 3. Delete document
    res_del = client.delete("/api/v1/documents/VNM_DELETE_FLOW")
    assert res_del.status_code == 200
    assert res_del.json()["deleted"] is True

    # 4. Verify no longer listed
    res_list_after = client.get("/api/v1/documents")
    assert "VNM_DELETE_FLOW" not in res_list_after.json()["documents"]


def test_document_delete_security_traversal_rejected():
    res = client.delete("/api/v1/documents/..%2F..%2Fetc%2Fpasswd")
    # Path traversal must be blocked with 400 Bad Request or 404
    assert res.status_code in (400, 404, 422)


# ==============================================================================
# S3-02: CLOUD BYOK ROUTER ENDPOINTS & ZERO-LEAK TESTS
# ==============================================================================

def test_cloud_status_endpoint():
    res = client.get("/api/v1/models/cloud/status")
    assert res.status_code == 200
    data = res.json()
    assert "available_providers" in data
    assert "anthropic" in data["available_providers"]
    assert "azure" in data["available_providers"]
    assert "openai" in data["available_providers"]
    assert "providers" in data
    assert "anthropic" in data["providers"]
    assert "configured" in data["providers"]["anthropic"]
    assert "model" in data["providers"]["anthropic"]


def test_cloud_key_update_endpoint_zero_leak():
    secret_key = "sk-ant-api03-TOP_SECRET_FINSIGHT_TEST_KEY_9999"
    res = client.post("/api/v1/models/cloud/keys", json={
        "provider": "anthropic",
        "api_key": secret_key,
    })
    assert res.status_code == 200
    res_text = res.text
    # Zero-Leak Rule 2: Secret key must NEVER appear in response body
    assert secret_key not in res_text
    data = res.json()
    assert data["provider"] == "anthropic"
    assert data["status"] == "configured"

    # Status must now reflect configured=True without leaking the key
    status_res = client.get("/api/v1/models/cloud/status")
    assert status_res.status_code == 200
    assert secret_key not in status_res.text
    status_data = status_res.json()
    assert status_data["providers"]["anthropic"]["configured"] is True


def test_cloud_key_update_invalid_provider_rejected():
    res = client.post("/api/v1/models/cloud/keys", json={
        "provider": "unsupported_provider",
        "api_key": "some-key",
    })
    # Literal validation should fail with 422
    assert res.status_code == 422


def test_query_with_cloud_inference_mode():
    query_payload = {
        "document_id": "VNM_2023_TEST_FLOW",
        "query_text": "Cơ cấu doanh thu theo biểu đồ thị trường năm 2023 thay đổi ra sao?",
        "top_k_pages": 1,
        "inference_mode": "cloud",
    }
    res = client.post("/api/v1/query", json=query_payload)
    assert res.status_code == 200
    data = res.json()
    assert "cloud" in data["engine_used"].lower()
    assert len(data["evidences"]) >= 1
    bbox = data["evidences"][0]["bounding_box"]
    assert 0 <= bbox["ymin"] < bbox["ymax"] <= 1000
    assert 0 <= bbox["xmin"] < bbox["xmax"] <= 1000


def test_websocket_broadcast_interop():
    """Verify that WebSocket broadcast relays citation jump events between peer clients."""
    with client.websocket_connect("/ws") as ws1:
        with client.websocket_connect("/ws") as ws2:
            payload = '{"type":"JUMP_TO_SOURCE","citationId":"test-citation-123"}'
            ws1.send_text(payload)
            received = ws2.receive_text()
            assert received == payload




