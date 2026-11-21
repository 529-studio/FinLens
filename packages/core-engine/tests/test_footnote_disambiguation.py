"""
FinSight Sprint 8 Footnote Disambiguation Tests
Verifies extraction of Thuyết minh BCTC citations, endpoint validation, and security traversal defense.
Governed by Sprint 8 Task S8-04, AGENTS.md Rule 13 (Security & Injection Defense).
"""

import pytest
from pathlib import Path
from fastapi.testclient import TestClient

import sys
REPO_ROOT = Path(__file__).resolve().parents[3]
ENGINE_SRC = REPO_ROOT / "packages" / "core-engine" / "src"
if str(ENGINE_SRC) not in sys.path:
    sys.path.insert(0, str(ENGINE_SRC))

from main import app

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_test_document():
    pdf_path = REPO_ROOT / "benchmarks" / "data" / "VNM_BCTC_2023_AUDITED.pdf"
    if pdf_path.exists():
        with open(pdf_path, "rb") as f:
            client.post(
                "/api/v1/documents/upload",
                files={"file": ("VNM_BCTC_2023_AUDITED.pdf", f, "application/pdf")},
                data={"document_id": "VNM_FOOTNOTE_TEST"}
            )


def test_footnote_extraction_endpoint_flow():
    """
    Verifies /api/v1/query/footnotes returns structured mappings
    linking balance sheet items to Thuyết minh citations.
    """
    resp = client.post(
        "/api/v1/query/footnotes",
        json={
            "document_id": "VNM_FOOTNOTE_TEST",
            "line_items": ["Tiền và các khoản tương đương tiền", "Đầu tư tài chính ngắn hạn"]
        }
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()

    assert data["document_id"] == "VNM_FOOTNOTE_TEST"
    assert data["total_footnotes"] >= 1
    assert len(data["footnotes"]) >= 1

    fn = data["footnotes"][0]
    assert "footnote_number" in fn
    assert "footnote_title" in fn
    assert "bounding_box" in fn
    assert "page_number" in fn
    assert fn["page_number"] == 2
    assert fn["footnote_number"] == "4"
    assert "tiền gửi" in fn["summary"].lower()


def test_footnote_security_path_traversal():
    """
    Rule 13B: Probes path traversal on /api/v1/query/footnotes.
    """
    resp = client.post(
        "/api/v1/query/footnotes",
        json={"document_id": "../../etc/passwd"}
    )
    assert resp.status_code == 400 or resp.status_code == 422
    assert "Access denied" in resp.text or "Invalid" in resp.text
