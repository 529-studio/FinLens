"""
FinSight PDF Page Renderer Module
Converts high-resolution PDF pages into normalized PNG images (150-200 DPI)
for ColPali visual patch indexing and VLM visual grounding.
Optimized for multi-core parallel rendering and persistent disk caching.
Governed by ADR-001, Sprint 1 Issue #3, Sprint 6 Issue #36, and 529 Engineering Standards.
"""

import os
import json
import hashlib
import logging
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional
import concurrent.futures
import pymupdf  # Modern PyMuPDF 2.x API

from contracts import is_path_safe

logger = logging.getLogger("finsight.renderer")


def _render_single_page_worker(
    pdf_path_str: str,
    page_idx: int,
    target_img_str: str,
    zoom: float
) -> Dict[str, Any]:
    """
    Independent worker rendering a single PDF page into PNG.
    Guarantees thread safety by opening an independent PyMuPDF document handle per thread.
    """
    doc = pymupdf.open(pdf_path_str)
    try:
        page = doc.load_page(page_idx)
        mat = pymupdf.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        pix.save(target_img_str)

        # Compute deterministic visual signature for fast indexing
        img_bytes = pix.tobytes("png")
        sig = hashlib.sha256(img_bytes).hexdigest()[:16]

        return {
            "page_number": page_idx + 1,
            "image_path": target_img_str,
            "width": pix.width,
            "height": pix.height,
            "signature": sig,
        }
    finally:
        doc.close()


class PdfRenderer:
    def __init__(
        self,
        output_base_dir: str = "~/.finsight/cache/rendered_pages",
        max_workers: Optional[int] = None
    ):
        self.output_base_dir = Path(os.path.expanduser(output_base_dir)).resolve()
        if not is_path_safe(str(self.output_base_dir)):
            raise ValueError(f"Access denied: output_base_dir '{self.output_base_dir}' escapes authorized boundaries")
        self.output_base_dir.mkdir(parents=True, exist_ok=True)
        self.max_workers = max_workers or min(os.cpu_count() or 4, 8)
        self.last_render_from_cache: bool = False

    def _get_file_metadata(self, resolved_pdf: Path) -> Dict[str, Any]:
        """Extracts file size and mtime for fast cache validation."""
        stat = resolved_pdf.stat()
        return {
            "file_size": stat.st_size,
            "file_mtime": stat.st_mtime,
        }

    def _read_manifest(self, manifest_file: Path) -> Optional[Dict[str, Any]]:
        """Safely loads manifest JSON if valid."""
        if not manifest_file.exists():
            return None
        try:
            with open(manifest_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning("Corrupt or invalid manifest at %s: %s", manifest_file, e)
            return None

    def _write_manifest(self, manifest_file: Path, data: Dict[str, Any]) -> None:
        """Atomically writes manifest JSON."""
        tmp_file = manifest_file.with_suffix(".tmp")
        try:
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            tmp_file.replace(manifest_file)
        except Exception as e:
            logger.error("Failed to write manifest %s: %s", manifest_file, e)
            if tmp_file.exists():
                tmp_file.unlink(missing_ok=True)

    def is_cached(self, pdf_path: str, document_id: str, dpi: int = 150) -> bool:
        """Checks if a valid, complete rendered cache exists on disk."""
        resolved_pdf = Path(os.path.expanduser(pdf_path)).resolve()
        if not resolved_pdf.exists():
            return False

        doc_dir = self.output_base_dir / document_id
        manifest_file = doc_dir / "manifest.json"
        manifest = self._read_manifest(manifest_file)
        if not manifest:
            return False

        meta = self._get_file_metadata(resolved_pdf)
        if (
            manifest.get("file_size") != meta["file_size"]
            or manifest.get("file_mtime") != meta["file_mtime"]
            or manifest.get("dpi") != dpi
        ):
            return False

        # Verify all cached page images physically exist on disk
        for page_info in manifest.get("pages", []):
            img_p = Path(page_info["image_path"])
            if not img_p.exists() or img_p.stat().st_size == 0:
                return False

        return True

    def render_document(
        self,
        pdf_path: str,
        document_id: str,
        dpi: int = 150,
        force_rerender: bool = False
    ) -> List[Tuple[int, Path, int, int]]:
        """
        Renders every page of a PDF file to high-quality PNG.
        Uses parallel multi-core rendering and fast disk caching.
        Returns a list of tuples: (page_number, image_path, width_px, height_px).
        """
        resolved_pdf = Path(os.path.expanduser(pdf_path)).resolve()
        if not resolved_pdf.exists():
            raise FileNotFoundError(f"PDF file not found: {resolved_pdf}")

        if not is_path_safe(str(resolved_pdf)):
            raise ValueError(f"Access denied: PDF path '{resolved_pdf}' escapes authorized boundaries")

        doc_dir = self.output_base_dir / document_id
        doc_dir.mkdir(parents=True, exist_ok=True)
        manifest_file = doc_dir / "manifest.json"

        # Check local disk cache
        if not force_rerender and self.is_cached(str(resolved_pdf), document_id, dpi):
            manifest = self._read_manifest(manifest_file)
            if manifest and "pages" in manifest:
                logger.info("Cache hit for document '%s' at %d DPI", document_id, dpi)
                self.last_render_from_cache = True
                results = [
                    (p["page_number"], Path(p["image_path"]), p["width"], p["height"])
                    for p in manifest["pages"]
                ]
                results.sort(key=lambda x: x[0])
                return results

        self.last_render_from_cache = False
        doc = pymupdf.open(resolved_pdf)
        total_pages = len(doc)
        doc.close()

        zoom = dpi / 72.0
        workers = min(self.max_workers, max(1, total_pages))

        rendered_pages: List[Dict[str, Any]] = []

        if total_pages <= 1 or workers <= 1:
            # Single-page fast path
            for page_idx in range(total_pages):
                page_res = _render_single_page_worker(
                    str(resolved_pdf),
                    page_idx,
                    str(doc_dir / f"page_{page_idx + 1:04d}.png"),
                    zoom
                )
                rendered_pages.append(page_res)
        else:
            # Multi-core parallel rendering
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
                futures = [
                    executor.submit(
                        _render_single_page_worker,
                        str(resolved_pdf),
                        page_idx,
                        str(doc_dir / f"page_{page_idx + 1:04d}.png"),
                        zoom
                    )
                    for page_idx in range(total_pages)
                ]
                for future in concurrent.futures.as_completed(futures):
                    rendered_pages.append(future.result())

        # Always sort strictly by page_number
        rendered_pages.sort(key=lambda x: x["page_number"])

        # Persist manifest for instant subsequent retrieval
        meta = self._get_file_metadata(resolved_pdf)
        manifest_data = {
            "document_id": document_id,
            "pdf_path": str(resolved_pdf),
            "file_size": meta["file_size"],
            "file_mtime": meta["file_mtime"],
            "dpi": dpi,
            "total_pages": total_pages,
            "pages": rendered_pages,
        }
        self._write_manifest(manifest_file, manifest_data)

        return [
            (p["page_number"], Path(p["image_path"]), p["width"], p["height"])
            for p in rendered_pages
        ]
