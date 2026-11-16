"""
FinSight PDF Page Renderer Module
Converts high-resolution PDF pages into normalized PNG images (150-200 DPI)
for ColPali visual patch indexing and VLM input.
"""

import os
from pathlib import Path
from typing import List, Tuple
import fitz  # PyMuPDF


class PdfRenderer:
    def __init__(self, output_base_dir: str = "~/.finsight/cache/rendered_pages"):
        self.output_base_dir = Path(os.path.expanduser(output_base_dir)).resolve()
        self.output_base_dir.mkdir(parents=True, exist_ok=True)

    def render_document(self, pdf_path: str, document_id: str, dpi: int = 150) -> List[Tuple[int, Path, int, int]]:
        """
        Renders every page of a PDF file to high-quality PNG.
        Returns a list of tuples: (page_number, image_path, width_px, height_px).
        """
        resolved_pdf = Path(os.path.expanduser(pdf_path)).resolve()
        if not resolved_pdf.exists():
            raise FileNotFoundError(f"PDF file not found: {resolved_pdf}")

        doc_dir = self.output_base_dir / document_id
        doc_dir.mkdir(parents=True, exist_ok=True)

        doc = fitz.open(resolved_pdf)
        results = []

        # PyMuPDF default resolution is 72 DPI; zoom factor = target_dpi / 72
        zoom = dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)

        for page_idx in range(len(doc)):
            page_num = page_idx + 1
            page = doc.load_page(page_idx)
            pix = page.get_pixmap(matrix=mat, alpha=False)

            image_filename = f"page_{page_num:04d}.png"
            image_path = doc_dir / image_filename
            pix.save(str(image_path))

            results.append((page_num, image_path, pix.width, pix.height))

        doc.close()
        return results
