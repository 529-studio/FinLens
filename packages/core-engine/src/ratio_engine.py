"""
Financial Ratio Calculation Engine & Cash Flow Health Screener (Sprint 11 Task S11-02)
Governed by AGENTS.md Rules 1, 2, 3, 11, 12, 13B, 14, 15 and ADR-003.
Provides deterministic ratio mathematics, DuPont 3-stage decomposition, and cash flow health grading.
"""

import re
import time
from typing import List, Dict, Any, Optional, Tuple

from contracts import (
    FinancialStatementInputs,
    FinancialRatioRequest,
    FinancialRatioResponse,
    RatioCategory,
    BenchmarkStatus,
    RatioItem,
    RatioCategoryGroup,
    DuPontAnalysis,
    CashFlowHealthGrade,
    CashFlowHealthScore,
    GroundedEvidence,
    BoundingBox,
)


def safe_divide(numerator: Optional[float], denominator: Optional[float], precision: int = 4) -> Optional[float]:
    """Safe division with division-by-zero protection and IEEE-754 precision normalization."""
    if numerator is None or denominator is None or denominator == 0.0:
        return None
    val = float(numerator) / float(denominator)
    return round((val + 1e-9), precision)


def calculate_liquidity_ratios(
    inputs: FinancialStatementInputs,
    evidences_map: Optional[Dict[str, GroundedEvidence]] = None,
) -> List[RatioItem]:
    """
    Computes liquidity ratios: Current Ratio, Quick Ratio, Cash Ratio.
    """
    evidences_map = evidences_map or {}
    ratios: List[RatioItem] = []

    # 1. Current Ratio
    cr_val = safe_divide(inputs.current_assets, inputs.current_liabilities)
    cr_status = BenchmarkStatus.NOT_APPLICABLE
    if cr_val is not None:
        if cr_val >= 2.0:
            cr_status = BenchmarkStatus.OPTIMAL
        elif cr_val >= 1.2:
            cr_status = BenchmarkStatus.ADEQUATE
        elif cr_val >= 1.0:
            cr_status = BenchmarkStatus.WARNING
        else:
            cr_status = BenchmarkStatus.CRITICAL

    ratios.append(
        RatioItem(
            code="current_ratio",
            name="Hệ số thanh toán hiện hành (Current Ratio)",
            category=RatioCategory.LIQUIDITY,
            value=cr_val,
            unit="x",
            benchmark_status=cr_status,
            formula_description="Tài sản ngắn hạn / Nợ ngắn hạn",
            evidences=[e for k, e in evidences_map.items() if k in ["current_assets", "current_liabilities"]],
        )
    )

    # 2. Quick Ratio
    qr_val = None
    if inputs.current_assets is not None and inputs.current_liabilities is not None and inputs.current_liabilities != 0.0:
        inv = inputs.inventories or 0.0
        qr_val = safe_divide(inputs.current_assets - inv, inputs.current_liabilities)

    qr_status = BenchmarkStatus.NOT_APPLICABLE
    if qr_val is not None:
        if qr_val >= 1.0:
            qr_status = BenchmarkStatus.OPTIMAL
        elif qr_val >= 0.8:
            qr_status = BenchmarkStatus.ADEQUATE
        else:
            qr_status = BenchmarkStatus.WARNING

    ratios.append(
        RatioItem(
            code="quick_ratio",
            name="Hệ số thanh toán nhanh (Quick Ratio)",
            category=RatioCategory.LIQUIDITY,
            value=qr_val,
            unit="x",
            benchmark_status=qr_status,
            formula_description="(Tài sản ngắn hạn - Hàng tồn kho) / Nợ ngắn hạn",
            evidences=[e for k, e in evidences_map.items() if k in ["current_assets", "inventories", "current_liabilities"]],
        )
    )

    # 3. Cash Ratio
    cash_val = safe_divide(inputs.cash_and_equivalents, inputs.current_liabilities)
    cash_status = BenchmarkStatus.NOT_APPLICABLE
    if cash_val is not None:
        if cash_val >= 0.5:
            cash_status = BenchmarkStatus.OPTIMAL
        elif cash_val >= 0.2:
            cash_status = BenchmarkStatus.ADEQUATE
        else:
            cash_status = BenchmarkStatus.WARNING

    ratios.append(
        RatioItem(
            code="cash_ratio",
            name="Hệ số thanh toán tiền mặt (Cash Ratio)",
            category=RatioCategory.LIQUIDITY,
            value=cash_val,
            unit="x",
            benchmark_status=cash_status,
            formula_description="Tiền & tương đương tiền / Nợ ngắn hạn",
            evidences=[e for k, e in evidences_map.items() if k in ["cash_and_equivalents", "current_liabilities"]],
        )
    )

    return ratios


