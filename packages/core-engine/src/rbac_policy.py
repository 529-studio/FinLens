"""
Enterprise Hierarchical RBAC Policy Engine & Credential Hardening (Sprint 13 S13-07)
Implements:
1. Strict Role Hierarchy (ADMIN > SENIOR_AUDITOR > JUNIOR_ANALYST > READ_ONLY_REVIEWER)
   with explicit permission inheritance.
2. Policy Rules (ALLOW / DENY) with Deny-Takes-Precedence and fnmatch resource scoping.
3. Salted PBKDF2-HMAC-SHA256 credential hashing & fail-closed verification.
"""

import base64
import fnmatch
import hashlib
import hmac
import json
import os
import secrets
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from dotenv import load_dotenv

from auth import Permission, Role
from contracts import (
    PolicyEffect,
    RBACPoliciesListResponse,
    RBACPolicyEvaluateRequest,
    RBACPolicyEvaluateResponse,
    RBACPolicyRuleDTO,
)

# Explicit .env anchor relative to __file__ (529 standard)
ENV_PATH = Path(__file__).resolve().parents[3] / ".env"
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)

PBKDF2_ITERATIONS = 100_000

WEAK_PASSWORDS: Set[str] = {
    "invalid_secret",
    "password",
    "123456",
    "12345678",
    "admin123",
    "qwerty123",
    "letmein",
}

ROLE_HIERARCHY_LEVEL: Dict[Role, int] = {
    Role.READ_ONLY_REVIEWER: 1,
    Role.JUNIOR_ANALYST: 2,
    Role.SENIOR_AUDITOR: 3,
    Role.ADMIN: 4,
}

# Direct permissions added at each tier (inherited upward)
_DIRECT_ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.READ_ONLY_REVIEWER: {Permission.DOC_READ},
    Role.JUNIOR_ANALYST: {Permission.TABLE_STITCH},
    Role.SENIOR_AUDITOR: {Permission.DOC_INGEST, Permission.AUDIT_READ},
    Role.ADMIN: {Permission.DOC_DELETE, Permission.ADMIN_CONFIG},
}

_ROLE_PARENT: Dict[Role, Optional[Role]] = {
    Role.READ_ONLY_REVIEWER: None,
    Role.JUNIOR_ANALYST: Role.READ_ONLY_REVIEWER,
    Role.SENIOR_AUDITOR: Role.JUNIOR_ANALYST,
    Role.ADMIN: Role.SENIOR_AUDITOR,
}

# Pre-hashed PBKDF2-HMAC-SHA256 bootstrap entry (zero plaintext secrets in source)
_DEFAULT_BOOTSTRAP_USERS: Dict[str, Dict[str, str]] = {
    "auditor_lan": {
        "role": Role.SENIOR_AUDITOR.value,
        "password_hash": "pbkdf2_sha256$100000$bMDzOhI9sMfE1Uk+wrEJ6w==$mjLEq+JKcVzQ+SUKRNXMd+oFS2KfJsVu+eqPKVqKt9k=",
    },
}


def hash_password(
    password: str,
    salt: Optional[bytes] = None,
    iterations: int = PBKDF2_ITERATIONS,
) -> str:
    """Hashes a password using salted PBKDF2-HMAC-SHA256."""
    if not password or len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    salt_bytes = salt if salt is not None else secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt_bytes, iterations)
    salt_b64 = base64.b64encode(salt_bytes).decode("ascii")
    hash_b64 = base64.b64encode(dk).decode("ascii")
    return f"pbkdf2_sha256${iterations}${salt_b64}${hash_b64}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verifies a plaintext password against a stored PBKDF2-HMAC-SHA256 hash in constant time."""
    if not password or not stored_hash:
        return False
    parts = stored_hash.strip().split("$")
    if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
        return False
    try:
        iterations = int(parts[1])
        if iterations < 10_000:
            return False
        salt_bytes = base64.b64decode(parts[2].encode("ascii"))
        expected_dk = base64.b64decode(parts[3].encode("ascii"))
    except Exception:
        return False

    computed_dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt_bytes, iterations)
    return hmac.compare_digest(computed_dk, expected_dk)


def get_inherited_permissions(role: Role) -> Set[Permission]:
    """Computes effective permissions for a role by traversing the role hierarchy."""
    perms: Set[Permission] = set()
    cursor: Optional[Role] = role
    visited: Set[Role] = set()
    while cursor is not None and cursor not in visited:
        visited.add(cursor)
        perms.update(_DIRECT_ROLE_PERMISSIONS.get(cursor, set()))
        cursor = _ROLE_PARENT.get(cursor)
    return perms


