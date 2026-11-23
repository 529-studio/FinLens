"""
Multi-Document Portfolio Synthesis & Cross-Filing Comparative Analytics Engine (Sprint 11 Task S11-01)
Governed by AGENTS.md Rules 1, 2, 3, 11, 12, 13, 14, 15 and ADR-003.
Provides deterministic financial calculations, hybrid metadata resolution, and cross-filing visual grounding.
"""

import re
import time
from typing import List, Dict, Any, Optional, Tuple, Set

from contracts import (
    PortfolioDocumentTarget,
    PortfolioSynthesisRequest,
    PortfolioSynthesisResponse,
    PortfolioSummary,
    EntityMetricSeries,
    TimeSeriesDataPoint,
    PeerRankingItem,
    GroundedEvidence,
    BoundingBox,
)


def resolve_target_metadata(
    target: PortfolioDocumentTarget,
    store_pages: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[str, str]:
    """
    Resolves enterprise entity ticker/name and fiscal period using Hybrid Graceful Degradation.
    Priority:
    1. Explicit target.entity and target.period
    2. Regex pattern extraction from target.document_id
    3. Stored page metadata inspection
    4. Fallback defaults
    """
    entity = target.entity
    period = target.period

    # If both provided explicitly, return immediately
    if entity and period:
        return entity, period

    # Regex extraction from document_id
    doc_id = target.document_id

    # Pattern matches e.g. VNM_2023_AUDITED, HPG-2022-ANNUAL, VIC_2021, FPT_Q4_2023_REPORT
    m_year = re.search(r"(?:^|[_\-])(?:Q[1-4][_\-])?(\d{4})(?:[_\-]|$)", doc_id)
    m_entity = re.match(r"^([a-zA-Z0-9]+)[_\-]", doc_id)

    if not entity:
        if m_entity:
            entity = m_entity.group(1).upper()
        else:
            entity = doc_id

    if not period:
        if m_year:
            period = m_year.group(1)
        else:
            # Fallback 3: check stored page metadata if available
            if store_pages:
                for p in store_pages:
                    text = p.get("text_preview", "")
                    m_p_year = re.search(r"\b(20[12]\d)\b", text)
                    if m_p_year:
                        period = m_p_year.group(1)
                        break
            if not period:
                period = "UNKNOWN"

    return entity, period


def calculate_yoy(v_prev: Optional[float], v_curr: Optional[float]) -> Optional[float]:
    """
    Calculates Year-over-Year (YoY) percentage delta: ((v_curr - v_prev) / |v_prev|) * 100.
    Handles IEEE-754 precision normalization and division-by-zero guards.
    """
    if v_prev is None or v_curr is None or v_prev == 0.0:
        return None
    delta_pct = ((v_curr - v_prev) / abs(v_prev)) * 100.0
    return round((delta_pct + 1e-9), 4)


def calculate_cagr(v_start: Optional[float], v_end: Optional[float], n_years: int) -> Optional[float]:
    """
    Calculates Compound Annual Growth Rate: (v_end / v_start)**(1 / n_years) - 1.
    Requires v_start > 0 and v_end > 0 and n_years > 0.
    """
    if v_start is None or v_end is None or n_years <= 0:
        return None
    if v_start <= 0.0 or v_end <= 0.0:
        return None

    try:
        ratio = v_end / v_start
        cagr = (ratio ** (1.0 / float(n_years))) - 1.0
        return round((cagr + 1e-9), 6)
    except (ZeroDivisionError, ValueError, OverflowError):
        return None


def calculate_margins(
    revenue: Optional[float],
    gross_profit: Optional[float],
    net_profit: Optional[float],
) -> Tuple[Optional[float], Optional[float]]:
    """
    Calculates Gross Margin and Net Margin percentages normalized by Revenue.
    """
    if revenue is None or revenue <= 0.0:
        return None, None

    gross_margin = None
    if gross_profit is not None:
        gross_margin = round(((gross_profit / revenue) * 100.0 + 1e-9), 4)

    net_margin = None
    if net_profit is not None:
        net_margin = round(((net_profit / revenue) * 100.0 + 1e-9), 4)

    return gross_margin, net_margin


def rank_entities_by_metric(
    series_list: List[EntityMetricSeries],
    metric_name: str,
    target_period: Optional[str] = None,
) -> List[PeerRankingItem]:
    """
    Ranks peer entities by a specified metric for a given period in descending order.
    """
    candidates = []
    for s in series_list:
        if s.metric.lower() != metric_name.lower():
            continue

        selected_point = None
        if target_period:
            for pt in s.series:
                if pt.period == target_period:
                    selected_point = pt
                    break
        else:
            if s.series:
                selected_point = s.series[-1]

        if selected_point and selected_point.value is not None:
            candidates.append({
                "entity": s.entity,
                "period": selected_point.period,
                "metric_name": metric_name,
                "metric_value": selected_point.value,
                "growth_rate": selected_point.yoy_growth,
                "evidence": selected_point.evidence,
            })

    # Sort descending by metric value
    candidates.sort(key=lambda x: x["metric_value"], reverse=True)

    rankings: List[PeerRankingItem] = []
    for idx, c in enumerate(candidates, start=1):
        rankings.append(
            PeerRankingItem(
                rank=idx,
                entity=c["entity"],
                period=c["period"],
                metric_name=c["metric_name"],
                metric_value=c["metric_value"],
                growth_rate=c["growth_rate"],
                evidence=c["evidence"],
            )
        )
    return rankings


def compute_portfolio_summary(
    time_series: List[EntityMetricSeries],
    peer_rankings: List[PeerRankingItem],
) -> PortfolioSummary:
    """
    Aggregates high-level metrics across the synthesized portfolio.
    """
    entities: Set[str] = set()
    periods: Set[str] = set()
    total_rev = 0.0
    has_rev = False

    fastest_grower = None
    max_growth = -float("inf")

    highest_margin_entity = None
    max_margin = -float("inf")

    for s in time_series:
        entities.add(s.entity)
        for pt in s.series:
            periods.add(pt.period)

        if s.metric.lower() == "revenue" and s.series:
            latest_pt = s.series[-1]
            if latest_pt.value is not None:
                total_rev += latest_pt.value
                has_rev = True

        if s.metric.lower() in ["net_margin", "gross_margin"] and s.series:
            latest_pt = s.series[-1]
            if latest_pt.value is not None and latest_pt.value > max_margin:
                max_margin = latest_pt.value
                highest_margin_entity = s.entity

    for r in peer_rankings:
        if r.growth_rate is not None and r.growth_rate > max_growth:
            max_growth = r.growth_rate
            fastest_grower = r.entity

    return PortfolioSummary(
        total_entities=len(entities),
        total_periods=len(periods),
        portfolio_revenue_aggregate=round(total_rev, 2) if has_rev else None,
        weighted_net_margin=round(max_margin, 2) if highest_margin_entity else None,
        fastest_growing_entity=fastest_grower,
        highest_margin_entity=highest_margin_entity,
    )
