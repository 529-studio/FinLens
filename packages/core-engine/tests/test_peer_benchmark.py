"""
Unit and API Integration Tests for Cross-Sectional Peer Benchmarking Engine (S13-04)
"""

import sys
from pathlib import Path
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from main import app
from peer_benchmark import PeerBenchmarkEngine, linear_percentile
from contracts import (
    BenchmarkWeightingMode,
    MetricBenchmarkConfig,
    PeerBenchmarkRequest,
    PeerCompanyMetric,
    PeerQuartileStanding,
)

client = TestClient(app)


def _sample_peers():
    return [
        PeerCompanyMetric(
            company_id="PEER_A",
            company_name="Peer A Dairy",
            market_cap=1000.0,
            metrics={"gross_margin": 30.0, "roe": 12.0, "debt_to_equity": 1.2},
        ),
        PeerCompanyMetric(
            company_id="PEER_B",
            company_name="Peer B Foods",
            market_cap=2000.0,
            metrics={"gross_margin": 35.0, "roe": 18.0, "debt_to_equity": 0.8},
        ),
        PeerCompanyMetric(
            company_id="PEER_C",
            company_name="Peer C Beverage",
            market_cap=5000.0,
            metrics={"gross_margin": 45.0, "roe": 25.0, "debt_to_equity": 0.4},
        ),
        PeerCompanyMetric(
            company_id="PEER_D",
            company_name="Peer D Nutrition",
            market_cap=2000.0,
            metrics={"gross_margin": 38.0, "roe": 20.0, "debt_to_equity": 0.6},
        ),
    ]


def test_equal_vs_market_cap_weighting_and_percentiles():
    engine = PeerBenchmarkEngine()
    peers = _sample_peers()

    req_eq = PeerBenchmarkRequest(
        sector_name="F&B / Dairy",
        target_company_id="VNM",
        target_company_name="Vinamilk",
        target_document_id="VNM_BCTC_2023_AUDITED",
        target_metrics={"gross_margin": 40.7, "debt_to_equity": 0.35},
        peers=peers,
        weighting_mode=BenchmarkWeightingMode.EQUAL,
    )
    res_eq = engine.evaluate(req_eq)
    assert res_eq.peer_count_evaluated == 4

    gm = next(r for r in res_eq.results if r.metric_code == "gross_margin")
    # Equal mean = (30 + 35 + 45 + 38)/4 = 37.0
    assert gm.equal_weighted_mean == 37.0
    # Market-cap mean = (30*1000 + 35*2000 + 45*5000 + 38*2000) / 10000 = 40.1
    assert gm.market_cap_weighted_mean == 40.1
    assert gm.active_sector_mean == 37.0
    assert gm.p50 == linear_percentile([30.0, 35.0, 38.0, 45.0], 0.50)
    assert gm.standing == PeerQuartileStanding.TOP_QUARTILE

    # Leverage polarity: lower debt_to_equity (0.35 < all peers) should be TOP_QUARTILE
    de = next(r for r in res_eq.results if r.metric_code == "debt_to_equity")
    assert de.higher_is_better is False
    assert de.percentile_rank == 100.0
    assert de.standing == PeerQuartileStanding.TOP_QUARTILE
    assert de.z_score > 0

    req_mcap = req_eq.model_copy(update={"weighting_mode": BenchmarkWeightingMode.MARKET_CAP})
    res_mcap = engine.evaluate(req_mcap)
    gm_mcap = next(r for r in res_mcap.results if r.metric_code == "gross_margin")
    assert gm_mcap.active_sector_mean == 40.1


def test_edge_cases_empty_peers_zero_stddev_and_target_exclusion():
    engine = PeerBenchmarkEngine()

    # 1. Empty peers
    res_empty = engine.evaluate(
        PeerBenchmarkRequest(
            sector_name="Dairy",
            target_company_id="VNM",
            target_company_name="Vinamilk",
            target_metrics={"gross_margin": 40.7},
            peers=[],
        )
    )
    assert res_empty.peer_count_evaluated == 0
    assert res_empty.results[0].standing == PeerQuartileStanding.INSUFFICIENT_DATA
    assert res_empty.composite_percentile_score is None

    # 2. Zero standard deviation + target accidentally included in peers + zero market_cap fallback
    peers = [
        PeerCompanyMetric(company_id="VNM", company_name="Vinamilk", market_cap=0.0, metrics={"roe": 99.0}),
        PeerCompanyMetric(company_id="P1", company_name="P1", market_cap=0.0, metrics={"roe": 15.0}),
        PeerCompanyMetric(company_id="P2", company_name="P2", market_cap=None, metrics={"roe": 15.0}),
    ]
    res_zero_std = engine.evaluate(
        PeerBenchmarkRequest(
            sector_name="Dairy",
            target_company_id="VNM",
            target_company_name="Vinamilk",
            target_metrics={"roe": 15.0},
            peers=peers,
            weighting_mode=BenchmarkWeightingMode.MARKET_CAP,
            exclude_target_from_pool=True,
        )
    )
    assert res_zero_std.peer_count_evaluated == 2
    roe = res_zero_std.results[0]
    assert roe.z_score == 0.0
    assert roe.active_sector_mean == 15.0


def test_peer_benchmark_api_and_security_traversal():
    payload = {
        "sector_name": "Dairy",
        "target_company_id": "VNM",
        "target_company_name": "Vinamilk",
        "target_document_id": "VNM_BCTC_2023_AUDITED",
        "target_metrics": {"gross_margin": 40.7, "roe": 21.5},
        "peers": [p.model_dump() for p in _sample_peers()],
        "metric_configs": [
            MetricBenchmarkConfig(metric_code="gross_margin", metric_name="Gross Margin", unit="%", higher_is_better=True).model_dump()
        ],
        "weighting_mode": "market_cap",
    }
    res = client.post("/api/v1/analysis/peer-benchmark", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["weighting_mode"] == "market_cap"
    assert data["peer_count_evaluated"] == 4
    assert data["composite_percentile_score"] is not None

    # Path traversal in target_document_id rejected
    bad_payload = {**payload, "target_document_id": "../../etc/passwd"}
    bad_res = client.post("/api/v1/analysis/peer-benchmark", json=bad_payload)
    assert bad_res.status_code == 422