def calculate_solvency_ratios(
    inputs: FinancialStatementInputs,
    evidences_map: Optional[Dict[str, GroundedEvidence]] = None,
) -> List[RatioItem]:
    """
    Computes solvency & leverage ratios: Debt-to-Equity, Debt-to-Assets, Financial Leverage, Interest Coverage.
    """
    evidences_map = evidences_map or {}
    ratios: List[RatioItem] = []

    # 1. Debt-to-Equity
    de_val = safe_divide(inputs.total_liabilities, inputs.equity)
    de_status = BenchmarkStatus.NOT_APPLICABLE
    if inputs.equity is not None and inputs.equity <= 0.0:
        de_status = BenchmarkStatus.CRITICAL
    elif de_val is not None:
        if de_val <= 1.0:
            de_status = BenchmarkStatus.OPTIMAL
        elif de_val <= 2.0:
            de_status = BenchmarkStatus.ADEQUATE
        elif de_val <= 3.0:
            de_status = BenchmarkStatus.WARNING
        else:
            de_status = BenchmarkStatus.CRITICAL

    ratios.append(
        RatioItem(
            code="debt_to_equity",
            name="Hệ số Nợ / Vốn chủ sở hữu (Debt-to-Equity)",
            category=RatioCategory.SOLVENCY,
            value=de_val,
            unit="x",
            benchmark_status=de_status,
            formula_description="Tổng nợ phải trả / Vốn chủ sở hữu",
            evidences=[e for k, e in evidences_map.items() if k in ["total_liabilities", "equity"]],
        )
    )

    # 2. Debt-to-Assets
    da_val = safe_divide(inputs.total_liabilities, inputs.total_assets)
    da_status = BenchmarkStatus.NOT_APPLICABLE
    if da_val is not None:
        if da_val <= 0.5:
            da_status = BenchmarkStatus.OPTIMAL
        elif da_val <= 0.7:
            da_status = BenchmarkStatus.ADEQUATE
        else:
            da_status = BenchmarkStatus.WARNING

    ratios.append(
        RatioItem(
            code="debt_to_assets",
            name="Hệ số Nợ / Tổng tài sản (Debt-to-Assets)",
            category=RatioCategory.SOLVENCY,
            value=da_val,
            unit="x",
            benchmark_status=da_status,
            formula_description="Tổng nợ phải trả / Tổng tài sản",
            evidences=[e for k, e in evidences_map.items() if k in ["total_liabilities", "total_assets"]],
        )
    )

    # 3. Financial Leverage (Equity Multiplier)
    fl_val = safe_divide(inputs.total_assets, inputs.equity)
    fl_status = BenchmarkStatus.NOT_APPLICABLE
    if inputs.equity is not None and inputs.equity <= 0.0:
        fl_status = BenchmarkStatus.CRITICAL
    elif fl_val is not None:
        if fl_val <= 2.0:
            fl_status = BenchmarkStatus.OPTIMAL
        elif fl_val <= 3.5:
            fl_status = BenchmarkStatus.ADEQUATE
        else:
            fl_status = BenchmarkStatus.WARNING

    ratios.append(
        RatioItem(
            code="financial_leverage",
            name="Đòn bẩy tài chính (Financial Leverage Multiplier)",
            category=RatioCategory.SOLVENCY,
            value=fl_val,
            unit="x",
            benchmark_status=fl_status,
            formula_description="Tổng tài sản / Vốn chủ sở hữu",
            evidences=[e for k, e in evidences_map.items() if k in ["total_assets", "equity"]],
        )
    )

    # 4. Interest Coverage
    ic_val = safe_divide(inputs.operating_profit, inputs.interest_expense)
    ic_status = BenchmarkStatus.NOT_APPLICABLE
    if ic_val is not None:
        if ic_val >= 3.0:
            ic_status = BenchmarkStatus.OPTIMAL
        elif ic_val >= 1.5:
            ic_status = BenchmarkStatus.ADEQUATE
        else:
            ic_status = BenchmarkStatus.CRITICAL

    ratios.append(
        RatioItem(
            code="interest_coverage",
            name="Hệ số chi trả lãi vay (Interest Coverage Ratio)",
            category=RatioCategory.SOLVENCY,
            value=ic_val,
            unit="x",
            benchmark_status=ic_status,
            formula_description="Lợi nhuận từ HĐKD (EBIT) / Chi phí lãi vay",
            evidences=[e for k, e in evidences_map.items() if k in ["operating_profit", "interest_expense"]],
        )
    )

    return ratios


