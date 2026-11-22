"""
FinTrace Enterprise Role-Based Access Control (RBAC) & JWT Security
Governed by Sprint 10 Task S10-03, AGENTS.md Rule 1, Rule 2 (Zero-Leak), Rule 13, and Rule 15.
Provides role permissions, JWT claims encoding/decoding, fail-closed enforcement, and FastAPI dependencies.
"""

import os
import time
import json
import hmac
import hashlib
import base64
from enum import Enum
from pathlib import Path
from typing import Set, Dict, Any, Optional
from pydantic import BaseModel, Field
from fastapi import HTTPException, Security, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv

# Enforce relative path for .env (529 engineering standard: env-and-auth-ops-debugging)
ENV_PATH = Path(__file__).resolve().parents[3] / ".env"
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)

DEFAULT_JWT_SECRET = "fintrace_super_secure_enterprise_banking_jwt_secret_key_2026_xyz"
JWT_SECRET = os.getenv("FINTRACE_JWT_SECRET", DEFAULT_JWT_SECRET)
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_MINUTES = int(os.getenv("FINTRACE_JWT_EXPIRATION_MINUTES", "480"))  # 8 hours default
RBAC_ENABLED = os.getenv("FINTRACE_RBAC_ENABLED", "false").lower() in ("true", "1", "yes")

security_scheme = HTTPBearer(auto_error=False)


class Role(str, Enum):
    ADMIN = "admin"
    SENIOR_AUDITOR = "senior_auditor"
    JUNIOR_ANALYST = "junior_analyst"
    READ_ONLY_REVIEWER = "read_only_reviewer"


class Permission(str, Enum):
    DOC_READ = "doc:read"
    DOC_INGEST = "doc:ingest"
    DOC_DELETE = "doc:delete"
    TABLE_STITCH = "table:stitch"
    AUDIT_READ = "audit:read"
    ADMIN_CONFIG = "admin:config"


ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.ADMIN: {
        Permission.DOC_READ,
        Permission.DOC_INGEST,
        Permission.DOC_DELETE,
        Permission.TABLE_STITCH,
        Permission.AUDIT_READ,
        Permission.ADMIN_CONFIG,
    },
    Role.SENIOR_AUDITOR: {
        Permission.DOC_READ,
        Permission.DOC_INGEST,
        Permission.TABLE_STITCH,
        Permission.AUDIT_READ,
    },
    Role.JUNIOR_ANALYST: {
        Permission.DOC_READ,
        Permission.TABLE_STITCH,
    },
    Role.READ_ONLY_REVIEWER: {
        Permission.DOC_READ,
    },
}


class User(BaseModel):
    user_id: str = Field(..., description="Unique alphanumeric username or employee ID")
    role: Role = Field(..., description="Role assigned in banking organizational hierarchy")
    name: str = Field("FinTrace User", description="User full display name")
    org: str = Field("Banking Enterprise", description="Organization or department")
    permissions: Set[Permission] = Field(default_factory=set, description="Granted permissions")

    def has_permission(self, perm: Permission) -> bool:
        return perm in self.permissions


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=64)
    password: str = Field(..., min_length=4)
    role: Optional[Role] = None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in_seconds: int
    user: User


