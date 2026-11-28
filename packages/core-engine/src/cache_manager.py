"""
FinSight Cache Manager & Performance Optimization Engine
Governed by ADR-001, Sprint 6 Issue #36, and 529 Engineering Standards.

Provides:
1. Thread-safe in-memory LRU Query Cache for sub-millisecond retrieval of repeated/navigational queries.
2. In-memory document metadata caching for LanceDB store queries.
3. Disk-based render cache statistics and invalidation.
"""

import os
import re
import json
import time
import shutil
import sqlite3
import logging
import threading
from pathlib import Path
from collections import OrderedDict
from typing import Dict, Any, Optional, List, Tuple, Union

from contracts import is_path_safe

logger = logging.getLogger("finsight.cache")

DEFAULT_CACHE_DB_PATH = Path(os.getenv("FINTRACE_CACHE_DB_PATH", "~/.finsight/cache/query_cache.db")).expanduser().resolve()


def _json_default(obj: Any) -> Any:
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


class QueryLRUCache:
    """
    Thread-safe Least Recently Used (LRU) cache for financial query responses.
    Supports process-local OrderedDict mode and multi-worker SQLite WAL shared mode.
    """

    def __init__(
        self,
        max_capacity: int = 256,
        shared_backend: Optional[str] = None,
        db_path: Optional[Union[str, Path]] = None,
    ):
        self.max_capacity = max_capacity
        self.shared_backend = (
            shared_backend
            or ("sqlite" if db_path is not None else os.getenv("FINTRACE_SHARED_BACKEND", "memory"))
        ).strip().lower()
        self.db_path = Path(db_path).expanduser().resolve() if db_path is not None else DEFAULT_CACHE_DB_PATH
        self._cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._doc_to_keys: Dict[str, set[str]] = {}
        self._lock = threading.RLock()
        self.hits: int = 0
        self.misses: int = 0

        if self.shared_backend == "sqlite":
            if not is_path_safe(str(self.db_path)):
                raise ValueError(f"Access denied: cache db_path '{self.db_path}' escapes authorized boundaries")
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._init_sqlite()

    def _connect_sqlite(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=30.0, isolation_level=None)
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
                        CREATE TABLE IF NOT EXISTS query_cache (
                            cache_key TEXT PRIMARY KEY,
                            doc_id TEXT NOT NULL,
                            response_json TEXT NOT NULL,
                            last_access REAL NOT NULL
                        );
                        """
                    )
                    conn.execute("CREATE INDEX IF NOT EXISTS idx_qcache_doc ON query_cache(doc_id);")
                    conn.execute("CREATE INDEX IF NOT EXISTS idx_qcache_lru ON query_cache(last_access);")
                    conn.execute(
                        """
                        CREATE TABLE IF NOT EXISTS cache_metrics (
                            id INTEGER PRIMARY KEY CHECK (id = 1),
                            hits INTEGER NOT NULL DEFAULT 0,
                            misses INTEGER NOT NULL DEFAULT 0
                        );
                        """
                    )
                    conn.execute("INSERT OR IGNORE INTO cache_metrics (id, hits, misses) VALUES (1, 0, 0);")
                return
            except sqlite3.OperationalError as e:
                if "locked" in str(e).lower() and attempt < 4:
                    time.sleep(0.05 * (attempt + 1))
                    continue
                raise

    def _make_key(self, doc_id: str, query_text: str, top_k: int, mode: str) -> str:
        norm_query = query_text.strip().lower()
        return f"{doc_id}::{top_k}::{mode}::{norm_query}"

    def get(self, doc_id: str, query_text: str, top_k: int, mode: str) -> Optional[Dict[str, Any]]:
        key = self._make_key(doc_id, query_text, top_k, mode)
        with self._lock:
            if self.shared_backend == "sqlite":
                now = time.monotonic()
                conn = self._connect_sqlite()
                try:
                    conn.execute("BEGIN IMMEDIATE;")
                    row = conn.execute(
                        "SELECT response_json FROM query_cache WHERE cache_key = ?",
                        (key,),
                    ).fetchone()
                    if row is not None:
                        conn.execute(
                            "UPDATE query_cache SET last_access = ? WHERE cache_key = ?",
                            (now, key),
                        )
                        conn.execute("UPDATE cache_metrics SET hits = hits + 1 WHERE id = 1")
                        conn.execute("COMMIT;")
                        self.hits += 1
                        return json.loads(row[0])
                    conn.execute("UPDATE cache_metrics SET misses = misses + 1 WHERE id = 1")
                    conn.execute("COMMIT;")
                    self.misses += 1
                    return None
                except Exception:
                    conn.execute("ROLLBACK;")
                    raise
                finally:
                    conn.close()

            if key in self._cache:
                self._cache.move_to_end(key)
                self.hits += 1
                logger.debug("Query cache hit for key: %s", key)
                return self._cache[key]
            self.misses += 1
            return None

    def put(self, doc_id: str, query_text: str, top_k: int, mode: str, response_data: Dict[str, Any]) -> None:
        key = self._make_key(doc_id, query_text, top_k, mode)
        with self._lock:
            if self.shared_backend == "sqlite":
                now = time.monotonic()
                payload_json = json.dumps(response_data, ensure_ascii=False, default=_json_default)
                conn = self._connect_sqlite()
                try:
                    conn.execute("BEGIN IMMEDIATE;")
                    conn.execute(
                        """
                        INSERT INTO query_cache (cache_key, doc_id, response_json, last_access)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT(cache_key) DO UPDATE SET
                            response_json = excluded.response_json,
                            last_access = excluded.last_access
                        """,
                        (key, doc_id, payload_json, now),
                    )
                    total = int(conn.execute("SELECT COUNT(*) FROM query_cache").fetchone()[0])
                    if total > self.max_capacity:
                        excess = total - self.max_capacity
                        conn.execute(
                            """
                            DELETE FROM query_cache WHERE cache_key IN (
                                SELECT cache_key FROM query_cache ORDER BY last_access ASC LIMIT ?
                            )
                            """,
                            (excess,),
                        )
                    conn.execute("COMMIT;")
                    return
                except Exception:
                    conn.execute("ROLLBACK;")
                    raise
                finally:
                    conn.close()

            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = response_data

            if doc_id not in self._doc_to_keys:
                self._doc_to_keys[doc_id] = set()
            self._doc_to_keys[doc_id].add(key)

            # Evict LRU if over capacity
            if len(self._cache) > self.max_capacity:
                oldest_key, _ = self._cache.popitem(last=False)
                # Clean from doc_to_keys index
                for d_id, keys in list(self._doc_to_keys.items()):
                    keys.discard(oldest_key)
                    if not keys:
                        del self._doc_to_keys[d_id]

    def invalidate_document(self, doc_id: str) -> int:
        """Invalidates all cached queries for a specific document."""
        with self._lock:
            if self.shared_backend == "sqlite":
                conn = self._connect_sqlite()
                try:
                    conn.execute("BEGIN IMMEDIATE;")
                    cur = conn.execute("DELETE FROM query_cache WHERE doc_id = ?", (doc_id,))
                    removed = int(cur.rowcount or 0)
                    conn.execute("COMMIT;")
                    return removed
                except Exception:
                    conn.execute("ROLLBACK;")
                    raise
                finally:
                    conn.close()

            keys = self._doc_to_keys.pop(doc_id, set())
            removed = 0
            for k in keys:
                if k in self._cache:
                    del self._cache[k]
                    removed += 1
            return removed

    def clear(self) -> None:
        with self._lock:
            if self.shared_backend == "sqlite":
                conn = self._connect_sqlite()
                try:
                    conn.execute("BEGIN IMMEDIATE;")
                    conn.execute("DELETE FROM query_cache")
                    conn.execute("UPDATE cache_metrics SET hits = 0, misses = 0 WHERE id = 1")
                    conn.execute("COMMIT;")
                except Exception:
                    conn.execute("ROLLBACK;")
                    raise
                finally:
                    conn.close()
            self._cache.clear()
            self._doc_to_keys.clear()
            self.hits = 0
            self.misses = 0

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            if self.shared_backend == "sqlite":
                with self._connect_sqlite() as conn:
                    entries = int(conn.execute("SELECT COUNT(*) FROM query_cache").fetchone()[0])
                    row = conn.execute("SELECT hits, misses FROM cache_metrics WHERE id = 1").fetchone()
                    hits = int(row[0]) if row else 0
                    misses = int(row[1]) if row else 0
                total_lookups = hits + misses
                ratio = (hits / total_lookups) if total_lookups > 0 else 0.0
                return {
                    "in_memory_query_cache_entries": entries,
                    "query_cache_hits": hits,
                    "query_cache_misses": misses,
                    "hit_ratio": round(ratio, 4),
                    "backend": "sqlite_wal",
                }

            total_lookups = self.hits + self.misses
            ratio = (self.hits / total_lookups) if total_lookups > 0 else 0.0
            return {
                "in_memory_query_cache_entries": len(self._cache),
                "query_cache_hits": self.hits,
                "query_cache_misses": self.misses,
                "hit_ratio": round(ratio, 4),
            }


class CacheManager:
    """
    Coordinates application-wide caching: in-memory query cache and rendered page disk cache.
    """

    def __init__(
        self,
        render_cache_dir: str = "~/.finsight/cache/rendered_pages",
        query_cache_size: int = 256,
        shared_backend: Optional[str] = None,
        cache_db_path: Optional[Union[str, Path]] = None,
    ):
        self.render_cache_dir = Path(os.path.expanduser(render_cache_dir)).resolve()
        self.query_cache = QueryLRUCache(
            max_capacity=query_cache_size,
            shared_backend=shared_backend,
            db_path=cache_db_path,
        )

    def get_stats(self) -> Dict[str, Any]:
        """Calculates global cache statistics across memory and disk."""
        query_stats = self.query_cache.stats()

        cached_docs = 0
        cached_pages = 0
        total_bytes = 0

        if self.render_cache_dir.exists():
            for doc_folder in self.render_cache_dir.iterdir():
                if doc_folder.is_dir() and not doc_folder.name.startswith("."):
                    cached_docs += 1
                    for f in doc_folder.iterdir():
                        if f.is_file():
                            total_bytes += f.stat().st_size
                            if f.suffix.lower() == ".png":
                                cached_pages += 1

        return {
            "total_cached_documents": cached_docs,
            "total_cached_pages": cached_pages,
            "rendered_cache_bytes": total_bytes,
            **query_stats,
        }

    def clear(self, scope: str = "all", document_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Clears cache based on scope ('all', 'queries', 'documents').
        Guarded by strict Path Traversal and direct-child containment validation.
        """
        if document_id:
            if not re.match(r"^[a-zA-Z0-9_\-]+$", document_id) or len(document_id) > 64:
                raise ValueError(f"Access denied: document_id '{document_id}' contains unsafe characters")

        cleared_queries = 0
        cleared_docs = 0

        if scope in ("all", "queries"):
            if document_id:
                cleared_queries = self.query_cache.invalidate_document(document_id)
            else:
                cleared_queries = len(self.query_cache._cache)
                self.query_cache.clear()

        if scope in ("all", "documents"):
            if document_id:
                target_dir = (self.render_cache_dir / document_id).resolve()
                if target_dir.parent != self.render_cache_dir:
                    raise ValueError(f"Access denied: document_id '{document_id}' escapes cache directory")
                if is_path_safe(str(target_dir)) and target_dir.exists():
                    shutil.rmtree(target_dir, ignore_errors=True)
                    cleared_docs = 1
            else:
                if self.render_cache_dir.exists() and is_path_safe(str(self.render_cache_dir)):
                    for doc_folder in self.render_cache_dir.iterdir():
                        if doc_folder.is_dir() and not doc_folder.name.startswith("."):
                            shutil.rmtree(doc_folder, ignore_errors=True)
                            cleared_docs += 1

        return {
            "scope": scope,
            "document_id": document_id,
            "cleared_queries": cleared_queries,
            "cleared_documents": cleared_docs,
        }


# Global singleton cache manager
cache_manager = CacheManager()