def calculate_profitability_ratios(
    inputs: FinancialStatementInputs,
    evidences_map: Optional[Dict[str, GroundedEvidence]] = None,
) -> List[RatioItem]:
    """
    Computes profitability margins and return ratios: Gross Margin, Operating Margin, Net Margin, ROA, ROE.
    """
    evidences_map = evidences_map or {}
    ratios: List[RatioItem] = []

    # 1. Gross Margin (%)
    gm_val = None
    if inputs.gross_profit is not None and inputs.revenue and inputs.revenue != 0.0:
        gm_val = safe_divide(inputs.gross_profit * 100.0, inputs.revenue, precision=2)

    ratios.append(
        RatioItem(
            code="gross_margin",
            name="Biên lợi nhuận gộp (Gross Margin)",
            category=RatioCategory.PROFITABILITY,
            value=gm_val,
            unit="%",
            benchmark_status=BenchmarkStatus.OPTIMAL if gm_val and gm_val >= 25.0 else BenchmarkStatus.ADEQUATE if gm_val else BenchmarkStatus.NOT_APPLICABLE,
            formula_description="Lợi nhuận gộp / Doanh thu thuần * 100",
            evidences=[e for k, e in evidences_map.items() if k in ["gross_profit", "revenue"]],
        )
    )

    # 2. Operating Margin (%)
    opm_val = None
    if inputs.operating_profit is not None and inputs.revenue and inputs.revenue != 0.0:
        opm_val = safe_divide(inputs.operating_profit * 100.0, inputs.revenue, precision=2)

    ratios.append(
        RatioItem(
            code="operating_margin",
            name="Biên lợi nhuận hoạt động (Operating Margin)",
            category=RatioCategory.PROFITABILITY,
            value=opm_val,
            unit="%",
            benchmark_status=BenchmarkStatus.OPTIMAL if opm_val and opm_val >= 15.0 else BenchmarkStatus.ADEQUATE if opm_val else BenchmarkStatus.NOT_APPLICABLE,
            formula_description="Lợi nhuận từ HĐKD / Doanh thu thuần * 100",
            evidences=[e for k, e in evidences_map.items() if k in ["operating_profit", "revenue"]],
        )
    )

    # 3. Net Margin (%)
    nm_val = None
    if inputs.net_income is not None and inputs.revenue and inputs.revenue != 0.0:
        nm_val = safe_divide(inputs.net_income * 100.0, inputs.revenue, precision=2)

    ratios.append(
        RatioItem(
            code="net_margin",
            name="Biên lợi nhuận ròng (Net Margin)",
            category=RatioCategory.PROFITABILITY,
            value=nm_val,
            unit="%",
            benchmark_status=BenchmarkStatus.OPTIMAL if nm_val and nm_val >= 10.0 else BenchmarkStatus.ADEQUATE if nm_val else BenchmarkStatus.NOT_APPLICABLE,
            formula_description="Lợi nhuận sau thuế / Doanh thu thuần * 100",
            evidences=[e for k, e in evidences_map.items() if k in ["net_income", "revenue"]],
        )
    )

    # 4. ROA (%)
    roa_val = None
    if inputs.net_income is not None and inputs.total_assets and inputs.total_assets != 0.0:
        roa_val = safe_divide(inputs.net_income * 100.0, inputs.total_assets, precision=2)

    ratios.append(
        RatioItem(
            code="roa",
            name="Tỷ suất sinh lời trên tổng tài sản (ROA)",
            category=RatioCategory.PROFITABILITY,
            value=roa_val,
            unit="%",
            benchmark_status=BenchmarkStatus.OPTIMAL if roa_val and roa_val >= 10.0 else BenchmarkStatus.ADEQUATE if roa_val else BenchmarkStatus.NOT_APPLICABLE,
            formula_description="Lợi nhuận sau thuế / Tổng tài sản * 100",
            evidences=[e for k, e in evidences_map.items() if k in ["net_income", "total_assets"]],
        )
    )

    # 5. ROE (%)
    roe_val = None
    if inputs.net_income is not None and inputs.equity and inputs.equity != 0.0:
        roe_val = safe_divide(inputs.net_income * 100.0, inputs.equity, precision=2)

    ratios.append(
        RatioItem(
            code="roe",
            name="Tỷ suất sinh lời trên vốn chủ sở hữu (ROE)",
            category=RatioCategory.PROFITABILITY,
            value=roe_val,
            unit="%",
            benchmark_status=BenchmarkStatus.OPTIMAL if roe_val and roe_val >= 18.0 else BenchmarkStatus.ADEQUATE if roe_val else BenchmarkStatus.NOT_APPLICABLE,
            formula_description="Lợi nhuận sau thuế / Vốn chủ sở hữu * 100",
            evidences=[e for k, e in evidences_map.items() if k in ["net_income", "equity"]],
        )
    )

    return ratios


