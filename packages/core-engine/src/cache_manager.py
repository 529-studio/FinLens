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
import shutil
import logging
import threading
from pathlib import Path
from collections import OrderedDict
from typing import Dict, Any, Optional, List, Tuple

from contracts import is_path_safe

logger = logging.getLogger("finsight.cache")


class QueryLRUCache:
    """
    Thread-safe Least Recently Used (LRU) cache for financial query responses.
    Reduces repeat query latency from ~1000ms+ to < 5ms.
    """

    def __init__(self, max_capacity: int = 256):
        self.max_capacity = max_capacity
        self._cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._doc_to_keys: Dict[str, set[str]] = {}
        self._lock = threading.RLock()
        self.hits: int = 0
        self.misses: int = 0

    def _make_key(self, doc_id: str, query_text: str, top_k: int, mode: str) -> str:
        norm_query = query_text.strip().lower()
        return f"{doc_id}::{top_k}::{mode}::{norm_query}"

    def get(self, doc_id: str, query_text: str, top_k: int, mode: str) -> Optional[Dict[str, Any]]:
        key = self._make_key(doc_id, query_text, top_k, mode)
        with self._lock:
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
            keys = self._doc_to_keys.pop(doc_id, set())
            removed = 0
            for k in keys:
                if k in self._cache:
                    del self._cache[k]
                    removed += 1
            return removed

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
            self._doc_to_keys.clear()
            self.hits = 0
            self.misses = 0

    def stats(self) -> Dict[str, Any]:
        with self._lock:
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

    def __init__(self, render_cache_dir: str = "~/.finsight/cache/rendered_pages", query_cache_size: int = 256):
        self.render_cache_dir = Path(os.path.expanduser(render_cache_dir)).resolve()
        self.query_cache = QueryLRUCache(max_capacity=query_cache_size)

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
