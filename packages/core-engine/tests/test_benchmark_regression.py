"""
FinTrace Benchmark Regression & CI Reporting Test Suite
Validates regression detection, baseline delta calculations, threshold violation gates,
markdown summary generation, zero-emoji compliance, and CLI exit codes.
Governed by Sprint 10 Task S10-01, AGENTS.md Rule 3, Rule 13, and Rule 15.
"""

import sys
import json
from pathlib import Path
import subprocess
import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
BENCHMARKS_DIR = REPO_ROOT / "benchmarks"
sys.path.insert(0, str(BENCHMARKS_DIR))

from eval_golden_suite import (
    calculate_iou,
    compare_benchmarks,
    format_markdown_report,
    evaluate_retrieval_suite,
    GoldenBenchmarkSummary,
    RegressionReport,
    RegressionDelta,
)


@pytest.fixture
def sample_baseline_dict():
    return {
        "total_queries": 105,
        "colpali_top_1_recall": 1.0,
        "colpali_top_3_recall": 1.0,
        "colpali_chart_blindness_rate": 0.0,
        "text_top_1_recall": 0.8381,
        "text_top_3_recall": 1.0,
        "text_chart_blindness_rate": 0.3429,
        "mean_iou": 0.922,
        "avg_latency_ms": 0.08,
        "dod_passed": True,
        "details": {
            "visual_queries_count": 35,
            "complex_table_count": 35,
            "footnote_count": 35,
        },
    }


@pytest.fixture
def sample_current_summary():
    return GoldenBenchmarkSummary(
        total_queries=105,
        colpali_top_1_recall=1.0,
        colpali_top_3_recall=1.0,
        colpali_chart_blindness_rate=0.0,
        text_top_1_recall=0.8381,
        text_top_3_recall=1.0,
        text_chart_blindness_rate=0.3429,
        mean_iou=0.922,
        avg_latency_ms=0.08,
        dod_passed=True,
        details={
            "visual_queries_count": 35,
            "complex_table_count": 35,
            "footnote_count": 35,
        },
    )


def test_calculate_iou_robustness_and_clamping():
    # Identical bounding box
    assert calculate_iou([100, 100, 200, 200], [100, 100, 200, 200]) == 1.0

    # Non-overlapping
    assert calculate_iou([100, 100, 200, 200], [300, 300, 400, 400]) == 0.0

    # Inverted coordinates [ymax, xmax, ymin, xmin] are normalized safely
    assert calculate_iou([200, 200, 100, 100], [100, 100, 200, 200]) == 1.0

    # Partial overlap
    iou = calculate_iou([0, 0, 100, 100], [0, 50, 100, 150])
    assert abs(iou - (1.0 / 3.0)) < 1e-4

    # Invalid box dimension
    assert calculate_iou([0, 0], [100, 100, 200, 200]) == 0.0


def test_compare_benchmarks_stable_no_regression(sample_current_summary, sample_baseline_dict):
    report = compare_benchmarks(sample_current_summary, sample_baseline_dict)
    assert isinstance(report, RegressionReport)
    assert not report.has_regression
    assert len(report.threshold_violations) == 0
    assert report.passed
    assert "PASSED" in report.summary_message

    for d in report.deltas:
        assert isinstance(d, RegressionDelta)
        assert not d.is_regression
        assert not d.violates_threshold


def test_compare_benchmarks_detects_recall_regression(sample_current_summary, sample_baseline_dict):
    # Simulate Top-1 recall drop by 3% (from 1.0 to 0.97) with 2% max drop tolerance
    sample_current_summary.colpali_top_1_recall = 0.97
    report = compare_benchmarks(
        sample_current_summary,
        sample_baseline_dict,
        max_drop_percent=2.0,
    )
    assert report.has_regression
    assert not report.passed
    top1_delta = next(d for d in report.deltas if d.metric == "ColPali Top-1 Recall")
    assert top1_delta.is_regression
    assert top1_delta.status == "[REGRESSION]"


def test_compare_benchmarks_detects_chart_blindness_regression(sample_current_summary, sample_baseline_dict):
    # Simulate chart blindness increase to 0.03 (above 0.0 threshold and > 2% drop)
    sample_current_summary.colpali_chart_blindness_rate = 0.03
    sample_current_summary.dod_passed = False
    report = compare_benchmarks(
        sample_current_summary,
        sample_baseline_dict,
        max_drop_percent=2.0,
    )
    assert report.has_regression
    assert len(report.threshold_violations) >= 1
    assert not report.passed


def test_compare_benchmarks_detects_threshold_violation(sample_current_summary, sample_baseline_dict):
    # Drop below absolute threshold (0.85)
    sample_current_summary.colpali_top_1_recall = 0.80
    sample_current_summary.dod_passed = False
    report = compare_benchmarks(sample_current_summary, sample_baseline_dict)
    assert not report.passed
    assert any("below threshold" in v for v in report.threshold_violations)


def test_format_markdown_report_zero_emojis(sample_current_summary, sample_baseline_dict):
    report = compare_benchmarks(sample_current_summary, sample_baseline_dict)
    md = format_markdown_report(report, sample_current_summary)

    assert "# FinTrace Golden Dataset Regression Benchmark Report" in md
    assert "| Metric | Baseline | Current | Delta | DoD Threshold | Status |" in md
    assert "`[PASS] PASSED`" in md
    assert "ColPali Top-1 Recall" in md

    # Rule 15: Zero raw Unicode emojis allowed in markdown UI reports
    for char in md:
        code = ord(char)
        # Check standard emoji ranges
        is_emoji = (
            (0x1F600 <= code <= 0x1F64F) or  # Emoticons
            (0x1F300 <= code <= 0x1F5FF) or  # Misc Symbols and Pictographs
            (0x1F680 <= code <= 0x1F6FF) or  # Transport and Map
            (0x1F700 <= code <= 0x1F77F) or  # Alchemical
            (0x1F780 <= code <= 0x1F7FF) or  # Geometric Shapes Extended (large colored circles)
            (0x1F900 <= code <= 0x1F9FF) or  # Supplemental Symbols and Pictographs
            (0x2600 <= code <= 0x26FF) or    # Misc symbols (warning, checkmark emoji)
            (0x2700 <= code <= 0x27BF)       # Dingbats
        )
        assert not is_emoji, f"Raw emoji character '{char}' (code {hex(code)}) found in markdown report!"


def test_evaluate_retrieval_suite_with_baseline(tmp_path):
    baseline_path = BENCHMARKS_DIR / "results" / "sprint8_golden_benchmark.json"
    manifest_path = BENCHMARKS_DIR / "data" / "manifest_golden_100.json"
    out_json = tmp_path / "test_out.json"
    out_md = tmp_path / "test_summary.md"

    summary = evaluate_retrieval_suite(
        manifest_path=manifest_path,
        dry_run=False,
        output_path=out_json,
        baseline_path=baseline_path,
        markdown_path=out_md,
    )

    assert isinstance(summary, GoldenBenchmarkSummary)
    assert summary.dod_passed is True
    assert summary.has_regression is False
    assert summary.regression_report is not None

    # Check output json was written
    assert out_json.exists()
    with open(out_json, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["total_queries"] == 105
    assert data["colpali_top_1_recall"] >= 0.85

    # Check markdown summary was generated
    assert out_md.exists()
    md_text = out_md.read_text(encoding="utf-8")
    assert "FinTrace Golden Dataset Regression Benchmark Report" in md_text
    assert "[PASS]" in md_text