def calculate_dupont_3stage(
    inputs: FinancialStatementInputs,
    evidences_map: Optional[Dict[str, GroundedEvidence]] = None,
) -> Optional[DuPontAnalysis]:
    """
    Computes 3-stage DuPont decomposition: ROE = Net Margin * Asset Turnover * Equity Multiplier.
    """
    evidences_map = evidences_map or {}
    if not (inputs.revenue and inputs.total_assets and inputs.equity and inputs.net_income):
        return None
    if inputs.revenue == 0.0 or inputs.total_assets == 0.0 or inputs.equity == 0.0:
        return None

    net_margin = safe_divide(inputs.net_income * 100.0, inputs.revenue, precision=2)
    asset_turnover = safe_divide(inputs.revenue, inputs.total_assets, precision=4)
    equity_multiplier = safe_divide(inputs.total_assets, inputs.equity, precision=4)
    roe = safe_divide(inputs.net_income * 100.0, inputs.equity, precision=2)

    narrative = (
        f"Phân tích DuPont 3 bước: ROE ({roe}%) = Biên lợi nhuận ròng ({net_margin}%) "
        f"x Vòng quay tài sản ({asset_turnover}x) x Đòn bẩy tài chính ({equity_multiplier}x)."
    )

    return DuPontAnalysis(
        net_profit_margin=net_margin,
        asset_turnover=asset_turnover,
        equity_multiplier=equity_multiplier,
        roe=roe,
        formula_narrative=narrative,
        evidences=list(evidences_map.values()),
    )


