"""
TDD Suite for FinSight PDF Page Renderer Module
Tests PyMuPDF page rendering, DPI scaling math, file integrity, and error paths.
Governed by Sprint 1 Issue #3 & 529 Engineering Standards.
"""

import os
import shutil
import pytest
from pathlib import Path
from PIL import Image

# Import under test
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from renderer import PdfRenderer


@pytest.fixture
def sample_pdf_path():
    repo_root = Path(__file__).resolve().parents[3]
    pdf_path = repo_root / "benchmarks" / "data" / "VNM_BCTC_2023_AUDITED.pdf"
    assert pdf_path.exists(), f"Fixture PDF missing at {pdf_path}"
    return str(pdf_path)


@pytest.fixture
def temp_cache_dir(tmp_path):
    cache_dir = tmp_path / "test_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    yield str(cache_dir)
    shutil.rmtree(cache_dir, ignore_errors=True)


def test_renderer_renders_correct_pages_and_dpi(sample_pdf_path, temp_cache_dir):
    """Verify that every page is rendered to PNG at target 150 DPI with accurate dimensions."""
    renderer = PdfRenderer(output_base_dir=temp_cache_dir)
    doc_id = "VNM_2023_TEST"

    results = renderer.render_document(sample_pdf_path, doc_id, dpi=150)

    # VNM sample PDF has 2 pages
    assert len(results) == 2

    # Check Page 1
    page1_num, page1_path, page1_w, page1_h = results[0]
    assert page1_num == 1
    assert page1_path.exists()
    assert page1_path.name == "page_0001.png"

    # A4 standard at 150 DPI: round(595 * 150 / 72) = 1240 px, round(842 * 150 / 72) = 1754 px
    assert abs(page1_w - 1240) <= 2
    assert abs(page1_h - 1754) <= 2

    # Check PIL can open and verify image mode
    with Image.open(page1_path) as img:
        assert img.format == "PNG"
        assert img.size == (page1_w, page1_h)

    # Check Page 2
    page2_num, page2_path, page2_w, page2_h = results[1]
    assert page2_num == 2
    assert page2_path.exists()
    assert page2_path.name == "page_0002.png"


def test_renderer_high_dpi_200(sample_pdf_path, temp_cache_dir):
    """Verify 200 DPI produces proportionally higher resolution images."""
    renderer = PdfRenderer(output_base_dir=temp_cache_dir)
    results = renderer.render_document(sample_pdf_path, "VNM_200DPI", dpi=200)

    # At 200 DPI: round(595 * 200 / 72) = 1653 px, round(842 * 200 / 72) = 2339 px
    _, _, w_200, h_200 = results[0]
    assert abs(w_200 - 1653) <= 2
    assert abs(h_200 - 2339) <= 2


def test_renderer_fails_cleanly_on_missing_file(temp_cache_dir):
    """Verify FileNotFoundError is raised with descriptive error message."""
    renderer = PdfRenderer(output_base_dir=temp_cache_dir)
    with pytest.raises(FileNotFoundError) as exc_info:
        renderer.render_document("/path/to/nonexistent/file.pdf", "MISSING_DOC")
    assert "PDF file not found" in str(exc_info.value)
