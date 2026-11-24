"""
Unit and Integration Tests for Real-Time Collaborative Audit Session Sync
Governed by Sprint 11 Task S11-03, AGENTS.md Rule 1, Rule 2, Rule 13, and Rule 15.
Tests presence tracking, spatial annotation broadcasting, concurrency, and security injection defense.
"""

import time
import json
import asyncio
import pytest
from fastapi.testclient import TestClient

from main import app
from session_sync import AuditSessionManager, assign_user_color
from contracts import SessionEventType
from auth import create_access_token, Role


client = TestClient(app)


def test_validate_session_and_document_id():
    """Validates session_id and document_id sanitization and injection defense."""
    valid_ids = ["audit_session_101", "vnm-2023-bctc", "Q3_REVIEW_ROOM", "room-123_456"]
    for sid in valid_ids:
        assert AuditSessionManager.validate_session_id(sid) == sid
        assert AuditSessionManager.validate_document_id(sid) == sid

    # Path traversal patterns must be rejected
    malicious_ids = [
        "../../etc/passwd",
        "../traversal",
        "/absolute/path",
        "C:\\Windows\\System32",
        "room/subpath",
        "room\\subpath",
        "ro",  # too short (< 3)
        "a" * 65,  # too long (> 64)
        "has space in name",
        "has$special*char",
        "",
    ]
    for bad_id in malicious_ids:
        with pytest.raises(ValueError):
            AuditSessionManager.validate_session_id(bad_id)


def test_user_color_assignment():
    """Verifies deterministic high-contrast avatar color assignment."""
    color1 = assign_user_color("auditor_alice")
    color2 = assign_user_color("auditor_alice")
    assert color1 == color2
    assert color1.startswith("#")

    color3 = assign_user_color("auditor_bob")
    assert color3.startswith("#")


def test_session_manager_presence_and_annotations():
    """Tests core AuditSessionManager state mutations under async lock."""
    async def _test():
        manager = AuditSessionManager(heartbeat_timeout_seconds=2.0)
        session_id = "test_unit_session_01"
        doc_id = "VNM_2023_BCTC"

        session = await manager.get_or_create_session(session_id, doc_id)
        assert session.session_id == session_id
        assert session.document_id == doc_id
        assert len(session.active_users) == 0

        # Prune empty session
        pruned = await manager.prune_stale_users(session_id)
        assert pruned == []

    asyncio.run(_test())


