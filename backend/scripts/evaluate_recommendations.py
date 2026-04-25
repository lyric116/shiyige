from __future__ import annotations
# ruff: noqa: E402, I001

import argparse
import json
import logging
import math
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from time import perf_counter

ROOT = Path(__file__).resolve().parents[2]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload, sessionmaker

from backend.app.core.config import AppSettings, get_app_settings
from backend.app.core.database import create_app_engine
from backend.app.core.security import hash_password
from backend.app.models.base import Base
from backend.app.models.product import Product
from backend.app.models.user import User, UserBehaviorLog, UserProfile
from backend.app.services.candidate_fusion import fuse_recall_results
from backend.app.services.embedding import get_embedding_provider
from backend.app.services.qdrant_client import get_qdrant_connection_status
from backend.app.services.ranker import rank_fused_candidates
from backend.app.services.ranking_features import build_ranking_feature_context
from backend.app.services.recommendation_pipeline import (
    load_pipeline_products,
    run_recommendation_pipeline,
)
from backend.app.services.recommendations import (
    baseline_recommend_products_for_user,
    load_user_behavior_logs,
)
from backend.app.tasks.collaborative_index_tasks import build_collaborative_index
from backend.app.tasks.qdrant_index_tasks import sync_products_to_qdrant
from backend.scripts.seed_base_data import seed_base_data

OUTPUT_PATH = Path("docs/generated/recommendation_evaluation_latest.md")
TOP_K = 5
QDRANT_LOCAL_URL = "http://127.0.0.1:6333"


@dataclass(slots=True)
class EvaluationScenario:
    name: str
    email: str
    username: str
    query: str
    seed_product_name: str
    relevant_category: str


@dataclass(frozen=True, slots=True)
class EvaluationMode:
    key: str
    label: str
    note: str


SCENARIOS = [
    EvaluationScenario(
        name="hanfu_style",
        email="eval-hanfu@example.com",
        username="eval-hanfu",
        query="春日汉服",
        seed_product_name="明制襦裙",
        relevant_category="汉服",
    ),
    EvaluationScenario(
        name="festival_gift",
        email="eval-gift@example.com",
        username="eval-gift",
        query="端午礼赠",
        seed_product_name="故宫宫廷香囊",
        relevant_category="文创",
    ),
    EvaluationScenario(
        name="craft_collectible",
        email="eval-craft@example.com",
        username="eval-craft",
        query="非遗家居陈设",
        seed_product_name="景泰蓝花瓶",
        relevant_category="非遗",
    ),
]

EVALUATION_MODES = [
    EvaluationMode(
        key="baseline",
        label="baseline",
        note="旧版 Python 余弦 + 规则加分路径。",
    ),
    EvaluationMode(
        key="dense_only",
        label="dense_only",
        note="仅使用 dense 内容召回结果。",
    ),
    EvaluationMode(
        key="dense_sparse",
        label="dense_sparse",
        note="使用 dense + sparse 混合召回结果。",
    ),
    EvaluationMode(
        key="dense_sparse_colbert",
        label="dense_sparse_colbert",
        note="dense + sparse 召回后接排序层作为 hybrid + rerank 对照。",
    ),
    EvaluationMode(
        key="multi_recall_weighted",
        label="multi_recall_weighted",
        note="多路召回 + 当前线上加权排序器。",
    ),
    EvaluationMode(
        key="multi_recall_ltr",
        label="multi_recall_ltr",
        note="多路召回 + LTR，关闭探索位并放宽类目连续约束。",
    ),
    EvaluationMode(
        key="multi_recall_ltr_diversity",
        label="multi_recall_ltr_diversity",
        note="多路召回 + LTR + 默认多样性与探索规则。",
    ),
]


def resolve_app_settings() -> AppSettings:
    settings = get_app_settings()
    if get_qdrant_connection_status(settings).available:
        return settings

    localhost_settings = settings.model_copy(update={"qdrant_url": QDRANT_LOCAL_URL})
    if get_qdrant_connection_status(localhost_settings).available:
        return localhost_settings
    return settings


def create_isolated_session() -> Session:
    with tempfile.NamedTemporaryFile(
        prefix="shiyige-eval-",
        suffix=".db",
        delete=False,
    ) as handle:
        database_url = f"sqlite:///{handle.name}"
    engine = create_app_engine(database_url)
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    return factory()


