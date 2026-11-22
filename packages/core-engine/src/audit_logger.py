"""
FinTrace Cryptographic Audit Logger
Structured JSONL audit log emitter with SHA-256 event chaining for tamper-evident compliance.
Governed by Sprint 10 Task S10-03, AGENTS.md Rule 2 (Zero-Leak), Rule 13, and Rule 15.
"""

import os
import json
import time
import hashlib
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field

DEFAULT_AUDIT_DIR = Path("~/.fintrace/audit").expanduser()
GENESIS_HASH = "0" * 64


class AuditEvent(BaseModel):
    """Immutable audit record cryptographically linked into the SHA-256 hash chain."""
    sequence_id: int = Field(..., ge=0, description="Monotonically increasing sequence number")
    timestamp: str = Field(..., description="ISO 8601 UTC timestamp")
    user_id: str = Field(..., description="ID of the user performing the action")
    role: str = Field(..., description="Role of the user at the time of the action")
    action: str = Field(..., description="Audited business action (e.g. DOC_QUERY, DOC_INGEST)")
    document_id: Optional[str] = Field(None, description="Target document identifier if applicable")
    details: Dict[str, Any] = Field(default_factory=dict, description="Contextual execution metadata")
    prev_hash: str = Field(..., description="SHA-256 digest of previous record")
    record_hash: str = Field(..., description="Cryptographic SHA-256 signature of this record")


