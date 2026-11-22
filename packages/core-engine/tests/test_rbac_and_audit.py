"""
FinTrace Enterprise RBAC & Tamper-Evident Audit Logging Test Suite
Validates JWT token encoding/decoding, role permission matrices, fail-closed access control,
cryptographic SHA-256 event chaining, tamper detection, zero-leak credential sanitization,
and regulatory audit log export APIs.
Governed by Sprint 10 Task S10-03, AGENTS.md Rule 1, Rule 2, Rule 3, Rule 13, and Rule 15.
"""

import os
import json
import time
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from auth import (
    Role,
    Permission,
    User,
    create_access_token,
    decode_access_token,
    ROLE_PERMISSIONS,
    JWT_SECRET,
)
from audit_logger import (
    AuditLogger,
    AuditEvent,
    compute_record_hash,
    GENESIS_HASH,
)
from main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def temp_audit_dir(tmp_path):
    audit_dir = tmp_path / "test_audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    return audit_dir


@pytest.fixture
def isolated_logger(temp_audit_dir):
    return AuditLogger(log_dir=temp_audit_dir)


# ============================================================================
# 1. JWT & RBAC Claims Unit Tests
# ============================================================================

def test_jwt_create_and_decode_success():
    token = create_access_token(
        user_id="auditor_lead",
        role=Role.SENIOR_AUDITOR,
        name="Senior Financial Auditor",
        org="Vietcombank Internal Audit",
        expires_in_minutes=60,
    )

    user = decode_access_token(token)
    assert isinstance(user, User)
    assert user.user_id == "auditor_lead"
    assert user.role == Role.SENIOR_AUDITOR
    assert user.name == "Senior Financial Auditor"
    assert user.org == "Vietcombank Internal Audit"
    assert Permission.DOC_READ in user.permissions
    assert Permission.DOC_INGEST in user.permissions
    assert Permission.AUDIT_READ in user.permissions
    assert Permission.DOC_DELETE not in user.permissions
    assert Permission.ADMIN_CONFIG not in user.permissions


def test_jwt_tampered_signature_rejected():
    token = create_access_token(
        user_id="attacker",
        role=Role.ADMIN,
    )
    # Alter the last character of signature
    tampered_token = token[:-1] + ("A" if token[-1] != "A" else "B")

    with pytest.raises(Exception) as exc_info:
        decode_access_token(tampered_token)
    assert "Invalid token signature" in str(exc_info.value.detail)


def test_jwt_expired_token_rejected():
    # Issue a token with negative expiration (-10 minutes)
    expired_token = create_access_token(
        user_id="expired_user",
        role=Role.JUNIOR_ANALYST,
        expires_in_minutes=-10,
    )

    with pytest.raises(Exception) as exc_info:
        decode_access_token(expired_token)
    assert "Token has expired" in str(exc_info.value.detail)


def test_rbac_permission_matrix_enforcement():
    # Admin has all permissions
    admin_perms = ROLE_PERMISSIONS[Role.ADMIN]
    assert len(admin_perms) == 6
    assert Permission.DOC_DELETE in admin_perms
    assert Permission.ADMIN_CONFIG in admin_perms

    # Senior Auditor cannot delete or configure admin settings
    senior_perms = ROLE_PERMISSIONS[Role.SENIOR_AUDITOR]
    assert Permission.DOC_INGEST in senior_perms
    assert Permission.AUDIT_READ in senior_perms
    assert Permission.DOC_DELETE not in senior_perms
    assert Permission.ADMIN_CONFIG not in senior_perms

    # Junior Analyst cannot ingest, delete, or read audit logs
    junior_perms = ROLE_PERMISSIONS[Role.JUNIOR_ANALYST]
    assert Permission.DOC_READ in junior_perms
    assert Permission.TABLE_STITCH in junior_perms
    assert Permission.DOC_INGEST not in junior_perms
    assert Permission.AUDIT_READ not in junior_perms

    # Read-Only Reviewer has only DOC_READ
    reviewer_perms = ROLE_PERMISSIONS[Role.READ_ONLY_REVIEWER]
    assert reviewer_perms == {Permission.DOC_READ}


# ============================================================================
# 2. Cryptographic SHA-256 Audit Logger Tests
# ============================================================================

def test_tamper_evident_audit_log_chain_verification(isolated_logger):
    # Log 5 sequential actions
    e1 = isolated_logger.log_event("user1", "admin", "AUTH_LOGIN")
    e2 = isolated_logger.log_event("user1", "admin", "DOC_INGEST", document_id="VNM_2023")
    e3 = isolated_logger.log_event("analyst2", "junior_analyst", "DOC_QUERY", document_id="VNM_2023")
    e4 = isolated_logger.log_event("auditor3", "senior_auditor", "TABLE_STITCH", document_id="VNM_2023")
    e5 = isolated_logger.log_event("auditor3", "senior_auditor", "AUDIT_EXPORT")

    assert e1.sequence_id == 0
    assert e1.prev_hash == GENESIS_HASH
    assert e2.sequence_id == 1
    assert e2.prev_hash == e1.record_hash
    assert e3.prev_hash == e2.record_hash
    assert e4.prev_hash == e3.record_hash
    assert e5.prev_hash == e4.record_hash

    is_valid, count, err = isolated_logger.verify_chain()
    assert is_valid is True
    assert count == 5
    assert err is None


