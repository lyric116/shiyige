from __future__ import annotations

from collections import Counter
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.models.recommendation_analytics import (
    RecommendationClickLog,
    RecommendationConversionLog,
    RecommendationImpressionLog,
    RecommendationRequestLog,
    SearchRequestLog,
)
from backend.app.models.recommendation_experiment import RecommendationExperiment
from backend.app.services.vector_store import VectorStoreRuntime, probe_vector_store_runtime
from backend.app.tasks.qdrant_index_tasks import get_product_index_status


def isoformat_or_none(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def build_recommendation_dashboard_payload(
    db: Session,
) -> dict[str, object]:
    runtime = probe_vector_store_runtime()
    vector_index = get_product_index_status(db)
    vector_index["failed_count"] = len(vector_index["failed_products"])

    active_product_count = int(vector_index["active_product_count"])
    recommendation_metrics = build_recommendation_metrics(
        db,
        active_product_count=active_product_count,
    )
    search_metrics = build_search_metrics(db)
    experiments = build_experiment_payload(db, runtime=runtime)

    return {
        "runtime": runtime.to_dict(),
        "vector_index": vector_index,
        "recommendation_metrics": recommendation_metrics,
        "search_metrics": search_metrics,
        "experiments": experiments,
    }


def build_recommendation_metrics(
    db: Session,
    *,
    active_product_count: int,
) -> dict[str, object]:
    request_count = int(db.scalar(select(func.count()).select_from(RecommendationRequestLog)) or 0)
    impression_count = int(
        db.scalar(select(func.count()).select_from(RecommendationImpressionLog)) or 0
    )
    click_count = int(db.scalar(select(func.count()).select_from(RecommendationClickLog)) or 0)
    add_to_cart_count = int(
        db.scalar(
            select(func.count())
            .select_from(RecommendationConversionLog)
            .where(RecommendationConversionLog.action_type == "add_to_cart")
        )
        or 0
    )
    pay_order_count = int(
        db.scalar(
            select(func.count())
            .select_from(RecommendationConversionLog)
            .where(RecommendationConversionLog.action_type == "pay_order")
        )
        or 0
    )
    covered_product_count = int(
        db.scalar(select(func.count(func.distinct(RecommendationImpressionLog.product_id)))) or 0
    )
    unique_user_count = int(
        db.scalar(
            select(func.count(func.distinct(RecommendationRequestLog.user_id))).where(
                RecommendationRequestLog.user_id.is_not(None)
            )
        )
        or 0
    )
    fallback_request_count = int(
        db.scalar(
            select(func.count())
            .select_from(RecommendationRequestLog)
            .where(RecommendationRequestLog.fallback_used.is_(True))
        )
        or 0
    )
    avg_latency_ms = float(
        db.scalar(select(func.avg(RecommendationRequestLog.latency_ms))) or 0.0
    )
    avg_candidate_count = float(
        db.scalar(select(func.avg(RecommendationRequestLog.candidate_count))) or 0.0
    )
    avg_impressions_per_request = impression_count / request_count if request_count else 0.0
    last_request_at = db.scalar(select(func.max(RecommendationRequestLog.created_at)))
    slot_breakdown = db.execute(
        select(
            RecommendationRequestLog.slot,
            func.count().label("total"),
        )
        .group_by(RecommendationRequestLog.slot)
        .order_by(func.count().desc(), RecommendationRequestLog.slot.asc())
    ).all()

    pipeline_breakdown = db.execute(
        select(
            RecommendationRequestLog.pipeline_version,
            RecommendationRequestLog.model_version,
            func.count().label("total"),
        )
        .group_by(
            RecommendationRequestLog.pipeline_version,
            RecommendationRequestLog.model_version,
        )
        .order_by(func.count().desc())
    ).all()
    channel_counter: Counter[str] = Counter()
    channel_rows = db.execute(select(RecommendationImpressionLog.recall_channels)).all()
    for row in channel_rows:
        for channel in row[0] or []:
            channel_counter[str(channel)] += 1

    ctr = click_count / impression_count if impression_count else 0.0
    add_to_cart_rate = add_to_cart_count / impression_count if impression_count else 0.0
    conversion_rate = pay_order_count / impression_count if impression_count else 0.0
    coverage_rate = (
        covered_product_count / active_product_count if active_product_count else 0.0
    )
    fallback_rate = fallback_request_count / request_count if request_count else 0.0

    return {
        "request_count": request_count,
        "impression_count": impression_count,
        "click_count": click_count,
        "add_to_cart_count": add_to_cart_count,
        "pay_order_count": pay_order_count,
        "covered_product_count": covered_product_count,
        "unique_user_count": unique_user_count,
        "fallback_request_count": fallback_request_count,
        "ctr": round(ctr, 4),
        "add_to_cart_rate": round(add_to_cart_rate, 4),
        "conversion_rate": round(conversion_rate, 4),
        "coverage_rate": round(coverage_rate, 4),
        "fallback_rate": round(fallback_rate, 4),
        "average_latency_ms": round(avg_latency_ms, 3),
        "average_candidate_count": round(avg_candidate_count, 3),
        "average_impressions_per_request": round(avg_impressions_per_request, 3),
        "last_request_at": isoformat_or_none(last_request_at),
        "slot_breakdown": [
            {
                "slot": str(slot),
                "total": int(total),
                "share": round((int(total) / request_count), 4) if request_count else 0.0,
            }
            for slot, total in slot_breakdown
        ],
        "pipeline_breakdown": [
            {
                "pipeline_version": str(pipeline_version),
                "model_version": str(model_version),
                "total": int(total),
                "share": round((int(total) / request_count), 4) if request_count else 0.0,
            }
            for pipeline_version, model_version, total in pipeline_breakdown
        ],
        "channel_breakdown": [
            {
                "channel": channel,
                "impression_count": count,
                "appearance_share": (
                    round((count / impression_count), 4) if impression_count else 0.0
                ),
            }
            for channel, count in sorted(
                channel_counter.items(),
                key=lambda item: (-item[1], item[0]),
            )
        ],
    }


def build_search_metrics(db: Session) -> dict[str, object]:
    request_count = int(db.scalar(select(func.count()).select_from(SearchRequestLog)) or 0)
    keyword_count = int(
        db.scalar(
            select(func.count())
            .select_from(SearchRequestLog)
            .where(SearchRequestLog.mode == "keyword")
        )
        or 0
    )
    semantic_count = int(
        db.scalar(
            select(func.count())
            .select_from(SearchRequestLog)
            .where(SearchRequestLog.mode == "semantic")
        )
        or 0
    )
    avg_latency_ms = float(db.scalar(select(func.avg(SearchRequestLog.latency_ms))) or 0.0)
    avg_result_count = float(db.scalar(select(func.avg(SearchRequestLog.total_results))) or 0.0)
    last_request_at = db.scalar(select(func.max(SearchRequestLog.created_at)))
    pipeline_breakdown = db.execute(
        select(
            SearchRequestLog.mode,
            SearchRequestLog.pipeline_version,
            func.count().label("total"),
        )
        .group_by(
            SearchRequestLog.mode,
            SearchRequestLog.pipeline_version,
        )
        .order_by(
            func.count().desc(),
            SearchRequestLog.mode.asc(),
            SearchRequestLog.pipeline_version.asc(),
        )
    ).all()

    return {
        "request_count": request_count,
        "keyword_count": keyword_count,
        "semantic_count": semantic_count,
        "average_latency_ms": round(avg_latency_ms, 3),
        "average_result_count": round(avg_result_count, 3),
        "last_request_at": isoformat_or_none(last_request_at),
        "pipeline_breakdown": [
            {
                "mode": str(mode),
                "pipeline_version": str(pipeline_version),
                "total": int(total),
                "share": round((int(total) / request_count), 4) if request_count else 0.0,
            }
            for mode, pipeline_version, total in pipeline_breakdown
        ],
    }


def build_experiment_payload(
    db: Session,
    *,
    runtime: VectorStoreRuntime | None = None,
) -> dict[str, object]:
    vector_runtime = runtime or probe_vector_store_runtime()
    active_key = derive_active_experiment_key(vector_runtime)
    active_rows = db.scalars(
        select(RecommendationExperiment)
        .where(RecommendationExperiment.is_active.is_(True))
        .order_by(RecommendationExperiment.updated_at.desc(), RecommendationExperiment.id.desc())
    ).all()
    row_by_key = {row.experiment_key: row for row in active_rows}

    items = [
        build_experiment_item(
            key="baseline",
            name="baseline",
            strategy="python_cosine_baseline",
            description="保留旧版 Python 全量余弦 + 规则加分链路，作为推荐与搜索对照组。",
            default_pipeline_version="baseline",
            default_model_version="baseline",
            capabilities=["dense_similarity", "rule_bonus", "baseline_compare"],
            config_json={
                "vector_store": "postgres_json",
                "dense_recall": False,
                "sparse_recall": False,
                "colbert_rerank": False,
                "collaborative_filtering": False,
                "ranking": "rule_bonus_only",
            },
            is_active=active_key == "baseline",
            db_row=row_by_key.get("baseline"),
        ),
        build_experiment_item(
            key="hybrid",
            name="hybrid",
            strategy="qdrant_dense_sparse",
            description="使用 Qdrant dense + sparse 双路召回，实现搜索阶段的混合检索。",
            default_pipeline_version=vector_runtime.recommendation_pipeline_version,
            default_model_version="dense_sparse",
            capabilities=["dense_recall", "sparse_recall", "rrf_fusion"],
            config_json={
                "vector_store": "qdrant",
                "dense_recall": True,
                "sparse_recall": True,
                "colbert_rerank": False,
                "collaborative_filtering": False,
                "ranking": "fusion_only",
            },
            is_active=active_key == "hybrid",
            db_row=row_by_key.get("hybrid"),
        ),
        build_experiment_item(
            key="hybrid_rerank",
            name="hybrid_rerank",
            strategy="qdrant_hybrid_colbert",
            description=(
                "在 hybrid 基础上增加 ColBERT late interaction 重排，"
                "用于答辩展示高级搜索链路。"
            ),
            default_pipeline_version=vector_runtime.recommendation_pipeline_version,
            default_model_version="dense_sparse_colbert",
            capabilities=["dense_recall", "sparse_recall", "colbert_rerank"],
            config_json={
                "vector_store": "qdrant",
                "dense_recall": True,
                "sparse_recall": True,
                "colbert_rerank": True,
                "collaborative_filtering": False,
                "ranking": "search_reranker",
            },
            is_active=active_key == "hybrid_rerank",
            db_row=row_by_key.get("hybrid_rerank"),
        ),
        build_experiment_item(
            key="full_pipeline",
            name="full_pipeline",
            strategy="multi_recall_ranker",
            description="当前推荐主链路：多路召回 + 协同过滤 + 可解释排序 + 业务规则 + 多样性。",
            default_pipeline_version=vector_runtime.recommendation_pipeline_version,
            default_model_version=vector_runtime.configured_recommendation_ranker,
            capabilities=[
                "dense_recall",
                "sparse_recall",
                "colbert_rerank",
                "collaborative_filtering",
                "ltr_or_weighted_ranker",
                "diversity_rules",
            ],
            config_json={
                "vector_store": "qdrant",
                "dense_recall": True,
                "sparse_recall": True,
                "colbert_rerank": True,
                "collaborative_filtering": True,
                "ranking": vector_runtime.configured_recommendation_ranker,
                "active_recommendation_backend": vector_runtime.active_recommendation_backend,
            },
            is_active=active_key == "full_pipeline",
            db_row=row_by_key.get("full_pipeline"),
        ),
    ]

    known_keys = {item["key"] for item in items}
    for row in active_rows:
        if row.experiment_key in known_keys:
            continue
        items.append(
            {
                "key": row.experiment_key,
                "name": row.name,
                "strategy": row.strategy,
                "pipeline_version": row.pipeline_version,
                "model_version": row.model_version,
                "is_active": False,
                "capabilities": [],
                "config_json": dict(row.config_json or {}),
                "artifact_json": dict(row.artifact_json or {}),
                "description": row.description,
                "updated_at": isoformat_or_none(row.updated_at),
            }
        )

    return {
        "active_key": active_key,
        "items": items,
    }


def build_experiment_item(
    *,
    key: str,
    name: str,
    strategy: str,
    description: str,
    default_pipeline_version: str | None,
    default_model_version: str | None,
    capabilities: list[str],
    config_json: dict[str, object],
    is_active: bool,
    db_row: RecommendationExperiment | None,
) -> dict[str, object]:
    return {
        "key": key,
        "name": db_row.name if db_row is not None else name,
        "strategy": db_row.strategy if db_row is not None else strategy,
        "pipeline_version": (
            db_row.pipeline_version if db_row is not None else default_pipeline_version
        ),
        "model_version": db_row.model_version if db_row is not None else default_model_version,
        "is_active": is_active,
        "capabilities": list(capabilities),
        "config_json": (
            dict(db_row.config_json or config_json)
            if db_row is not None
            else config_json
        ),
        "artifact_json": dict(db_row.artifact_json or {}) if db_row is not None else {},
        "description": db_row.description if db_row and db_row.description else description,
        "updated_at": isoformat_or_none(db_row.updated_at) if db_row is not None else None,
    }


def derive_active_experiment_key(runtime: VectorStoreRuntime) -> str:
    if runtime.degraded_to_baseline or runtime.active_recommendation_backend == "baseline":
        return "baseline"
    if runtime.active_recommendation_backend == "multi_recall":
        return "full_pipeline"
    if runtime.active_search_backend == "qdrant_hybrid":
        return "hybrid_rerank"
    return "hybrid"
