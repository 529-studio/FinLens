"""
FinSight LanceDB Persistent Multi-Vector Store
Governed by PRD §2, ADR-001, and AGENTS.md Rule 13 (Security & Injection Defense).

Provides disk-backed persistence for:
1. Rendered document page metadata (dimensions, signatures, paths).
2. Multi-vector visual patch embeddings (ColPali/late-interaction tensors).
3. Fast nearest-neighbor vector search and enterprise audit statistics.
"""

import os
import re
import json
import time
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from dotenv import load_dotenv

# Enforce relative path for .env (529 standard: env-and-auth-ops-debugging)
ENV_PATH = Path(__file__).resolve().parents[3] / ".env"
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)

from contracts import is_path_safe

logger = logging.getLogger("finsight.store")

DEFAULT_LANCEDB_DIR = os.getenv("FINSIGHT_LANCEDB_DIR", "~/.finsight/lancedb")
TABLE_NAME = "document_pages"
PATCH_TABLE_NAME = "document_patches"
DEFAULT_VECTOR_DIM = 128


class StoreSecurityError(Exception):
    """Raised when an unsafe path or injection payload is detected in store operations."""
    pass


class LanceDBStore:
    """
    Persistent disk storage engine managing multi-vector representations of document pages.
    """

    def __init__(
        self,
        db_dir: Optional[Union[str, Path]] = None,
        vector_dim: int = DEFAULT_VECTOR_DIM,
    ):
        raw_dir = db_dir or DEFAULT_LANCEDB_DIR
        self.db_dir = Path(raw_dir).expanduser().resolve()
        self.vector_dim = vector_dim

        # AGENTS.md Rule 13: Path Traversal Defense
        if not is_path_safe(str(self.db_dir)):
            raise StoreSecurityError(
                f"Access denied: db_dir '{self.db_dir}' escapes authorized boundaries"
            )

        self.db_dir.mkdir(parents=True, exist_ok=True)
        self._db = None
        self._table = None
        self._patch_table = None
        self._pages_cache: Dict[str, List[Dict[str, Any]]] = {}
        self._patches_cache: Dict[str, Dict[int, Any]] = {}
        self._cache_epoch: int = 0

    def _sanitize_doc_id(self, doc_id: str) -> str:
        """Sanitizes document_id and rejects injection / path traversal characters."""
        if not doc_id or "\0" in doc_id or ".." in doc_id:
            raise StoreSecurityError(f"Invalid document identifier: '{doc_id}' contains unsafe characters")
        if not re.fullmatch(r"[a-zA-Z0-9_\-]+", doc_id):
            raise StoreSecurityError(f"Invalid document identifier: '{doc_id}' must be alphanumeric with '_' or '-'")
        if len(doc_id) > 64:
            raise StoreSecurityError(f"Document identifier exceeds maximum length of 64 characters")
        return doc_id

    def connect(self) -> None:
        """Connects to LanceDB on disk and ensures the document_pages table exists."""
        if self._db is None:
            import lancedb
            import pyarrow as pa

            self._db = lancedb.connect(str(self.db_dir))
            # Heed deprecation: use list_tables() over table_names()
            if hasattr(self._db, "list_tables"):
                existing_tables = list(self._db.list_tables())
            else:
                existing_tables = self._db.table_names()

            if TABLE_NAME in existing_tables:
                self._table = self._db.open_table(TABLE_NAME)
            else:
                schema = pa.schema([
                    pa.field("doc_id", pa.string()),
                    pa.field("page_number", pa.int32()),
                    pa.field("image_path", pa.string()),
                    pa.field("width", pa.int32()),
                    pa.field("height", pa.int32()),
                    pa.field("signature", pa.string()),
                    pa.field("vector", pa.list_(pa.float32(), self.vector_dim)),
                    pa.field("metadata", pa.string()),
                    pa.field("indexed_at", pa.float64()),
                ])
                self._table = self._db.create_table(TABLE_NAME, schema=schema)

            if PATCH_TABLE_NAME in existing_tables:
                self._patch_table = self._db.open_table(PATCH_TABLE_NAME)
            else:
                patch_schema = pa.schema([
                    pa.field("doc_id", pa.string()),
                    pa.field("page_number", pa.int32()),
                    pa.field("patch_index", pa.int32()),
                    pa.field("vector", pa.list_(pa.float32(), self.vector_dim)),
                    pa.field("indexed_at", pa.float64()),
                ])
                self._patch_table = self._db.create_table(PATCH_TABLE_NAME, schema=patch_schema)

    def _ensure_connected(self):
        if self._table is None or self._patch_table is None:
            self.connect()

    def upsert_pages(self, doc_id: str, pages: List[Dict[str, Any]]) -> int:
        """
        Idempotently inserts or updates document page representations in LanceDB.
        """
        clean_id = self._sanitize_doc_id(doc_id)
        self._ensure_connected()

        # Remove existing records for this document to ensure idempotency
        try:
            self._table.delete(f"doc_id = '{clean_id}'")
        except Exception as e:
            logger.debug("Delete prior records for %s returned: %s", clean_id, e)

        rows = []
        now = time.time()
        for p in pages:
            vector = p.get("vector")
            if vector is None:
                # Deterministic synthetic fallback vector if neural embedding omitted
                vector = [0.01 * (p.get("page_number", 1) % 10)] * self.vector_dim

            meta = p.get("metadata", {})
            meta_str = json.dumps(meta, ensure_ascii=False) if isinstance(meta, dict) else str(meta)

            rows.append({
                "doc_id": clean_id,
                "page_number": int(p.get("page_number", 1)),
                "image_path": str(p.get("image_path", "")),
                "width": int(p.get("width", 0)),
                "height": int(p.get("height", 0)),
                "signature": str(p.get("signature", "")),
                "vector": [float(v) for v in vector[:self.vector_dim]],
                "metadata": meta_str,
                "indexed_at": float(now),
            })

        if rows:
            self._table.add(rows)

        self._pages_cache.pop(clean_id, None)
        self._cache_epoch += 1
        return len(rows)

    def upsert_page_patches(self, doc_id: str, patches: List[Dict[str, Any]]) -> int:
        """
        Idempotently persists multi-vector visual patch embeddings for a document in LanceDB.
        Each item expects: page_number (int), patch_index (int), vector (List[float] of length vector_dim).
        """
        clean_id = self._sanitize_doc_id(doc_id)
        self._ensure_connected()

        try:
            self._patch_table.delete(f"doc_id = '{clean_id}'")
        except Exception as e:
            logger.debug("Delete prior patches for %s returned: %s", clean_id, e)

        rows = []
        now = time.time()
        for p in patches:
            vec = p.get("vector")
            if vec is None:
                continue
            vec_list = [float(v) for v in vec[:self.vector_dim]]
            if len(vec_list) < self.vector_dim:
                vec_list.extend([0.0] * (self.vector_dim - len(vec_list)))
            rows.append({
                "doc_id": clean_id,
                "page_number": int(p["page_number"]),
                "patch_index": int(p.get("patch_index", 0)),
                "vector": vec_list,
                "indexed_at": float(now),
            })

        if rows:
            self._patch_table.add(rows)

        self._patches_cache.pop(clean_id, None)
        self._cache_epoch += 1
        return len(rows)

    def get_page_patches(
        self,
        doc_id: str,
        page_numbers: Optional[List[int]] = None,
    ) -> Dict[int, List[List[float]]]:
        """
        Retrieves stored multi-vector patch lists keyed by 1-indexed page_number.
        Uses in-memory cache per document for sub-millisecond MaxSim scoring.
        """
        clean_id = self._sanitize_doc_id(doc_id)
        if clean_id not in self._patches_cache:
            self._ensure_connected()
            try:
                rows = (
                    self._patch_table.search()
                    .where(f"doc_id = '{clean_id}'")
                    .limit(100000)
                    .to_list()
                )
            except Exception as e:
                logger.error("Failed to query patches for %s: %s", clean_id, e)
                rows = []

            grouped: Dict[int, List[tuple]] = {}
            for r in rows:
                p_num = int(r["page_number"])
                grouped.setdefault(p_num, []).append((int(r["patch_index"]), r["vector"]))

            ordered: Dict[int, List[List[float]]] = {}
            for p_num, items in grouped.items():
                items.sort(key=lambda x: x[0])
                ordered[p_num] = [vec for _, vec in items]
            self._patches_cache[clean_id] = ordered

        cached_doc = self._patches_cache[clean_id]
        if page_numbers is None:
            return cached_doc
        return {p: cached_doc[p] for p in page_numbers if p in cached_doc}

    def search_patches(self, doc_id: str, query_vector: List[float], top_k: int = 32) -> List[Dict[str, Any]]:
        """
        Executes LanceDB nearest-neighbor search across individual visual patch vectors
        scoped to a specific document.
        """
        clean_id = self._sanitize_doc_id(doc_id)
        self._ensure_connected()

        try:
            vec = [float(v) for v in query_vector[:self.vector_dim]]
            if len(vec) < self.vector_dim:
                vec.extend([0.0] * (self.vector_dim - len(vec)))
            return (
                self._patch_table.search(vec)
                .where(f"doc_id = '{clean_id}'")
                .limit(top_k)
                .to_list()
            )
        except Exception as e:
            logger.error("Patch vector search failed for %s: %s", clean_id, e)
            return []

    def get_pages(self, doc_id: str) -> List[Dict[str, Any]]:
        """Retrieves all indexed pages for a given document, sorted by page_number (cached in-memory)."""
        clean_id = self._sanitize_doc_id(doc_id)
        if clean_id in self._pages_cache:
            return self._pages_cache[clean_id]

        self._ensure_connected()

        try:
            results = (
                self._table.search()
                .where(f"doc_id = '{clean_id}'")
                .limit(10000)
                .to_list()
            )
        except Exception as e:
            logger.error("Failed to query pages for %s: %s", clean_id, e)
            return []

        # Parse metadata and format results
        formatted = []
        for r in results:
            meta = r.get("metadata", "{}")
            try:
                parsed_meta = json.loads(meta) if isinstance(meta, str) else meta
            except Exception:
                parsed_meta = {}

            formatted.append({
                "doc_id": r["doc_id"],
                "page_number": r["page_number"],
                "image_path": r["image_path"],
                "width": r["width"],
                "height": r["height"],
                "signature": r["signature"],
                "metadata": parsed_meta,
                "indexed_at": r["indexed_at"],
            })

        formatted.sort(key=lambda x: x["page_number"])
        self._pages_cache[clean_id] = formatted
        return formatted

    def search(self, doc_id: str, query_vector: List[float], top_k: int = 2) -> List[Dict[str, Any]]:
        """
        Executes vector nearest-neighbor search scoped to a specific document.
        """
        clean_id = self._sanitize_doc_id(doc_id)
        self._ensure_connected()

        try:
            vec = [float(v) for v in query_vector[:self.vector_dim]]
            results = (
                self._table.search(vec)
                .where(f"doc_id = '{clean_id}'")
                .limit(top_k)
                .to_list()
            )
            return results
        except Exception as e:
            logger.error("Vector search failed for %s: %s", clean_id, e)
            return []

    def delete_document(self, doc_id: str) -> bool:
        """Deletes all page vectors and records for a document."""
        clean_id = self._sanitize_doc_id(doc_id)
        self._ensure_connected()

        try:
            self._table.delete(f"doc_id = '{clean_id}'")
            if self._patch_table is not None:
                self._patch_table.delete(f"doc_id = '{clean_id}'")
            self._pages_cache.pop(clean_id, None)
            self._patches_cache.pop(clean_id, None)
            self._cache_epoch += 1
            return True
        except Exception as e:
            logger.error("Failed to delete document %s: %s", clean_id, e)
            return False

    def clear_memory_cache(self) -> None:
        """Clears the in-memory document page and patch caches."""
        self._pages_cache.clear()
        self._patches_cache.clear()
        self._cache_epoch += 1

    def list_documents(self) -> List[str]:
        """Returns the unique list of document identifiers currently indexed."""
        self._ensure_connected()
        import pyarrow as pa

        try:
            arrow_tbl = self._table.to_arrow()
            if arrow_tbl.num_rows == 0:
                return []
            unique_ids = pa.compute.unique(arrow_tbl["doc_id"]).to_pylist()
            return sorted(unique_ids)
        except Exception as e:
            logger.error("Failed to list documents: %s", e)
            return []

    def get_stats(self) -> Dict[str, Any]:
        """Calculates disk usage, total page records, and document counts."""
        self._ensure_connected()

        total_pages = self._table.count_rows()
        docs = self.list_documents()

        # Compute disk size
        disk_size = 0
        try:
            for root, _, files in os.walk(self.db_dir):
                for f in files:
                    fp = os.path.join(root, f)
                    if os.path.exists(fp):
                        disk_size += os.path.getsize(fp)
        except Exception:
            disk_size = 0

        return {
            "db_path": str(self.db_dir),
            "total_documents": len(docs),
            "total_pages": total_pages,
            "disk_size_bytes": disk_size,
            "vector_dimension": self.vector_dim,
        }
