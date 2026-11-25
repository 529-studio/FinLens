"""
Cross-Sectional Industry Peer Benchmarking & Sector Percentile Engine (Sprint 13 S13-04)
Computes deterministic linear percentiles (P10/P25/P50/P75/P90), equal-weighted and
market-cap weighted sector means, polarity-aware percentile ranks, and z-scores.
"""

import math
import time
from typing import Dict, List, Optional, Tuple

from contracts import (
    BenchmarkWeightingMode,
    MetricBenchmarkConfig,
    MetricBenchmarkResult,
    PeerBenchmarkRequest,
    PeerBenchmarkResponse,
    PeerCompanyMetric,
    PeerQuartileStanding,
)

# Default polarity & display metadata for common financial ratios
DEFAULT_METRIC_METADATA: Dict[str, Tuple[str, str, bool]] = {
    "gross_margin": ("Biên lợi nhuận gộp", "%", True),
    "operating_margin": ("Biên lợi nhuận hoạt động", "%", True),
    "net_margin": ("Biên lợi nhuận ròng", "%", True),
    "roe": ("Tỷ suất sinh lời trên vốn chủ (ROE)", "%", True),
    "roa": ("Tỷ suất sinh lời trên tổng tài sản (ROA)", "%", True),
    "current_ratio": ("Hệ số thanh toán hiện hành", "x", True),
    "quick_ratio": ("Hệ số thanh toán nhanh", "x", True),
    "debt_to_equity": ("Tỷ lệ Nợ / Vốn chủ sở hữu", "x", False),
    "debt_to_assets": ("Tỷ lệ Nợ / Tổng tài sản", "x", False),
    "pe_ratio": ("Hệ số giá trên thu nhập (P/E)", "x", False),
    "ev_ebitda": ("EV / EBITDA", "x", False),
}


def _is_finite_number(val: Optional[float]) -> bool:
    return val is not None and isinstance(val, (int, float)) and math.isfinite(float(val))


def linear_percentile(sorted_values: List[float], quantile: float) -> Optional[float]:
    """
    Computes deterministic linear-interpolated percentile on sorted values (quantile in [0, 1]).
    """
    if not sorted_values:
        return None
    if len(sorted_values) == 1:
        return round(sorted_values[0], 4)

    q = max(0.0, min(1.0, quantile))
    pos = q * (len(sorted_values) - 1)
    lower_idx = int(math.floor(pos))
    upper_idx = int(math.ceil(pos))
    if lower_idx == upper_idx:
        return round(sorted_values[lower_idx], 4)
    weight = pos - lower_idx
    interpolated = sorted_values[lower_idx] * (1.0 - weight) + sorted_values[upper_idx] * weight
    return round(interpolated, 4)


def compute_percentile_rank(
    target_val: float,
    peer_values: List[float],
    higher_is_better: bool = True,
) -> float:
    """
    Computes target percentile rank (0.0-100.0) relative to peer distribution using
    mid-rank handling for ties and polarity inversion when lower values are stronger.
    """
    if not peer_values:
        return 50.0
    below = sum(1 for v in peer_values if v < target_val)
    equal = sum(1 for v in peer_values if v == target_val)
    raw_pct = ((below + 0.5 * equal) / len(peer_values)) * 100.0
    adjusted = raw_pct if higher_is_better else (100.0 - raw_pct)
    return round(max(0.0, min(100.0, adjusted)), 2)


def classify_standing(percentile_rank: Optional[float]) -> PeerQuartileStanding:
    """Maps polarity-adjusted percentile rank into quartile standing."""
    if percentile_rank is None:
        return PeerQuartileStanding.INSUFFICIENT_DATA
    if percentile_rank >= 75.0:
        return PeerQuartileStanding.TOP_QUARTILE
    if percentile_rank >= 50.0:
        return PeerQuartileStanding.ABOVE_MEDIAN
    if percentile_rank >= 25.0:
        return PeerQuartileStanding.BELOW_MEDIAN
    return PeerQuartileStanding.BOTTOM_QUARTILE