def suppress_http_logs() -> None:
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def prepare_vector_runtime(
    session: Session,
    *,
    settings: AppSettings,
) -> dict[str, object]:
    status = get_qdrant_connection_status(settings)
    if not status.available:
        return {
            "qdrant_ready": False,
            "qdrant_url": settings.qdrant_url,
            "reason": status.error,
        }

    started_at = perf_counter()
    sync_result = sync_products_to_qdrant(
        session,
        mode="full",
        settings=settings,
    )
    collaborative_result = build_collaborative_index(session, settings=settings)
    return {
        "qdrant_ready": True,
        "qdrant_url": settings.qdrant_url,
        "sync_result": sync_result,
        "collaborative_result": collaborative_result,
        "prep_latency_ms": elapsed_ms(started_at),
    }


def ensure_evaluation_user(session: Session, scenario: EvaluationScenario) -> User:
    user = session.scalar(select(User).where(User.email == scenario.email))
    if user is None:
        user = User(
            email=scenario.email,
            username=scenario.username,
            password_hash=hash_password("eval-pass-123"),
            role="user",
            is_active=True,
        )
        user.profile = UserProfile(display_name=scenario.username)
        session.add(user)
        session.flush()

    existing_logs = session.scalar(
        select(func.count())
        .select_from(UserBehaviorLog)
        .where(UserBehaviorLog.user_id == user.id)
    )
    if existing_logs:
        return user

    seed_product = session.scalar(
        select(Product)
        .options(selectinload(Product.category))
        .where(Product.name == scenario.seed_product_name)
    )
    if seed_product is None:
        raise RuntimeError(f"seed product not found: {scenario.seed_product_name}")

    session.add_all(
        [
            UserBehaviorLog(
                user_id=user.id,
                behavior_type="search",
                target_type="search",
                ext_json={"query": scenario.query},
            ),
            UserBehaviorLog(
                user_id=user.id,
                behavior_type="view_product",
                target_type="product",
                target_id=seed_product.id,
            ),
            UserBehaviorLog(
                user_id=user.id,
                behavior_type="add_to_cart",
                target_type="product",
                target_id=seed_product.id,
            ),
        ]
    )
    session.commit()
    return user


def build_relevant_product_ids(session: Session, scenario: EvaluationScenario) -> set[int]:
    seed_product = session.scalar(select(Product).where(Product.name == scenario.seed_product_name))
    assert seed_product is not None
    products = session.scalars(
        select(Product)
        .options(selectinload(Product.category))
        .where(Product.status == 1)
        .order_by(Product.id.asc())
    ).all()
    relevant_ids = [
        product.id
        for product in products
        if product.id != seed_product.id
        and product.category is not None
        and product.category.name == scenario.relevant_category
    ]
    return set(relevant_ids[:3])


def build_click_targets(relevant_ids: set[int]) -> set[int]:
    return set(sorted(relevant_ids)[:2])


def build_conversion_targets(relevant_ids: set[int]) -> set[int]:
    return set(sorted(relevant_ids)[:1])


def build_ltr_weights_file() -> str:
    payload = {
        "model_version": "ltr-json-demo-v1",
        "intercept": 0.05,
        "weights": {
            "dense_recall_score": 0.18,
            "sparse_recall_score": 0.12,
            "collaborative_score": 0.16,
            "item_cooccurrence_score": 0.08,
            "category_match": 0.10,
            "tag_match_count": 0.08,
            "price_affinity": 0.05,
            "user_recent_interest_score": 0.09,
            "rating_avg": 0.05,
            "freshness_score": 0.04,
            "content_quality_score": 0.05,
            "exploration_candidate": 0.03,
        },
    }
    output_path = Path(tempfile.gettempdir()) / "shiyige-ltr-eval-weights.json"
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return str(output_path)


def build_recall_subset(
    keys: list[str],
    recall_results: dict[str, list],
) -> dict[str, list]:
    return {
        key: recall_results.get(key, [])
        for key in keys
        if recall_results.get(key)
    }


def run_fused_subset(
    session: Session,
    *,
    pipeline_run,
    recall_keys: list[str],
) -> list[int]:
    recall_subset = build_recall_subset(recall_keys, pipeline_run.recall_results)
    fused = fuse_recall_results(recall_subset)
    products_by_id = load_pipeline_products(
        session,
        product_ids=[candidate.product_id for candidate in fused],
    )
    return [
        candidate.product_id
        for candidate in fused
        if candidate.product_id not in pipeline_run.consumed_product_ids
        and candidate.product_id in products_by_id
    ][:TOP_K]


