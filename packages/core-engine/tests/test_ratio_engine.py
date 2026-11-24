"""
TDD Test Suite for Financial Ratio Calculation Engine & Cash Flow Health Screener (Sprint 11 Task S11-02)
Governed by AGENTS.md Rules 1, 2, 3, 11, 12, 13B, 14, 15 and ADR-003.
"""

import sys
from pathlib import Path
import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from contracts import (
    FinancialStatementInputs,
    FinancialRatioRequest,
    RatioCategory,
    BenchmarkStatus,
    RatioItem,
    RatioCategoryGroup,
    DuPontAnalysis,
    CashFlowHealthGrade,
    CashFlowHealthScore,
    FinancialRatioResponse,
    BoundingBox,
    GroundedEvidence,
)
from ratio_engine import (
    calculate_liquidity_ratios,
    calculate_solvency_ratios,
    calculate_profitability_ratios,
    calculate_dupont_3stage,
    screen_cash_flow_health,
    FinancialRatioEngine,
)


def test_ratio_contracts_validation_success():
    """Verify construction and validation of FinancialRatioRequest and models."""
    inputs = FinancialStatementInputs(
        revenue=60478.0,
        gross_profit=24614.0,
        operating_profit=11200.0,
        net_income=9019.0,
        interest_expense=350.0,
        current_assets=35000.0,
        cash_and_equivalents=12000.0,
        inventories=5500.0,
        total_assets=52000.0,
        current_liabilities=18000.0,
        total_liabilities=21000.0,
        equity=31000.0,
        operating_cash_flow=10500.0,
        capex=2000.0,
    )
    req = FinancialRatioRequest(
        document_id="VNM_2023_AUDITED",
        raw_inputs_override=inputs,
        include_dupont=True,
        include_cash_flow_screening=True,
        inference_mode="auto",
    )
    assert req.document_id == "VNM_2023_AUDITED"
    assert req.raw_inputs_override.revenue == 60478.0
    assert req.include_dupont is True

    # Test Response model assembly
    evidence = GroundedEvidence(
        page_number=1,
        bounding_box=BoundingBox(ymin=100, xmin=150, ymax=300, xmax=800),
        label="Doanh thu thuần",
        extracted_value="60,478 tỷ",
        confidence=0.98,
        document_id="VNM_2023_AUDITED",
    )
    ratio_item = RatioItem(
        code="current_ratio",
        name="Hệ số thanh toán hiện hành",
        category=RatioCategory.LIQUIDITY,
        value=1.94,
        unit="x",
        benchmark_status=BenchmarkStatus.ADEQUATE,
        formula_description="Tài sản ngắn hạn / Nợ ngắn hạn",
        evidences=[evidence],
    )
    group = RatioCategoryGroup(category=RatioCategory.LIQUIDITY, ratios=[ratio_item])
    dupont = DuPontAnalysis(
        net_profit_margin=14.91,
        asset_turnover=1.16,
        equity_multiplier=1.68,
        roe=29.09,
        formula_narrative="ROE (29.09%) = Net Margin (14.91%) * Asset Turnover (1.16) * Leverage (1.68)",
        evidences=[evidence],
    )
    cf_health = CashFlowHealthScore(
        grade=CashFlowHealthGrade.STRONG,
        earnings_quality_ratio=1.16,
        free_cash_flow=8500.0,
        ocf_to_current_debt=0.58,
        health_summary="Chất lượng dòng tiền xuất sắc, OCF vượt trội so với LNST.",
        warning_signals=[],
        evidences=[evidence],
    )
    res = FinancialRatioResponse(
        document_id="VNM_2023_AUDITED",
        ratio_groups=[group],
        dupont_analysis=dupont,
        cash_flow_health=cf_health,
        raw_inputs_used=inputs,
        evidences=[evidence],
        latency_ms=85.2,
        engine_used="mlx-qwen2.5-vl-7b-4bit",
    )
    assert res.document_id == "VNM_2023_AUDITED"
    assert len(res.ratio_groups) == 1
    assert res.dupont_analysis.roe == 29.09
    assert res.cash_flow_health.grade == CashFlowHealthGrade.STRONG


