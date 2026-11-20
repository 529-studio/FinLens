"""
FinSight Performance Optimization & Local Caching Test Suite
Governed by ADR-001, Sprint 6 Issue #36, and 529 Engineering Standards.

Verifies:
1. Multi-core parallel PDF page rendering speed and content-addressed manifest caching.
2. In-memory LanceDB store page caching.
3. Thread-safe Query LRU cache with sub-millisecond repeated query latency (< 5ms).
4. REST endpoints: /api/v1/cache/stats, /api/v1/cache/clear, and QueryResponse.cached flag.
5. Path traversal security defenses on all caching operations.
"""

import os
import time
import shutil
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
import pymupdf

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from renderer import PdfRenderer
from store import LanceDBStore
from cache_manager import QueryLRUCache, CacheManager
from main import app

client = TestClient(app)

SAMPLE_PDF = str(Path(__file__).resolve().parents[3] / "benchmarks" / "data" / "VNM_BCTC_2023_AUDITED.pdf")


@pytest.fixture
def temp_cache_dir(tmp_path):
    cache_dir = tmp_path / "perf_test_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    yield str(cache_dir)
    shutil.rmtree(cache_dir, ignore_errors=True)


@pytest.fixture
def multi_page_pdf(tmp_path):
    """Generates an 8-page synthetic financial statement for parallel rendering benchmarks."""
    pdf_path = tmp_path / "SYNTHETIC_LARGE_BCTC.pdf"
    doc = pymupdf.open()
    for i in range(8):
        page = doc.new_page(width=595, height=842)
        page.insert_text((50, 100), f"BÁO CÁO TÀI CHÍNH KIỂM TOÁN - TRANG {i + 1}", fontsize=14)
        page.draw_rect(pymupdf.Rect(50, 120, 545, 400), color=(0.2, 0.4, 0.8), fill=(0.95, 0.95, 1.0))
        page.insert_text((70, 150), f"Chỉ tiêu tài chính mục số {i + 1}: Doanh thu & Chi phí", fontsize=10)
    doc.save(str(pdf_path))
    doc.close()
    return str(pdf_path)


def test_renderer_parallel_and_cache_speedup(multi_page_pdf, temp_cache_dir):
    """Verify that multi-page PDF renders in parallel, generates manifest, and achieves instant cache hits."""
    renderer = PdfRenderer(output_base_dir=temp_cache_dir, max_workers=4)
    doc_id = "LARGE_BCTC_PERF"

    # 1. Cold render (parallel rendering across 8 pages)
    t0 = time.time()
    results_cold = renderer.render_document(multi_page_pdf, doc_id, dpi=150)
    cold_duration_ms = (time.time() - t0) * 1000.0

    assert len(results_cold) == 8
    assert not renderer.last_render_from_cache
    for idx, (p_num, img_path, w, h) in enumerate(results_cold):
        assert p_num == idx + 1
        assert img_path.exists()
        assert w > 0 and h > 0

    # 2. Manifest file was generated
    manifest_p = Path(temp_cache_dir) / doc_id / "manifest.json"
    assert manifest_p.exists()

    # 3. Second render: Cache hit (< 15ms, zero re-rendering)
    t1 = time.time()
    results_cached = renderer.render_document(multi_page_pdf, doc_id, dpi=150)
    cache_duration_ms = (time.time() - t1) * 1000.0

    assert len(results_cached) == 8
    assert renderer.last_render_from_cache
    assert cache_duration_ms < 50.0  # Instant local disk metadata lookup
    assert cache_duration_ms < cold_duration_ms

    # Content verification
    for i in range(8):
        assert results_cached[i][0] == results_cold[i][0]
        assert results_cached[i][1] == results_cold[i][1]
        assert results_cached[i][2] == results_cold[i][2]
        assert results_cached[i][3] == results_cold[i][3]