def run_reranked_subset(
    session: Session,
    *,
    user_id: int,
    pipeline_run,
    recall_keys: list[str],
    settings: AppSettings,
) -> list[int]:
    recall_subset = build_recall_subset(recall_keys, pipeline_run.recall_results)
    fused = fuse_recall_results(recall_subset)
    products_by_id = load_pipeline_products(
        session,
        product_ids=[candidate.product_id for candidate in fused],
    )
    filtered = [
        candidate
        for candidate in fused
        if (
            candidate.product_id not in pipeline_run.consumed_product_ids
            and candidate.product_id in products_by_id
        )
    ]
    logs = load_user_behavior_logs(session, user_id)
    ranking_context = build_ranking_feature_context(
        session,
        user_id=user_id,
        top_terms=pipeline_run.top_terms,
        consumed_product_ids=pipeline_run.consumed_product_ids,
        recent_product_ids=pipeline_run.recent_product_ids,
        logs=logs,
        candidate_product_ids=[candidate.product_id for candidate in filtered],
    )
    ranked = rank_fused_candidates(
        filtered,
        products_by_id=products_by_id,
        context=ranking_context,
        limit=TOP_K,
        settings=settings,
    )
    return [candidate.product.id for candidate in ranked[:TOP_K]]


def run_mode(
    session: Session,
    *,
    user_id: int,
    mode: str,
    app_settings: AppSettings,
    ltr_model_path: str,
) -> tuple[list[int], float]:
    started_at = perf_counter()
    provider = get_embedding_provider(app_settings)

    if mode == "baseline":
        results = baseline_recommend_products_for_user(
            session,
            user_id=user_id,
            limit=TOP_K,
            provider=provider,
        )
        return [result.product.id for result in results[:TOP_K]], elapsed_ms(started_at)

    if mode == "multi_recall_weighted":
        pipeline = run_recommendation_pipeline(
            session,
            user_id=user_id,
            limit=TOP_K,
            settings=app_settings,
        )
        return [candidate.product.id for candidate in pipeline.candidates[:TOP_K]], elapsed_ms(
            started_at
        )

    if mode in {"multi_recall_ltr", "multi_recall_ltr_diversity"}:
        ltr_settings = app_settings.model_copy(
            update={
                "recommendation_ranker": "ltr_ranker",
                "recommendation_ltr_model_path": ltr_model_path,
                "recommendation_exploration_ratio": (
                    0.0
                    if mode == "multi_recall_ltr"
                    else app_settings.recommendation_exploration_ratio
                ),
                "recommendation_max_consecutive_category": (
                    TOP_K
                    if mode == "multi_recall_ltr"
                    else app_settings.recommendation_max_consecutive_category
                ),
            }
        )
        pipeline = run_recommendation_pipeline(
            session,
            user_id=user_id,
            limit=TOP_K,
            settings=ltr_settings,
        )
        return [candidate.product.id for candidate in pipeline.candidates[:TOP_K]], elapsed_ms(
            started_at
        )

    pipeline = run_recommendation_pipeline(
        session,
        user_id=user_id,
        limit=TOP_K,
        settings=app_settings,
    )
    if mode == "dense_only":
        return run_fused_subset(
            session,
            pipeline_run=pipeline,
            recall_keys=["content_profile"],
        ), elapsed_ms(started_at)

    if mode == "dense_sparse":
        return run_fused_subset(
            session,
            pipeline_run=pipeline,
            recall_keys=["content_profile", "sparse_interest"],
        ), elapsed_ms(started_at)

    if mode == "dense_sparse_colbert":
        return run_reranked_subset(
            session,
            user_id=user_id,
            pipeline_run=pipeline,
            recall_keys=["content_profile", "sparse_interest"],
            settings=app_settings,
        ), elapsed_ms(started_at)

    raise ValueError(f"unsupported evaluation mode: {mode}")


def elapsed_ms(started_at: float) -> float:
    return round((perf_counter() - started_at) * 1000, 3)


def precision_at_k(items: list[int], relevant_ids: set[int], k: int) -> float:
    if k <= 0:
        return 0.0
    hits = sum(1 for product_id in items[:k] if product_id in relevant_ids)
    return hits / float(k)


def recall_at_k(items: list[int], relevant_ids: set[int], k: int) -> float:
    if not relevant_ids:
        return 0.0
    hits = sum(1 for product_id in items[:k] if product_id in relevant_ids)
    return hits / float(len(relevant_ids))