def screen_cash_flow_health(
    inputs: FinancialStatementInputs,
    evidences_map: Optional[Dict[str, GroundedEvidence]] = None,
) -> Optional[CashFlowHealthScore]:
    """
    Evaluates Cash Flow Health and Earnings Quality (OCF/Net Income, FCF = OCF - Capex).
    Assigns grades: STRONG, MODERATE, CAUTION, DISTRESS.
    """
    if inputs.operating_cash_flow is None:
        return None

    evidences_map = evidences_map or {}
    ocf = inputs.operating_cash_flow
    capex = inputs.capex or 0.0
    fcf = round((ocf - capex + 1e-9), 4)

    eq_ratio = None
    if inputs.net_income is not None and inputs.net_income != 0.0:
        eq_ratio = safe_divide(ocf, inputs.net_income, precision=4)

    ocf_debt = safe_divide(ocf, inputs.current_liabilities, precision=4)

    warnings: List[str] = []
    grade = CashFlowHealthGrade.MODERATE
    summary = ""

    if ocf < 0.0:
        grade = CashFlowHealthGrade.DISTRESS
        warnings.append("Dòng tiền kinh doanh (OCF) bị âm, doanh nghiệp đang thâm hụt tiền từ hoạt động cốt lõi.")
        summary = "Xếp loại DISTRESS: Dòng tiền hoạt động kinh doanh âm nghiêm trọng, phụ thuộc vào vay nợ hoặc huy động vốn."
    elif fcf < 0.0 or (eq_ratio is not None and eq_ratio < 0.5):
        grade = CashFlowHealthGrade.CAUTION
        if fcf < 0.0:
            warnings.append(f"Dòng tiền tự do (FCF = {fcf:,.1f}) âm, tiền từ HĐKD không đủ trang trải chi phí vốn (Capex).")
        if eq_ratio is not None and eq_ratio < 0.5:
            warnings.append(f"Tỷ lệ chất lượng lợi nhuận OCF/LNST thấp ({eq_ratio:.2f} < 0.5), rủi ro dồn tích (accruals) cao.")
        summary = "Xếp loại CAUTION: Doanh nghiệp có dòng tiền tự do FCF âm hoặc lợi nhuận sổ sách không đi kèm dòng tiền thực tế."
    elif eq_ratio is not None and eq_ratio >= 1.0 and fcf > 0.0:
        grade = CashFlowHealthGrade.STRONG
        summary = "Xếp loại STRONG: Chất lượng lợi nhuận xuất sắc (OCF >= LNST), dòng tiền tự do dồi dào tài trợ tăng trưởng."
    else:
        grade = CashFlowHealthGrade.MODERATE
        summary = "Xếp loại MODERATE: Dòng tiền hoạt động ổn định ở mức trung bình, đáp ứng các nghĩa vụ ngắn hạn."

    return CashFlowHealthScore(
        grade=grade,
        earnings_quality_ratio=eq_ratio,
        free_cash_flow=fcf,
        ocf_to_current_debt=ocf_debt,
        health_summary=summary,
        warning_signals=warnings,
        evidences=[e for k, e in evidences_map.items() if k in ["operating_cash_flow", "capex", "net_income"]],
    )


