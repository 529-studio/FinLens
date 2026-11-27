import sys
from pathlib import Path

from fastapi.testclient import TestClient

CORE_SRC = Path(__file__).resolve().parents[1] / "src"
if str(CORE_SRC) not in sys.path:
    sys.path.insert(0, str(CORE_SRC))

from auth import Permission, Role, create_access_token
from contracts import PolicyEffect, RBACPolicyEvaluateRequest, RBACPolicyRuleDTO
from main import app
from rbac_policy import (
    HierarchicalRBACEngine,
    get_inherited_permissions,
    hash_password,
    verify_password,
)


def test_role_hierarchy_inheritance():
    reviewer_perms = get_inherited_permissions(Role.READ_ONLY_REVIEWER)
    junior_perms = get_inherited_permissions(Role.JUNIOR_ANALYST)
    senior_perms = get_inherited_permissions(Role.SENIOR_AUDITOR)
    admin_perms = get_inherited_permissions(Role.ADMIN)

    assert reviewer_perms == {Permission.DOC_READ}
    assert reviewer_perms.issubset(junior_perms)
    assert junior_perms.issubset(senior_perms)
    assert senior_perms.issubset(admin_perms)
    assert Permission.DOC_DELETE in admin_perms
    assert Permission.DOC_DELETE not in senior_perms


def test_deny_override_takes_precedence_over_allow():
    engine = HierarchicalRBACEngine()
    engine.add_policy(
        RBACPolicyRuleDTO(
            policy_id="pol-allow-junior-restricted",
            effect=PolicyEffect.ALLOW,
            roles=[Role.JUNIOR_ANALYST.value],
            permissions=[Permission.DOC_READ.value],
            resource_pattern="doc:VNM_*",
        )
    )
    engine.add_policy(
        RBACPolicyRuleDTO(
            policy_id="pol-deny-junior-vnm-secret",
            effect=PolicyEffect.DENY,
            roles=[Role.JUNIOR_ANALYST.value],
            permissions=[Permission.DOC_READ.value],
            resource_pattern="doc:VNM_2024_DRAFT",
        )
    )

    allowed_res = engine.evaluate(
        RBACPolicyEvaluateRequest(
            role=Role.JUNIOR_ANALYST.value,
            permission=Permission.DOC_READ.value,
            resource="doc:VNM_2023",
        )
    )
    assert allowed_res.allowed is True
    assert allowed_res.matched_policy_id == "pol-allow-junior-restricted"

    denied_res = engine.evaluate(
        RBACPolicyEvaluateRequest(
            role=Role.JUNIOR_ANALYST.value,
            permission=Permission.DOC_READ.value,
            resource="doc:VNM_2024_DRAFT",
        )
    )
    assert denied_res.allowed is False
    assert denied_res.effect == PolicyEffect.DENY
    assert denied_res.matched_policy_id == "pol-deny-junior-vnm-secret"


def test_pbkdf2_credential_hashing_and_fail_closed_auth():
    hashed = hash_password("BankAudit#2026")
    assert hashed.startswith("pbkdf2_sha256$100000$")
    assert verify_password("BankAudit#2026", hashed) is True
    assert verify_password("wrong_password", hashed) is False

    engine = HierarchicalRBACEngine(users_store={})
    engine.register_user("analyst_1", "StrongPass#99", Role.JUNIOR_ANALYST)

    ok, role, reason = engine.authenticate("analyst_1", "StrongPass#99")
    assert ok is True
    assert role == Role.JUNIOR_ANALYST

    # Arbitrary password rejected (fail-closed)
    bad_ok, _, bad_reason = engine.authenticate("analyst_1", "arbitrary_password")
    assert bad_ok is False
    assert bad_reason == "password_mismatch"

    # Privilege escalation blocked
    esc_ok, _, esc_reason = engine.authenticate("analyst_1", "StrongPass#99", requested_role=Role.ADMIN)
    assert esc_ok is False
    assert esc_reason == "privilege_escalation_denied"


def test_rbac_api_login_hardening_and_policy_endpoints():
    client = TestClient(app)

    # Arbitrary password on login must fail closed with 401
    bad_login = client.post(
        "/api/v1/auth/login",
        json={"username": "auditor_lan", "password": "arbitrary_wrong_password"},
    )
    assert bad_login.status_code == 401

    # Privilege escalation on login must fail with 403
    esc_login = client.post(
        "/api/v1/auth/login",
        json={"username": "auditor_lan", "password": "secure_password_2026", "role": "admin"},
    )
    assert esc_login.status_code == 403

    # Evaluate policy endpoint
    eval_resp = client.post(
        "/api/v1/rbac/evaluate",
        json={"role": "senior_auditor", "permission": "doc:delete", "resource": "doc:VNM_2023"},
    )
    assert eval_resp.status_code == 200
    assert eval_resp.json()["allowed"] is False

    # List policies requires AUDIT_READ
    junior_token = create_access_token(user_id="j1", role=Role.JUNIOR_ANALYST)
    assert client.get(
        "/api/v1/rbac/policies",
        headers={"Authorization": f"Bearer {junior_token}"},
    ).status_code == 403

    senior_token = create_access_token(user_id="s1", role=Role.SENIOR_AUDITOR)
    pol_resp = client.get(
        "/api/v1/rbac/policies",
        headers={"Authorization": f"Bearer {senior_token}"},
    )
    assert pol_resp.status_code == 200
    assert pol_resp.json()["total_policies"] >= 2
