"""
Unit and Integration Tests for Offline Air-Gapped Licensing Engine
Governed by Sprint 11 Task S11-04, AGENTS.md Rule 1, Rule 2 (Zero-Leak), Rule 13, and Rule 15.
Tests hardware fingerprinting, Ed25519 asymmetric signatures, atomic storage, and RBAC enforcement.
"""

import os
import time
import json
import base64
import tempfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

from main import app
from contracts import (
    LicenseTier,
    LicenseState,
    LicensePayload,
    LicenseFileDTO,
)
from licensing import (
    get_machine_fingerprint,
    canonicalize_payload,
    generate_test_license,
    LicenseManager,
)
from auth import create_access_token, Role


client = TestClient(app)


@pytest.fixture
def test_keypair():
    """Generates an ephemeral Ed25519 keypair for cryptographic testing."""
    priv = ed25519.Ed25519PrivateKey.generate()
    pub = priv.public_key()
    pub_bytes = pub.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return priv, pub_bytes


def test_machine_fingerprint_properties():
    """Verifies that hardware fingerprint is deterministic, 64-hex SHA-256, and zero-leak."""
    fp1 = get_machine_fingerprint()
    fp2 = get_machine_fingerprint()

    assert fp1 == fp2
    assert len(fp1) == 64
    assert all(c in "0123456789abcdef" for c in fp1)

    # Zero-Leak check: no raw MAC colon separators or obvious cleartext
    assert ":" not in fp1
    assert " " not in fp1


def test_ed25519_signature_and_tamper_detection(test_keypair):
    """Verifies positive digital signature verification and tamper rejection."""
    priv, pub_bytes = test_keypair
    host_fp = get_machine_fingerprint()

    payload = LicensePayload(
        customer_id="VIETINBANK_HQ",
        customer_name="VietinBank Enterprise Audit",
        tier=LicenseTier.ENTERPRISE,
        issued_at=time.time() - 3600,
        expires_at=time.time() + (365 * 86400),
        max_users=50,
        features=["visual_rag", "table_stitching", "comparative_query", "ratio_engine", "session_sync"],
        machine_fingerprint=host_fp,
    )

    license_file = generate_test_license(priv, payload)

    manager = LicenseManager(
        license_path=Path("/tmp/non_existent_license_test.json"),
        public_key_bytes=pub_bytes,
    )

    # 1. Valid signature verifies
    assert manager.verify_signature(license_file) is True
    status = manager.evaluate_license(license_file)
    assert status.state == LicenseState.ACTIVE
    assert status.is_valid is True
    assert status.tier == LicenseTier.ENTERPRISE
    assert status.customer_id == "VIETINBANK_HQ"
    assert status.days_remaining is not None and status.days_remaining >= 364

    # 2. Tampered payload fails verification
    tampered_payload = payload.model_copy(update={"max_users": 999})
    tampered_file = LicenseFileDTO(payload=tampered_payload, signature=license_file.signature)
    assert manager.verify_signature(tampered_file) is False
    tampered_status = manager.evaluate_license(tampered_file)
    assert tampered_status.state == LicenseState.INVALID_SIGNATURE
    assert tampered_status.is_valid is False

    # 3. Tampered signature fails verification
    bad_sig = "a" * len(license_file.signature)
    bad_sig_file = LicenseFileDTO(payload=payload, signature=bad_sig)
    assert manager.verify_signature(bad_sig_file) is False


def test_license_expiration_evaluation(test_keypair):
    """Verifies that expired licenses are identified as EXPIRED."""
    priv, pub_bytes = test_keypair
    host_fp = get_machine_fingerprint()

    past_time = time.time() - (10 * 86400)
    expired_payload = LicensePayload(
        customer_id="BIDV_BRANCH",
        customer_name="BIDV Audit",
        tier=LicenseTier.PROFESSIONAL,
        issued_at=past_time - (30 * 86400),
        expires_at=past_time,
        max_users=5,
        features=["visual_rag"],
        machine_fingerprint=host_fp,
    )

    expired_file = generate_test_license(priv, expired_payload)

    manager = LicenseManager(
        license_path=Path("/tmp/non_existent_license_test.json"),
        public_key_bytes=pub_bytes,
    )

    status = manager.evaluate_license(expired_file)
    assert status.state == LicenseState.EXPIRED
    assert status.is_valid is False
    assert status.days_remaining == 0


