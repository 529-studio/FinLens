"""
Tests for MLXEngine (packages/core-engine/src/mlx_engine.py)
Governed by Issue #10, ADR-002, and AGENTS.md Rule 13 (Security & Injection Defense).
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from mlx_engine import (
    MLXEngine,
    MemoryCeilingExceededError,
    MEMORY_CEILING_GB,
)
from model_manager import ModelManager


@pytest.fixture
def mock_model_manager(tmp_path):
    mgr = ModelManager(cache_dir=tmp_path / "models")
    return mgr


def test_mlx_engine_init(mock_model_manager):
    engine = MLXEngine(model_manager=mock_model_manager)
    assert engine.model_id == "mlx-community/Qwen2.5-VL-7B-Instruct-4bit"
    assert engine.memory_ceiling_gb == MEMORY_CEILING_GB
    assert engine.is_loaded is False


def test_mlx_engine_memory_usage_structure(mock_model_manager):
    engine = MLXEngine(model_manager=mock_model_manager)
    mem = engine.get_memory_usage()

    assert "metal_active_bytes" in mem
    assert "process_rss_bytes" in mem
    assert "total_used_gb" in mem
    assert "is_under_ceiling" in mem
    assert mem["ceiling_gb"] == 6.0
    # On test environment, initial memory should be below 6GB
    assert mem["is_under_ceiling"] is True


def test_memory_ceiling_enforcement(mock_model_manager):
    engine = MLXEngine(model_manager=mock_model_manager)

    # Simulate memory spike exceeding 6.0GB (e.g. 6.5GB)
    with patch.object(engine, "get_memory_usage", return_value={
        "metal_active_bytes": 5 * 1024**3,
        "metal_peak_bytes": 5 * 1024**3,
        "process_rss_bytes": 2 * 1024**3,
        "total_used_bytes": 7 * 1024**3,
        "total_used_gb": 7.0,
        "ceiling_gb": 6.0,
        "is_under_ceiling": False,
    }):
        with pytest.raises(MemoryCeilingExceededError, match="Memory ceiling exceeded"):
            engine.check_memory_ceiling()


def test_path_traversal_rejected_in_analyze(mock_model_manager):
    engine = MLXEngine(model_manager=mock_model_manager)
    with pytest.raises(ValueError, match="Access denied"):
        engine.analyze_page(
            image_path="../../../etc/shadow",
            page_number=1,
            query="What is the net profit?",
        )


def test_parse_vlm_output_with_json_boxes(mock_model_manager):
    engine = MLXEngine(model_manager=mock_model_manager)
    raw_vlm = """
    Theo báo cáo tài chính, doanh thu nội địa đạt 50.617 tỷ VNĐ.
    ```json
    [
      {
        "ymin": 308,
        "xmin": 84,
        "ymax": 617,
        "xmax": 915,
        "label": "Biểu đồ 1: Cơ cấu doanh thu",
        "extracted_value": "50.617 tỷ (83.7%)",
        "confidence": 0.98
      }
    ]
    ```
    """
    answer, evidences = engine.parse_vlm_output(raw_vlm, page_number=1)
    assert "doanh thu nội địa" in answer.lower()
    assert len(evidences) == 1
    assert evidences[0]["ymin"] == 308
    assert evidences[0]["xmin"] == 84
    assert evidences[0]["ymax"] == 617
    assert evidences[0]["xmax"] == 915
    assert evidences[0]["page_number"] == 1


def test_parse_vlm_output_coordinate_clamping(mock_model_manager):
    engine = MLXEngine(model_manager=mock_model_manager)
    # ymin negative, ymax > 1000
    raw_vlm = """
    ```json
    [
      {
        "ymin": -50,
        "xmin": -20,
        "ymax": 1200,
        "xmax": 1100,
        "label": "Test Box",
        "extracted_value": "Clamped",
        "confidence": 0.95
      }
    ]
    ```
    """
    _, evidences = engine.parse_vlm_output(raw_vlm, page_number=2)
    assert len(evidences) == 1
    assert evidences[0]["ymin"] >= 0
    assert evidences[0]["xmin"] >= 0
    assert evidences[0]["ymax"] <= 1000
    assert evidences[0]["xmax"] <= 1000
    assert evidences[0]["ymax"] > evidences[0]["ymin"]
    assert evidences[0]["xmax"] > evidences[0]["xmin"]


def test_analyze_page_fallback_when_model_not_loaded(mock_model_manager):
    engine = MLXEngine(model_manager=mock_model_manager)
    # Create safe dummy image in allowed tmp dir
    safe_dir = Path("/tmp/finsight_test")
    safe_dir.mkdir(parents=True, exist_ok=True)
    dummy_img = safe_dir / "test_page_1.png"
    dummy_img.write_text("fake image content")

    res = engine.analyze_page(
        image_path=str(dummy_img),
        page_number=1,
        query="Biểu đồ doanh thu năm 2023",
    )

    assert res["engine"] == "mlx-qwen2.5-vl-7b-4bit"
    assert "answer" in res
    assert len(res["evidences"]) >= 1
    assert "memory_usage" in res
    assert res["memory_usage"]["is_under_ceiling"] is True


@patch("mlx_engine.mlx_vlm")
def test_analyze_page_live_generation(mock_vlm, mock_model_manager):
    engine = MLXEngine(model_manager=mock_model_manager)
    engine._model = MagicMock()
    engine._processor = MagicMock()

    mock_vlm.generate.return_value = """
    Lợi nhuận gộp đạt 40.7%.
    ```json
    [{"ymin": 200, "xmin": 100, "ymax": 500, "xmax": 800, "label": "Lợi nhuận gộp", "confidence": 0.99}]
    ```
    """

    safe_dir = Path("/tmp/finsight_test")
    safe_dir.mkdir(parents=True, exist_ok=True)
    dummy_img = safe_dir / "test_page_live.png"
    dummy_img.write_text("fake image content")

    res = engine.analyze_page(
        image_path=str(dummy_img),
        page_number=1,
        query="Biên lợi nhuận gộp",
    )

    assert "Lợi nhuận gộp đạt 40.7%" in res["answer"]
    assert len(res["evidences"]) == 1
    assert res["evidences"][0]["ymin"] == 200
    mock_vlm.generate.assert_called_once()