def test_ratio_contracts_path_traversal_rejection():
    """Verify that path traversal in document_id is strictly rejected (Rule 13B)."""
    with pytest.raises(ValidationError):
        FinancialRatioRequest(document_id="../../etc/passwd")

    with pytest.raises(ValidationError):
        FinancialRatioRequest(document_id="doc/with/slash")

    with pytest.raises(ValidationError):
        FinancialRatioRequest(document_id="doc;injection")


def test_liquidity_ratios_calculation_and_benchmarks():
    """Verify calculation and benchmark classification of liquidity ratios."""
    # Current Assets: 2000, Inventories: 500, Cash: 400, Current Liabilities: 1000
    inputs = FinancialStatementInputs(
        current_assets=2000.0,
        inventories=500.0,
        cash_and_equivalents=400.0,
        current_liabilities=1000.0,
    )
    ratios = calculate_liquidity_ratios(inputs)
    ratio_dict = {r.code: r for r in ratios}

    # Current ratio = 2000 / 1000 = 2.0 (OPTIMAL >= 2.0)
    assert ratio_dict["current_ratio"].value == 2.0
    assert ratio_dict["current_ratio"].benchmark_status == BenchmarkStatus.OPTIMAL

    # Quick ratio = (2000 - 500) / 1000 = 1.5 (OPTIMAL >= 1.0)
    assert ratio_dict["quick_ratio"].value == 1.5
    assert ratio_dict["quick_ratio"].benchmark_status == BenchmarkStatus.OPTIMAL

    # Cash ratio = 400 / 1000 = 0.4 (ADEQUATE 0.2 - 0.5)
    assert ratio_dict["cash_ratio"].value == 0.4
    assert ratio_dict["cash_ratio"].benchmark_status == BenchmarkStatus.ADEQUATE


def test_solvency_and_leverage_ratios_edge_cases():
    """Verify solvency ratios and leverage metrics."""
    inputs = FinancialStatementInputs(
        total_assets=10000.0,
        total_liabilities=4000.0,
        equity=6000.0,
        operating_profit=1500.0,
        interest_expense=300.0,
    )
    ratios = calculate_solvency_ratios(inputs)
    ratio_dict = {r.code: r for r in ratios}

    # Debt-to-Equity = 4000 / 6000 = 0.6667 (OPTIMAL <= 1.0)
    assert ratio_dict["debt_to_equity"].value == 0.6667
    assert ratio_dict["debt_to_equity"].benchmark_status == BenchmarkStatus.OPTIMAL

    # Debt-to-Assets = 4000 / 10000 = 0.4 (OPTIMAL <= 0.5)
    assert ratio_dict["debt_to_assets"].value == 0.4
    assert ratio_dict["debt_to_assets"].benchmark_status == BenchmarkStatus.OPTIMAL

    # Financial Leverage = 10000 / 6000 = 1.6667
    assert ratio_dict["financial_leverage"].value == 1.6667

    # Interest Coverage = 1500 / 300 = 5.0 (OPTIMAL >= 3.0)
    assert ratio_dict["interest_coverage"].value == 5.0
    assert ratio_dict["interest_coverage"].benchmark_status == BenchmarkStatus.OPTIMAL


