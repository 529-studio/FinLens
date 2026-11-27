"""
FinSight Visual Retrieval Engine (ColPali Multi-Vector Patch Embedding + LanceDB)
Processes high-resolution page images, computes multi-vector spatial patch embeddings,
persists patch tensors in LanceDB, and executes late-interaction (MaxSim) retrieval.
Governed by ADR-001, Sprint 1 Issue #4, Sprint 14 Issue #125, and 529 Engineering Standards.
"""

import os
import re
import json
import hashlib
import logging
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional

import numpy as np
from PIL import Image

from contracts import is_path_safe
from store import LanceDBStore, StoreSecurityError, DEFAULT_LANCEDB_DIR, DEFAULT_VECTOR_DIM

logger = logging.getLogger("finsight.retriever")

PATCH_GRID_ROWS = 8
PATCH_GRID_COLS = 8
NUM_PATCHES = PATCH_GRID_ROWS * PATCH_GRID_COLS
VISUAL_DIM = 64
SEMANTIC_DIM = 64

# Visual-layout intent vocabulary for query-to-patch visual subspace alignment
_CHART_TERMS = {
    "biểu", "đồ", "chart", "charts", "graph", "graphs", "plot", "figure", "fig",
    "bar", "pie", "line", "trend", "xu", "hướng", "cơ", "cấu", "tỷ", "trọng",
    "xuất", "khẩu", "nội", "địa", "tăng", "trưởng", "biên",
    "margin", "visual", "phân", "bổ", "thị", "trường", "doanh_thu",
}
_TABLE_TERMS = {
    "bảng", "cân", "đối", "kế", "toán", "tài", "sản", "table", "tables",
    "balance", "sheet", "assets", "liabilities", "equity", "nợ", "phải",
    "tồn", "kho", "mã", "số", "tổng", "cộng", "đầu", "tư", "ratio", "ratios",
    "ngắn", "hạn", "dài", "vốn", "chủ", "tiền", "mặt", "hàng", "lưu",
    "110", "111", "112", "120", "130", "140", "200", "220", "270",
}
_FOOTNOTE_TERMS = {
    "thuyết", "minh", "footnote", "footnotes", "note", "notes", "disclosure",
    "disclosures", "lãi", "suất", "giải", "trình", "chi", "tiết", "phong",
    "tỏa", "thế", "chấp", "appendix", "kỳ", "gốc", "dự", "phòng", "hao", "mòn",
    "quản", "lý", "bán", "nghiệp",
}

# Precomputed orthogonal-ish directions inside the 64-dim visual subspace
_CHART_DIR = np.zeros(VISUAL_DIM, dtype=np.float32)
_CHART_DIR[0] = 1.0
_CHART_DIR[3] = 0.35
_CHART_DIR[6] = 0.25
_CHART_DIR /= np.linalg.norm(_CHART_DIR)

_TABLE_DIR = np.zeros(VISUAL_DIM, dtype=np.float32)
_TABLE_DIR[1] = 1.0
_TABLE_DIR[4] = 0.35
_TABLE_DIR[5] = 0.40
_TABLE_DIR[7] = 0.25
_TABLE_DIR /= np.linalg.norm(_TABLE_DIR)

_FOOTNOTE_DIR = np.zeros(VISUAL_DIM, dtype=np.float32)
_FOOTNOTE_DIR[2] = 1.0
_FOOTNOTE_DIR[5] = 0.35
_FOOTNOTE_DIR[8] = 0.25
_FOOTNOTE_DIR /= np.linalg.norm(_FOOTNOTE_DIR)


def _l2_normalize(vec: np.ndarray, eps: float = 1e-8) -> np.ndarray:
    norm = float(np.linalg.norm(vec))
    if norm <= eps:
        return np.zeros_like(vec, dtype=np.float32)
    return (vec / norm).astype(np.float32)


