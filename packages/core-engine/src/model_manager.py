"""
FinSight Model Weight & Cache Manager
Governed by Issue #10, ADR-002, AGENTS.md Rule 13 (Security & Injection Defense),
and 529 Engineering Standards.
Enforces:
1. Strict user confirmation gate before downloading model weights.
2. Directory traversal prevention on model identifiers and cache paths.
3. Offline mode detection and fallback routing.
"""

import os
import re
import socket
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

# Enforce relative path for .env (529 standard: env-and-auth-ops-debugging)
ENV_PATH = Path(__file__).resolve().parents[3] / ".env"
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)

logger = logging.getLogger("finsight.model_manager")

DEFAULT_MODEL_ID = "mlx-community/Qwen2.5-VL-7B-Instruct-4bit"
DEFAULT_CACHE_DIR = Path("~/.finsight/models").expanduser().resolve()

QUANTIZED_REGISTRY: Dict[str, Dict[str, Any]] = {
    "mlx-community/Qwen2.5-VL-7B-Instruct-4bit": {
        "quantization": "4bit",
        "precision": "int4",
        "estimated_size_gb": 4.5,
        "memory_ceiling_gb": 6.0,
        "family": "vlm",
    },
    "mlx-community/Qwen2.5-VL-7B-Instruct-8bit": {
        "quantization": "8bit",
        "precision": "int8",
        "estimated_size_gb": 8.2,
        "memory_ceiling_gb": 10.0,
        "family": "vlm",
    },
    "mlx-community/ColPali-v1.2-4bit": {
        "quantization": "4bit",
        "precision": "int4",
        "estimated_size_gb": 2.2,
        "memory_ceiling_gb": 4.0,
        "family": "retrieval",
    },
    "mlx-community/ColPali-v1.2-8bit": {
        "quantization": "8bit",
        "precision": "int8",
        "estimated_size_gb": 3.8,
        "memory_ceiling_gb": 6.0,
        "family": "retrieval",
    },
}

try:
    from huggingface_hub import snapshot_download
except ImportError:
    snapshot_download = None


class ModelSecurityError(Exception):
    """Raised when an unsafe path or traversal attempt is detected."""
    pass


class UnconfirmedDownloadError(Exception):
    """Raised when a download attempt is made without explicit user confirmation."""
    pass


class ModelOfflineError(Exception):
    """Raised when model weights are not cached and the system is offline."""
    pass


class ModelManager:
    """
    Manages local Apple Silicon MLX model weights, caching, and download authorization.
    """

    def __init__(self, cache_dir: Optional[Path] = None):
        self.default_model_id = DEFAULT_MODEL_ID
        raw_cache = cache_dir or DEFAULT_CACHE_DIR
        self.cache_dir = Path(raw_cache).expanduser().resolve()
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _sanitize_model_id(self, model_id: str) -> str:
        """Sanitizes model id and rejects directory traversal characters."""
        if not model_id or "\0" in model_id or ".." in model_id:
            raise ModelSecurityError(f"Invalid model identifier: '{model_id}' contains unsafe characters")
        if not re.match(r"^[a-zA-Z0-9_\-\.\/]+$", model_id):
            raise ModelSecurityError(f"Invalid model identifier: '{model_id}' contains invalid format")
        return model_id

    def get_model_dir(self, model_id: Optional[str] = None) -> Path:
        """Returns the isolated local cache directory for a given model."""
        mid = self._sanitize_model_id(model_id or self.default_model_id)
        folder_name = mid.replace("/", "--")
        resolved = (self.cache_dir / folder_name).resolve()

        # Enforce that resolved path resides strictly inside cache_dir
        if resolved != self.cache_dir and self.cache_dir not in resolved.parents:
            raise ModelSecurityError(f"Path traversal detected: {resolved} escapes cache root {self.cache_dir}")
        return resolved

    def is_cached(self, model_id: Optional[str] = None) -> bool:
        """Checks if model weights and config exist in local cache directory."""
        model_dir = self.get_model_dir(model_id)
        if not model_dir.exists() or not model_dir.is_dir():
            return False

        # Consider cached if config.json exists or any weight files are present
        has_config = (model_dir / "config.json").exists()
        has_weights = any(model_dir.glob("*.safetensors")) or any(model_dir.glob("*.npz"))
        return has_config or has_weights

    def get_model_info(self, model_id: Optional[str] = None) -> Dict[str, Any]:
        """Provides metadata, estimated footprint, quantization type, and cache state."""
        mid = model_id or self.default_model_id
        model_dir = self.get_model_dir(mid)
        cached = self.is_cached(mid)

        reg_info = QUANTIZED_REGISTRY.get(mid)
        if reg_info:
            quant = reg_info["quantization"]
            precision = reg_info["precision"]
            family = reg_info["family"]
            size_gb = reg_info["estimated_size_gb"]
            ceiling_gb = reg_info["memory_ceiling_gb"]
        else:
            is_8bit = "8bit" in mid.lower() or "-8b" in mid.lower()
            quant = "8bit" if is_8bit else "4bit"
            precision = "int8" if is_8bit else "int4"
            family = "retrieval" if "colpali" in mid.lower() else "vlm"
            size_gb = 8.2 if is_8bit else 4.5
            ceiling_gb = 10.0 if is_8bit else 6.0

        return {
            "model_id": mid,
            "quantization": quant,
            "precision": precision,
            "family": family,
            "estimated_size_gb": size_gb,
            "memory_ceiling_gb": ceiling_gb,
            "is_cached": cached,
            "cache_dir": str(model_dir),
            "offline_ready": cached,
        }

    def list_supported_quantized_models(self) -> List[Dict[str, Any]]:
        """Returns list of supported models across 4-bit and 8-bit quantizations."""
        models = []
        for mid, info in QUANTIZED_REGISTRY.items():
            entry = dict(info)
            entry["model_id"] = mid
            entry["is_cached"] = self.is_cached(mid)
            models.append(entry)
        return models

    def is_offline(self) -> bool:
        """Detects whether offline mode is active or huggingface.co is unreachable."""
        env_offline = os.getenv("HF_HUB_OFFLINE", "0").strip().strip("\"'").lower()
        if env_offline in ("1", "true", "yes"):
            return True

        # Quick network reachability check (1.0s timeout)
        try:
            socket.create_connection(("huggingface.co", 443), timeout=1.0)
            return False
        except (OSError, socket.timeout):
            return True

    def download_model(self, model_id: Optional[str] = None, confirmed: bool = False) -> Path:
        """
        Downloads model weights into local cache ONLY if confirmed is True.
        Enforces Zero-Download without confirmation policy.
        """
        mid = self._sanitize_model_id(model_id or self.default_model_id)
        target_dir = self.get_model_dir(mid)

        if self.is_cached(mid):
            logger.info("Model '%s' is already cached at %s", mid, target_dir)
            return target_dir

        if not confirmed:
            raise UnconfirmedDownloadError(
                f"Model '{mid}' (~4.5GB) is not cached locally. "
                "Downloading requires explicit user confirmation (confirm=True)."
            )

        if self.is_offline():
            raise ModelOfflineError(
                f"Cannot download model '{mid}': system is offline and weights are not cached."
            )

        if snapshot_download is None:
            raise RuntimeError("huggingface_hub is not installed in the environment")

        logger.info("User confirmed download for '%s'. Downloading into %s...", mid, target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        snapshot_download(
            repo_id=mid,
            local_dir=str(target_dir),
            local_dir_use_symlinks=False,
        )
        return target_dir
