"""
FinSight Sprint 8 WebSocket Streaming Inference Tests
Tests real-time progressive token streaming and security validation over /ws/query/stream.
Governed by Sprint 8 Task S8-03, AGENTS.md Rule 13 (Security & Injection Defense).
"""

import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

import sys
REPO_ROOT = Path(__file__).resolve().parents[3]
ENGINE_SRC = REPO_ROOT / "packages" / "core-engine" / "src"
if str(ENGINE_SRC) not in sys.path:
    sys.path.insert(0, str(ENGINE_SRC))

from main import app
from renderer import PdfRenderer

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_test_document():
    """Ensure sample document is rendered and indexed for testing."""
    pdf_path = REPO_ROOT / "benchmarks" / "data" / "VNM_BCTC_2023_AUDITED.pdf"
    if pdf_path.exists():
        with open(pdf_path, "rb") as f:
            client.post(
                "/api/v1/documents/upload",
                files={"file": ("VNM_BCTC_2023_AUDITED.pdf", f, "application/pdf")},
                data={"document_id": "VNM_STREAM_TEST"}
            )


def test_websocket_streaming_inference_flow():
    """
    Verifies full streaming lifecycle:
    1. Client connects to /ws/query/stream
    2. Sends query payload
    3. Receives progressive token events
    4. Receives evidence event with bounding boxes
    5. Receives done event with final answer
    """
    with client.websocket_connect("/ws/query/stream") as websocket:
        request_payload = {
            "document_id": "VNM_STREAM_TEST",
            "query_text": "Cơ cấu doanh thu nội địa năm 2023?",
            "inference_mode": "auto"
        }
        websocket.send_text(json.dumps(request_payload))

        tokens = []
        evidences = []
        done_received = False
        final_answer = ""

        # Receive streamed messages
        while not done_received:
            raw_msg = websocket.receive_text()
            data = json.loads(raw_msg)
            event_type = data.get("event")

            if event_type == "token":
                tokens.append(data.get("token", ""))
            elif event_type == "evidence":
                evidences = data.get("evidences", [])
            elif event_type == "done":
                done_received = True
                final_answer = data.get("answer", "")
            elif event_type == "error":
                pytest.fail(f"Unexpected error event received: {data.get('error')}")

        assert len(tokens) > 0, "Expected at least 1 streamed token chunk"
        assert done_received is True, "Expected 'done' event at end of stream"
        assert len(final_answer) > 0, "Expected non-empty final answer"
        assert "".join(tokens) == final_answer, "Concatenated tokens must match final answer"
        assert len(evidences) > 0, "Expected visual grounding evidence in stream"
        assert "ymin" in evidences[0] and "xmin" in evidences[0]


def test_websocket_streaming_security_path_traversal():
    """
    Rule 13B Security Defense:
    Probes path traversal injection against /ws/query/stream.
    Must return an error event and not expose arbitrary filesystem paths.
    """
    with client.websocket_connect("/ws/query/stream") as websocket:
        malicious_payload = {
            "document_id": "../../etc/passwd",
            "query_text": "Sensitive data extraction attack"
        }
        websocket.send_text(json.dumps(malicious_payload))

        raw_msg = websocket.receive_text()
        data = json.loads(raw_msg)

        assert data.get("event") == "error", "Expected error event on path traversal attempt"
        assert "Access denied" in data.get("error", "") or "Invalid" in data.get("error", "")