def _base64url_encode(data: bytes) -> str:
    """Encodes bytes to URL-safe base64 string without trailing padding."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _base64url_decode(encoded: str) -> bytes:
    """Decodes URL-safe base64 string with restored padding."""
    padding = 4 - (len(encoded) % 4)
    if padding and padding != 4:
        encoded += "=" * padding
    return base64.urlsafe_b64decode(encoded.encode("ascii"))


def create_access_token(
    user_id: str,
    role: Role,
    name: str = "FinTrace User",
    org: str = "Banking Enterprise",
    expires_in_minutes: Optional[int] = None,
    secret_key: Optional[str] = None,
) -> str:
    """
    Creates an RFC 7519 compliant HS256 JWT access token using Python standard library.
    Zero external dependencies, zero supply-chain risk.
    """
    secret = secret_key or JWT_SECRET
    exp_minutes = expires_in_minutes if expires_in_minutes is not None else JWT_EXPIRATION_MINUTES
    now = int(time.time())
    exp = now + (exp_minutes * 60)

    header = {"alg": JWT_ALGORITHM, "typ": "JWT"}
    payload = {
        "sub": user_id,
        "role": role.value if isinstance(role, Role) else str(role),
        "name": name,
        "org": org,
        "iat": now,
        "exp": exp,
    }

    header_b64 = _base64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _base64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")

    signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    sig_b64 = _base64url_encode(signature)

    return f"{header_b64}.{payload_b64}.{sig_b64}"


def decode_access_token(token: str, secret_key: Optional[str] = None) -> User:
    """
    Decodes and cryptographically verifies an HS256 JWT access token.
    Enforces signature authenticity, token expiration, and role validation.
    """
    secret = secret_key or JWT_SECRET
    parts = token.strip().split(".")
    if len(parts) != 3:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed JWT token: must contain exactly 3 dot-separated segments",
            headers={"WWW-Authenticate": "Bearer"},
        )

    header_b64, payload_b64, sig_b64 = parts

    try:
        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        expected_sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
        provided_sig = _base64url_decode(sig_b64)

        if not hmac.compare_digest(expected_sig, provided_sig):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token signature: cryptographic verification failed",
                headers={"WWW-Authenticate": "Bearer"},
            )

        payload_bytes = _base64url_decode(payload_b64)
        payload = json.loads(payload_bytes.decode("utf-8"))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token decoding failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check expiration
    exp = payload.get("exp")
    if exp is not None and int(exp) < int(time.time()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please authenticate again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Validate role
    role_val = payload.get("role")
    try:
        user_role = Role(role_val)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Unknown or invalid role in token claims: '{role_val}'",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_perms = set(ROLE_PERMISSIONS.get(user_role, set()))
    return User(
        user_id=payload.get("sub", "unknown"),
        role=user_role,
        name=payload.get("name", "FinTrace User"),
        org=payload.get("org", "Banking Enterprise"),
        permissions=user_perms,
    )


def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Security(security_scheme)) -> User:
    """
    FastAPI dependency extracting current user from Authorization header.
    In development mode without token, defaults to local Admin user to maintain backward compatibility.
    When Authorization header is provided or RBAC_ENABLED is true, strictly validates token (Fail-Closed).
    """
    if credentials is not None and credentials.credentials:
        return decode_access_token(credentials.credentials)

    # Fail-closed if RBAC is strictly enabled in environment
    if RBAC_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header. Enterprise RBAC requires Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Permissive fallback for local developer / existing test harness
    return User(
        user_id="local_admin",
        role=Role.ADMIN,
        name="Local System Administrator",
        org="Localhost",
        permissions=set(ROLE_PERMISSIONS[Role.ADMIN]),
    )


def require_permission(required_perm: Permission):
    """Factory creating a FastAPI dependency enforcing specific permission check."""
    def permission_checker(user: User = Depends(get_current_user)) -> User:
        if not user.has_permission(required_perm):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Role '{user.role.value}' lacks required permission '{required_perm.value}'.",
            )
        return user
    return permission_checker


def require_role(min_role: Role):
    """Factory creating a FastAPI dependency enforcing minimum role requirement."""
    role_hierarchy = {
        Role.READ_ONLY_REVIEWER: 1,
        Role.JUNIOR_ANALYST: 2,
        Role.SENIOR_AUDITOR: 3,
        Role.ADMIN: 4,
    }

    def role_checker(user: User = Depends(get_current_user)) -> User:
        user_level = role_hierarchy.get(user.role, 0)
        req_level = role_hierarchy.get(min_role, 99)
        if user_level < req_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Operation requires at least '{min_role.value}' role (current: '{user.role.value}').",
            )
        return user
    return role_checker
