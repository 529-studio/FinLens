"""
FinSight S14-01 Test Suite: ColPali Multi-Vector Patch Embedding & LanceDB Vector Search
Verifies multi-vector patch generation, MaxSim late-interaction scoring, LanceDB persistence,
re-load across store instances, multi-page financial PDF retrieval, and path-traversal security.
"""

import sys
from pathlib import Path
import numpy as np
import pymupdf
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from renderer import PdfRenderer
from retriever import ColPaliPatchEmbedder, VisualRetriever, NUM_PATCHES
from store import LanceDBStore, StoreSecurityError, DEFAULT_VECTOR_DIM


@pytest.fixture
def sample_multipage_financial_pdf(tmp_path):
    """Generates a realistic 4-page financial PDF with distinct visual & semantic regions."""
    pdf_path = tmp_path / "REALISTIC_FIN_REPORT.pdf"
    doc = pymupdf.open()

    # Page 1: Executive overview + colored bar chart
    p1 = doc.new_page(width=595, height=842)
    p1.insert_text((50, 70), "FEDERAL FINANCIAL STABILITY SUMMARY", fontsize=15)
    p1.draw_rect(pymupdf.Rect(70, 180, 140, 420), color=(0.1, 0.3, 0.8), fill=(0.2, 0.45, 0.85))
    p1.draw_rect(pymupdf.Rect(180, 240, 250, 420), color=(0.8, 0.2, 0.2), fill=(0.85, 0.3, 0.25))
    p1.draw_rect(pymupdf.Rect(290, 200, 360, 420), color=(0.1, 0.6, 0.3), fill=(0.2, 0.7, 0.4))
    p1.insert_text((70, 460), "Chart 1: Asset Valuation and Equity Risk Premia Trend", fontsize=11)

    # Page 2: Commercial Real Estate & Bank Leverage
    p2 = doc.new_page(width=595, height=842)
    p2.insert_text((50, 70), "SECTION 2: COMMERCIAL REAL ESTATE VULNERABILITIES", fontsize=14)
    p2.insert_text((50, 120), "Commercial real estate office vacancy rates rose sharply across metropolitan markets.", fontsize=10)
    p2.insert_text((50, 145), "Regional bank exposure to multifamily and office mortgages requires close supervision.", fontsize=10)

    # Page 3: Treasury Market Liquidity & Hedge Fund Leverage Table
    p3 = doc.new_page(width=595, height=842)
    p3.insert_text((50, 70), "CONSOLIDATED BANKING BALANCE SHEET TABLE", fontsize=14)
    for row_idx in range(12):
        y = 110 + row_idx * 24
        p3.draw_line((50, y), (540, y))
        p3.insert_text((55, y + 16), f"Line {row_idx+1:02d}   Treasury Liquidity & Capital Tier 1   {1200 + row_idx * 45}", fontsize=9)
    p3.draw_line((50, 110), (50, 400))
    p3.draw_line((380, 110), (380, 400))
    p3.draw_line((540, 110), (540, 400))

    # Page 4: Footnote disclosures on household debt & inflation
    p4 = doc.new_page(width=595, height=842)
    p4.insert_text((50, 70), "FOOTNOTE DISCLOSURES AND APPENDIX", fontsize=14)
    p4.insert_text((50, 520), "Footnote 7: Household mortgage delinquency and consumer credit card balances.", fontsize=10)
    p4.insert_text((50, 545), "Interest rate sensitivity and core PCE inflation stress test assumptions.", fontsize=10)

    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


def test_patch_embedder_dimensions_and_maxsim(tmp_path, sample_multipage_financial_pdf):
    renderer = PdfRenderer(output_base_dir=str(tmp_path / "render_cache"))
    pages = renderer.render_document(str(sample_multipage_financial_pdf), "FIN_EMBED_TEST", dpi=100)
    assert len(pages) == 4

    embedder = ColPaliPatchEmbedder()
    embedded = embedder.embed_document_pages(pages)
    assert len(embedded) == 4

    for page_num, (patches, pooled) in embedded.items():
        assert patches.shape == (NUM_PATCHES, DEFAULT_VECTOR_DIM)
        assert pooled.shape == (DEFAULT_VECTOR_DIM,)
        # Verify L2 normalization on non-zero rows and pooled vector
        norms = np.linalg.norm(patches, axis=1)
        assert np.all((norms <= 1.0001) & (norms >= 0.9999))
        assert abs(float(np.linalg.norm(pooled)) - 1.0) < 1e-4

    q_vecs = embedder.embed_query("commercial real estate office vacancy regional bank")
    assert q_vecs.ndim == 2
    assert q_vecs.shape[1] == DEFAULT_VECTOR_DIM

    scores = {p: embedder.compute_maxsim(q_vecs, mat) for p, (mat, _) in embedded.items()}
    assert scores[2] > scores[1]
    assert scores[2] > scores[4]