def test_profitability_and_dupont_decomposition():
    """Verify profitability margins, ROA, ROE, and 3-stage DuPont reconciliation."""
    # Revenue: 10000, Gross Profit: 4000, Operating Profit: 2000, Net Income: 1500
    # Total Assets: 12000, Equity: 6000
    inputs = FinancialStatementInputs(
        revenue=10000.0,
        gross_profit=4000.0,
        operating_profit=2000.0,
        net_income=1500.0,
        total_assets=12000.0,
        equity=6000.0,
    )
    ratios = calculate_profitability_ratios(inputs)
    ratio_dict = {r.code: r for r in ratios}

    # Gross Margin = 4000 / 10000 * 100 = 40.0%
    assert ratio_dict["gross_margin"].value == 40.0
    # Operating Margin = 2000 / 10000 * 100 = 20.0%
    assert ratio_dict["operating_margin"].value == 20.0
    # Net Margin = 1500 / 10000 * 100 = 15.0%
    assert ratio_dict["net_margin"].value == 15.0
    # ROA = 1500 / 12000 * 100 = 12.5%
    assert ratio_dict["roa"].value == 12.5
    # ROE = 1500 / 6000 * 100 = 25.0%
    assert ratio_dict["roe"].value == 25.0

    # DuPont 3-stage:
    # Net Margin: 15.0% (0.15), Asset Turnover: 10000 / 12000 = 0.8333, Equity Multiplier: 12000 / 6000 = 2.0
    # ROE = 15.0 * 0.8333 * 2.0 = 25.0%
    dupont = calculate_dupont_3stage(inputs)
    assert dupont is not None
    assert dupont.net_profit_margin == 15.0
    assert dupont.asset_turnover == 0.8333
    assert dupont.equity_multiplier == 2.0
    assert dupont.roe == 25.0


def test_cash_flow_health_screener_grades():
    """Verify Cash Flow Health classification across grades (STRONG, MODERATE, CAUTION, DISTRESS)."""
    # Grade STRONG: OCF: 2000, Net Income: 1500 (EQ: 1.33 >= 1.0), Capex: 500 (FCF: 1500 > 0)
    strong_inputs = FinancialStatementInputs(
        net_income=1500.0,
        operating_cash_flow=2000.0,
        capex=500.0,
        current_liabilities=3000.0,
    )
    score_strong = screen_cash_flow_health(strong_inputs)
    assert score_strong is not None
    assert score_strong.grade == CashFlowHealthGrade.STRONG
    assert score_strong.free_cash_flow == 1500.0
    assert score_strong.earnings_quality_ratio == 1.3333

    # Grade CAUTION: OCF: 500, Net Income: 1500 (EQ: 0.33 < 0.5)
    caution_inputs = FinancialStatementInputs(
        net_income=1500.0,
        operating_cash_flow=500.0,
        capex=200.0,
        current_liabilities=3000.0,
    )
    score_caution = screen_cash_flow_health(caution_inputs)
    assert score_caution is not None
    assert score_caution.grade == CashFlowHealthGrade.CAUTION
    assert any("thấp" in w.lower() for w in score_caution.warning_signals)

    # Grade DISTRESS: OCF: -500 (Negative operating cash flow)
    distress_inputs = FinancialStatementInputs(
        net_income=1000.0,
        operating_cash_flow=-500.0,
        capex=200.0,
        current_liabilities=2000.0,
    )
    score_distress = screen_cash_flow_health(distress_inputs)
    assert score_distress is not None
    assert score_distress.grade == CashFlowHealthGrade.DISTRESS
    assert any("âm" in w.lower() for w in score_distress.warning_signals)


def test_zero_division_and_negative_equity_safety():
    """Verify that division by zero and negative equity do not raise exceptions and return safe values."""
    zero_inputs = FinancialStatementInputs(
        revenue=0.0,
        current_assets=1000.0,
        current_liabilities=0.0, # Zero liability
        equity=0.0,             # Zero equity
        total_assets=0.0,
        interest_expense=0.0,
    )
    liq = calculate_liquidity_ratios(zero_inputs)
    assert all(r.value is None for r in liq)

    solv = calculate_solvency_ratios(zero_inputs)
    assert all(r.value is None for r in solv)

    dupont = calculate_dupont_3stage(zero_inputs)
    assert dupont is None

    # Negative equity
    neg_equity_inputs = FinancialStatementInputs(
        total_assets=5000.0,
        total_liabilities=7000.0,
        equity=-2000.0, # Negative equity
        operating_profit=500.0,
        interest_expense=100.0,
    )
    solv_neg = calculate_solvency_ratios(neg_equity_inputs)
    ratio_dict = {r.code: r for r in solv_neg}
    assert ratio_dict["debt_to_equity"].benchmark_status == BenchmarkStatus.CRITICAL