class PeerBenchmarkEngine:
    """Cross-sectional sector benchmarking calculator."""

    def evaluate(self, req: PeerBenchmarkRequest) -> PeerBenchmarkResponse:
        start_time = time.time()

        filtered_peers: List[PeerCompanyMetric] = [
            p
            for p in req.peers
            if not (req.exclude_target_from_pool and p.company_id == req.target_company_id)
        ]

        config_map: Dict[str, MetricBenchmarkConfig] = {
            cfg.metric_code: cfg for cfg in req.metric_configs
        }

        metric_codes: List[str] = list(req.target_metrics.keys())
        for cfg in req.metric_configs:
            if cfg.metric_code not in metric_codes:
                metric_codes.append(cfg.metric_code)
        for peer in filtered_peers:
            for code in peer.metrics.keys():
                if code not in metric_codes:
                    metric_codes.append(code)

        results: List[MetricBenchmarkResult] = []
        valid_ranks: List[float] = []

        for code in metric_codes:
            cfg = config_map.get(code)
            default_name, default_unit, default_polarity = DEFAULT_METRIC_METADATA.get(
                code, (code.replace("_", " ").title(), "", True)
            )
            metric_name = (cfg.metric_name if cfg and cfg.metric_name else default_name)
            unit = cfg.unit if cfg and cfg.unit else default_unit
            higher_is_better = cfg.higher_is_better if cfg is not None else default_polarity

            raw_target = req.target_metrics.get(code)
            target_val: Optional[float] = float(raw_target) if _is_finite_number(raw_target) else None

            peer_vals: List[float] = []
            weighted_pairs: List[Tuple[float, float]] = []

            for peer in filtered_peers:
                pval = peer.metrics.get(code)
                if not _is_finite_number(pval):
                    continue
                fval = float(pval)  # type: ignore[arg-type]
                peer_vals.append(fval)
                if _is_finite_number(peer.market_cap) and float(peer.market_cap or 0.0) > 0.0:
                    weighted_pairs.append((fval, float(peer.market_cap)))  # type: ignore[arg-type]

            peer_count = len(peer_vals)
            if peer_count == 0:
                results.append(
                    MetricBenchmarkResult(
                        metric_code=code,
                        metric_name=metric_name,
                        unit=unit,
                        higher_is_better=higher_is_better,
                        target_value=round(target_val, 4) if target_val is not None else None,
                        peer_count=0,
                        standing=PeerQuartileStanding.INSUFFICIENT_DATA,
                    )
                )
                continue

            sorted_vals = sorted(peer_vals)
            eq_mean = round(sum(peer_vals) / peer_count, 4)

            total_mcap = sum(w for _, w in weighted_pairs)
            if total_mcap > 0.0:
                mcap_mean = round(sum(v * w for v, w in weighted_pairs) / total_mcap, 4)
            else:
                mcap_mean = eq_mean

            active_mean = (
                mcap_mean
                if req.weighting_mode == BenchmarkWeightingMode.MARKET_CAP
                else eq_mean
            )

            variance = sum((v - eq_mean) ** 2 for v in peer_vals) / peer_count
            std_dev = math.sqrt(variance)

            p10 = linear_percentile(sorted_vals, 0.10)
            p25 = linear_percentile(sorted_vals, 0.25)
            p50 = linear_percentile(sorted_vals, 0.50)
            p75 = linear_percentile(sorted_vals, 0.75)
            p90 = linear_percentile(sorted_vals, 0.90)

            pct_rank: Optional[float] = None
            z_score: Optional[float] = None
            if target_val is not None:
                pct_rank = compute_percentile_rank(target_val, peer_vals, higher_is_better=higher_is_better)
                valid_ranks.append(pct_rank)
                if std_dev > 1e-12:
                    raw_z = (target_val - eq_mean) / std_dev
                    z_score = round(raw_z if higher_is_better else -raw_z, 4)
                else:
                    z_score = 0.0

            results.append(
                MetricBenchmarkResult(
                    metric_code=code,
                    metric_name=metric_name,
                    unit=unit,
                    higher_is_better=higher_is_better,
                    target_value=round(target_val, 4) if target_val is not None else None,
                    peer_count=peer_count,
                    equal_weighted_mean=eq_mean,
                    market_cap_weighted_mean=mcap_mean,
                    active_sector_mean=active_mean,
                    p10=p10,
                    p25=p25,
                    p50=p50,
                    p75=p75,
                    p90=p90,
                    percentile_rank=pct_rank,
                    z_score=z_score,
                    standing=classify_standing(pct_rank),
                )
            )

        composite_score = round(sum(valid_ranks) / len(valid_ranks), 2) if valid_ranks else None
        top_count = sum(1 for r in results if r.standing == PeerQuartileStanding.TOP_QUARTILE)
        weight_label = (
            "trọng số vốn hóa (market-cap weighted)"
            if req.weighting_mode == BenchmarkWeightingMode.MARKET_CAP
            else "bình quân gia quyền đều (equal-weighted)"
        )
        narrative = (
            f"Đánh giá {req.target_company_name} trong ngành {req.sector_name} "
            f"so với {len(filtered_peers)} doanh nghiệp cùng ngành theo phương pháp {weight_label}: "
            f"điểm bách phân vị tổng hợp đạt {composite_score if composite_score is not None else 'N/A'} "
            f"({top_count}/{len(results)} chỉ tiêu thuộc nhóm Top Quartile)."
        )

        elapsed_ms = round((time.time() - start_time) * 1000.0, 2)
        return PeerBenchmarkResponse(
            sector_name=req.sector_name,
            target_company_id=req.target_company_id,
            target_company_name=req.target_company_name,
            target_document_id=req.target_document_id,
            weighting_mode=req.weighting_mode,
            peer_count_evaluated=len(filtered_peers),
            composite_percentile_score=composite_score,
            results=results,
            narrative=narrative,
            execution_time_ms=elapsed_ms,
        )