def ndcg_at_k(items: list[int], relevant_ids: set[int], k: int) -> float:
    dcg = 0.0
    for index, product_id in enumerate(items[:k], start=1):
        if product_id in relevant_ids:
            dcg += 1.0 / math.log2(index + 1)
    ideal_hits = min(len(relevant_ids), k)
    if ideal_hits == 0:
        return 0.0
    idcg = sum(1.0 / math.log2(index + 1) for index in range(1, ideal_hits + 1))
    return dcg / idcg


def mrr(items: list[int], relevant_ids: set[int]) -> float:
    for index, product_id in enumerate(items, start=1):
        if product_id in relevant_ids:
            return 1.0 / float(index)
    return 0.0


def diversity_score(session: Session, items: list[int]) -> float:
    products = session.scalars(
        select(Product)
        .options(selectinload(Product.category))
        .where(Product.id.in_(items))
    ).all()
    if len(products) < 2:
        return 0.0

    differences = 0
    comparisons = 0
    for left_index, left in enumerate(products):
        for right in products[left_index + 1 :]:
            comparisons += 1
            if left.category_id != right.category_id:
                differences += 1
    return differences / float(comparisons or 1)


def novelty_score(popularity_map: dict[int, int], items: list[int]) -> float:
    values: list[float] = []
    for product_id in items:
        popularity = popularity_map.get(product_id, 0)
        values.append(1.0 / math.log2(popularity + 2.0))
    return mean(values) if values else 0.0


def build_popularity_map(session: Session) -> dict[int, int]:
    rows = session.execute(
        select(UserBehaviorLog.target_id, func.count(UserBehaviorLog.id))
        .where(
            UserBehaviorLog.target_type == "product",
            UserBehaviorLog.target_id.is_not(None),
        )
        .group_by(UserBehaviorLog.target_id)
    ).all()
    return {int(product_id): int(total) for product_id, total in rows if product_id is not None}


def percentile(values: list[float], ratio: float) -> float:
    if not values:
        return 0.0
    index = min(max(int(math.ceil(len(values) * ratio)) - 1, 0), len(values) - 1)
    return round(float(values[index]), 3)


def evaluate_scenarios() -> dict[str, object]:
    session = create_isolated_session()
    suppress_http_logs()
    app_settings = resolve_app_settings()
    ltr_model_path = build_ltr_weights_file()
    try:
        Base.metadata.create_all(bind=session.get_bind())
        seed_base_data(session)
        runtime_summary = prepare_vector_runtime(session, settings=app_settings)
        session.expire_all()
        popularity_map = build_popularity_map(session)
        catalog_size = int(
            session.scalar(
                select(func.count()).select_from(Product).where(Product.status == 1)
            )
            or 1
        )
        aggregated: dict[str, dict[str, object]] = {
            mode.key: {
                "precision_at_5": [],
                "recall_at_5": [],
                "ndcg_at_5": [],
                "mrr": [],
                "diversity": [],
                "novelty": [],
                "ctr": [],
                "cvr": [],
                "add_to_cart_rate": [],
                "latency_ms": [],
                "recommended_ids": set(),
            }
            for mode in EVALUATION_MODES
        }

        for scenario in SCENARIOS:
            user = ensure_evaluation_user(session, scenario)
            relevant_ids = build_relevant_product_ids(session, scenario)
            click_targets = build_click_targets(relevant_ids)
            conversion_targets = build_conversion_targets(relevant_ids)

            for mode in EVALUATION_MODES:
                items, latency_ms = run_mode(
                    session,
                    user_id=user.id,
                    mode=mode.key,
                    app_settings=app_settings,
                    ltr_model_path=ltr_model_path,
                )
                aggregated[mode.key]["precision_at_5"].append(
                    precision_at_k(items, relevant_ids, TOP_K)
                )
                aggregated[mode.key]["recall_at_5"].append(
                    recall_at_k(items, relevant_ids, TOP_K)
                )
                aggregated[mode.key]["ndcg_at_5"].append(ndcg_at_k(items, relevant_ids, TOP_K))
                aggregated[mode.key]["mrr"].append(mrr(items, relevant_ids))
                aggregated[mode.key]["diversity"].append(diversity_score(session, items))
                aggregated[mode.key]["novelty"].append(novelty_score(popularity_map, items))
                aggregated[mode.key]["ctr"].append(precision_at_k(items, click_targets, TOP_K))
                aggregated[mode.key]["cvr"].append(
                    precision_at_k(items, conversion_targets, TOP_K)
                )
                aggregated[mode.key]["add_to_cart_rate"].append(
                    precision_at_k(items, conversion_targets | click_targets, TOP_K)
                )
                aggregated[mode.key]["latency_ms"].append(latency_ms)
                aggregated[mode.key]["recommended_ids"].update(items)

        report_rows: list[dict[str, object]] = []
        for mode in EVALUATION_MODES:
            values = aggregated[mode.key]
            latencies = sorted(values["latency_ms"])
            report_rows.append(
                {
                    "mode": mode.label,
                    "precision_at_5": round(mean(values["precision_at_5"]), 4),
                    "recall_at_5": round(mean(values["recall_at_5"]), 4),
                    "ndcg_at_5": round(mean(values["ndcg_at_5"]), 4),
                    "mrr": round(mean(values["mrr"]), 4),
                    "coverage": round(
                        len(values["recommended_ids"]) / float(catalog_size),
                        4,
                    ),
                    "diversity": round(mean(values["diversity"]), 4),
                    "novelty": round(mean(values["novelty"]), 4),
                    "ctr": round(mean(values["ctr"]), 4),
                    "cvr": round(mean(values["cvr"]), 4),
                    "add_to_cart_rate": round(mean(values["add_to_cart_rate"]), 4),
                    "p50_latency_ms": percentile(latencies, 0.50),
                    "p95_latency_ms": percentile(latencies, 0.95),
                    "p99_latency_ms": percentile(latencies, 0.99),
                    "note": mode.note,
                }
            )

        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_PATH.write_text(
            render_markdown(report_rows, runtime_summary=runtime_summary),
            encoding="utf-8",
        )
        return {
            "scenarios": [scenario.name for scenario in SCENARIOS],
            "rows": report_rows,
            "runtime": runtime_summary,
            "output": str(OUTPUT_PATH),
        }
    finally:
        session.close()


