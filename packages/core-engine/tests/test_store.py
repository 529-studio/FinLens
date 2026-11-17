"""
Tests for LanceDBStore (packages/core-engine/src/store.py)
Governed by PRD §2, ADR-001, and AGENTS.md Rule 13 (Security & Injection Defense).
"""

import pytest
from pathlib import Path
from store import (
    LanceDBStore,
    DEFAULT_LANCEDB_DIR,
    StoreSecurityError,
)


@pytest.fixture
def temp_store_dir(tmp_path):
    store_dir = tmp_path / "lancedb_test"
    store_dir.mkdir(parents=True, exist_ok=True)
    return store_dir


def test_store_init_default():
    store = LanceDBStore()
    assert store.db_dir == Path(DEFAULT_LANCEDB_DIR).expanduser().resolve()
    assert store.vector_dim == 128


def test_store_init_custom_dir(temp_store_dir):
    store = LanceDBStore(db_dir=temp_store_dir)
    assert store.db_dir == temp_store_dir


def test_store_path_traversal_db_dir_rejected():
    with pytest.raises(StoreSecurityError, match="escapes authorized boundaries"):
        LanceDBStore(db_dir="../../../etc/passwd")


def test_store_path_traversal_doc_id_rejected(temp_store_dir):
    store = LanceDBStore(db_dir=temp_store_dir)
    bad_doc_ids = ["../../escape", "doc;rm", "doc\0null", "invalid/slash"]
    for bad_id in bad_doc_ids:
        with pytest.raises(StoreSecurityError):
            store.get_pages(bad_id)
        with pytest.raises(StoreSecurityError):
            store.delete_document(bad_id)


def test_store_upsert_and_get_pages(temp_store_dir):
    store = LanceDBStore(db_dir=temp_store_dir)
    doc_id = "VNM_2023_STORE_TEST"

    # Dummy 128-dimensional vector
    dummy_vec1 = [0.1] * 128
    dummy_vec2 = [0.2] * 128

    pages = [
        {
            "page_number": 1,
            "image_path": "/tmp/finsight_test/page_1.png",
            "width": 1240,
            "height": 1755,
            "signature": "hash_page_1",
            "vector": dummy_vec1,
            "metadata": {"title": "Biểu đồ doanh thu"},
        },
        {
            "page_number": 2,
            "image_path": "/tmp/finsight_test/page_2.png",
            "width": 1240,
            "height": 1755,
            "signature": "hash_page_2",
            "vector": dummy_vec2,
            "metadata": {"title": "Thuyết minh số 4"},
        },
    ]

    count = store.upsert_pages(doc_id, pages)
    assert count == 2

    # Retrieve pages
    retrieved = store.get_pages(doc_id)
    assert len(retrieved) == 2
    assert retrieved[0]["page_number"] == 1
    assert retrieved[0]["signature"] == "hash_page_1"
    assert retrieved[1]["page_number"] == 2


def test_store_persistence_across_reconnect(temp_store_dir):
    store1 = LanceDBStore(db_dir=temp_store_dir)
    doc_id = "VNM_PERSIST_TEST"
    pages = [
        {
            "page_number": 1,
            "image_path": "/tmp/finsight_test/persist_1.png",
            "width": 1240,
            "height": 1755,
            "signature": "sig_persist",
            "vector": [0.05] * 128,
            "metadata": {"note": "persistent"},
        }
    ]
    store1.upsert_pages(doc_id, pages)

    # Reconnect with a new instance pointing to same directory
    store2 = LanceDBStore(db_dir=temp_store_dir)
    retrieved = store2.get_pages(doc_id)
    assert len(retrieved) == 1
    assert retrieved[0]["signature"] == "sig_persist"


def test_store_idempotent_upsert(temp_store_dir):
    store = LanceDBStore(db_dir=temp_store_dir)
    doc_id = "VNM_IDEMPOTENT"
    pages = [
        {
            "page_number": 1,
            "image_path": "/tmp/finsight_test/p1.png",
            "width": 1000,
            "height": 1000,
            "signature": "sig_v1",
            "vector": [0.1] * 128,
        }
    ]
    store.upsert_pages(doc_id, pages)

    # Re-upsert updated version of page 1
    updated_pages = [
        {
            "page_number": 1,
            "image_path": "/tmp/finsight_test/p1.png",
            "width": 1000,
            "height": 1000,
            "signature": "sig_v2",
            "vector": [0.1] * 128,
        }
    ]
    store.upsert_pages(doc_id, updated_pages)

    retrieved = store.get_pages(doc_id)
    assert len(retrieved) == 1
    assert retrieved[0]["signature"] == "sig_v2"


def test_store_vector_search(temp_store_dir):
    store = LanceDBStore(db_dir=temp_store_dir)
    doc_id = "VNM_SEARCH_TEST"

    # Distinct vectors for page 1 and page 2
    vec1 = [1.0] * 64 + [0.0] * 64
    vec2 = [0.0] * 64 + [1.0] * 64

    store.upsert_pages(doc_id, [
        {"page_number": 1, "image_path": "p1.png", "width": 100, "height": 100, "signature": "s1", "vector": vec1},
        {"page_number": 2, "image_path": "p2.png", "width": 100, "height": 100, "signature": "s2", "vector": vec2},
    ])

    # Search with vector close to page 1
    query_vec = [0.9] * 64 + [0.1] * 64
    results = store.search(doc_id, query_vec, top_k=1)
    assert len(results) == 1
    assert results[0]["page_number"] == 1


def test_store_list_and_delete_documents(temp_store_dir):
    store = LanceDBStore(db_dir=temp_store_dir)
    store.upsert_pages("DOC_A", [{"page_number": 1, "image_path": "a.png", "width": 10, "height": 10, "signature": "a", "vector": [0.1]*128}])
    store.upsert_pages("DOC_B", [{"page_number": 1, "image_path": "b.png", "width": 10, "height": 10, "signature": "b", "vector": [0.2]*128}])

    docs = store.list_documents()
    assert "DOC_A" in docs
    assert "DOC_B" in docs

    # Delete DOC_A
    deleted = store.delete_document("DOC_A")
    assert deleted is True

    docs_after = store.list_documents()
    assert "DOC_A" not in docs_after
    assert "DOC_B" in docs_after
    assert store.get_pages("DOC_A") == []


def test_store_get_stats(temp_store_dir):
    store = LanceDBStore(db_dir=temp_store_dir)
    store.upsert_pages("DOC_STATS", [
        {"page_number": 1, "image_path": "p1.png", "width": 10, "height": 10, "signature": "s1", "vector": [0.1]*128},
        {"page_number": 2, "image_path": "p2.png", "width": 10, "height": 10, "signature": "s2", "vector": [0.2]*128},
    ])

    stats = store.get_stats()
    assert stats["total_documents"] >= 1
    assert stats["total_pages"] >= 2
    assert stats["disk_size_bytes"] >= 0
    assert "db_path" in stats