def test_lancedb_patch_persistence_across_reconnect(tmp_path, sample_multipage_financial_pdf):
    cache_dir = tmp_path / "render_cache"
    db_dir = tmp_path / "lancedb"

    renderer = PdfRenderer(output_base_dir=str(cache_dir))
    pages = renderer.render_document(str(sample_multipage_financial_pdf), "PERSIST_DOC", dpi=100)

    store1 = LanceDBStore(db_dir=str(db_dir))
    ret1 = VisualRetriever(store=store1)
    count = ret1.index_document("PERSIST_DOC", pages)
    assert count == 4

    # Reload in a completely fresh store/retriever instance (no warm memory cache)
    store2 = LanceDBStore(db_dir=str(db_dir))
    patches = store2.get_page_patches("PERSIST_DOC")
    assert set(patches.keys()) == {1, 2, 3, 4}
    assert len(patches[1]) == NUM_PATCHES

    ret2 = VisualRetriever(store=store2)
    cre_hits = ret2.search_with_scores("PERSIST_DOC", "commercial real estate office vacancy", top_k=2)
    assert cre_hits[0]["page_number"] == 2
    assert cre_hits[0]["score"] > 0.0

    fn_hits = ret2.search_with_scores("PERSIST_DOC", "household mortgage delinquency consumer credit card", top_k=2)
    assert fn_hits[0]["page_number"] == 4

    chart_hits = ret2.search_with_scores("PERSIST_DOC", "bar chart asset valuation risk premia", top_k=2)
    assert chart_hits[0]["page_number"] == 1

    # Verify delete_document cleans up both document_pages and document_patches
    assert store2.delete_document("PERSIST_DOC") is True
    assert store2.get_pages("PERSIST_DOC") == []
    assert store2.get_page_patches("PERSIST_DOC") == {}


def test_retriever_and_store_security_boundaries(tmp_path):
    store = LanceDBStore(db_dir=str(tmp_path / "lancedb"))
    retriever = VisualRetriever(store=store)
    for bad_id in ["../../etc/passwd", "doc;drop", "doc\0null", "doc\nnewline"]:
        with pytest.raises(StoreSecurityError):
            retriever.search(bad_id, "financial query")
        with pytest.raises(StoreSecurityError):
            retriever.index_document(bad_id, [])
        with pytest.raises(StoreSecurityError):
            store.get_page_patches(bad_id)
        with pytest.raises(StoreSecurityError):
            store.search_patches(bad_id, [0.1] * DEFAULT_VECTOR_DIM)

    # Unsafe image_path must be rejected before filesystem access
    with pytest.raises(StoreSecurityError, match="escapes authorized boundaries"):
        retriever.index_document("SAFE_DOC", [(1, Path("/etc/passwd"), 100, 100)])


def test_retriever_edge_cases_and_cache_invalidation(tmp_path):
    store = LanceDBStore(db_dir=str(tmp_path / "lancedb"))
    retriever = VisualRetriever(store=store)

    # 1. Empty document indexing and unindexed search
    assert retriever.index_document("EMPTY_DOC", []) == 0
    unindexed = retriever.search_with_scores("UNINDEXED_DOC", "any query")
    assert unindexed[0]["page_number"] == 1
    assert unindexed[0]["score"] == 0.0
    assert store.get_page_patches("MISSING_DOC") == {}
    assert store.get_page_patches("MISSING_DOC", page_numbers=[]) == {}

    # 2. Missing/corrupt image paths fall back deterministically without crashing
    missing_img = tmp_path / "nonexistent_page_1.png"
    corrupt_img = tmp_path / "corrupt_page_2.png"
    corrupt_img.write_text("not a valid png")
    count = retriever.index_document("SYNTH_DOC", [
        (1, missing_img, 100, 100),
        (2, corrupt_img, 100, 100),
    ])
    assert count == 2
    assert len(store.get_page_patches("SYNTH_DOC", page_numbers=[])) == 0
    assert set(store.get_page_patches("SYNTH_DOC").keys()) == {1, 2}

    # 3. Cache epoch invalidation when store.clear_memory_cache() or delete_document() is called
    assert "SYNTH_DOC" in retriever._np_patch_cache
    store.clear_memory_cache()
    assert len(retriever.search("SYNTH_DOC", "query", top_k=2)) == 2
    # Epoch mismatch evicted stale cache and reloaded cleanly
    assert retriever._np_patch_cache["SYNTH_DOC"][0] == store._cache_epoch

    assert store.delete_document("SYNTH_DOC") is True
    # Searching after store.delete_document must not return stale cached pages
    assert retriever.search("SYNTH_DOC", "query", top_k=2) == [1]