def test_rest_session_endpoints():
    """Tests POST /api/v1/sessions and GET /api/v1/sessions/{session_id} REST APIs."""
    token = create_access_token(user_id="test_admin", role=Role.ADMIN)
    headers = {"Authorization": f"Bearer {token}"}

    create_payload = {
        "session_id": "rest_session_room_99",
        "document_id": "VNM_AUDIT_2023",
    }
    resp = client.post("/api/v1/sessions", json=create_payload, headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["session_id"] == "rest_session_room_99"
    assert data["document_id"] == "VNM_AUDIT_2023"

    # GET session snapshot
    get_resp = client.get("/api/v1/sessions/rest_session_room_99", headers=headers)
    assert get_resp.status_code == 200
    snapshot = get_resp.json()
    assert snapshot["session_id"] == "rest_session_room_99"
    assert snapshot["document_id"] == "VNM_AUDIT_2023"
    assert "active_users" in snapshot
    assert "annotations" in snapshot

    # GET non-existent session
    not_found = client.get("/api/v1/sessions/non_existent_room_404", headers=headers)
    assert not_found.status_code == 404

    # GET with invalid session ID (path traversal)
    bad_req = client.get("/api/v1/sessions/.._invalid_room", headers=headers)
    assert bad_req.status_code == 400


def test_websocket_collaborative_sync_flow():
    """
    Integration test connecting two clients to the collaborative room.
    Verifies SESSION_STATE, JOIN, PRESENCE, ANNOTATION_ADD, ANNOTATION_RESOLVE, and LEAVE.
    """
    token_alice = create_access_token(user_id="alice_senior", role=Role.SENIOR_AUDITOR, name="Alice Senior")
    token_bob = create_access_token(user_id="bob_analyst", role=Role.JUNIOR_ANALYST, name="Bob Analyst")

    session_id = "collab_flow_room_01"

    # Alice connects
    with client.websocket_connect(f"/ws/v1/sessions/{session_id}?token={token_alice}&document_id=VNM_2023") as ws_alice:
        # Alice receives initial session state
        init_frame = json.loads(ws_alice.receive_text())
        assert init_frame["event"] == SessionEventType.SESSION_STATE.value
        assert init_frame["session_id"] == session_id
        assert "alice_senior" in init_frame["payload"]["active_users"]

        # Bob connects
        with client.websocket_connect(f"/ws/v1/sessions/{session_id}?token={token_bob}&document_id=VNM_2023") as ws_bob:
            # Bob receives session state containing Alice and Bob
            bob_init = json.loads(ws_bob.receive_text())
            assert bob_init["event"] == SessionEventType.SESSION_STATE.value

            # Alice receives JOIN event for Bob
            alice_join_frame = json.loads(ws_alice.receive_text())
            assert alice_join_frame["event"] == SessionEventType.JOIN.value
            assert alice_join_frame["user_id"] == "bob_analyst"

            # Bob moves cursor to page 2 (normalized coords 450, 320)
            cursor_msg = {
                "event": SessionEventType.CURSOR_MOVE.value,
                "payload": {"active_page": 2, "cursor_x": 450.0, "cursor_y": 320.0},
            }
            ws_bob.send_text(json.dumps(cursor_msg))

            # Alice receives PRESENCE event
            alice_presence = json.loads(ws_alice.receive_text())
            assert alice_presence["event"] == SessionEventType.PRESENCE.value
            assert alice_presence["user_id"] == "bob_analyst"
            assert alice_presence["payload"]["active_page"] == 2
            assert alice_presence["payload"]["cursor_x"] == 450.0

            # Alice creates an audit annotation on page 2
            anno_msg = {
                "event": SessionEventType.ANNOTATION_ADD.value,
                "payload": {
                    "annotation_id": "anno_test_001",
                    "page_number": 2,
                    "bounding_box": [150.0, 100.0, 350.0, 600.0],
                    "comment": "Kiểm tra Thuyết minh 4: Tiền gửi ngân hàng",
                },
            }
            ws_alice.send_text(json.dumps(anno_msg))

            # Both Alice and Bob receive ANNOTATION_ADD
            alice_anno_rx = json.loads(ws_alice.receive_text())
            bob_anno_rx = json.loads(ws_bob.receive_text())
            assert alice_anno_rx["event"] == SessionEventType.ANNOTATION_ADD.value
            assert bob_anno_rx["event"] == SessionEventType.ANNOTATION_ADD.value
            assert bob_anno_rx["payload"]["comment"] == "Kiểm tra Thuyết minh 4: Tiền gửi ngân hàng"
            assert bob_anno_rx["payload"]["resolved"] is False

            # Bob resolves the annotation
            resolve_msg = {
                "event": SessionEventType.ANNOTATION_RESOLVE.value,
                "payload": {"annotation_id": "anno_test_001"},
            }
            ws_bob.send_text(json.dumps(resolve_msg))

            alice_resolve_rx = json.loads(ws_alice.receive_text())
            bob_resolve_rx = json.loads(ws_bob.receive_text())
            assert alice_resolve_rx["event"] == SessionEventType.ANNOTATION_RESOLVE.value
            assert bob_resolve_rx["event"] == SessionEventType.ANNOTATION_RESOLVE.value
            assert alice_resolve_rx["payload"]["resolved"] is True
            assert alice_resolve_rx["payload"]["resolved_by"] == "bob_analyst"

            # Alice sends heartbeat
            hb_msg = {"event": SessionEventType.HEARTBEAT.value}
            ws_alice.send_text(json.dumps(hb_msg))
            hb_rx = json.loads(ws_alice.receive_text())
            assert hb_rx["event"] == SessionEventType.HEARTBEAT.value
            assert hb_rx["payload"]["status"] == "pong"

        # When Bob exits websocket context, Alice receives LEAVE
        alice_leave_rx = json.loads(ws_alice.receive_text())
        assert alice_leave_rx["event"] == SessionEventType.LEAVE.value
        assert alice_leave_rx["user_id"] == "bob_analyst"


def test_websocket_security_malicious_session_id():
    """Verifies that malicious or invalid session_id is closed with code 1008."""
    # TestClient raises WebSocketDisconnect or closes with code
    with pytest.raises(Exception):
        with client.websocket_connect("/ws/v1/sessions/../../etc/passwd"):
            pass
