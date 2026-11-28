"""
FinTrace Cryptographic Audit Logger
Structured JSONL audit log emitter with SHA-256 event chaining for tamper-evident compliance.
Governed by Sprint 10 Task S10-03, AGENTS.md Rule 2 (Zero-Leak), Rule 13, and Rule 15.
"""

import os
import json
import time
import hashlib
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Union
from pydantic import BaseModel, Field

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows fallback
    fcntl = None

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

    def __init__(
        self,
        log_dir: Optional[Union[Path, str]] = None,
        shared_backend: Optional[str] = None,
    ):
        raw_dir = os.getenv("FINTRACE_AUDIT_DIR")
        if log_dir is not None:
            self.log_dir = Path(log_dir).expanduser().resolve()
        elif raw_dir:
            self.log_dir = Path(raw_dir).expanduser().resolve()
        else:
            self.log_dir = DEFAULT_AUDIT_DIR

        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / "audit.jsonl"
        self.db_file = self.log_dir / "audit.db"
        self.shared_backend = (
            shared_backend
            or os.getenv("FINTRACE_SHARED_BACKEND", "jsonl")
        ).strip().lower()
        self._lock = threading.Lock()
        self._last_sequence = -1
        self._last_hash = GENESIS_HASH

        if self.shared_backend == "sqlite":
            self._init_sqlite()
        self._initialize_chain_head()

    def _connect_sqlite(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_file), timeout=30.0, isolation_level=None)
        conn.execute("PRAGMA busy_timeout=10000;")
        return conn

    def _init_sqlite(self) -> None:
        for attempt in range(5):
            try:
                with self._connect_sqlite() as conn:
                    conn.execute("PRAGMA journal_mode=WAL;")
                    conn.execute("PRAGMA synchronous=NORMAL;")
                    conn.execute(
                        """
                        CREATE TABLE IF NOT EXISTS audit_events (
                            sequence_id INTEGER PRIMARY KEY,
                            timestamp TEXT NOT NULL,
                            user_id TEXT NOT NULL,
                            role TEXT NOT NULL,
                            action TEXT NOT NULL,
                            document_id TEXT,
                            details_json TEXT NOT NULL,
                            prev_hash TEXT NOT NULL,
                            record_hash TEXT NOT NULL
                        );
                        """
                    )
                    conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_events(action);")
                    conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_doc ON audit_events(document_id);")
                return
            except sqlite3.OperationalError as e:
                if "locked" in str(e).lower() and attempt < 4:
                    time.sleep(0.05 * (attempt + 1))
                    continue
                raise

    def _read_jsonl_tail(self) -> Tuple[int, str]:
        if not self.log_file.exists() or self.log_file.stat().st_size == 0:
            return -1, GENESIS_HASH
        with open(self.log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            for line in reversed(lines):
                clean = line.strip()
                if clean:
                    try:
                        record = json.loads(clean)
                        return int(record["sequence_id"]), str(record["record_hash"])
                    except Exception:
                        continue
        return -1, GENESIS_HASH

    def _initialize_chain_head(self):
        """Reads the tail of existing audit log storage to resume the hash chain."""
        if self.shared_backend == "sqlite":
            with self._connect_sqlite() as conn:
                row = conn.execute(
                    "SELECT sequence_id, record_hash FROM audit_events ORDER BY sequence_id DESC LIMIT 1"
                ).fetchone()
                if row:
                    self._last_sequence = int(row[0])
                    self._last_hash = str(row[1])
                    return
            self._last_sequence = -1
            self._last_hash = GENESIS_HASH
            return

        self._last_sequence, self._last_hash = self._read_jsonl_tail()

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
            now_iso = datetime.now(timezone.utc).isoformat()

            if self.shared_backend == "sqlite":
                conn = self._connect_sqlite()
                try:
                    conn.execute("BEGIN IMMEDIATE;")
                    row = conn.execute(
                        "SELECT sequence_id, record_hash FROM audit_events ORDER BY sequence_id DESC LIMIT 1"
                    ).fetchone()
                    prev_seq = int(row[0]) if row else -1
                    prev_hash = str(row[1]) if row else GENESIS_HASH
                    next_seq = prev_seq + 1
                    payload = {
                        "sequence_id": next_seq,
                        "timestamp": now_iso,
                        "user_id": user_id,
                        "role": role,
                        "action": action,
                        "document_id": document_id,
                        "details": sanitized_details,
                    }
                    rec_hash = compute_record_hash(prev_hash, payload)
                    event = AuditEvent(
                        sequence_id=next_seq,
                        timestamp=now_iso,
                        user_id=user_id,
                        role=role,
                        action=action,
                        document_id=document_id,
                        details=sanitized_details,
                        prev_hash=prev_hash,
                        record_hash=rec_hash,
                    )
                    conn.execute(
                        """
                        INSERT INTO audit_events (
                            sequence_id, timestamp, user_id, role, action,
                            document_id, details_json, prev_hash, record_hash
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            event.sequence_id,
                            event.timestamp,
                            event.user_id,
                            event.role,
                            event.action,
                            event.document_id,
                            json.dumps(event.details, ensure_ascii=False),
                            event.prev_hash,
                            event.record_hash,
                        ),
                    )
                    conn.execute("COMMIT;")
                    self._last_sequence = next_seq
                    self._last_hash = rec_hash
                    return event
                except Exception:
                    conn.execute("ROLLBACK;")
                    raise
                finally:
                    conn.close()

            # Default JSONL mode with cross-process advisory file lock + tail sync
            with open(self.log_file, "a+", encoding="utf-8") as f:
                if fcntl is not None:
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    prev_seq, prev_hash = self._read_jsonl_tail()
                    next_seq = prev_seq + 1
                    payload = {
                        "sequence_id": next_seq,
                        "timestamp": now_iso,
                        "user_id": user_id,
                        "role": role,
                        "action": action,
                        "document_id": document_id,
                        "details": sanitized_details,
                    }
                    rec_hash = compute_record_hash(prev_hash, payload)
                    event = AuditEvent(
                        sequence_id=next_seq,
                        timestamp=now_iso,
                        user_id=user_id,
                        role=role,
                        action=action,
                        document_id=document_id,
                        details=sanitized_details,
                        prev_hash=prev_hash,
                        record_hash=rec_hash,
                    )
                    f.seek(0, os.SEEK_END)
                    f.write(json.dumps(event.model_dump(), ensure_ascii=False) + "\n")
                    f.flush()
                    self._last_sequence = next_seq
                    self._last_hash = rec_hash
                    return event
                finally:
                    if fcntl is not None:
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    def get_events(
        self,
        limit: int = 50,
        offset: int = 0,
        action: Optional[str] = None,
        user_id: Optional[str] = None,
        document_id: Optional[str] = None,
    ) -> Tuple[List[AuditEvent], int]:
        """Retrieves paginated audit events with optional filters."""
        if self.shared_backend == "sqlite":
            clauses = []
            params: List[Any] = []
            if action:
                clauses.append("action = ?")
                params.append(action)
            if user_id:
                clauses.append("user_id = ?")
                params.append(user_id)
            if document_id:
                clauses.append("document_id = ?")
                params.append(document_id)
            where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
            with self._connect_sqlite() as conn:
                total_count = int(
                    conn.execute(f"SELECT COUNT(*) FROM audit_events {where_sql}", params).fetchone()[0]
                )
                rows = conn.execute(
                    f"""
                    SELECT sequence_id, timestamp, user_id, role, action,
                           document_id, details_json, prev_hash, record_hash
                    FROM audit_events {where_sql}
                    ORDER BY sequence_id DESC
                    LIMIT ? OFFSET ?
                    """,
                    [*params, limit, offset],
                ).fetchall()
            events = [
                AuditEvent(
                    sequence_id=r[0],
                    timestamp=r[1],
                    user_id=r[2],
                    role=r[3],
                    action=r[4],
                    document_id=r[5],
                    details=json.loads(r[6]),
                    prev_hash=r[7],
                    record_hash=r[8],
                )
                for r in rows
            ]
            return events, total_count

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
        if self.shared_backend == "sqlite" and custom_path is None:
            with self._connect_sqlite() as conn:
                rows = conn.execute(
                    """
                    SELECT sequence_id, timestamp, user_id, role, action,
                           document_id, details_json, prev_hash, record_hash
                    FROM audit_events ORDER BY sequence_id ASC
                    """
                ).fetchall()
            if not rows:
                return True, 0, None
            expected_prev = GENESIS_HASH
            expected_seq = 0
            for idx, r in enumerate(rows):
                actual_seq, ts, uid, role_val, act, doc_id, details_raw, actual_prev, actual_hash = r
                if actual_seq != expected_seq:
                    return False, idx, f"Sequence break at row {idx+1}: expected sequence {expected_seq}, got {actual_seq}"
                if actual_prev != expected_prev:
                    return False, idx, f"Hash chain broken at row {idx+1}: expected prev_hash {expected_prev}, got {actual_prev}"
                payload = {
                    "sequence_id": actual_seq,
                    "timestamp": ts,
                    "user_id": uid,
                    "role": role_val,
                    "action": act,
                    "document_id": doc_id,
                    "details": json.loads(details_raw),
                }
                recalculated = compute_record_hash(actual_prev, payload)
                if recalculated != actual_hash:
                    return False, idx, f"Tampered record at row {idx+1}: recalculated hash {recalculated} does not match recorded hash {actual_hash}"
                expected_prev = actual_hash
                expected_seq += 1
            return True, expected_seq, None

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
            if self.shared_backend == "sqlite":
                with self._connect_sqlite() as conn:
                    rows = conn.execute(
                        """
                        SELECT sequence_id, timestamp, user_id, role, action,
                               document_id, details_json, prev_hash, record_hash
                        FROM audit_events ORDER BY sequence_id ASC
                        """
                    ).fetchall()
                with open(dest, "w", encoding="utf-8") as out:
                    for r in rows:
                        evt = {
                            "sequence_id": r[0],
                            "timestamp": r[1],
                            "user_id": r[2],
                            "role": r[3],
                            "action": r[4],
                            "document_id": r[5],
                            "details": json.loads(r[6]),
                            "prev_hash": r[7],
                            "record_hash": r[8],
                        }
                        out.write(json.dumps(evt, ensure_ascii=False) + "\n")
                return dest

            if self.log_file.exists():
                with open(self.log_file, "r", encoding="utf-8") as src, open(dest, "w", encoding="utf-8") as out:
                    for line in src:
                        out.write(line)
            else:
                dest.touch()

        return dest


# Global audit logger instance
audit_logger = AuditLogger()