def render_markdown(
    rows: list[dict[str, object]],
    *,
    runtime_summary: dict[str, object],
) -> str:
    lines = [
        "# Recommendation Evaluation",
        "",
        "## Runtime",
        "",
        f"* qdrant_ready: `{runtime_summary.get('qdrant_ready', False)}`",
        f"* qdrant_url: `{runtime_summary.get('qdrant_url', 'n/a')}`",
        f"* scenarios: `{len(SCENARIOS)}`",
        f"* top_k: `{TOP_K}`",
    ]

    if runtime_summary.get("qdrant_ready"):
        lines.extend(
            [
                f"* qdrant_sync: `{runtime_summary['sync_result']}`",
                f"* collaborative_index: `{runtime_summary['collaborative_result']}`",
                f"* preparation_latency_ms: `{runtime_summary['prep_latency_ms']}`",
            ]
        )
    else:
        lines.append(f"* degradation_reason: `{runtime_summary.get('reason', 'unknown')}`")

    lines.extend(
        [
            "",
            "## Comparison",
            "",
            (
                "| Mode | P@5 | R@5 | NDCG@5 | MRR | Coverage | Diversity | "
                "Novelty | CTR | CVR | Add-to-cart | p50 ms | p95 ms | p99 ms |"
            ),
            (
                "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
            ),
        ]
    )
    for row in rows:
        lines.append(
            "| {mode} | {precision_at_5} | {recall_at_5} | {ndcg_at_5} | {mrr} | "
            "{coverage} | {diversity} | {novelty} | {ctr} | {cvr} | "
            "{add_to_cart_rate} | {p50_latency_ms} | {p95_latency_ms} | "
            "{p99_latency_ms} |".format(**row)
        )

    lines.extend(["", "## Notes", ""])
    for row in rows:
        lines.append(f"* `{row['mode']}`: {row['note']}")
    lines.extend(
        [
            "* `dense_sparse_colbert` 是 hybrid + rerank 的近似实验，"
            "复用了 dense+sparse 召回后接排序层。",
            "* `multi_recall_ltr` 与 `multi_recall_ltr_diversity` 的差异在于"
            "是否保留默认探索位和类目连续约束。",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate recommendation quality")
    parser.add_argument("--scenario", default="all", help="Scenario selector")
    args = parser.parse_args()

    if args.scenario != "all":
        raise SystemExit("Only --scenario all is currently supported")

    result = evaluate_scenarios()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