class FinancialRatioEngine:
    """
    Decoupled domain coordinator for financial ratio calculation and cash flow health screening.
    Supports explicit input overrides or automated visual extraction from stored filings.
    """

    def __init__(self, store: Any, retriever: Any, router: Any):
        self.store = store
        self.retriever = retriever
        self.router = router

    async def analyze(self, req: FinancialRatioRequest) -> FinancialRatioResponse:
        start_time = time.time()

        # 1. Verify document exists in store
        pages = self.store.get_pages(req.document_id)
        if not pages:
            raise FileNotFoundError(f"Document '{req.document_id}' not found in index. Please ingest it first.")

        evidences_map: Dict[str, GroundedEvidence] = {}
        all_evidences: List[GroundedEvidence] = []
        engine_used = "deterministic-formula-engine"

        # 2. Obtain inputs (either explicit override or automated extraction)
        if req.raw_inputs_override is not None:
            inputs = req.raw_inputs_override
        else:
            inputs, extracted_evidences = await self._extract_line_items_from_document(
                req.document_id, mode=req.inference_mode
            )
            evidences_map = extracted_evidences
            all_evidences.extend(extracted_evidences.values())
            engine_used = "hybrid-vlm-ratio-engine"

        # 3. Calculate ratio groups
        liq_ratios = calculate_liquidity_ratios(inputs, evidences_map)
        solv_ratios = calculate_solvency_ratios(inputs, evidences_map)
        prof_ratios = calculate_profitability_ratios(inputs, evidences_map)

        ratio_groups = [
            RatioCategoryGroup(category=RatioCategory.LIQUIDITY, ratios=liq_ratios),
            RatioCategoryGroup(category=RatioCategory.SOLVENCY, ratios=solv_ratios),
            RatioCategoryGroup(category=RatioCategory.PROFITABILITY, ratios=prof_ratios),
        ]

        # 4. DuPont 3-stage decomposition
        dupont = None
        if req.include_dupont:
            dupont = calculate_dupont_3stage(inputs, evidences_map)

        # 5. Cash Flow Health Screener
        cf_health = None
        if req.include_cash_flow_screening:
            cf_health = screen_cash_flow_health(inputs, evidences_map)

        duration_ms = (time.time() - start_time) * 1000.0

        return FinancialRatioResponse(
            document_id=req.document_id,
            ratio_groups=ratio_groups,
            dupont_analysis=dupont,
            cash_flow_health=cf_health,
            raw_inputs_used=inputs,
            evidences=all_evidences,
            latency_ms=round(duration_ms, 2),
            engine_used=engine_used,
        )

    async def _extract_line_items_from_document(
        self, document_id: str, mode: str
    ) -> Tuple[FinancialStatementInputs, Dict[str, GroundedEvidence]]:
        """
        Coordinates visual retrieval and VLM extraction to parse statement line items.
        """
        candidate_pages = self.retriever.search(
            document_id,
            "Bảng cân đối kế toán kết quả hoạt động kinh doanh lưu chuyển tiền tệ",
            top_k=3,
        )
        if not candidate_pages:
            candidate_pages = [1]

        stored_pages = self.store.get_pages(document_id)
        page_dict = {p["page_number"]: p["image_path"] for p in stored_pages}

        extracted_data: Dict[str, Any] = {}
        evidences_map: Dict[str, GroundedEvidence] = {}

        for p_num in candidate_pages:
            img_path = page_dict.get(p_num)
            if not img_path:
                continue

            query = (
                "Bóc tách các chỉ số tài chính chính: Doanh thu thuần (revenue), "
                "Lợi nhuận gộp (gross_profit), Lợi nhuận sau thuế (net_income), "
                "Tài sản ngắn hạn (current_assets), Hàng tồn kho (inventories), "
                "Tiền và tương đương tiền (cash_and_equivalents), Tổng tài sản (total_assets), "
                "Nợ ngắn hạn (current_liabilities), Tổng nợ (total_liabilities), Vốn chủ sở hữu (equity), "
                "Dòng tiền thuần từ HĐKD (operating_cash_flow), Chi mua sắm TSCĐ (capex)."
            )

            res = await self.router.analyze_page(
                image_path=img_path,
                query=query,
                page_number=p_num,
                preferred_mode=mode,
            )

            if "extracted_items" in res and isinstance(res["extracted_items"], dict):
                for k, v in res["extracted_items"].items():
                    if k not in extracted_data and v is not None:
                        try:
                            extracted_data[k] = float(v)
                        except (ValueError, TypeError):
                            pass

            for ev in res.get("evidences", []):
                ev_obj = GroundedEvidence(
                    page_number=ev.get("page_number", p_num),
                    bounding_box=BoundingBox(
                        ymin=ev["ymin"],
                        xmin=ev["xmin"],
                        ymax=ev["ymax"],
                        xmax=ev["xmax"],
                    ),
                    label=ev.get("label", "Chỉ số tài chính"),
                    extracted_value=ev.get("extracted_value"),
                    confidence=ev.get("confidence", 0.95),
                    document_id=document_id,
                )
                lbl = ev_obj.label.lower()
                for key in ["revenue", "gross_profit", "net_income", "current_assets", "current_liabilities", "equity", "operating_cash_flow", "capex"]:
                    if key in lbl or key in extracted_data:
                        evidences_map[key] = ev_obj

        valid_fields = FinancialStatementInputs.model_fields.keys()
        inputs = FinancialStatementInputs(**{k: v for k, v in extracted_data.items() if k in valid_fields})
        return inputs, evidences_map

