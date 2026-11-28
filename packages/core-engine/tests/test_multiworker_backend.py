"""
FinSight S14-04 Test Suite: Multi-Worker Shared Audit & Cache Backend
Verifies:
1. AuditLogger in both `sqlite` (WAL + BEGIN IMMEDIATE) and `jsonl` (fcntl.flock) modes
   maintains a 100% unbroken SHA-256 hash chain across 4 concurrent OS worker processes.
2. QueryLRUCache in `sqlite` WAL mode shares cached query responses, LRU evictions,
   hit/miss counters, and document invalidations across separate OS worker processes.
3. Path traversal rejection on shared cache DB paths.
"""

import concurrent.futures
import multiprocessing
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from audit_logger import AuditLogger
from cache_manager import QueryLRUCache


def _worker_log_events(args):
    log_dir_str, backend, worker_id, count = args
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
    from audit_logger import AuditLogger

    logger = AuditLogger(log_dir=Path(log_dir_str), shared_backend=backend)
    for i in range(count):
        logger.log_event(
            user_id=f"worker_{worker_id}",
            role="senior_auditor",
            action="MULTIWORKER_TEST",
            document_id=f"DOC_{worker_id}",
            details={"iter": i, "api_key": "secret_should_be_redacted"},
        )
    return count


def _worker_cache_put(args):
    db_path_str, doc_id, query_text, answer = args
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
    from cache_manager import QueryLRUCache

    cache = QueryLRUCache(max_capacity=16, shared_backend="sqlite", db_path=db_path_str)
    cache.put(doc_id, query_text, 2, "local", {"answer": answer, "evidences": []})
    return True


@pytest.mark.parametrize("backend", ["sqlite", "jsonl"])
def test_audit_logger_multiprocess_hash_chain_integrity(tmp_path, backend):
    """
    Spawns 4 separate OS worker processes writing 15 events each concurrently (60 total)
    and verifies the resulting SHA-256 hash chain is 100% intact with zero sequence collisions.
    """
    audit_dir = tmp_path / f"audit_{backend}"
    audit_dir.mkdir(parents=True, exist_ok=True)

    # Pre-initialize storage before spawning workers
    master = AuditLogger(log_dir=audit_dir, shared_backend=backend)
    assert master.verify_chain() == (True, 0, None)

    ctx = multiprocessing.get_context("spawn")
    tasks = [(str(audit_dir), backend, wid, 15) for wid in range(4)]
    with concurrent.futures.ProcessPoolExecutor(max_workers=4, mp_context=ctx) as pool:
        results = list(pool.map(_worker_log_events, tasks))

    assert sum(results) == 60
    is_valid, total, err = master.verify_chain()
    assert is_valid is True, f"Multi-worker {backend} chain broken: {err}"
    assert total == 60

    events, total_count = master.get_events(limit=100)
    assert total_count == 60
    assert all(e.details["api_key"] == "[REDACTED]" for e in events)

    # Verify export works identically
    export_path = master.export_events(tmp_path / f"export_{backend}.jsonl")
    assert export_path.exists()
    assert len(export_path.read_text(encoding="utf-8").strip().splitlines()) == 60


def test_query_lru_cache_shared_across_workers_and_processes(tmp_path):
    """
    Verifies QueryLRUCache in SQLite WAL mode shares puts, hits, LRU evictions,
    and document invalidations across separate worker instances and OS processes.
    """
    db_path = tmp_path / "shared_cache.db"
    ctx = multiprocessing.get_context("spawn")

    # Worker process 1 populates cache
    with concurrent.futures.ProcessPoolExecutor(max_workers=2, mp_context=ctx) as pool:
        list(pool.map(_worker_cache_put, [
            (str(db_path), "FED_2025_11", "commercial real estate", "CRE risks elevated"),
            (str(db_path), "FED_2025_04", "treasury liquidity", "Liquidity stable"),
        ]))

    # Worker instance 2 (fresh instance in main process) gets immediate cache hit
    worker2 = QueryLRUCache(max_capacity=2, shared_backend="sqlite", db_path=db_path)
    hit = worker2.get("FED_2025_11", "commercial real estate", 2, "local")
    assert hit is not None
    assert hit["answer"] == "CRE risks elevated"

    # Put a 3rd entry -> evicts LRU ("FED_2025_04" since "FED_2025_11" was just touched)
    worker2.put("FED_2024_11", "inflation outlook", 2, "local", {"answer": "Moderating"})
    assert worker2.get("FED_2025_04", "treasury liquidity", 2, "local") is None
    assert worker2.get("FED_2025_11", "commercial real estate", 2, "local") is not None

    # Invalidate from another instance
    worker3 = QueryLRUCache(max_capacity=2, shared_backend="sqlite", db_path=db_path)
    removed = worker3.invalidate_document("FED_2025_11")
    assert removed == 1
    assert worker2.get("FED_2025_11", "commercial real estate", 2, "local") is None

    st = worker3.stats()
    assert st["backend"] == "sqlite_wal"
    assert st["query_cache_hits"] >= 2
    assert st["query_cache_misses"] >= 2

    worker3.clear()
    assert worker2.stats()["in_memory_query_cache_entries"] == 0


def test_query_lru_cache_sqlite_path_traversal_rejected():
    with pytest.raises(ValueError, match="escapes authorized boundaries"):
        QueryLRUCache(shared_backend="sqlite", db_path="/etc/evil_cache.db")
