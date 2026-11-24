# S12-04: Multi-Tenant Enterprise Workspace Isolation & Cryptographic Data Encryption at Rest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement multi-tenant enterprise workspace isolation, tenant-specific sandboxing, and authenticated cryptographic encryption at rest (AES-256-GCM) with atomic file permissions (`0o600`/`0o700`) and strict cross-tenant leakage defense.

**Architecture:**
1. `packages/core-engine/src/contracts.py`: Defines `WorkspaceTier`, `EncryptionAlgorithm`, `TenantWorkspaceCreateRequest`, `TenantWorkspaceResponse`, `TenantAccessVerificationRequest`, `TenantAccessVerificationResponse`.
2. `packages/core-engine/src/workspace_security.py`: Core encryption and isolation manager (`WorkspaceSecurityManager`) implementing key derivation (HKDF/PBKDF2), AES-256-GCM encryption/decryption at rest with authentication tag validation, workspace directory provisioning (`0o700`), and cross-tenant access control.
3. `packages/core-engine/src/main.py`: Exposes REST endpoints (`POST /api/v1/workspaces/create`, `GET /api/v1/workspaces/{workspace_id}/status`, `POST /api/v1/workspaces/{workspace_id}/verify-access`) with RBAC and path traversal guards.

**Tech Stack:**
- Python 3.13, FastAPI, Pydantic v2, Pytest, `cryptography` (or `hashlib` & `secrets`), standard library.
- Standards: AGENTS.md Rules 1, 2, 3, 11, 12, 13B, 14, 15 and ADR-006, ADR-007.

**Spec:** Issue #103 (`[security] S12-04: Multi-Tenant Enterprise Workspace Isolation & Cryptographic Data Encryption at Rest`).

---

## Global Constraints

- **Git Flow (Rule 12):** Active branch is `feat/s12-04-workspace-isolation` targeting `dev`. PR merge commit required.
- **Security & Path Traversal (Rule 13B):** Every `workspace_id` strictly validated against regex `^[a-zA-Z0-9_\-]+$` and rejects any `..` path traversal attempt.
- **Zero-Leak Policy (Rule 2):** Zero raw encryption keys, salt secrets, or private tokens leaked in responses or logs.
- **Zero Raw Emojis in UI / Output (Rule 15):** 0 raw emojis in responses, descriptions, or code comments.
- **Strict POSIX Permissions:** Created tenant workspace directories enforce `0o700`; tenant configuration files enforce `0o600`.

---

## Review Focus

1. **Path Traversal Across Workspace IDs:** Supplying `../../etc/shadow` in `workspace_id` immediately triggers HTTP 400/422.
2. **Cross-Tenant Document Access Rejection:** A tenant in `workspace_A` requesting a document belonging to `workspace_B` must be denied (`allowed = False`).
3. **AES-256-GCM Ciphertext Tamper Detection:** Tampering with a single byte in the ciphertext or authentication tag must raise an authentication error and fail decryption cleanly.
4. **POSIX Permission Enforcement:** Provable validation that created tenant workspace directory has `0o700` and config files have `0o600`.
5. **Key Fingerprint Zero-Leak:** Response returns only non-reversible SHA-256 key fingerprint, never the raw derived symmetric key.

---

### Task 1: Workspace Security Contracts (`contracts.py`)
- Modify: `packages/core-engine/src/contracts.py`
- Test: `packages/core-engine/tests/test_workspace_security.py`

### Task 2: Core Encryption & Workspace Manager (`workspace_security.py`)
- Create: `packages/core-engine/src/workspace_security.py`
- Test: `packages/core-engine/tests/test_workspace_security.py`

### Task 3: REST API Endpoints (`main.py`)
- Modify: `packages/core-engine/src/main.py`
- Test: `packages/core-engine/tests/test_workspace_security.py`

### Task 4: Full Verification, Independent Subagent Audit & Merge
- Run full core-engine test suite.
- Push branch, create PR targeting `dev`, dispatch independent subagent audit.
- Merge PR with `--merge`.