@pytest.mark.anyio
async def test_engine_analyze_missing_document_raises_404():
    """Verify that analyzing an unindexed document raises FileNotFoundError."""
    from unittest.mock import MagicMock

    store = MagicMock()
    store.get_pages.return_value = []
    retriever = MagicMock()
    router = MagicMock()

    engine = FinancialRatioEngine(store=store, retriever=retriever, router=router)
    req = FinancialRatioRequest(document_id="NON_EXISTENT_DOC")
    with pytest.raises(FileNotFoundError) as exc_info:
        await engine.analyze(req)
    assert "NON_EXISTENT_DOC" in str(exc_info.value)


@pytest.mark.anyio
async def test_engine_analyze_with_override_inputs():
    """Verify analysis using explicit inputs override without calling router."""
    from unittest.mock import MagicMock

    store = MagicMock()
    store.get_pages.return_value = [{"page_number": 1, "image_path": "/tmp/1.png"}]
    retriever = MagicMock()
    router = MagicMock()

    engine = FinancialRatioEngine(store=store, retriever=retriever, router=router)
    inputs = FinancialStatementInputs(
        revenue=50000.0,
        gross_profit=20000.0,
        operating_profit=10000.0,
        net_income=8000.0,
        interest_expense=500.0,
        current_assets=25000.0,
        cash_and_equivalents=8000.0,
        inventories=4000.0,
        total_assets=45000.0,
        current_liabilities=15000.0,
        total_liabilities=20000.0,
        equity=25000.0,
        operating_cash_flow=9000.0,
        capex=1500.0,
    )
    req = FinancialRatioRequest(
        document_id="VNM_2023",
        raw_inputs_override=inputs,
        include_dupont=True,
        include_cash_flow_screening=True,
    )
    res = await engine.analyze(req)
    assert res.document_id == "VNM_2023"
    assert len(res.ratio_groups) == 3
    assert res.dupont_analysis is not None
    assert res.dupont_analysis.roe == 32.0
    assert res.cash_flow_health is not None
    assert res.cash_flow_health.grade == CashFlowHealthGrade.STRONG
    assert res.latency_ms > 0
    # Router should not be invoked when override is provided
    router.analyze_page.assert_not_called()


@pytest.mark.anyio
async def test_engine_analyze_automated_extraction_mocked():
    """Verify automated line item extraction from document pages and ratio computation."""
    from unittest.mock import MagicMock, AsyncMock

    store = MagicMock()
    store.get_pages.return_value = [
        {"page_number": 1, "image_path": "/tmp/vnm_p1.png"},
        {"page_number": 2, "image_path": "/tmp/vnm_p2.png"},
    ]
    retriever = MagicMock()
    retriever.search.return_value = [1, 2]

    mock_vlm_output = {
        "engine": "mock-vlm",
        "answer": "Báo cáo tài chính năm 2023",
        "extracted_items": {
            "revenue": 60478.0,
            "gross_profit": 24614.0,
            "net_income": 9019.0,
            "current_assets": 35000.0,
            "current_liabilities": 18000.0,
            "operating_cash_flow": 10500.0,
        },
        "evidences": [
            {
                "page_number": 1,
                "ymin": 200,
                "xmin": 100,
                "ymax": 250,
                "xmax": 900,
                "label": "Doanh thu thuần",
                "extracted_value": "60,478 tỷ",
                "confidence": 0.98,
                "document_id": "VNM_2023_AUDITED",
            }
        ],
    }
    router = MagicMock()
    router.analyze_page = AsyncMock(return_value=mock_vlm_output)

    engine = FinancialRatioEngine(store=store, retriever=retriever, router=router)
    req = FinancialRatioRequest(document_id="VNM_2023_AUDITED")
    res = await engine.analyze(req)

    assert res.document_id == "VNM_2023_AUDITED"
    assert res.raw_inputs_used.revenue == 60478.0
    assert len(res.evidences) >= 1
    assert res.evidences[0].document_id == "VNM_2023_AUDITED"
    assert 0 <= res.evidences[0].bounding_box.ymin < res.evidences[0].bounding_box.ymax <= 1000