class HierarchicalRBACEngine:
    """
    Enterprise RBAC engine enforcing role hierarchy inheritance, deny-override policies,
    workspace/document resource scoping, and fail-closed PBKDF2 credential verification.
    """

    def __init__(
        self,
        policies: Optional[List[RBACPolicyRuleDTO]] = None,
        users_store: Optional[Dict[str, Dict[str, str]]] = None,
    ):
        self._policies: List[RBACPolicyRuleDTO] = list(policies) if policies is not None else [
            RBACPolicyRuleDTO(
                policy_id="pol-deny-guest-delete",
                effect=PolicyEffect.DENY,
                roles=[Role.READ_ONLY_REVIEWER.value, Role.JUNIOR_ANALYST.value, Role.SENIOR_AUDITOR.value],
                permissions=[Permission.DOC_DELETE.value, Permission.ADMIN_CONFIG.value],
                resource_pattern="*",
                description="Explicitly deny destructive delete and admin config for non-admin roles",
            ),
            RBACPolicyRuleDTO(
                policy_id="pol-allow-auditor-audit-logs",
                effect=PolicyEffect.ALLOW,
                roles=[Role.SENIOR_AUDITOR.value, Role.ADMIN.value],
                permissions=[Permission.AUDIT_READ.value],
                resource_pattern="audit:*",
                description="Allow Senior Auditors and Admins to inspect tamper-evident audit trails",
            ),
        ]
        self._users: Dict[str, Dict[str, str]] = (
            dict(users_store) if users_store is not None else self._load_users_from_env()
        )

    @staticmethod
    def _load_users_from_env() -> Dict[str, Dict[str, str]]:
        raw = os.getenv("FINTRACE_AUTH_USERS_JSON", "").strip()
        if raw:
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                return {}
        return dict(_DEFAULT_BOOTSTRAP_USERS)

    def register_user(self, username: str, password: str, role: Role) -> None:
        """Registers or updates a user with a salted PBKDF2-HMAC-SHA256 hash."""
        clean_user = username.strip().lower()
        if password.lower() in WEAK_PASSWORDS:
            raise ValueError("Password rejected: weak or disallowed credential")
        self._users[clean_user] = {
            "role": role.value,
            "password_hash": hash_password(password),
        }

    def authenticate(
        self,
        username: str,
        password: str,
        requested_role: Optional[Role] = None,
    ) -> Tuple[bool, Optional[Role], str]:
        """
        Fail-closed credential verification.
        Returns (authenticated, resolved_role, reason).
        """
        if not password or len(password) < 8 or password.lower() in WEAK_PASSWORDS:
            return False, None, "invalid_or_weak_credentials"

        clean_user = username.strip().lower()
        record = self._users.get(clean_user)
        if not record:
            return False, None, "unknown_user_fail_closed"

        stored_hash = record.get("password_hash", "")
        if not verify_password(password, stored_hash):
            return False, None, "password_mismatch"

        try:
            assigned_role = Role(record["role"])
        except Exception:
            return False, None, "invalid_assigned_role"

        if requested_role is not None:
            req_level = ROLE_HIERARCHY_LEVEL.get(requested_role, 99)
            assigned_level = ROLE_HIERARCHY_LEVEL.get(assigned_role, 0)
            if req_level > assigned_level:
                return False, assigned_role, "privilege_escalation_denied"
            return True, requested_role, "authenticated"

        return True, assigned_role, "authenticated"

    def add_policy(self, rule: RBACPolicyRuleDTO) -> None:
        self._policies.append(rule)

    def list_policies(self) -> RBACPoliciesListResponse:
        return RBACPoliciesListResponse(
            total_policies=len(self._policies),
            policies=list(self._policies),
            role_hierarchy={
                role.value: sorted(p.value for p in get_inherited_permissions(role))
                for role in ROLE_HIERARCHY_LEVEL
            },
        )

    def evaluate(self, req: RBACPolicyEvaluateRequest) -> RBACPolicyEvaluateResponse:
        """
        Evaluates access with Deny-Takes-Precedence over Allow and Role Hierarchy.
        """
        role = Role(req.role)
        perm = Permission(req.permission)
        resource = req.resource.strip() or "*"

        # 1. Explicit DENY overrides everything
        for rule in self._policies:
            if rule.effect != PolicyEffect.DENY:
                continue
            if self._rule_matches(rule, role, perm, resource):
                return RBACPolicyEvaluateResponse(
                    allowed=False,
                    effect=PolicyEffect.DENY,
                    role=role.value,
                    permission=perm.value,
                    resource=resource,
                    matched_policy_id=rule.policy_id,
                    reason=f"Denied by explicit DENY policy '{rule.policy_id}'",
                )

        # 2. Explicit ALLOW rules
        for rule in self._policies:
            if rule.effect != PolicyEffect.ALLOW:
                continue
            if self._rule_matches(rule, role, perm, resource):
                return RBACPolicyEvaluateResponse(
                    allowed=True,
                    effect=PolicyEffect.ALLOW,
                    role=role.value,
                    permission=perm.value,
                    resource=resource,
                    matched_policy_id=rule.policy_id,
                    reason=f"Allowed by explicit ALLOW policy '{rule.policy_id}'",
                )

        # 3. Role hierarchy inheritance fallback
        effective_perms = get_inherited_permissions(role)
        if perm in effective_perms:
            return RBACPolicyEvaluateResponse(
                allowed=True,
                effect=PolicyEffect.ALLOW,
                role=role.value,
                permission=perm.value,
                resource=resource,
                matched_policy_id=None,
                reason=f"Allowed via hierarchical role inheritance for '{role.value}'",
            )

        return RBACPolicyEvaluateResponse(
            allowed=False,
            effect=PolicyEffect.DENY,
            role=role.value,
            permission=perm.value,
            resource=resource,
            matched_policy_id=None,
            reason=f"Denied: role '{role.value}' lacks permission '{perm.value}'",
        )

    @staticmethod
    def _rule_matches(rule: RBACPolicyRuleDTO, role: Role, perm: Permission, resource: str) -> bool:
        role_match = (not rule.roles) or (role.value in rule.roles)
        perm_match = (not rule.permissions) or (perm.value in rule.permissions)
        resource_match = fnmatch.fnmatch(resource, rule.resource_pattern)
        return role_match and perm_match and resource_match
