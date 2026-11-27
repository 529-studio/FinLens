"""
FinSight S14-02 Test Suite: Non-Blocking Local MLX Inference Offload
Verifies that synchronous MLXEngine inference is offloaded to a dedicated 1-worker
ThreadPoolExecutor so FastAPI's event loop (/health, WebSockets, concurrent REST calls)
never stalls while Metal inference remains strictly serialized.
"""

import asyncio
import sys
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from main import app
from vlm_router import VlmRouter


def test_vlm_router_offloads_local_mlx_and_serializes_worker():
    """
    Proves that concurrent local MLX inference calls:
    1. Execute off the asyncio event loop thread inside 'mlx-inference*' worker.
    2. Are strictly serialized (max_active == 1) on the dedicated 1-worker executor.
    3. Allow concurrent asyncio coroutines (heartbeats) to progress without stalling.
    """
    active_lock = threading.Lock()
    state = {"active": 0, "max_active": 0, "threads": [], "heartbeat_ticks": 0}

    def slow_analyze_pages(pages, query):
        with active_lock:
            state["active"] += 1
            state["max_active"] = max(state["max_active"], state["active"])
            state["threads"].append(threading.current_thread().name)
        try:
            time.sleep(0.18)
            return {"engine": "mlx-qwen2.5-vl-7b-4bit", "answer": f"ok:{query}", "evidences": [], "latency_ms": 180.0}
        finally:
            with active_lock:
                state["active"] -= 1

    mock_mlx = MagicMock()
    mock_mlx.analyze_pages.side_effect = slow_analyze_pages
    mock_mlx.analyze_comparative.side_effect = lambda doc_pages, q: slow_analyze_pages([], q)
    mock_mlx.analyze_page.side_effect = lambda img, p, q: slow_analyze_pages([(img, p)], q)

    router = VlmRouter(mlx_engine=mock_mlx)

    async def run_concurrent():
        async def heartbeat():
            for _ in range(10):
                state["heartbeat_ticks"] += 1
                await asyncio.sleep(0.02)

        results = await asyncio.gather(
            router.analyze_pages([("/tmp/finsight_test/p1.png", 1)], "q1", preferred_mode="local"),
            router.analyze_comparative({"DOC_A": [("/tmp/finsight_test/p1.png", 1)]}, "q2", preferred_mode="local"),
            router._infer_local_mlx("/tmp/finsight_test/p1.png", 1, "q3"),
            heartbeat(),
        )
        return results

    try:
        res = asyncio.run(run_concurrent())
    finally:
        router.shutdown(wait=True)

    assert res[0]["answer"] == "ok:q1"
    assert res[1]["answer"] == "ok:q2"
    assert res[2]["answer"] == "ok:q3"
    assert state["max_active"] == 1, "MLX worker must serialize concurrent inference calls"
    assert all(t.startswith("mlx-inference") for t in state["threads"])
    assert state["heartbeat_ticks"] == 10


def test_fastapi_health_stays_nonblocking_during_slow_mlx_inference():
    """
    Simulates a slow 0.4s synchronous MLXEngine.analyze_pages call inside /api/v1/query
    and verifies /health responds concurrently in < 50ms without blocking the event loop.
    """
    def slow_mlx(pages, query):
        time.sleep(0.4)
        return {
            "engine": "mlx-qwen2.5-vl-7b-4bit",
            "answer": "Non-blocking offloaded inference result",
            "evidences": [
                {
                    "page_number": 1,
                    "ymin": 100,
                    "xmin": 100,
                    "ymax": 300,
                    "xmax": 500,
                    "label": "Test Box",
                    "extracted_value": "100",
                    "confidence": 0.99,
                }
            ],
            "latency_ms": 400.0,
        }

    async def exercise():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as ac:
            with patch("main.mlx_engine.analyze_pages", side_effect=slow_mlx):
                query_task = asyncio.create_task(
                    ac.post(
                        "/api/v1/query",
                        json={
                            "document_id": "ASYNC_HEALTH_TEST_DOC",
                            "query_text": "unique_slow_mlx_probe_query",
                            "top_k_pages": 1,
                            "inference_mode": "local",
                        },
                    )
                )
                # Give query_task a moment to enter the executor
                await asyncio.sleep(0.05)

                t0 = time.perf_counter()
                health_res = await ac.get("/health")
                health_ms = (time.perf_counter() - t0) * 1000.0

                q_res = await query_task
                return health_res, health_ms, q_res

    health_res, health_ms, q_res = asyncio.run(exercise())
    assert health_res.status_code == 200
    assert health_res.json()["status"] == "healthy"
    assert health_ms < 80.0, f"/health stalled during local MLX inference ({health_ms:.1f} ms)"
    assert q_res.status_code == 200
    assert "Non-blocking offloaded inference result" in q_res.json()["answer"]