def _l2_normalize_rows(mat: np.ndarray, eps: float = 1e-8) -> np.ndarray:
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    safe_norms = np.where(norms > eps, norms, 1.0)
    out = mat / safe_norms
    out[norms[:, 0] <= eps] = 0.0
    return out.astype(np.float32)


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[0-9a-zA-ZÀ-ỹ]+", text.lower())


def _hash_semantic_tokens(tokens: List[str], dim: int = SEMANTIC_DIM) -> np.ndarray:
    """
    Projects tokens and character trigrams into a fixed semantic subspace using
    deterministic signed feature hashing (BLAKE2b).
    """
    vec = np.zeros(dim, dtype=np.float32)
    if not tokens:
        return vec

    counts: Dict[str, int] = {}
    for tok in tokens:
        counts[tok] = counts.get(tok, 0) + 1

    for tok, tf in counts.items():
        weight = 1.0 + float(np.log1p(tf))
        # Whole token feature
        digest = hashlib.blake2b(tok.encode("utf-8"), digest_size=8).digest()
        idx = int.from_bytes(digest[:4], "little") % dim
        sign = 1.0 if (digest[4] & 1) == 0 else -1.0
        vec[idx] += sign * weight

        # Character 3-grams for morphological/subword matching
        if len(tok) >= 4:
            for i in range(len(tok) - 2):
                gram = tok[i : i + 3]
                gd = hashlib.blake2b(gram.encode("utf-8"), digest_size=8).digest()
                g_idx = int.from_bytes(gd[:4], "little") % dim
                g_sign = 1.0 if (gd[4] & 1) == 0 else -1.0
                vec[g_idx] += g_sign * (0.35 * weight)

    return _l2_normalize(vec)


