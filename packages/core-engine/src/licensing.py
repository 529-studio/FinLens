"""
FinTrace Offline Air-Gapped License Activation & Hardware Fingerprinting Engine
Governed by Sprint 11 Task S11-04, AGENTS.md Rule 1, Rule 2 (Zero-Leak), Rule 13, and Rule 15.
Provides one-way hardware fingerprinting, Ed25519 digital signature verification,
atomic license file persistence, and graceful fallback to Community Evaluation.
"""

import os
import sys
import time
import json
import uuid
import base64
import hashlib
import platform
import subprocess
import threading
import tempfile
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.exceptions import InvalidSignature

from contracts import (
    LicenseTier,
    LicenseState,
    LicensePayload,
    LicenseFileDTO,
    LicenseStatusResponse,
)

logger = logging.getLogger("fintrace.licensing")

# Default embedded vendor Ed25519 public key (32 bytes raw)
DEFAULT_VENDOR_PUBKEY_HEX = "5b32db35c3be491b24b8024b7b51fdb914b06b6115753912702956e419473df4"
FINGERPRINT_SALT = "fintrace_enterprise_banking_hardware_salt_2026_xyz"


def get_machine_fingerprint() -> str:
    """
    Computes a deterministic, one-way SHA-256 machine hardware fingerprint.
    Zero-Leak (Rule 2): Raw hardware serials and MAC addresses are salted and
    hashed irreversibly, never exposed in cleartext.
    """
    identifiers = []

    # 1. Primary MAC address node
    try:
        raw_node = str(uuid.getnode())
        identifiers.append(raw_node)
    except Exception:
        identifiers.append("unknown_node")

    # 2. Operating System & Architecture
    identifiers.append(platform.system())
    identifiers.append(platform.machine())

    # 3. System Hardware UUID (OS-specific)
    os_name = platform.system().lower()
    machine_guid = ""
    try:
        if os_name == "darwin":
            # macOS IOPlatformUUID
            out = subprocess.check_output(
                ["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"],
                stderr=subprocess.DEVNULL,
                timeout=2,
            ).decode("utf-8", errors="ignore")
            for line in out.splitlines():
                if "IOPlatformUUID" in line:
                    machine_guid = line.split("=")[-1].strip().strip('"')
                    break
        elif os_name == "linux":
            # Linux /etc/machine-id
            for p in ["/etc/machine-id", "/var/lib/dbus/machine-id"]:
                if os.path.exists(p):
                    with open(p, "r", encoding="utf-8") as f:
                        machine_guid = f.read().strip()
                        break
        elif os_name == "windows":
            # Windows MachineGuid
            out = subprocess.check_output(
                ["reg", "query", "HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Cryptography", "/v", "MachineGuid"],
                stderr=subprocess.DEVNULL,
                timeout=2,
            ).decode("utf-8", errors="ignore")
            for line in out.splitlines():
                if "MachineGuid" in line:
                    machine_guid = line.split()[-1].strip()
                    break
    except Exception:
        pass

    if machine_guid:
        identifiers.append(machine_guid)
    else:
        # Fallback to python sys node name
        identifiers.append(platform.node())

    raw_combined = f"{FINGERPRINT_SALT}::" + "::".join(identifiers)
    return hashlib.sha256(raw_combined.encode("utf-8")).hexdigest()


def canonicalize_payload(payload: LicensePayload) -> bytes:
    """Produces deterministic canonical JSON byte representation for Ed25519 signing/verification."""
    data = payload.model_dump()
    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")


def generate_test_license(
    private_key: ed25519.Ed25519PrivateKey,
    payload: LicensePayload,
) -> LicenseFileDTO:
    """Helper utility for generating signed license packages (used in test suites and vendor tool)."""
    canonical_bytes = canonicalize_payload(payload)
    sig_bytes = private_key.sign(canonical_bytes)
    sig_b64 = base64.urlsafe_b64encode(sig_bytes).decode("ascii").rstrip("=")
    return LicenseFileDTO(payload=payload, signature=sig_b64)


