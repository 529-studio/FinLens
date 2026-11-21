"""
FinSight Sprint 8 Benchmark Tests: Golden Dataset & Retrieval Accuracy
Verifies manifest structure, 100+ queries coverage, IoU computation, and DoD compliance.
Governed by Sprint 8 Task S8-01, AGENTS.md Rule 3 & Rule 13.
"""

import sys
import json
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
BENCHMARKS_DIR = REPO_ROOT / "benchmarks"
sys.path.insert(0, str(BENCHMARKS_DIR))

# Import module under test (will fail before implementation)
from eval_golden_suite import (
    load_golden_manifest,
    calculate_iou,
    evaluate_retrieval_suite,
    GoldenBenchmarkSummary,
)


def test_golden_manifest_structure_and_coverage():
    manifest_path = BENCHMARKS_DIR / "data" / "manifest_golden_100.json"
    assert manifest_path.exists(), f"Golden manifest not found at {manifest_path}"

    data = load_golden_manifest(manifest_path)
    assert "benchmark_suite" in data
    assert "queries" in data
    queries = data["queries"]

    # Must cover at least 100 enterprise financial queries across Vietnam BCTC
    assert len(queries) >= 100, f"Expected >= 100 queries in golden dataset, got {len(queries)}"

    categories = set(q["category"] for q in queries)
    assert "visual_chart" in categories, "Missing visual_chart queries"
    assert "complex_table" in categories, "Missing complex_table queries"
    assert "footnote_disclosure" in categories, "Missing footnote_disclosure queries"

    # Validate ground truth fields
    for q in queries:
        assert "id" in q
        assert "query" in q
        assert "target_page" in q
        assert "ground_truth_bbox" in q
        bbox = q["ground_truth_bbox"]
        assert len(bbox) == 4
        # Normalized coordinates [ymin, xmin, ymax, xmax] between 0 and 1000
        ymin, xmin, ymax, xmax = bbox
        assert 0 <= ymin <= ymax <= 1000
        assert 0 <= xmin <= xmax <= 1000


def test_calculate_iou_metric():
    # Identical bounding boxes
    assert calculate_iou([100, 100, 200, 200], [100, 100, 200, 200]) == 1.0

    # Non-overlapping bounding boxes
    assert calculate_iou([100, 100, 200, 200], [300, 300, 400, 400]) == 0.0

    # 50% overlap calculation
    # Box A: 100x100 (area 10000) from (0,0) to (100,100)
    # Box B: 100x100 (area 10000) from (50,0) to (150,100)
    # Inter: 50x100 (area 5000), Union: 15000 -> IoU = 1/3
    iou = calculate_iou([0, 0, 100, 100], [0, 50, 100, 150])
    assert abs(iou - (1.0 / 3.0)) < 1e-4


def test_evaluate_retrieval_suite_dod_gates():
    manifest_path = BENCHMARKS_DIR / "data" / "manifest_golden_100.json"
    summary = evaluate_retrieval_suite(manifest_path=manifest_path, dry_run=True)

    assert isinstance(summary, GoldenBenchmarkSummary)
    assert summary.total_queries >= 100
    assert summary.colpali_top_1_recall >= 0.85, f"Top-1 recall {summary.colpali_top_1_recall} below DoD 85%"
    assert summary.colpali_top_3_recall >= 0.95, f"Top-3 recall {summary.colpali_top_3_recall} below DoD 95%"
    assert summary.colpali_chart_blindness_rate <= 0.0, f"Chart blindness {summary.colpali_chart_blindness_rate} must be 0%"
    assert summary.mean_iou >= 0.80, f"Mean IoU {summary.mean_iou} below DoD 0.80"
