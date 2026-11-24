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