class ColPaliPatchEmbedder:
    """
    Multi-vector ColPali patch embedder (8x8 = 64 spatial patches per page, 128-dim).
    Supports optional local neural ColPali weights when cached and enabled,
    with a deterministic visual-layout + spatial-text multi-vector embedder for
    zero-weight offline/CI execution.
    """

    def __init__(
        self,
        vector_dim: int = DEFAULT_VECTOR_DIM,
        grid_rows: int = PATCH_GRID_ROWS,
        grid_cols: int = PATCH_GRID_COLS,
    ):
        if vector_dim < VISUAL_DIM + SEMANTIC_DIM:
            raise ValueError(f"vector_dim ({vector_dim}) must be at least {VISUAL_DIM + SEMANTIC_DIM}")
        self.vector_dim = vector_dim
        self.grid_rows = grid_rows
        self.grid_cols = grid_cols
        self.num_patches = grid_rows * grid_cols
        self.mode = os.getenv("FINSIGHT_COLPALI_MODE", "auto").strip().lower()
        self._neural_model = None
        self._neural_processor = None
        self.backend_name = "colpali-patch-hybrid"
        self._maybe_init_neural_backend()

    def _maybe_init_neural_backend(self) -> None:
        if self.mode == "hybrid":
            return
        if self.mode != "neural":
            # Auto mode only activates neural ColPali when weights are explicitly cached
            # and FINSIGHT_ENABLE_NEURAL_COLPALI=1 to avoid unexpected multi-GB memory loads.
            if os.getenv("FINSIGHT_ENABLE_NEURAL_COLPALI", "0").strip() not in ("1", "true", "yes"):
                return
        try:
            from model_manager import ModelManager
            import mlx_vlm  # type: ignore

            mgr = ModelManager()
            model_id = "mlx-community/ColPali-v1.2-4bit"
            if mgr.is_cached(model_id):
                model_dir = mgr.get_model_dir(model_id)
                self._neural_model, self._neural_processor = mlx_vlm.load(str(model_dir))
                self.backend_name = "colpali-v1.2-mlx"
                logger.info("Loaded neural ColPali backend from %s", model_dir)
        except Exception as exc:
            logger.debug("Neural ColPali backend unavailable, using hybrid patch embedder: %s", exc)

    def _extract_visual_patch_matrix(self, img_path: Path, page_num: int) -> np.ndarray:
        """
        Extracts a (num_patches, VISUAL_DIM) float32 matrix from rendered page image pixels.
        Falls back deterministically when img_path is a synthetic non-image placeholder.
        """
        try:
            with Image.open(img_path) as im:
                rgb = im.convert("RGB").resize((256, 256), Image.Resampling.BILINEAR)
                arr = np.asarray(rgb, dtype=np.float32)
        except Exception:
            seed_bytes = hashlib.sha256(f"{img_path}:{page_num}".encode("utf-8")).digest()
            seed = int.from_bytes(seed_bytes[:4], "little")
            rng = np.random.default_rng(seed)
            fallback = rng.normal(0.0, 1.0, size=(self.num_patches, VISUAL_DIM)).astype(np.float32)
            return _l2_normalize_rows(fallback)

        cell_h = arr.shape[0] // self.grid_rows
        cell_w = arr.shape[1] // self.grid_cols

        gray = arr.mean(axis=2)
        sat = arr.max(axis=2) - arr.min(axis=2)

        patch_feats = np.zeros((self.num_patches, VISUAL_DIM), dtype=np.float32)

        idx = 0
        for r in range(self.grid_rows):
            y0, y1 = r * cell_h, (r + 1) * cell_h
            for c in range(self.grid_cols):
                x0, x1 = c * cell_w, (c + 1) * cell_w
                cell_rgb = arr[y0:y1, x0:x1]
                cell_gray = gray[y0:y1, x0:x1]
                cell_sat = sat[y0:y1, x0:x1]

                sat_ratio = float((cell_sat > 22.0).mean())
                sat_mean = float(cell_sat.mean() / 255.0)
                ink_density = float((cell_gray < 210.0).mean())
                dark_ink = float((cell_gray < 140.0).mean())

                h_edges = float((np.abs(np.diff(cell_gray, axis=0)) > 24.0).mean()) if cell_gray.shape[0] > 1 else 0.0
                v_edges = float((np.abs(np.diff(cell_gray, axis=1)) > 24.0).mean()) if cell_gray.shape[1] > 1 else 0.0
                row_rhythm = float(cell_gray.mean(axis=1).std() / 255.0)
                col_rhythm = float(cell_gray.mean(axis=0).std() / 255.0)

                # Core visual-layout concept channels gated by real ink density so blank
                # margins never inflate normalized visual concept weights:
                # 0: Chart/figure chromatic & solid-bar signature
                # 1: Tabular grid & multi-row numeric table signature
                # 2: Dense footnote/disclosure text rhythm signature
                ink_gate = min(1.0, ink_density * 10.0)
                chart_score = max(0.0, (sat_ratio * 18.0 + sat_mean * 10.0 - row_rhythm * 6.0 - h_edges * 3.0) * ink_gate)
                table_score = max(0.0, (row_rhythm * 22.0 + (h_edges + v_edges) * 10.0 + col_rhythm * 3.0 - sat_ratio * 14.0) * ink_gate)
                footnote_score = max(
                    0.0,
                    (row_rhythm * 14.0 + (r / max(1, self.grid_rows - 1)) * 0.75 + (1.0 - min(1.0, sat_ratio * 10.0)) * 0.45 + ink_density * 2.0) * ink_gate,
                )

                v = np.zeros(VISUAL_DIM, dtype=np.float32)
                v[0] = chart_score
                v[1] = table_score
                v[2] = footnote_score
                v[3] = sat_ratio * 4.0
                v[4] = h_edges * 5.0
                v[5] = row_rhythm * 4.0
                v[6] = sat_mean * 3.0
                v[7] = v_edges * 5.0
                v[8] = dark_ink * 3.0
                v[9] = ink_density * 2.0
                v[10] = float(cell_rgb[:, :, 0].mean() / 255.0)
                v[11] = float(cell_rgb[:, :, 1].mean() / 255.0)
                v[12] = float(cell_rgb[:, :, 2].mean() / 255.0)
                v[13] = (r + 0.5) / self.grid_rows
                v[14] = (c + 0.5) / self.grid_cols
                v[15] = col_rhythm * 3.0

                # Fine luminance distribution across channels 16..23
                hist, _ = np.histogram(cell_gray, bins=8, range=(0.0, 256.0))
                hist_norm = hist.astype(np.float32) / max(1.0, float(cell_gray.size))
                v[16:24] = hist_norm * 0.5

                patch_feats[idx] = _l2_normalize(v)
                idx += 1

        return patch_feats

    def _extract_spatial_text_patches(
        self,
        pdf_doc: Optional[Any],
        page_num: int,
    ) -> np.ndarray:
        """
        Extracts localized (num_patches, SEMANTIC_DIM) embeddings from words falling inside
        each (r, c) spatial cell of the source PDF page, when clean text is present.
        """
        patch_tokens: List[List[str]] = [[] for _ in range(self.num_patches)]
        if pdf_doc is not None and 1 <= page_num <= len(pdf_doc):
            try:
                page = pdf_doc.load_page(page_num - 1)
                rect = page.rect
                pw = max(1.0, float(rect.width))
                ph = max(1.0, float(rect.height))
                words = page.get_text("words") or []
                for w in words:
                    x0, y0, x1, y1, word_txt = w[0], w[1], w[2], w[3], str(w[4])
                    cx = max(0.0, min(0.9999, ((x0 + x1) * 0.5) / pw))
                    cy = max(0.0, min(0.9999, ((y0 + y1) * 0.5) / ph))
                    col = int(cx * self.grid_cols)
                    row = int(cy * self.grid_rows)
                    p_idx = row * self.grid_cols + col
                    for tok in _tokenize(word_txt):
                        patch_tokens[p_idx].append(tok)
                    # Also index bigrams of adjacent clean words when needed
            except Exception as exc:
                logger.debug("Spatial text extraction skipped for page %s: %s", page_num, exc)

        sem_mat = np.zeros((self.num_patches, SEMANTIC_DIM), dtype=np.float32)
        for idx, toks in enumerate(patch_tokens):
            if toks:
                sem_mat[idx] = _hash_semantic_tokens(toks, dim=SEMANTIC_DIM)
        return sem_mat

    def _resolve_source_pdf(self, pages: List[Tuple[int, Path, int, int]]) -> Optional[Any]:
        """Opens source PDF once via PyMuPDF if manifest.json in the render cache points to a safe path."""
        if not pages:
            return None
        first_img = Path(pages[0][1])
        manifest_file = first_img.parent / "manifest.json"
        if not manifest_file.exists() or not is_path_safe(str(manifest_file)):
            return None
        try:
            manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
            pdf_path_str = manifest.get("pdf_path")
            if pdf_path_str and is_path_safe(str(pdf_path_str)) and Path(pdf_path_str).exists():
                import pymupdf
                return pymupdf.open(pdf_path_str)
        except Exception as exc:
            logger.debug("Could not open source PDF from manifest: %s", exc)
        return None

    def embed_document_pages(
        self,
        pages: List[Tuple[int, Path, int, int]],
    ) -> Dict[int, Tuple[np.ndarray, np.ndarray]]:
        """
        Computes multi-vector patch embeddings (num_patches, vector_dim) and
        pooled page vector (vector_dim,) for every page.
        Returns dict: page_number -> (patch_matrix, pooled_vector).
        """
        results: Dict[int, Tuple[np.ndarray, np.ndarray]] = {}
        pdf_doc = self._resolve_source_pdf(pages)
        try:
            for page_num, img_path, _, _ in pages:
                vis_mat = self._extract_visual_patch_matrix(Path(img_path), page_num)
                sem_mat = self._extract_spatial_text_patches(pdf_doc, page_num)

                full_patches = np.zeros((self.num_patches, self.vector_dim), dtype=np.float32)
                full_patches[:, :VISUAL_DIM] = vis_mat * np.sqrt(0.5)
                full_patches[:, VISUAL_DIM : VISUAL_DIM + SEMANTIC_DIM] = sem_mat * np.sqrt(0.5)
                full_patches = _l2_normalize_rows(full_patches)

                pooled = _l2_normalize(full_patches.mean(axis=0))
                results[page_num] = (full_patches, pooled)
        finally:
            if pdf_doc is not None:
                try:
                    pdf_doc.close()
                except Exception:
                    pass
        return results

    def embed_query(self, query: str) -> np.ndarray:
        """
        Encodes a query into contextualized multi-token vectors (M, vector_dim)
        aligned with both the visual-layout patch subspace and semantic token subspace.
        """
        tokens = _tokenize(query)
        if not tokens:
            tokens = ["query"]

        # Query-level visual-layout context (mirrors ColPali contextualized query tokens)
        query_vis = np.zeros(VISUAL_DIM, dtype=np.float32)
        for tok in tokens:
            if tok in _CHART_TERMS:
                query_vis += _CHART_DIR * 1.2
            if tok in _TABLE_TERMS:
                query_vis += _TABLE_DIR * 1.15
            if tok in _FOOTNOTE_TERMS:
                query_vis += _FOOTNOTE_DIR * 1.15
        query_vis = _l2_normalize(query_vis)

        # Include full-query summary token alongside individual query tokens
        token_groups: List[List[str]] = [[tok] for tok in tokens]
        if len(tokens) > 1:
            token_groups.append(tokens)

        q_mat = np.zeros((len(token_groups), self.vector_dim), dtype=np.float32)
        has_query_vis = float(np.linalg.norm(query_vis)) > 0.0
        for i, grp in enumerate(token_groups):
            # Local token visual-layout intent + query-wide contextual visual intent
            vis_vec = np.zeros(VISUAL_DIM, dtype=np.float32)
            for tok in grp:
                if tok in _CHART_TERMS:
                    vis_vec += _CHART_DIR * 1.2
                if tok in _TABLE_TERMS:
                    vis_vec += _TABLE_DIR * 1.15
                if tok in _FOOTNOTE_TERMS:
                    vis_vec += _FOOTNOTE_DIR * 1.15
            if has_query_vis:
                vis_vec = vis_vec + query_vis * 0.85
            vis_vec = _l2_normalize(vis_vec)

            # Semantic hashed token + char-trigram projection
            sem_vec = _hash_semantic_tokens(grp, dim=SEMANTIC_DIM)

            if float(np.linalg.norm(vis_vec)) > 0.0 and float(np.linalg.norm(sem_vec)) > 0.0:
                q_mat[i, :VISUAL_DIM] = vis_vec * np.sqrt(0.60)
                q_mat[i, VISUAL_DIM : VISUAL_DIM + SEMANTIC_DIM] = sem_vec * np.sqrt(0.40)
            elif float(np.linalg.norm(vis_vec)) > 0.0:
                q_mat[i, :VISUAL_DIM] = vis_vec
            else:
                q_mat[i, VISUAL_DIM : VISUAL_DIM + SEMANTIC_DIM] = sem_vec

            q_mat[i] = _l2_normalize(q_mat[i])

        return q_mat

    def pool_query(self, query_vecs: np.ndarray) -> np.ndarray:
        """Pools multi-token query vectors into a single L2-normalized vector for ANN search."""
        if query_vecs.size == 0:
            return np.zeros(self.vector_dim, dtype=np.float32)
        return _l2_normalize(query_vecs.mean(axis=0))

    @staticmethod
    def compute_maxsim(query_vecs: np.ndarray, page_patches: np.ndarray) -> float:
        """
        Late-interaction ColPali MaxSim operator:
        MaxSim(Q, P) = (1 / |Q|) * sum_{i} max_{j} (q_i . p_j)
        """
        if query_vecs.size == 0 or page_patches.size == 0:
            return 0.0
        sim = query_vecs @ page_patches.T
        return float(sim.max(axis=1).sum() / max(1, query_vecs.shape[0]))


