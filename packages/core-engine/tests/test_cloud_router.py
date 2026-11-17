"""
Tests for Cloud BYOK Router (packages/core-engine/src/cloud_router.py)
Governed by PRD §3, ADR-002, and AGENTS.md Rule 2 (Zero-Leak) & Rule 13 (Security).
"""

import asyncio
import pytest
from pathlib import Path
from unittest.mock import patch, AsyncMock

from cloud_router import CloudRouter, CloudRouterSecurityError


@pytest.fixture
def clean_cloud_router(monkeypatch):
    # Clear any ambient env keys
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("AZURE_API_KEY", raising=False)
    monkeypatch.delenv("AZURE_API_BASE", raising=False)
    return CloudRouter()


def test_cloud_router_init_empty(clean_cloud_router):
    router = clean_cloud_router
    assert router.get_available_providers() == []


def test_cloud_router_init_with_keys(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "  sk-ant-test-key-12345  ")
    monkeypatch.setenv("OPENAI_API_KEY", "\"sk-openai-test-key-67890\"")
    router = CloudRouter()

    providers = router.get_available_providers()
    assert "anthropic" in providers
    assert "openai" in providers

    # Verify keys are cleanly stripped of quotes and spaces
    assert router.anthropic_key == "sk-ant-test-key-12345"
    assert router.openai_key == "sk-openai-test-key-67890"


def test_zero_leak_status_does_not_expose_keys(monkeypatch):
    secret_key = "sk-super-secret-production-key-never-leak"
    monkeypatch.setenv("ANTHROPIC_API_KEY", secret_key)
    router = CloudRouter()

    status = router.get_provider_status()
    assert status["anthropic"]["configured"] is True
    # Ensure neither full key nor secret fragments leak into status
    assert secret_key not in str(status)
    assert "super-secret" not in str(status)


def test_path_traversal_image_path_rejected(clean_cloud_router):
    router = clean_cloud_router
    with pytest.raises(ValueError, match="Access denied"):
        router._encode_image_base64("../../../etc/shadow")


def test_parse_vlm_output_json_and_clamping(clean_cloud_router):
    router = clean_cloud_router
    raw_response = """
    Phân tích BCTC Vinamilk:
    ```json
    [
      {
        "ymin": -10,
        "xmin": 50,
        "ymax": 1200,
        "xmax": 900,
        "label": "Biểu đồ doanh thu 2023",
        "extracted_value": "50.617 tỷ",
        "confidence": 0.98
      }
    ]
    ```
    """
    answer, evidences = router.parse_vlm_output(raw_response, page_number=1)
    assert "Phân tích BCTC" in answer
    assert len(evidences) == 1
    ev = evidences[0]
    assert ev["ymin"] == 0  # clamped from -10
    assert ev["ymax"] == 1000  # clamped from 1200
    assert ev["xmin"] == 50
    assert ev["xmax"] == 900
    assert ev["ymax"] > ev["ymin"]
    assert ev["xmax"] > ev["xmin"]


def test_analyze_page_offline_fallback_when_no_keys(clean_cloud_router):
    router = clean_cloud_router
    # Create safe dummy image
    safe_dir = Path("/tmp/finsight_test")
    safe_dir.mkdir(parents=True, exist_ok=True)
    img_path = safe_dir / "cloud_test_p1.png"
    img_path.write_text("fake image")

    res = asyncio.run(router.analyze_page(
        image_path=str(img_path),
        page_number=1,
        query="Biểu đồ cơ cấu doanh thu",
        provider="anthropic",
    ))
    assert res["engine"] == "anthropic-claude-3-5-sonnet-20241022-cloud"
    assert "answer" in res
    assert len(res["evidences"]) >= 1
    assert res["evidences"][0]["page_number"] == 1


@patch("cloud_router.litellm.acompletion")
def test_analyze_page_mocked_litellm_completion(mock_acompletion, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-valid-key")
    router = CloudRouter()

    # Mock litellm completion response
    mock_resp = AsyncMock()
    mock_choice = AsyncMock()
    mock_choice.message.content = """
    Doanh thu nội địa đạt 50.617 tỷ (83.7%).
    ```json
    [{"ymin": 300, "xmin": 80, "ymax": 600, "xmax": 900, "label": "Biểu đồ 1", "confidence": 0.99}]
    ```
    """
    mock_resp.choices = [mock_choice]
    mock_resp.model = "claude-3-5-sonnet-20241022"
    mock_acompletion.return_value = mock_resp

    safe_dir = Path("/tmp/finsight_test")
    safe_dir.mkdir(parents=True, exist_ok=True)
    img_path = safe_dir / "cloud_live_p1.png"
    img_path.write_text("dummy")

    res = asyncio.run(router.analyze_page(
        image_path=str(img_path),
        page_number=1,
        query="Doanh thu nội địa",
        provider="anthropic",
    ))

    assert "Doanh thu nội địa đạt 50.617 tỷ" in res["answer"]
    assert len(res["evidences"]) == 1
    assert res["evidences"][0]["ymin"] == 300
    mock_acompletion.assert_called_once()

