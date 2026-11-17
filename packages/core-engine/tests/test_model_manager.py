"""
Tests for ModelManager (packages/core-engine/src/model_manager.py)
Governed by Issue #10, ADR-002, and AGENTS.md Rule 13 (Security & Injection Defense).
"""

import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from model_manager import (
    ModelManager,
    DEFAULT_MODEL_ID,
    UnconfirmedDownloadError,
    ModelSecurityError,
)


@pytest.fixture
def temp_cache_dir(tmp_path):
    cache = tmp_path / "models"
    cache.mkdir(parents=True, exist_ok=True)
    return cache


def test_model_manager_init(temp_cache_dir):
    mgr = ModelManager(cache_dir=temp_cache_dir)
    assert mgr.default_model_id == DEFAULT_MODEL_ID
    assert mgr.cache_dir == temp_cache_dir


def test_get_model_dir_safe(temp_cache_dir):
    mgr = ModelManager(cache_dir=temp_cache_dir)
    safe_dir = mgr.get_model_dir("mlx-community/Qwen2.5-VL-7B-Instruct-4bit")
    assert safe_dir.parent == temp_cache_dir
    assert "Qwen2.5-VL-7B-Instruct-4bit" in safe_dir.name


def test_get_model_dir_path_traversal_rejection(temp_cache_dir):
    mgr = ModelManager(cache_dir=temp_cache_dir)
    with pytest.raises(ModelSecurityError):
        mgr.get_model_dir("../../../etc/passwd")


def test_is_cached_empty_dir(temp_cache_dir):
    mgr = ModelManager(cache_dir=temp_cache_dir)
    assert mgr.is_cached(DEFAULT_MODEL_ID) is False


def test_is_cached_with_model_files(temp_cache_dir):
    mgr = ModelManager(cache_dir=temp_cache_dir)
    model_dir = mgr.get_model_dir(DEFAULT_MODEL_ID)
    model_dir.mkdir(parents=True, exist_ok=True)
    (model_dir / "config.json").write_text('{"model_type": "qwen2_5_vl"}')

    assert mgr.is_cached(DEFAULT_MODEL_ID) is True


def test_get_model_info(temp_cache_dir):
    mgr = ModelManager(cache_dir=temp_cache_dir)
    info = mgr.get_model_info(DEFAULT_MODEL_ID)
    assert info["model_id"] == DEFAULT_MODEL_ID
    assert info["quantization"] == "4bit"
    assert info["estimated_size_gb"] == 4.5
    assert info["is_cached"] is False
    assert "cache_dir" in info


def test_download_model_requires_explicit_confirmation(temp_cache_dir):
    mgr = ModelManager(cache_dir=temp_cache_dir)
    # When confirmed=False (default), must raise UnconfirmedDownloadError
    with pytest.raises(UnconfirmedDownloadError, match="explicit user confirmation"):
        mgr.download_model(DEFAULT_MODEL_ID, confirmed=False)


def test_download_model_when_already_cached(temp_cache_dir):
    mgr = ModelManager(cache_dir=temp_cache_dir)
    model_dir = mgr.get_model_dir(DEFAULT_MODEL_ID)
    model_dir.mkdir(parents=True, exist_ok=True)
    (model_dir / "config.json").write_text("{}")

    # Even with confirmed=False, if already cached, return directory immediately
    result = mgr.download_model(DEFAULT_MODEL_ID, confirmed=False)
    assert result == model_dir


@patch("model_manager.snapshot_download")
def test_download_model_confirmed_executes_download(mock_download, temp_cache_dir):
    mgr = ModelManager(cache_dir=temp_cache_dir)
    target_dir = mgr.get_model_dir(DEFAULT_MODEL_ID)
    mock_download.return_value = str(target_dir)

    result = mgr.download_model(DEFAULT_MODEL_ID, confirmed=True)
    assert result == target_dir
    mock_download.assert_called_once()


def test_is_offline_detection():
    mgr = ModelManager()
    with patch.dict(os.environ, {"HF_HUB_OFFLINE": "1"}):
        assert mgr.is_offline() is True