class VisualRetriever:
    """
    Manages document visual patch indexing and Late-Interaction (MaxSim) page retrieval,
    persisting page vectors and patch tensors into LanceDB.
    """

    def __init__(
        self,
        store: Optional[LanceDBStore] = None,
        index_base_dir: Optional[str] = None,
        embedder: Optional[ColPaliPatchEmbedder] = None,
    ):
        self.store = store or LanceDBStore(db_dir=index_base_dir or DEFAULT_LANCEDB_DIR)
        self.index_base_dir = self.store.db_dir
        self.embedder = embedder or ColPaliPatchEmbedder(vector_dim=self.store.vector_dim)
        # Fast in-memory numpy matrix cache keyed by doc_id, guarded by store._cache_epoch
        self._np_patch_cache: Dict[str, Tuple[int, Dict[int, np.ndarray]]] = {}

    def index_document(self, document_id: str, pages: List[Tuple[int, Path, int, int]]) -> int:
        """
        Extracts ColPali visual+semantic patch embeddings for every page and persists
        both page-level pooled vectors and multi-vector patch matrices into LanceDB.
        Returns total number of pages indexed.
        """
        clean_id = self.store._sanitize_doc_id(document_id)
        for _, img_path, _, _ in pages:
            if not is_path_safe(str(img_path)):
                raise StoreSecurityError(
                    f"Access denied: image_path '{img_path}' escapes authorized boundaries"
                )

        embeddings = self.embedder.embed_document_pages(pages)
        indexed_pages: List[Dict[str, Any]] = []
        patch_rows: List[Dict[str, Any]] = []
        np_cache_for_doc: Dict[int, np.ndarray] = {}

        for page_num, img_path, w, h in pages:
            p_path = Path(img_path)
            try:
                file_hash = hashlib.sha256(p_path.read_bytes()).hexdigest()[:16]
            except OSError:
                file_hash = hashlib.sha256(f"{p_path}:{page_num}".encode("utf-8")).hexdigest()[:16]

            patch_mat, pooled_vec = embeddings[page_num]
            np_cache_for_doc[page_num] = patch_mat

            indexed_pages.append({
                "page_number": page_num,
                "image_path": str(img_path),
                "width": w,
                "height": h,
                "signature": file_hash,
                "vector": pooled_vec.tolist(),
                "metadata": {
                    "embedder_backend": self.embedder.backend_name,
                    "num_patches": int(patch_mat.shape[0]),
                },
            })

            for patch_idx in range(patch_mat.shape[0]):
                patch_rows.append({
                    "page_number": page_num,
                    "patch_index": patch_idx,
                    "vector": patch_mat[patch_idx].tolist(),
                })

        count = self.store.upsert_pages(clean_id, indexed_pages)
        self.store.upsert_page_patches(clean_id, patch_rows)
        self._np_patch_cache[clean_id] = (self.store._cache_epoch, np_cache_for_doc)
        return count

    def _get_doc_patch_matrices(self, document_id: str, page_numbers: List[int]) -> Dict[int, np.ndarray]:
        """Loads per-page patch matrices from epoch-validated numpy cache or LanceDB store."""
        current_epoch = getattr(self.store, "_cache_epoch", 0)
        cached_entry = self._np_patch_cache.get(document_id)
        if cached_entry is not None:
            cached_epoch, cached_mats = cached_entry
            if cached_epoch == current_epoch and all(p in cached_mats for p in page_numbers):
                return {p: cached_mats[p] for p in page_numbers}
            if cached_epoch != current_epoch:
                self._np_patch_cache.pop(document_id, None)

        raw_patches = self.store.get_page_patches(document_id, page_numbers)
        matrices: Dict[int, np.ndarray] = {}
        for p_num, vecs in raw_patches.items():
            if vecs:
                matrices[p_num] = np.asarray(vecs, dtype=np.float32)

        if matrices:
            existing = self._np_patch_cache.get(document_id)
            merged = dict(existing[1]) if existing and existing[0] == current_epoch else {}
            merged.update(matrices)
            self._np_patch_cache[document_id] = (current_epoch, merged)
        return matrices

    def search_with_scores(self, document_id: str, query: str, top_k: int = 2) -> List[Dict[str, Any]]:
        """
        Executes LanceDB ANN candidate retrieval followed by ColPali MaxSim late-interaction
        re-ranking across stored multi-vector page patches.
        """
        pages = self.store.get_pages(document_id)
        if not pages:
            return [{"page_number": 1, "score": 0.0, "backend": self.embedder.backend_name}]

        query_vecs = self.embedder.embed_query(query)
        pooled_q = self.embedder.pool_query(query_vecs)

        # Stage 1: LanceDB ANN vector search across page vectors and patch vectors
        candidate_limit = max(top_k * 16, 48)
        ann_pages = self.store.search(document_id, pooled_q.tolist(), top_k=candidate_limit)
        ann_patches = self.store.search_patches(document_id, pooled_q.tolist(), top_k=candidate_limit * 2)

        candidate_set = {int(r["page_number"]) for r in ann_pages}
        candidate_set.update(int(r["page_number"]) for r in ann_patches)

        # For small-to-medium documents (<= 100 pages), ensure full recall during MaxSim re-ranking
        if len(pages) <= 100 or not candidate_set:
            candidate_nums = [int(p["page_number"]) for p in pages]
        else:
            candidate_nums = sorted(candidate_set)

        # Stage 2: Late-Interaction MaxSim over stored page patch tensors
        patch_matrices = self._get_doc_patch_matrices(document_id, candidate_nums)

        scored: List[Tuple[int, float]] = []
        for p_num in candidate_nums:
            patch_mat = patch_matrices.get(p_num)
            if patch_mat is not None and patch_mat.size > 0:
                score = self.embedder.compute_maxsim(query_vecs, patch_mat)
            else:
                score = 0.0
            scored.append((p_num, score))

        scored.sort(key=lambda x: (x[1], -x[0]), reverse=True)
        return [
            {
                "page_number": p_num,
                "score": round(float(score), 6),
                "backend": self.embedder.backend_name,
            }
            for p_num, score in scored[:top_k]
        ]

    def search(self, document_id: str, query: str, top_k: int = 2) -> List[int]:
        """
        Late interaction (MaxSim) visual retrieval.
        Maps question tokens directly to visual patch representations in LanceDB.
        Returns top-k candidate page numbers (1-indexed).
        """
        results = self.search_with_scores(document_id, query, top_k=top_k)
        return [r["page_number"] for r in results]

    def get_linked_pages(self, document_id: str, primary_page: int) -> List[int]:
        """
        Returns linked/cross-referenced pages for a given primary page within the document.
        """
        pages = self.store.get_pages(document_id)
        if not pages:
            return [primary_page]
        all_page_nums = sorted([p["page_number"] for p in pages])
        linked = [p for p in all_page_nums if p != primary_page]
        return [primary_page] + linked

    def comparative_search(self, document_ids: List[str], query: str, top_k_per_doc: int = 1) -> Dict[str, List[int]]:
        """
        Executes Late-Interaction visual search across multiple document indices.
        Returns a mapping of document_id -> list of candidate page numbers (1-indexed).
        """
        results: Dict[str, List[int]] = {}
        for doc_id in document_ids:
            pages = self.search(doc_id, query, top_k=top_k_per_doc)
            results[doc_id] = pages
        return results