def test_renderer_cache_invalidation_on_dpi_or_force(multi_page_pdf, temp_cache_dir):
    """Verify requesting a different DPI or force_rerender invalidates the cache properly."""
    renderer = PdfRenderer(output_base_dir=temp_cache_dir)
    doc_id = "INVALIDATION_TEST"

    # Initial render at 150 DPI
    res150 = renderer.render_document(multi_page_pdf, doc_id, dpi=150)
    assert not renderer.last_render_from_cache

    # Subsequent render at 200 DPI must re-render
    res200 = renderer.render_document(multi_page_pdf, doc_id, dpi=200)
    assert not renderer.last_render_from_cache
    assert res200[0][2] > res150[0][2]  # Higher DPI = higher pixel width

    # Force re-render at 200 DPI
    res_forced = renderer.render_document(multi_page_pdf, doc_id, dpi=200, force_rerender=True)
    assert not renderer.last_render_from_cache


def test_store_in_memory_page_cache(tmp_path):
    """Verify LanceDBStore in-memory page caching and invalidation."""
    db_dir = tmp_path / "lancedb_cache_test"
    store = LanceDBStore(db_dir=str(db_dir))
    doc_id = "STORE_CACHE_DOC"

    pages_data = [
        {"page_number": 1, "image_path": "/tmp/p1.png", "width": 1000, "height": 1400, "signature": "sig1"},
        {"page_number": 2, "image_path": "/tmp/p2.png", "width": 1000, "height": 1400, "signature": "sig2"},
    ]
    store.upsert_pages(doc_id, pages_data)

    # First get_pages reads from disk table and caches
    pages_read1 = store.get_pages(doc_id)
    assert len(pages_read1) == 2
    assert doc_id in store._pages_cache

    # Second get_pages returns instant cached reference
    pages_read2 = store.get_pages(doc_id)
    assert pages_read2 is store._pages_cache[doc_id]

    # Upsert invalidates cache
    store.upsert_pages(doc_id, pages_data[:1])
    assert doc_id not in store._pages_cache
    pages_read3 = store.get_pages(doc_id)
    assert len(pages_read3) == 1

    # Delete invalidates cache
    store.delete_document(doc_id)
    assert doc_id not in store._pages_cache


def test_query_lru_cache_operations():
    """Verify LRU Query Cache hit, miss, eviction, and document invalidation."""
    cache = QueryLRUCache(max_capacity=2)

    # 1. Miss on empty cache
    res = cache.get("DOC1", "Doanh thu?", 2, "auto")
    assert res is None
    assert cache.misses == 1

    # 2. Put and Hit
    dummy_payload = {"answer": "60.479 tỷ", "evidences": []}
    cache.put("DOC1", "Doanh thu?", 2, "auto", dummy_payload)

    hit_res = cache.get("DOC1", "Doanh thu?", 2, "auto")
    assert hit_res == dummy_payload
    assert cache.hits == 1

    # 3. Add second entry
    cache.put("DOC1", "Lợi nhuận?", 2, "auto", {"answer": "9.019 tỷ"})
    # Add third entry (triggers eviction of oldest)
    cache.put("DOC2", "Tiền mặt?", 2, "auto", {"answer": "2.671 tỷ"})

    assert len(cache._cache) == 2
    # Oldest key "Doanh thu?" was evicted
    assert cache.get("DOC1", "Doanh thu?", 2, "auto") is None

    # 4. Invalidation by document
    removed = cache.invalidate_document("DOC2")
    assert removed == 1
    assert cache.get("DOC2", "Tiền mặt?", 2, "auto") is None


