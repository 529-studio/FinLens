"""
TDD Test Suite for Multi-Tenant Enterprise Workspace Isolation & Cryptographic Data Encryption at Rest (Sprint 12 Task S12-04)
Governed by AGENTS.md Rules 1, 2, 3, 11, 12, 13B, 14, 15 and ADR-006, ADR-007.
"""

import os
import stat
import tempfile
import sys
from pathlib import Path
import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from contracts import (
    WorkspaceTier,
    EncryptionAlgorithm,
    TenantWorkspaceCreateRequest,
    TenantWorkspaceResponse,
    TenantAccessVerificationRequest,
    TenantAccessVerificationResponse,
)


def test_workspace_security_contracts_validation():
    """Verify DTO instantiation, enum mappings, and default values."""
    req = TenantWorkspaceCreateRequest(
        workspace_id="tenant_vnm_audit_2023",
        tenant_name="Vinamilk Internal Audit Group",
        tier=WorkspaceTier.ENTERPRISE_ISOLATED,
        encryption_algorithm=EncryptionAlgorithm.AES_256_GCM,
        kms_key_id="kms-key-vnm-vault-01",
    )
    assert req.workspace_id == "tenant_vnm_audit_2023"
    assert req.tier == WorkspaceTier.ENTERPRISE_ISOLATED
    assert req.encryption_algorithm == EncryptionAlgorithm.AES_256_GCM

    res = TenantWorkspaceResponse(
        workspace_id="tenant_vnm_audit_2023",
        tenant_name="Vinamilk Internal Audit Group",
        tier=WorkspaceTier.ENTERPRISE_ISOLATED,
        encryption_algorithm=EncryptionAlgorithm.AES_256_GCM,
        is_encrypted=True,
        storage_path="/var/finsight/workspaces/tenant_vnm_audit_2023",
        key_fingerprint="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        created_at=1732490000.0,
    )
    assert res.is_encrypted is True
    assert len(res.key_fingerprint) == 64


def test_workspace_security_contracts_path_traversal():
    """Verify path traversal rejection on workspace_id."""
    with pytest.raises(ValidationError):
        TenantWorkspaceCreateRequest(
            workspace_id="../../etc/shadow",
            tenant_name="Malicious Tenant",
        )

    with pytest.raises(ValidationError):
        TenantAccessVerificationRequest(
            workspace_id="../evil_dir",
            requested_document_id="doc1",
        )


# ============================================================================
# Task 2 Tests: Pure Encryption & Workspace Isolation Manager
# ============================================================================

from workspace_security import (
    derive_tenant_key,
    encrypt_data_at_rest,
    decrypt_data_at_rest,
    WorkspaceSecurityManager,
)


def test_derive_tenant_key():
    """Verify deterministic 256-bit key derivation using HMAC-SHA256."""
    salt = b"FINTRACE_CRYPTO_SALT_123456"
    key1 = derive_tenant_key(secret_seed="tenant_secret_seed_alpha", salt=salt)
    key2 = derive_tenant_key(secret_seed="tenant_secret_seed_alpha", salt=salt)
    key3 = derive_tenant_key(secret_seed="tenant_secret_seed_beta", salt=salt)

    assert len(key1) == 32  # 256 bits
    assert key1 == key2
    assert key1 != key3


def test_aes_256_gcm_encryption_and_decryption():
    """Verify authenticated roundtrip encryption and tamper rejection."""
    key = derive_tenant_key("master_seed_001", b"salt_for_testing")
    plaintext = b"AUDITED_FINANCIAL_METRICS_CONFIDENTIAL: REVENUE=60,478B VND"

    encrypted_bundle = encrypt_data_at_rest(plaintext, key, associated_data=b"tenant_vnm")
    assert "ciphertext" in encrypted_bundle
    assert "nonce" in encrypted_bundle
    assert "tag" in encrypted_bundle

    # Valid decryption
    decrypted = decrypt_data_at_rest(
        ciphertext_b64=encrypted_bundle["ciphertext"],
        nonce_b64=encrypted_bundle["nonce"],
        tag_b64=encrypted_bundle["tag"],
        key=key,
        associated_data=b"tenant_vnm",
    )
    assert decrypted == plaintext

    # Tampered ciphertext rejection
    tampered_ciphertext = encrypted_bundle["ciphertext"][:-4] + "AAAA"
    with pytest.raises(ValueError, match="Decryption failed or ciphertext was tampered"):
        decrypt_data_at_rest(
            ciphertext_b64=tampered_ciphertext,
            nonce_b64=encrypted_bundle["nonce"],
            tag_b64=encrypted_bundle["tag"],
            key=key,
            associated_data=b"tenant_vnm",
        )