class LicenseManager:
    """
    Manages air-gapped cryptographic license activation, validation, and storage.
    Enforces thread-safe in-memory caching and atomic file writes.
    """

    def __init__(
        self,
        license_path: Optional[Path] = None,
        public_key_bytes: Optional[bytes] = None,
    ):
        if license_path:
            self.license_path = license_path
        else:
            env_path = os.getenv("FINTRACE_LICENSE_FILE")
            if env_path:
                self.license_path = Path(env_path).expanduser().resolve()
            else:
                self.license_path = Path("~/.finsight/license.json").expanduser().resolve()

        if public_key_bytes:
            self.public_key_bytes = public_key_bytes
        else:
            hex_str = os.getenv("FINTRACE_LICENSE_PUBKEY_HEX", DEFAULT_VENDOR_PUBKEY_HEX)
            self.public_key_bytes = bytes.fromhex(hex_str)

        self._lock = threading.Lock()
        self._cached_license: Optional[LicenseFileDTO] = None
        self._machine_fingerprint = get_machine_fingerprint()

        self._load_from_disk()

    @property
    def machine_fingerprint(self) -> str:
        return self._machine_fingerprint

    def _load_from_disk(self) -> None:
        """Loads and caches existing license file from disk if present."""
        if not self.license_path.exists():
            return

        try:
            with open(self.license_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
            self._cached_license = LicenseFileDTO.model_validate(raw_data)
            logger.info("Loaded license file for customer '%s' from %s", self._cached_license.payload.customer_id, self.license_path)
        except Exception as e:
            logger.warning("Failed to parse license file at %s: %s", self.license_path, e)
            self._cached_license = None

    def verify_signature(self, license_file: LicenseFileDTO) -> bool:
        """Cryptographically verifies Ed25519 signature of license payload."""
        try:
            pubkey = ed25519.Ed25519PublicKey.from_public_bytes(self.public_key_bytes)
            canonical_bytes = canonicalize_payload(license_file.payload)

            sig_b64 = license_file.signature
            padding = 4 - (len(sig_b64) % 4)
            if padding and padding != 4:
                sig_b64 += "=" * padding
            sig_bytes = base64.urlsafe_b64decode(sig_b64)

            pubkey.verify(sig_bytes, canonical_bytes)
            return True
        except (InvalidSignature, Exception) as e:
            logger.warning("Ed25519 license signature verification failed: %s", e)
            return False

    def evaluate_license(
        self,
        license_file: Optional[LicenseFileDTO],
        current_time: Optional[float] = None,
    ) -> LicenseStatusResponse:
        """Evaluates license validity, state, remaining days, and active features."""
        now = current_time if current_time is not None else time.time()

        if license_file is None:
            return LicenseStatusResponse(
                state=LicenseState.COMMUNITY_EVALUATION,
                is_valid=True,
                tier=LicenseTier.COMMUNITY,
                customer_id=None,
                customer_name="Community User",
                machine_fingerprint=self._machine_fingerprint,
                days_remaining=None,
                max_users=1,
                features=["visual_rag", "ratio_engine"],
                expires_at=None,
            )

        # 1. Cryptographic Signature Check
        if not self.verify_signature(license_file):
            return LicenseStatusResponse(
                state=LicenseState.INVALID_SIGNATURE,
                is_valid=False,
                tier=license_file.payload.tier,
                customer_id=license_file.payload.customer_id,
                customer_name=license_file.payload.customer_name,
                machine_fingerprint=self._machine_fingerprint,
                days_remaining=None,
                max_users=license_file.payload.max_users,
                features=[],
                expires_at=license_file.payload.expires_at,
            )

        payload = license_file.payload

        # 2. Expiration Check
        if now > payload.expires_at:
            return LicenseStatusResponse(
                state=LicenseState.EXPIRED,
                is_valid=False,
                tier=payload.tier,
                customer_id=payload.customer_id,
                customer_name=payload.customer_name,
                machine_fingerprint=self._machine_fingerprint,
                days_remaining=0,
                max_users=payload.max_users,
                features=[],
                expires_at=payload.expires_at,
            )

        # 3. Hardware Fingerprint Check
        if payload.machine_fingerprint != "*" and payload.machine_fingerprint != self._machine_fingerprint:
            return LicenseStatusResponse(
                state=LicenseState.FINGERPRINT_MISMATCH,
                is_valid=False,
                tier=payload.tier,
                customer_id=payload.customer_id,
                customer_name=payload.customer_name,
                machine_fingerprint=self._machine_fingerprint,
                days_remaining=max(0, int((payload.expires_at - now) / 86400)),
                max_users=payload.max_users,
                features=[],
                expires_at=payload.expires_at,
            )

        # 4. Valid Active License
        days_left = max(0, int((payload.expires_at - now) / 86400))
        return LicenseStatusResponse(
            state=LicenseState.ACTIVE,
            is_valid=True,
            tier=payload.tier,
            customer_id=payload.customer_id,
            customer_name=payload.customer_name,
            machine_fingerprint=self._machine_fingerprint,
            days_remaining=days_left,
            max_users=payload.max_users,
            features=payload.features,
            expires_at=payload.expires_at,
        )

    def get_status(self) -> LicenseStatusResponse:
        """Returns the current evaluated status of the active license."""
        with self._lock:
            return self.evaluate_license(self._cached_license)

    def activate(self, raw_input: Any) -> Tuple[bool, str, LicenseStatusResponse]:
        """
        Activates and persists a new air-gapped license key.
        Accepts raw JSON string, base64-encoded string, or dictionary.
        Enforces atomic disk writes and 0o600 Unix file permissions.
        """
        with self._lock:
            try:
                if isinstance(raw_input, str):
                    clean_str = raw_input.strip()
                    if clean_str.startswith("{"):
                        data = json.loads(clean_str)
                    else:
                        # Try base64 decoding
                        decoded = base64.b64decode(clean_str).decode("utf-8")
                        data = json.loads(decoded)
                elif isinstance(raw_input, dict):
                    data = raw_input
                else:
                    raise ValueError("License data must be a JSON string, base64 string, or dictionary")

                license_dto = LicenseFileDTO.model_validate(data)
            except Exception as e:
                status_resp = self.evaluate_license(self._cached_license)
                return False, f"Invalid license format: {str(e)}", status_resp

            status_resp = self.evaluate_license(license_dto)

            if status_resp.state != LicenseState.ACTIVE:
                reason_map = {
                    LicenseState.INVALID_SIGNATURE: "Cryptographic digital signature verification failed",
                    LicenseState.EXPIRED: f"License has expired on {time.strftime('%Y-%m-%d', time.gmtime(license_dto.payload.expires_at))}",
                    LicenseState.FINGERPRINT_MISMATCH: f"Machine fingerprint mismatch: license bound to '{license_dto.payload.machine_fingerprint}', host is '{self._machine_fingerprint}'",
                }
                err_msg = reason_map.get(status_resp.state, f"Activation rejected: {status_resp.state.value}")
                return False, err_msg, status_resp

            # Atomic write to disk
            self.license_path.parent.mkdir(parents=True, exist_ok=True)
            temp_fd, temp_path = tempfile.mkstemp(dir=str(self.license_path.parent), prefix="license_tmp_")
            try:
                with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
                    json.dump(license_dto.model_dump(), f, indent=2)
                # Restrict permissions to owner read/write only (0o600)
                os.chmod(temp_path, 0o600)
                os.replace(temp_path, str(self.license_path))
            except Exception as e:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                return False, f"Failed to persist license file: {str(e)}", status_resp

            self._cached_license = license_dto
            logger.info("Successfully activated enterprise license for customer '%s'", license_dto.payload.customer_id)
            return True, f"License successfully activated for '{license_dto.payload.customer_name}' ({license_dto.payload.tier.value.upper()})", status_resp
