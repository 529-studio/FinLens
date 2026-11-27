import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

CORE_SRC = Path(__file__).resolve().parents[1] / "src"
if str(CORE_SRC) not in sys.path:
    sys.path.insert(0, str(CORE_SRC))

from cashflow_reconciler import CashFlowReconciler
from contracts import (
    BoundingBox,
    CashFlowReconcileRequest,
    DirectCashFlowInput,
    IndirectCashFlowInput,
    ReconciliationStatus,
)
from main import app


def test_exact_reconciliation_with_working_capital_sign_conventions():
    engine = CashFlowReconciler()
    # Direct: 1200 - 500 - 200 - 30 - 70 + 10 = 410
    # Indirect: NI=350 + DA=80 + NonCash=10 - dAR(50) - dInv(20) + dAP(35) + dOtherWC(5) = 410
    req = CashFlowReconcileRequest(
        document_id="VNM_2024_Q4",
        period_label="FY2024",
        direct=DirectCashFlowInput(
            cash_received_from_customers=1200.0,
            cash_paid_to_suppliers=-500.0,
            cash_paid_to_employees=-200.0,
            interest_paid=-30.0,
            taxes_paid=-70.0,
            other_operating_cash=10.0,
        ),
        indirect=IndirectCashFlowInput(
            net_income=350.0,
            depreciation_amortization=80.0,
            non_cash_adjustments=10.0,
            delta_receivables=50.0,
            delta_inventory=20.0,
            delta_payables=35.0,
            delta_other_working_capital=5.0,
        ),
        citations={
            "cash_received_from_customers": BoundingBox(ymin=120, xmin=100, ymax=145, xmax=890),
            "net_income": BoundingBox(ymin=310, xmin=100, ymax=335, xmax=890),
        },
        citation_pages={
            "cash_received_from_customers": 12,
            "net_income": 14,
        },
    )

    res = engine.reconcile(req)
    assert res.direct_cfo == 410.0
    assert res.indirect_cfo == 410.0
    assert res.reconciliation_variance == 0.0
    assert res.variance_pct == 0.0
    assert res.status == ReconciliationStatus.RECONCILED
    assert res.non_cash_total_addback == 90.0
    assert res.working_capital_net_impact == -30.0  # -50 - 20 + 35 + 5

    cust_item = next(i for i in res.line_items if i.item_code == "cash_received_from_customers")
    assert cust_item.bounding_box is not None
    assert cust_item.bounding_box.ymin == 120
    assert cust_item.page_number == 12


def test_outflows_as_positive_flag_and_material_mismatch():
    engine = CashFlowReconciler()
    req = CashFlowReconcileRequest(
        document_id="FPT_2024",
        period_label="FY2024",
        direct_outflows_as_positive=True,
        direct=DirectCashFlowInput(
            cash_received_from_customers=1000.0,
            cash_paid_to_suppliers=400.0,
            cash_paid_to_employees=100.0,
            interest_paid=20.0,
            taxes_paid=30.0,
        ),
        indirect=IndirectCashFlowInput(
            net_income=300.0,
            depreciation_amortization=50.0,
            delta_receivables=10.0,  # -10 impact -> indirect = 340
        ),
        materiality_threshold_pct=1.0,
    )

    res = engine.reconcile(req)
    assert res.direct_cfo == 450.0  # 1000 - 400 - 100 - 20 - 30
    assert res.indirect_cfo == 340.0
    assert res.reconciliation_variance == 110.0
    assert res.status == ReconciliationStatus.MATERIAL_MISMATCH
    assert res.variance_pct == pytest.approx(24.4444, rel=1e-3)


def test_zero_denominator_safety_and_immaterial_variance():
    engine = CashFlowReconciler()

    # Case 1: Both Direct & Indirect CFO are 0 -> 0.0% variance, RECONCILED
    req_zero = CashFlowReconcileRequest(
        document_id="ZERO_CO",
        direct=DirectCashFlowInput(),
        indirect=IndirectCashFlowInput(),
    )
    res_zero = engine.reconcile(req_zero)
    assert res_zero.direct_cfo == 0.0
    assert res_zero.variance_pct == 0.0
    assert res_zero.status == ReconciliationStatus.RECONCILED

    # Case 2: Direct CFO = 0, Indirect CFO = 15 -> variance_pct is None, MATERIAL_MISMATCH (no ZeroDivisionError)
    req_div_zero = CashFlowReconcileRequest(
        document_id="ZERO_DIRECT",
        direct=DirectCashFlowInput(),
        indirect=IndirectCashFlowInput(net_income=15.0),
    )
    res_div_zero = engine.reconcile(req_div_zero)
    assert res_div_zero.variance_pct is None
    assert res_div_zero.status == ReconciliationStatus.MATERIAL_MISMATCH

    # Case 3: Immaterial variance (0.5% <= 1.0%)
    req_immaterial = CashFlowReconcileRequest(
        document_id="SMALL_DIFF",
        direct=DirectCashFlowInput(cash_received_from_customers=1000.0),
        indirect=IndirectCashFlowInput(net_income=995.0),
        materiality_threshold_pct=1.0,
    )
    res_imm = engine.reconcile(req_immaterial)
    assert res_imm.status == ReconciliationStatus.IMMATERIAL_VARIANCE


def test_cashflow_reconcile_api_and_security_traversal():
    client = TestClient(app)

    # Path traversal rejected with 422
    bad_payload = {
        "document_id": "../../etc/passwd",
        "direct": {"cash_received_from_customers": 100.0},
        "indirect": {"net_income": 100.0},
    }
    bad_resp = client.post("/api/v1/analysis/cashflow-reconcile", json=bad_payload)
    assert bad_resp.status_code == 422

    # Out-of-bounds bounding box rejected with 422 ([0, 1000] ADR-003 invariant)
    bad_bbox_payload = {
        "document_id": "VNM_2024",
        "direct": {"cash_received_from_customers": 100.0},
        "indirect": {"net_income": 100.0},
        "citations": {
            "net_income": {"ymin": -5, "xmin": 0, "ymax": 1200, "xmax": 500}
        },
    }
    bad_bbox_resp = client.post("/api/v1/analysis/cashflow-reconcile", json=bad_bbox_payload)
    assert bad_bbox_resp.status_code == 422

    # Valid API call
    good_payload = {
        "document_id": "VNM_2024_Q4",
        "period_label": "FY2024",
        "direct": {
            "cash_received_from_customers": 500.0,
            "cash_paid_to_suppliers": -200.0,
        },
        "indirect": {
            "net_income": 250.0,
            "depreciation_amortization": 50.0,
        },
        "citations": {
            "net_income": {"ymin": 100, "xmin": 50, "ymax": 130, "xmax": 900}
        },
    }
    resp = client.post("/api/v1/analysis/cashflow-reconcile", json=good_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["direct_cfo"] == 300.0
    assert data["indirect_cfo"] == 300.0
    assert data["status"] == "reconciled"
    assert data["citations"]["net_income"]["ymin"] == 100