def compute_record_hash(prev_hash: str, payload_dict: Dict[str, Any]) -> str:
    """
    Computes deterministic SHA-256 hash chaining previous hash and canonical JSON payload.
    Ensures zero tampering: any bit change in historical records invalidates entire chain.
    """
    canonical_json = json.dumps(payload_dict, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    hasher = hashlib.sha256()
    hasher.update(prev_hash.encode("utf-8"))
    hasher.update(canonical_json.encode("utf-8"))
    return hasher.hexdigest()


class AuditLogger:
    """
    Thread-safe, tamper-evident audit log manager for banking compliance.
    Maintains a continuous append-only cryptographic SHA-256 event chain.
    """

    def __init__(self, log_dir: Optional[Path] = None):
        raw_dir = os.getenv("FINTRACE_AUDIT_DIR")
        if log_dir is not None:
            self.log_dir = log_dir
        elif raw_dir:
            self.log_dir = Path(raw_dir).expanduser().resolve()
        else:
            self.log_dir = DEFAULT_AUDIT_DIR

        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / "audit.jsonl"
        self._lock = threading.Lock()
        self._last_sequence = -1
        self._last_hash = GENESIS_HASH

        self._initialize_chain_head()

    def _initialize_chain_head(self):
        """Reads the tail of existing audit log file to resume the hash chain."""
        if not self.log_file.exists() or self.log_file.stat().st_size == 0:
            self._last_sequence = -1
            self._last_hash = GENESIS_HASH
            return

        with open(self.log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            for line in reversed(lines):
                clean = line.strip()
                if clean:
                    try:
                        record = json.loads(clean)
                        self._last_sequence = int(record["sequence_id"])
                        self._last_hash = str(record["record_hash"])
                        return
                    except Exception:
                        continue

        self._last_sequence = -1
        self._last_hash = GENESIS_HASH

    def log_event(
        self,
        user_id: str,
        role: str,
        action: str,
        document_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        """
        Appends a new cryptographically chained audit event to the log file.
        Thread-safe under high concurrent query loads.
        """
        clean_details = details or {}
        # Zero-leak sanitization: never record raw API keys or passwords in audit logs
        sanitized_details = {
            k: ("[REDACTED]" if any(sec in k.lower() for sec in ["key", "secret", "password", "token"]) else v)
            for k, v in clean_details.items()
        }

        with self._lock:
            next_seq = self._last_sequence + 1
            now_iso = datetime.now(timezone.utc).isoformat()

            payload = {
                "sequence_id": next_seq,
                "timestamp": now_iso,
                "user_id": user_id,
                "role": role,
                "action": action,
                "document_id": document_id,
                "details": sanitized_details,
            }

            rec_hash = compute_record_hash(self._last_hash, payload)

            event = AuditEvent(
                sequence_id=next_seq,
                timestamp=now_iso,
                user_id=user_id,
                role=role,
                action=action,
                document_id=document_id,
                details=sanitized_details,
                prev_hash=self._last_hash,
                record_hash=rec_hash,
            )

            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(event.model_dump(), ensure_ascii=False) + "\n")

            self._last_sequence = next_seq
            self._last_hash = rec_hash

            return event

    def get_events(
        self,
        limit: int = 50,
        offset: int = 0,
        action: Optional[str] = None,
        user_id: Optional[str] = None,
        document_id: Optional[str] = None,
    ) -> Tuple[List[AuditEvent], int]:
        """Retrieves paginated audit events with optional filters."""
        if not self.log_file.exists():
            return [], 0

        matching_events: List[AuditEvent] = []
        with open(self.log_file, "r", encoding="utf-8") as f:
            for line in f:
                clean = line.strip()
                if not clean:
                    continue
                try:
                    data = json.loads(clean)
                    if action and data.get("action") != action:
                        continue
                    if user_id and data.get("user_id") != user_id:
                        continue
                    if document_id and data.get("document_id") != document_id:
                        continue
                    matching_events.append(AuditEvent(**data))
                except Exception:
                    continue

        total_count = len(matching_events)
        # Reverse to show newest first
        matching_events.reverse()
        paginated = matching_events[offset : offset + limit]
        return paginated, total_count

    def verify_chain(self, custom_path: Optional[Path] = None) -> Tuple[bool, int, Optional[str]]:
        """
        Validates the entire cryptographic SHA-256 event chain from Genesis.
        Returns:
            (is_valid: bool, total_records: int, error_message: Optional[str])
        """
        target = custom_path or self.log_file
        if not target.exists() or target.stat().st_size == 0:
            return True, 0, None

        expected_prev = GENESIS_HASH
        expected_seq = 0

        with open(target, "r", encoding="utf-8") as f:
            for line_idx, line in enumerate(f):
                clean = line.strip()
                if not clean:
                    continue
                try:
                    record = json.loads(clean)
                except Exception as e:
                    return False, line_idx, f"Line {line_idx+1}: Corrupt JSON format ({str(e)})"

                actual_seq = record.get("sequence_id")
                actual_prev = record.get("prev_hash")
                actual_hash = record.get("record_hash")

                if actual_seq != expected_seq:
                    return False, line_idx, (
                        f"Sequence break at line {line_idx+1}: expected sequence {expected_seq}, "
                        f"got {actual_seq}"
                    )

                if actual_prev != expected_prev:
                    return False, line_idx, (
                        f"Hash chain broken at line {line_idx+1}: expected prev_hash {expected_prev}, "
                        f"got {actual_prev}"
                    )

                payload = {
                    "sequence_id": record.get("sequence_id"),
                    "timestamp": record.get("timestamp"),
                    "user_id": record.get("user_id"),
                    "role": record.get("role"),
                    "action": record.get("action"),
                    "document_id": record.get("document_id"),
                    "details": record.get("details", {}),
                }

                recalculated = compute_record_hash(actual_prev, payload)
                if recalculated != actual_hash:
                    return False, line_idx, (
                        f"Tampered record at line {line_idx+1}: recalculated hash {recalculated} "
                        f"does not match recorded hash {actual_hash}"
                    )

                expected_prev = actual_hash
                expected_seq += 1

        return True, expected_seq, None

    def export_events(self, destination_path: Optional[Path] = None) -> Path:
        """Exports audit logs to target destination for regulatory banking compliance."""
        dest = destination_path or (self.log_dir / f"audit_export_{int(time.time())}.jsonl")
        dest.parent.mkdir(parents=True, exist_ok=True)

        # Ensure lock during export to prevent partial write
        with self._lock:
            if self.log_file.exists():
                with open(self.log_file, "r", encoding="utf-8") as src, open(dest, "w", encoding="utf-8") as out:
                    for line in src:
                        out.write(line)
            else:
                dest.touch()

        return dest


# Global audit logger instance
audit_logger = AuditLogger()