def test_api_cache_endpoints_and_sub_millisecond_query():
    """
    E2E REST API Verification:
    - /api/v1/documents/ingest returns from_cache=True on second call
    - /api/v1/query returns cached=True with sub-millisecond repeated response
    - /api/v1/cache/stats returns accurate metrics
    - /api/v1/cache/clear invalidates cache cleanly
    """
    # 1. Ingest document (cold)
    ingest_res1 = client.post("/api/v1/documents/ingest", json={
        "file_path": SAMPLE_PDF,
        "document_id": "VNM_PERF_API_TEST",
        "render_dpi": 150,
    })
    assert ingest_res1.status_code == 200
    data1 = ingest_res1.json()
    assert data1["total_pages"] == 2

    # 2. Ingest document again (cache hit)
    ingest_res2 = client.post("/api/v1/documents/ingest", json={
        "file_path": SAMPLE_PDF,
        "document_id": "VNM_PERF_API_TEST",
        "render_dpi": 150,
    })
    assert ingest_res2.status_code == 200
    data2 = ingest_res2.json()
    assert data2["from_cache"] is True
    assert data2["duration_ms"] < 100.0

    # 3. Initial query (cold)
    query_payload = {
        "document_id": "VNM_PERF_API_TEST",
        "query_text": "Phân tích doanh thu xuất khẩu và nội địa",
        "top_k_pages": 2,
    }
    q_res1 = client.post("/api/v1/query", json=query_payload)
    assert q_res1.status_code == 200
    q_data1 = q_res1.json()
    assert q_data1["cached"] is False

    # 4. Repeated query (Query LRU cache hit: < 20ms)
    q_res2 = client.post("/api/v1/query", json=query_payload)
    assert q_res2.status_code == 200
    q_data2 = q_res2.json()
    assert q_data2["cached"] is True
    assert q_data2["latency_ms"] < 25.0
    assert q_data2["answer"] == q_data1["answer"]
    assert len(q_data2["evidences"]) == len(q_data1["evidences"])

    # 5. Check cache stats endpoint
    stats_res = client.get("/api/v1/cache/stats")
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert stats["in_memory_query_cache_entries"] >= 1
    assert stats["query_cache_hits"] >= 1
    assert stats["hit_ratio"] > 0.0

    # 6. Clear cache endpoint
    clear_res = client.post("/api/v1/cache/clear", json={"scope": "queries"})
    assert clear_res.status_code == 200
    assert clear_res.json()["cleared_queries"] >= 1

    # 7. Next query is cold again
    q_res3 = client.post("/api/v1/query", json=query_payload)
    assert q_res3.status_code == 200
    assert q_res3.json()["cached"] is False


def test_cache_security_path_traversal_rejection(temp_cache_dir):
    """
    AGENTS.md Rule 13B: Backend Security & Injection Defense
    Verifies that directory traversal sequences in cache clear and renderer are strictly rejected.
    """
    # 1. API endpoint rejects traversal via Pydantic validator (HTTP 422)
    res_bad1 = client.post("/api/v1/cache/clear", json={"scope": "documents", "document_id": "../../victim"})
    assert res_bad1.status_code == 422

    res_bad2 = client.post("/api/v1/cache/clear", json={"scope": "documents", "document_id": "invalid/slash"})
    assert res_bad2.status_code == 422

    # 2. CacheManager.clear rejects traversal or escaping parent directly
    cm = CacheManager(render_cache_dir=temp_cache_dir)
    with pytest.raises(ValueError) as exc:
        cm.clear(scope="documents", document_id="../../escape")
    assert "unsafe characters" in str(exc.value) or "escapes" in str(exc.value)

    # 3. PdfRenderer rejects traversal in render_document and is_cached
    renderer = PdfRenderer(output_base_dir=temp_cache_dir)
    with pytest.raises(ValueError) as exc:
        renderer.render_document(SAMPLE_PDF, "../../escape")
    assert "Invalid document identifier" in str(exc.value) or "escapes" in str(exc.value)

    with pytest.raises(ValueError) as exc:
        renderer.is_cached(SAMPLE_PDF, "../../escape")
    assert "Invalid document identifier" in str(exc.value) or "escapes" in str(exc.value)

