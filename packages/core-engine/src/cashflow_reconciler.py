"""
Advanced Cash Flow Statement Direct-to-Indirect Reconciliation Engine (Sprint 13 S13-05)
Cross-checks Direct Method Operating Cash Flow (CFO) against Indirect Method derivation
(Net Income + Non-Cash Adjustments + Working Capital Changes) per VAS 24 / IFRS / GAAP.
"""

import math
import time
from typing import Dict, List, Optional, Tuple

from contracts import (
    BoundingBox,
    CashFlowLineItemResult,
    CashFlowReconcileRequest,
    CashFlowReconcileResponse,
    ReconciliationStatus,
)


def _finite_float(val: float, field_name: str) -> float:
    """Validates that a numeric input is finite (no NaN or Inf)."""
    f = float(val)
    if not math.isfinite(f):
        raise ValueError(f"Non-finite numeric value for '{field_name}': {val}")
    return f


class CashFlowReconciler:
    """
    Reconciles Direct Method CFO against Indirect Method CFO, enforcing working capital
    sign conventions, materiality thresholds, zero-denominator safety, and [0, 1000]
    visual grounding citation preservation.
    """

    def reconcile(self, req: CashFlowReconcileRequest) -> CashFlowReconcileResponse:
        start = time.perf_counter()

        d = req.direct
        ind = req.indirect
        outflow_sign = -1.0 if req.direct_outflows_as_positive else 1.0

        # Validate & compute Direct Method components
        direct_specs: List[Tuple[str, str, float, float]] = [
            (
                "cash_received_from_customers",
                "Tiền thu từ bán hàng, cung cấp dịch vụ",
                _finite_float(d.cash_received_from_customers, "cash_received_from_customers"),
                1.0,
            ),
            (
                "cash_paid_to_suppliers",
                "Tiền chi trả cho người cung cấp hàng hóa, dịch vụ",
                _finite_float(d.cash_paid_to_suppliers, "cash_paid_to_suppliers"),
                outflow_sign,
            ),
            (
                "cash_paid_to_employees",
                "Tiền chi trả cho người lao động",
                _finite_float(d.cash_paid_to_employees, "cash_paid_to_employees"),
                outflow_sign,
            ),
            (
                "interest_paid",
                "Tiền lãi vay đã trả",
                _finite_float(d.interest_paid, "interest_paid"),
                outflow_sign,
            ),
            (
                "taxes_paid",
                "Thuế thu nhập doanh nghiệp đã nộp",
                _finite_float(d.taxes_paid, "taxes_paid"),
                outflow_sign,
            ),
            (
                "other_operating_cash",
                "Tiền thu/chi khác từ hoạt động kinh doanh",
                _finite_float(d.other_operating_cash, "other_operating_cash"),
                1.0,
            ),
        ]

        # Validate & compute Indirect Method components (balance-sheet delta conventions)
        indirect_specs: List[Tuple[str, str, float, float]] = [
            (
                "net_income",
                "Lợi nhuận trước thuế / Lợi nhuận ròng",
                _finite_float(ind.net_income, "net_income"),
                1.0,
            ),
            (
                "depreciation_amortization",
                "Khấu hao TSCĐ và BĐSĐT",
                _finite_float(ind.depreciation_amortization, "depreciation_amortization"),
                1.0,
            ),
            (
                "non_cash_adjustments",
                "Các khoản điều chỉnh phi tiền tệ khác",
                _finite_float(ind.non_cash_adjustments, "non_cash_adjustments"),
                1.0,
            ),
            (
                "delta_receivables",
                "Tăng/giảm các khoản phải thu (-ΔAR)",
                _finite_float(ind.delta_receivables, "delta_receivables"),
                -1.0,
            ),
            (
                "delta_inventory",
                "Tăng/giảm hàng tồn kho (-ΔInv)",
                _finite_float(ind.delta_inventory, "delta_inventory"),
                -1.0,
            ),
            (
                "delta_payables",
                "Tăng/giảm các khoản phải trả (+ΔAP)",
                _finite_float(ind.delta_payables, "delta_payables"),
                1.0,
            ),
            (
                "delta_other_working_capital",
                "Tăng/giảm vốn lưu động khác",
                _finite_float(ind.delta_other_working_capital, "delta_other_working_capital"),
                1.0,
            ),
        ]

        line_items: List[CashFlowLineItemResult] = []
        direct_cfo = 0.0
        for code, label, raw_val, multiplier in direct_specs:
            impact = round(raw_val * multiplier, 4)
            direct_cfo += impact
            line_items.append(
                self._build_line_item("direct", code, label, raw_val, impact, req.citations, req.citation_pages)
            )

        indirect_cfo = 0.0
        impacts_by_code: Dict[str, float] = {}
        for code, label, raw_val, multiplier in indirect_specs:
            impact = round(raw_val * multiplier, 4)
            indirect_cfo += impact
            impacts_by_code[code] = impact
            line_items.append(
                self._build_line_item("indirect", code, label, raw_val, impact, req.citations, req.citation_pages)
            )

        direct_cfo = round(direct_cfo, 4)
        indirect_cfo = round(indirect_cfo, 4)
        reconciliation_variance = round(direct_cfo - indirect_cfo, 4)
        abs_variance = round(abs(reconciliation_variance), 4)

        non_cash_total_addback = round(
            impacts_by_code["depreciation_amortization"] + impacts_by_code["non_cash_adjustments"],
            4,
        )
        working_capital_net_impact = round(
            impacts_by_code["delta_receivables"]
            + impacts_by_code["delta_inventory"]
            + impacts_by_code["delta_payables"]
            + impacts_by_code["delta_other_working_capital"],
            4,
        )

        # Zero-denominator variance safety
        if abs(direct_cfo) < 1e-9:
            variance_pct: Optional[float] = 0.0 if abs_variance <= req.reconciliation_tolerance else None
        else:
            variance_pct = round((abs_variance / abs(direct_cfo)) * 100.0, 4)

        # Materiality classification
        if abs_variance <= req.reconciliation_tolerance:
            status = ReconciliationStatus.RECONCILED
        elif variance_pct is not None and variance_pct <= req.materiality_threshold_pct:
            status = ReconciliationStatus.IMMATERIAL_VARIANCE
        else:
            status = ReconciliationStatus.MATERIAL_MISMATCH

        pct_str = f"{variance_pct:.2f}%" if variance_pct is not None else "N/A (Direct CFO = 0)"
        narrative = (
            f"Đối chiếu Lưu chuyển tiền tệ thuần từ HĐKD (CFO) kỳ {req.period_label} "
            f"[{req.document_id}]: Trực tiếp = {direct_cfo:,.2f}, Gián tiếp = {indirect_cfo:,.2f}, "
            f"Chênh lệch = {reconciliation_variance:+,.2f} ({pct_str}) -> {status.value.upper()}."
        )

        elapsed_ms = round((time.perf_counter() - start) * 1000.0, 3)
        return CashFlowReconcileResponse(
            document_id=req.document_id,
            period_label=req.period_label,
            direct_cfo=direct_cfo,
            indirect_cfo=indirect_cfo,
            reconciliation_variance=reconciliation_variance,
            abs_variance=abs_variance,
            variance_pct=variance_pct,
            status=status,
            working_capital_net_impact=working_capital_net_impact,
            non_cash_total_addback=non_cash_total_addback,
            line_items=line_items,
            citations=req.citations,
            narrative=narrative,
            execution_time_ms=elapsed_ms,
        )

    @staticmethod
    def _build_line_item(
        method: str,
        code: str,
        label: str,
        raw_val: float,
        impact: float,
        citations: Dict[str, BoundingBox],
        citation_pages: Dict[str, int],
    ) -> CashFlowLineItemResult:
        bbox = citations.get(code)
        page = citation_pages.get(code)
        return CashFlowLineItemResult(
            method=method,
            item_code=code,
            label=label,
            raw_input=round(raw_val, 4),
            cfo_impact=impact,
            bounding_box=bbox,
            page_number=page,
        )