def test_workspace_manager_provisioning_and_permissions():
    """Verify tenant workspace provisioning with strict 0o700/0o600 POSIX permissions."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = WorkspaceSecurityManager(base_dir=tmpdir)

        req = TenantWorkspaceCreateRequest(
            workspace_id="tenant_hpg_2023",
            tenant_name="Hoa Phat Internal Audit",
            tier=WorkspaceTier.ENTERPRISE_ISOLATED,
        )

        res = manager.create_workspace(req)
        assert res.workspace_id == "tenant_hpg_2023"
        assert res.is_encrypted is True
        assert len(res.key_fingerprint) == 64

        workspace_path = Path(res.storage_path)
        assert workspace_path.exists()

        # Check POSIX permissions (0o700 on directory, 0o600 on config file)
        dir_stat = os.stat(workspace_path)
        dir_mode = stat.S_IMODE(dir_stat.st_mode)
        assert dir_mode == 0o700

        config_path = workspace_path / "workspace.enc.json"
        assert config_path.exists()
        file_stat = os.stat(config_path)
        file_mode = stat.S_IMODE(file_stat.st_mode)
        assert file_mode == 0o600


def test_workspace_manager_cross_tenant_isolation():
    """Verify cross-tenant document isolation and unauthorized access rejection."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = WorkspaceSecurityManager(base_dir=tmpdir)

        # Create two isolated workspaces
        manager.create_workspace(
            TenantWorkspaceCreateRequest(workspace_id="tenant_vnm", tenant_name="VNM Tenant")
        )
        manager.create_workspace(
            TenantWorkspaceCreateRequest(workspace_id="tenant_hpg", tenant_name="HPG Tenant")
        )

        # Associate documents
        manager.register_document("tenant_vnm", "VNM_2023_AUDITED")
        manager.register_document("tenant_hpg", "HPG_2023_AUDITED")

        # In-tenant access allowed
        assert manager.verify_tenant_access("tenant_vnm", "VNM_2023_AUDITED") is True
        assert manager.verify_tenant_access("tenant_hpg", "HPG_2023_AUDITED") is True

        # Cross-tenant access rejected
        assert manager.verify_tenant_access("tenant_vnm", "HPG_2023_AUDITED") is False
        assert manager.verify_tenant_access("tenant_hpg", "VNM_2023_AUDITED") is False


# ============================================================================
# Task 3 Tests: REST Endpoints under /api/v1/workspaces
# ============================================================================

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_api_workspace_create_and_status_flow():
    """Verify POST /api/v1/workspaces/create and GET status flow."""
    payload = {
        "workspace_id": "tenant_api_test_01",
        "tenant_name": "API Testing Group",
        "tier": "enterprise_isolated",
        "encryption_algorithm": "aes-256-gcm",
    }
    res = client.post("/api/v1/workspaces/create", json=payload)
    assert res.status_code == 200, f"Create workspace failed: {res.text}"
    data = res.json()
    assert data["workspace_id"] == "tenant_api_test_01"
    assert data["is_encrypted"] is True
    assert len(data["key_fingerprint"]) == 64

    # GET status
    status_res = client.get("/api/v1/workspaces/tenant_api_test_01/status")
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["workspace_id"] == "tenant_api_test_01"


def test_api_workspace_verify_access_endpoint():
    """Verify POST /api/v1/workspaces/{workspace_id}/verify-access endpoint."""
    # Create workspace and register doc
    client.post(
        "/api/v1/workspaces/create",
        json={"workspace_id": "tenant_sec_02", "tenant_name": "Security Group"},
    )

    # In-tenant doc access
    res = client.post(
        "/api/v1/workspaces/tenant_sec_02/verify-access",
        json={"workspace_id": "tenant_sec_02", "requested_document_id": "VNM_2023_AUDITED"},
    )
    assert res.status_code == 200
    assert "allowed" in res.json()


def test_api_workspace_path_traversal():
    """Verify path traversal attack is blocked on workspace creation and status."""
    bad_payload = {
        "workspace_id": "../../etc/passwd",
        "tenant_name": "Evil Group",
    }
    res = client.post("/api/v1/workspaces/create", json=bad_payload)
    assert res.status_code in [400, 422]

    bad_get = client.get("/api/v1/workspaces/..%2F..%2Fetc/status")
    assert bad_get.status_code in [400, 404, 422]


def test_api_workspace_unauthorized():
    """Verify invalid token returns 401."""
    headers = {"Authorization": "Bearer invalid.fake.token"}
    res = client.post(
        "/api/v1/workspaces/create",
        json={"workspace_id": "tenant_unauth_01", "tenant_name": "Unauth"},
        headers=headers,
    )
    assert res.status_code == 401
