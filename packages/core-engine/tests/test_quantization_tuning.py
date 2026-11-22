"""
FinTrace VLM & Retrieval Quantization Tuning Test Suite
Tests 4-bit vs 8-bit precision configurations, memory ceiling enforcement,
benchmarking harness, trade-off calculations, and zero-emoji compliance.
Governed by Sprint 10 Task S10-04, ADR-002, AGENTS.md Rule 3, Rule 13, and Rule 15.
"""

import sys
import json
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
BENCHMARKS_DIR = REPO_ROOT / "benchmarks"
sys.path.insert(0, str(BENCHMARKS_DIR))

from model_manager import ModelManager, QUANTIZED_REGISTRY
from mlx_engine import MLXEngine
from eval_quantization import (
    run_quantization_evaluation,
    format_markdown_tradeoff_report,
    QuantizationBenchmarkReport,
    QuantizationMetric,
)


def test_model_manager_quantized_registry_and_heuristics():
    manager = ModelManager()

    # 1. Verify registry contents
    assert "mlx-community/Qwen2.5-VL-7B-Instruct-4bit" in QUANTIZED_REGISTRY
    assert "mlx-community/Qwen2.5-VL-7B-Instruct-8bit" in QUANTIZED_REGISTRY
    assert "mlx-community/ColPali-v1.2-4bit" in QUANTIZED_REGISTRY
    assert "mlx-community/ColPali-v1.2-8bit" in QUANTIZED_REGISTRY

    # 2. Verify 4-bit model info
    info_4bit = manager.get_model_info("mlx-community/Qwen2.5-VL-7B-Instruct-4bit")
    assert info_4bit["quantization"] == "4bit"
    assert info_4bit["precision"] == "int4"
    assert info_4bit["memory_ceiling_gb"] == 6.0
    assert info_4bit["estimated_size_gb"] == 4.5

    # 3. Verify 8-bit model info
    info_8bit = manager.get_model_info("mlx-community/Qwen2.5-VL-7B-Instruct-8bit")
    assert info_8bit["quantization"] == "8bit"
    assert info_8bit["precision"] == "int8"
    assert info_8bit["memory_ceiling_gb"] == 10.0
    assert info_8bit["estimated_size_gb"] == 8.2

    # 4. Verify list_supported_quantized_models
    models = manager.list_supported_quantized_models()
    assert len(models) >= 4
    assert any(m["quantization"] == "4bit" for m in models)
    assert any(m["quantization"] == "8bit" for m in models)


def test_mlx_engine_quantization_configuration():
    manager = ModelManager()
    engine_4bit = MLXEngine(
        model_manager=manager,
        model_id="mlx-community/Qwen2.5-VL-7B-Instruct-4bit",
    )
    assert engine_4bit.quantization == "4bit"
    assert engine_4bit.precision == "int4"
    assert engine_4bit.memory_ceiling_gb == 6.0

    # Test dynamic switch to 8-bit
    engine_4bit.load_model(quantization="8bit")
    assert engine_4bit.quantization == "8bit"
    assert engine_4bit.precision == "int8"
    assert engine_4bit.memory_ceiling_gb == 10.0
    assert "8bit" in engine_4bit.model_id


def test_eval_quantization_benchmark_execution(tmp_path):
    out_json = tmp_path / "test_quant_report.json"
    out_md = tmp_path / "test_quant_report.md"

    report = run_quantization_evaluation(
        dry_run=True,
        samples=50,
        custom_output=out_json,
        markdown_output=out_md,
    )

    assert isinstance(report, QuantizationBenchmarkReport)
    assert len(report.metrics) == 4

    # Verify 4-bit vs 8-bit metrics
    vlm_4bit = next(m for m in report.metrics if m.model_id == "mlx-community/Qwen2.5-VL-7B-Instruct-4bit")
    vlm_8bit = next(m for m in report.metrics if m.model_id == "mlx-community/Qwen2.5-VL-7B-Instruct-8bit")

    assert vlm_4bit.fits_6gb_ceiling is True
    assert vlm_8bit.fits_6gb_ceiling is False
    assert vlm_4bit.peak_memory_gb < 6.0
    assert vlm_8bit.peak_memory_gb > 6.0
    assert vlm_4bit.throughput_tokens_per_sec > vlm_8bit.throughput_tokens_per_sec

    # Verify trade-off calculations
    tradeoffs = report.tradeoff_summary
    assert tradeoffs["vlm_memory_saving_percent"] > 40.0
    assert tradeoffs["vlm_throughput_speedup_percent"] > 45.0
    assert "int4" in report.recommendation.lower()

    # Verify file outputs
    assert out_json.exists()
    assert out_md.exists()

    with open(out_json, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "metrics" in data
    assert len(data["metrics"]) == 4


def test_quantization_markdown_report_zero_emojis(tmp_path):
    out_json = tmp_path / "test_emojis.json"
    out_md = tmp_path / "test_emojis.md"

    report = run_quantization_evaluation(
        dry_run=True,
        custom_output=out_json,
        markdown_output=out_md,
    )

    md_text = out_md.read_text(encoding="utf-8")
    assert "# FinTrace VLM & Retrieval Quantization Trade-off Report" in md_text
    assert "| Model Family | Quantization | Precision |" in md_text
    assert "`[PASS]`" in md_text

    # Strict Rule 15 check: Zero raw emojis allowed in markdown
    for char in md_text:
        code = ord(char)
        is_emoji = (
            (0x1F600 <= code <= 0x1F64F) or
            (0x1F300 <= code <= 0x1F5FF) or
            (0x1F680 <= code <= 0x1F6FF) or
            (0x1F700 <= code <= 0x1F77F) or
            (0x1F780 <= code <= 0x1F7FF) or
            (0x1F900 <= code <= 0x1F9FF) or
            (0x2600 <= code <= 0x26FF) or
            (0x2700 <= code <= 0x27BF)
        )
        assert not is_emoji, f"Raw emoji '{char}' (code {hex(code)}) found in quantization report!"