def test_hardware_fingerprint_mismatch_and_floating(test_keypair):
    """Verifies that licenses bound to foreign machines are rejected, while floating licenses pass."""
    priv, pub_bytes = test_keypair
    foreign_fp = "00112233445566778899aabbccddeeff00112233445566778899aabbccddeeff"

    bound_payload = LicensePayload(
        customer_id="MB_BANK",
        customer_name="MB Bank",
        tier=LicenseTier.ENTERPRISE,
        issued_at=time.time(),
        expires_at=time.time() + 86400,
        max_users=20,
        features=["visual_rag"],
        machine_fingerprint=foreign_fp,
    )
    bound_file = generate_test_license(priv, bound_payload)

    manager = LicenseManager(
        license_path=Path("/tmp/non_existent_license_test.json"),
        public_key_bytes=pub_bytes,
    )

    # Foreign machine rejected
    status = manager.evaluate_license(bound_file)
    assert status.state == LicenseState.FINGERPRINT_MISMATCH
    assert status.is_valid is False

    # Floating license with wildcard "*" accepted
    floating_payload = bound_payload.model_copy(update={"machine_fingerprint": "*"})
    floating_file = generate_test_license(priv, floating_payload)
    floating_status = manager.evaluate_license(floating_file)
    assert floating_status.state == LicenseState.ACTIVE
    assert floating_status.is_valid is True


def test_atomic_persistence_and_reload(test_keypair):
    """Verifies atomic writing to disk, file permissions 0o600, and automatic reload."""
    priv, pub_bytes = test_keypair
    host_fp = get_machine_fingerprint()

    payload = LicensePayload(
        customer_id="TECHCOMBANK_AUDIT",
        customer_name="Techcombank Risk Dept",
        tier=LicenseTier.ENTERPRISE,
        issued_at=time.time(),
        expires_at=time.time() + (180 * 86400),
        max_users=100,
        features=["all"],
        machine_fingerprint=host_fp,
    )
    license_file = generate_test_license(priv, payload)

    with tempfile.TemporaryDirectory() as tmpdir:
        license_path = Path(tmpdir) / "sub" / "license.json"
        manager = LicenseManager(license_path=license_path, public_key_bytes=pub_bytes)

        # Before activation, community evaluation
        initial_status = manager.get_status()
        assert initial_status.state == LicenseState.COMMUNITY_EVALUATION

        # Activate
        success, msg, active_status = manager.activate(license_file.model_dump())
        assert success is True
        assert active_status.state == LicenseState.ACTIVE
        assert license_path.exists()

        # Check permissions (0o600 on POSIX)
        if os.name != "nt":
            mode = os.stat(license_path).st_mode & 0o777
            assert mode == 0o600

        # Create new manager pointing to same path; should auto-load
        manager2 = LicenseManager(license_path=license_path, public_key_bytes=pub_bytes)
        reload_status = manager2.get_status()
        assert reload_status.state == LicenseState.ACTIVE
        assert reload_status.customer_id == "TECHCOMBANK_AUDIT"
        assert reload_status.tier == LicenseTier.ENTERPRISE


def test_rest_license_api_endpoints(test_keypair):
    """Tests /api/v1/license/status and /api/v1/license/activate REST endpoints and RBAC."""
    priv, pub_bytes = test_keypair
    token_admin = create_access_token(user_id="sys_admin", role=Role.ADMIN)
    token_junior = create_access_token(user_id="junior_auditor", role=Role.JUNIOR_ANALYST)

    headers_admin = {"Authorization": f"Bearer {token_admin}"}
    headers_junior = {"Authorization": f"Bearer {token_junior}"}

    # 1. GET /api/v1/license/status (Junior has DOC_READ, should succeed)
    status_resp = client.get("/api/v1/license/status", headers=headers_junior)
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert "state" in status_data
    assert "machine_fingerprint" in status_data

    # 2. POST /api/v1/license/activate without ADMIN_CONFIG (Junior should be rejected 403)
    activate_resp = client.post(
        "/api/v1/license/activate",
        json={"license_key": "{}"},
        headers=headers_junior,
    )
    assert activate_resp.status_code == 403

    # 3. POST /api/v1/license/activate with invalid JSON (Admin should get 400)
    bad_activate = client.post(
        "/api/v1/license/activate",
        json={"license_key": "not_valid_json"},
        headers=headers_admin,
    )
    assert bad_activate.status_code == 400