def test_tamper_evident_audit_log_detects_tampering(isolated_logger):
    isolated_logger.log_event("u1", "admin", "DOC_INGEST", document_id="DOC_A")
    isolated_logger.log_event("u2", "senior_auditor", "DOC_QUERY", document_id="DOC_A")
    isolated_logger.log_event("u3", "admin", "DOC_DELETE", document_id="DOC_A")

    # Verify initial valid state
    is_valid, count, _ = isolated_logger.verify_chain()
    assert is_valid is True
    assert count == 3

    # Tamper with record 1 (change action from DOC_QUERY to MALICIOUS_ACTION)
    lines = []
    with open(isolated_logger.log_file, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f):
            if idx == 1:
                data = json.loads(line)
                data["action"] = "MALICIOUS_ALTERATION"
                lines.append(json.dumps(data) + "\n")
            else:
                lines.append(line)

    with open(isolated_logger.log_file, "w", encoding="utf-8") as f:
        f.writelines(lines)

    # Verification must fail and report tampering
    is_valid_after, count_after, err = isolated_logger.verify_chain()
    assert is_valid_after is False
    assert "Tampered record at line 2" in err


def test_audit_log_zero_leak_sanitization(isolated_logger):
    sensitive_details = {
        "api_key": "sk-ant-api03-super-secret-key",
        "user_password": "super_secret_password_123",
        "auth_token": "bearer_secret_token",
        "client_ip": "192.168.1.100",
    }
    event = isolated_logger.log_event("admin_user", "admin", "CONFIG_UPDATE", details=sensitive_details)

    assert event.details["api_key"] == "[REDACTED]"
    assert event.details["user_password"] == "[REDACTED]"
    assert event.details["auth_token"] == "[REDACTED]"
    assert event.details["client_ip"] == "192.168.1.100"


# ============================================================================
# 3. FastAPI Endpoint Integration & Role Enforcement Tests
# ============================================================================

def test_api_auth_login_and_me_flow(client):
    # Login as senior auditor
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": "auditor_lan", "password": "secure_password_2026", "role": "senior_auditor"},
    )
    assert login_resp.status_code == 200
    data = login_resp.json()
    token = data["access_token"]
    assert data["user"]["role"] == "senior_auditor"

    # Query /api/v1/auth/me with Bearer token
    headers = {"Authorization": f"Bearer {token}"}
    me_resp = client.get("/api/v1/auth/me", headers=headers)
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["user_id"] == "auditor_lan"
    assert me_data["role"] == "senior_auditor"
    assert "audit:read" in me_data["permissions"]
    assert "doc:ingest" in me_data["permissions"]
    assert "doc:delete" not in me_data["permissions"]


def test_api_fail_closed_role_enforcement_on_delete(client):
    # 1. Junior Analyst attempts document delete -> Must receive 403 Forbidden
    junior_token = create_access_token(user_id="junior_01", role=Role.JUNIOR_ANALYST)
    junior_headers = {"Authorization": f"Bearer {junior_token}"}
    del_junior = client.delete("/api/v1/documents/VNM_2023", headers=junior_headers)
    assert del_junior.status_code == 403
    assert "doc:delete" in del_junior.json()["detail"]

    # 2. Senior Auditor attempts document delete -> Must receive 403 Forbidden
    senior_token = create_access_token(user_id="senior_01", role=Role.SENIOR_AUDITOR)
    senior_headers = {"Authorization": f"Bearer {senior_token}"}
    del_senior = client.delete("/api/v1/documents/VNM_2023", headers=senior_headers)
    assert del_senior.status_code == 403
    assert "doc:delete" in del_senior.json()["detail"]

    # 3. Admin attempts document delete -> Allowed past RBAC gate (returns 404 if not found, not 403)
    admin_token = create_access_token(user_id="admin_01", role=Role.ADMIN)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    del_admin = client.delete("/api/v1/documents/VNM_2023", headers=admin_headers)
    assert del_admin.status_code in (200, 404)


def test_api_fail_closed_role_enforcement_on_ingest(client):
    # Junior Analyst attempts document ingest -> Must receive 403 Forbidden
    junior_token = create_access_token(user_id="junior_02", role=Role.JUNIOR_ANALYST)
    junior_headers = {"Authorization": f"Bearer {junior_token}"}
    ingest_payload = {
        "file_path": "/tmp/fintrace_test/sample.pdf",
        "document_id": "TEST_DOC",
    }
    resp = client.post("/api/v1/documents/ingest", json=ingest_payload, headers=junior_headers)
    assert resp.status_code == 403
    assert "doc:ingest" in resp.json()["detail"]


def test_api_audit_endpoints_and_verification(client, tmp_path):
    admin_token = create_access_token(user_id="bank_admin", role=Role.ADMIN)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    junior_token = create_access_token(user_id="junior_user", role=Role.JUNIOR_ANALYST)
    junior_headers = {"Authorization": f"Bearer {junior_token}"}

    # Junior analyst forbidden from audit endpoints
    assert client.get("/api/v1/audit/events", headers=junior_headers).status_code == 403
    assert client.get("/api/v1/audit/verify", headers=junior_headers).status_code == 403
    assert client.post("/api/v1/audit/export", headers=junior_headers).status_code == 403

    # Admin allowed to retrieve events and verify chain
    verify_resp = client.get("/api/v1/audit/verify", headers=admin_headers)
    assert verify_resp.status_code == 200
    v_data = verify_resp.json()
    assert v_data["valid"] is True
    assert "[PASS] VERIFIED" in v_data["status"]

    events_resp = client.get("/api/v1/audit/events", headers=admin_headers)
    assert events_resp.status_code == 200
    assert "events" in events_resp.json()

    # Admin exports audit log to safe path
    export_target = str(tmp_path / "compliance_export.jsonl")
    export_resp = client.post(
        f"/api/v1/audit/export?destination_path={export_target}",
        headers=admin_headers,
    )
    assert export_resp.status_code == 200
    assert export_resp.json()["status"] == "SUCCESS"
    assert Path(export_target).exists()
