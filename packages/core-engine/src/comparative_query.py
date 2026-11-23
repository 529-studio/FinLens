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


def parse_financial_value(val: Any) -> Optional[float]:
    """Extracts clean float representation from formatted financial numbers or strings."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        cleaned = re.sub(r"[^\d\.,\-]", "", val).strip()
        if not cleaned:
            return None
        if "." in cleaned and "," in cleaned:
            if cleaned.rfind(",") > cleaned.rfind("."):
                cleaned = cleaned.replace(".", "").replace(",", ".")
            else:
                cleaned = cleaned.replace(",", "")
        elif "." in cleaned:
            parts = cleaned.split(".")
            if len(parts) == 2 and len(parts[1]) == 3 and int(parts[0]) > 0:
                cleaned = parts[0] + parts[1]
        elif "," in cleaned:
            parts = cleaned.split(",")
            if len(parts) == 2 and len(parts[1]) == 3 and int(parts[0]) > 0:
                cleaned = parts[0] + parts[1]
            else:
                cleaned = cleaned.replace(",", ".")
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def canonicalize_metric_name(raw_name: str) -> str:
    """Maps Vietnamese or multi-language metric names to canonical metric keys."""
    raw = raw_name.lower()
    if any(k in raw for k in ["doanh thu", "revenue", "sales"]):
        return "revenue"
    if any(k in raw for k in ["lợi nhuận gộp", "gross profit"]):
        return "gross_profit"
    if any(k in raw for k in ["lợi nhuận sau thuế", "lợi nhuận thuần", "net profit", "net income", "profit after tax"]):
        return "net_profit"
    if any(k in raw for k in ["biên lợi nhuận gộp", "gross margin"]):
        return "gross_margin"
    if any(k in raw for k in ["biên lợi nhuận ròng", "biên lợi nhuận thuần", "net margin"]):
        return "net_margin"
    return re.sub(r"[^a-zA-Z0-9_]+", "_", raw).strip("_") or "metric"


class PortfolioSynthesisEngine:
    """
    Decoupled domain coordinator for multi-document portfolio synthesis and cross-filing comparative analytics.
    Injected with DocumentStore, VisualRetriever, and VlmRouter dependencies.
    """

    def __init__(self, store: Any, retriever: Any, router: Any):
        self.store = store
        self.retriever = retriever
        self.router = router

    async def synthesize(self, req: PortfolioSynthesisRequest) -> PortfolioSynthesisResponse:
        start_time = time.time()

        # 1. Existence check for all target documents
        for target in req.documents:
            pages = self.store.get_pages(target.document_id)
            if not pages:
                raise FileNotFoundError(f"Document '{target.document_id}' not found in index. Please ingest it first.")

        # 2. Partitioned multi-document retrieval
        doc_ids = [target.document_id for target in req.documents]
        retrieved_pages_map = self.retriever.comparative_search(
            doc_ids,
            req.query_text or "So sánh tài chính",
            top_k_per_doc=1,
        )

        # 3. Assemble document pages mapping with image paths
        doc_pages: Dict[str, List[Tuple[str, int]]] = {}
        for doc_id, page_nums in retrieved_pages_map.items():
            stored_pages = self.store.get_pages(doc_id)
            page_dict = {p["page_number"]: p["image_path"] for p in stored_pages}
            doc_pages[doc_id] = []
            for p_num in page_nums:
                img_path = page_dict.get(p_num)
                if img_path:
                    doc_pages[doc_id].append((img_path, p_num))

        # 4. Dispatch visual comparative inference
        vlm_res = await self.router.analyze_comparative(
            doc_pages=doc_pages,
            query=req.query_text or "So sánh tài chính",
            preferred_mode=req.inference_mode,
        )

        # 5. Extract and normalize GroundedEvidence
        evidences: List[GroundedEvidence] = []
        for e in vlm_res.get("evidences", []):
            evidences.append(
                GroundedEvidence(
                    page_number=e["page_number"],
                    bounding_box=BoundingBox(
                        ymin=e["ymin"],
                        xmin=e["xmin"],
                        ymax=e["ymax"],
                        xmax=e["xmax"],
                    ),
                    label=e["label"],
                    extracted_value=e.get("extracted_value"),
                    confidence=e["confidence"],
                    document_id=e.get("document_id"),
                )
            )

        # 6. Resolve metadata and map document_id -> (entity, period)
        doc_meta: Dict[str, Tuple[str, str]] = {}
        for target in req.documents:
            stored_pages = self.store.get_pages(target.document_id)
            ent, per = resolve_target_metadata(target, stored_pages)
            doc_meta[target.document_id] = (ent, per)

        # 7. Build time series metrics from comparative_metrics
        comparative_metrics = vlm_res.get("comparative_metrics", [])
        time_series = self._build_time_series(
            comparative_metrics=comparative_metrics,
            doc_meta=doc_meta,
            evidences=evidences,
            metrics_requested=req.metrics_requested,
        )

        # 8. Compute peer rankings
        primary_metric = "revenue"
        peer_rankings = rank_entities_by_metric(time_series, metric_name=primary_metric)
        if not peer_rankings and time_series:
            peer_rankings = rank_entities_by_metric(time_series, metric_name=time_series[0].metric)

        # 9. Compute portfolio summary
        summary = compute_portfolio_summary(time_series, peer_rankings)

        duration_ms = (time.time() - start_time) * 1000.0

        return PortfolioSynthesisResponse(
            portfolio_summary=summary,
            time_series_metrics=time_series,
            peer_rankings=peer_rankings,
            synthesis_narrative=vlm_res.get("answer", "Portfolio synthesis complete."),
            evidences=evidences,
            retrieved_pages=retrieved_pages_map,
            latency_ms=round(duration_ms, 2),
            engine_used=vlm_res.get("engine", "unknown"),
        )

    def _build_time_series(
        self,
        comparative_metrics: List[Dict[str, Any]],
        doc_meta: Dict[str, Tuple[str, str]],
        evidences: List[GroundedEvidence],
        metrics_requested: List[str],
    ) -> List[EntityMetricSeries]:
        """
        Groups extracted metrics by (entity, metric), calculates YoY and CAGR, and attaches GroundedEvidence.
        """
        # (entity, canonical_metric) -> List[TimeSeriesDataPoint]
        grouped: Dict[Tuple[str, str], List[TimeSeriesDataPoint]] = {}

        for m in comparative_metrics:
            raw_name = m.get("metric", "metric")
            canonical_name = canonicalize_metric_name(raw_name)
            unit = m.get("unit", "VND")
            doc_values = m.get("doc_values", {})

            for doc_id, val_str in doc_values.items():
                if doc_id not in doc_meta:
                    continue
                entity, period = doc_meta[doc_id]
                val_float = parse_financial_value(val_str)

                # Match evidence by doc_id
                matched_evidence = None
                for ev in evidences:
                    if ev.document_id == doc_id:
                        matched_evidence = ev
                        break

                key = (entity, canonical_name)
                if key not in grouped:
                    grouped[key] = []

                grouped[key].append(
                    TimeSeriesDataPoint(
                        period=period,
                        value=val_float,
                        unit=unit,
                        evidence=matched_evidence,
                    )
                )

        series_list: List[EntityMetricSeries] = []
        for (entity, metric_name), points in grouped.items():
            # Sort points by period (e.g. 2021 -> 2022 -> 2023)
            points.sort(key=lambda p: p.period)

            # Compute YoY growth between consecutive periods
            for i in range(1, len(points)):
                points[i].yoy_growth = calculate_yoy(points[i - 1].value, points[i].value)

            # Compute CAGR if >= 2 points
            cagr = None
            if len(points) >= 2 and points[0].value and points[-1].value:
                p_start = points[0].period
                p_end = points[-1].period
                if p_start.isdigit() and p_end.isdigit():
                    n_years = int(p_end) - int(p_start)
                else:
                    n_years = len(points) - 1
                if n_years > 0:
                    cagr = calculate_cagr(points[0].value, points[-1].value, n_years)

            series_list.append(
                EntityMetricSeries(
                    entity=entity,
                    metric=metric_name,
                    series=points,
                    cagr=cagr,
                )
            )

        return series_list

