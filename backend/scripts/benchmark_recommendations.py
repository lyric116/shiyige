from __future__ import annotations
# ruff: noqa: E402, I001

import argparse
import asyncio
import json
import logging
import math
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[2]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import AppSettings, get_app_settings
from backend.app.core.database import get_session_factory
from backend.app.core.security import create_access_token, hash_password
from backend.app.main import create_app
from backend.app.models.base import Base
from backend.app.models.product import Product
from backend.app.models.user import User, UserBehaviorLog, UserProfile
from backend.app.services.qdrant_client import get_qdrant_connection_status
from backend.app.services.vector_store import probe_vector_store_runtime
from backend.app.tasks.collaborative_index_tasks import build_collaborative_index
from backend.app.tasks.qdrant_index_tasks import sync_products_to_qdrant
from backend.scripts.generate_synthetic_catalog import ensure_synthetic_catalog
from backend.scripts.seed_base_data import seed_base_data

OUTPUT_PATH = Path("docs/performance_benchmark.md")
QDRANT_LOCAL_URL = "http://127.0.0.1:6333"
SEARCH_QUERIES = ["汉服", "香囊", "非遗", "礼盒", "刺绣", "春日汉服", "国风送礼"]
SEMANTIC_QUERIES = ["春日汉服穿搭", "适合送礼的传统文创", "非遗家居陈设"]


@dataclass(frozen=True, slots=True)
class BenchmarkUserContext:
    user_id: int
    headers: dict[str, str]


@dataclass(slots=True)
class BenchmarkRow:
    endpoint: str
    sample_size: int
    qps: float
    error_rate: float
    avg_candidate_count: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    notes: str


def resolve_app_settings() -> AppSettings:
    settings = get_app_settings()
    if get_qdrant_connection_status(settings).available:
        return settings

    localhost_settings = settings.model_copy(update={"qdrant_url": QDRANT_LOCAL_URL})
    if get_qdrant_connection_status(localhost_settings).available:
        return localhost_settings
    return settings


def build_benchmark_settings() -> AppSettings:
    base_settings = resolve_app_settings()
    return base_settings.model_copy(
        update={
            "embedding_provider": "local_hash",
            "sparse_embedding_provider": "local_hash",
            "colbert_embedding_provider": "local_hash",
        }
    )


def suppress_http_logs() -> None:
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def apply_runtime_settings(settings: AppSettings) -> None:
    os.environ["QDRANT_URL"] = settings.qdrant_url
    os.environ["QDRANT_COLLECTION_PRODUCTS"] = settings.qdrant_collection_products
    os.environ["QDRANT_COLLECTION_CF"] = settings.qdrant_collection_cf
    os.environ["EMBEDDING_PROVIDER"] = settings.embedding_provider
    os.environ["SPARSE_EMBEDDING_PROVIDER"] = settings.sparse_embedding_provider
    os.environ["COLBERT_EMBEDDING_PROVIDER"] = settings.colbert_embedding_provider
    get_app_settings.cache_clear()


def ensure_benchmark_users(
    session: Session,
    *,
    target_users: int,
    product_ids: list[int],
) -> list[BenchmarkUserContext]:
    existing_users = session.scalars(
        select(User)
        .where(User.email.like("benchmark-user-%@example.com"))
        .order_by(User.id.asc())
    ).all()
    existing_count = len(existing_users)
    if existing_count < target_users:
        total_products = len(product_ids)
        for index in range(existing_count + 1, target_users + 1):
            user = User(
                email=f"benchmark-user-{index:05d}@example.com",
                username=f"benchmark_user_{index:05d}",
                password_hash=hash_password("benchmark-pass-123"),
                role="user",
                is_active=True,
            )
            user.profile = UserProfile(display_name=f"benchmark-{index:05d}")
            session.add(user)
            session.flush()

            seed_ids = [
                product_ids[(index - 1) % total_products],
                product_ids[index % total_products],
                product_ids[(index + 1) % total_products],
            ]
            query = SEARCH_QUERIES[(index - 1) % len(SEARCH_QUERIES)]
            session.add_all(
                [
                    UserBehaviorLog(
                        user_id=user.id,
                        behavior_type="search",
                        target_type="search",
                        ext_json={"query": query},
                    ),
                    UserBehaviorLog(
                        user_id=user.id,
                        behavior_type="view_product",
                        target_type="product",
                        target_id=seed_ids[0],
                    ),
                    UserBehaviorLog(
                        user_id=user.id,
                        behavior_type="add_to_cart",
                        target_type="product",
                        target_id=seed_ids[1],
                    ),
                    UserBehaviorLog(
                        user_id=user.id,
                        behavior_type="view_product",
                        target_type="product",
                        target_id=seed_ids[2],
                    ),
                ]
            )
            if index % 100 == 0:
                session.commit()

        session.commit()

    users = session.scalars(
        select(User)
        .where(User.email.like("benchmark-user-%@example.com"))
        .order_by(User.id.asc())
    ).all()[:target_users]
    return [
        BenchmarkUserContext(
            user_id=user.id,
            headers={
                "Authorization": (
                    f"Bearer {create_access_token(str(user.id), role=user.role)}"
                ),
            },
        )
        for user in users
    ]


def percentile(values: list[float], ratio: float) -> float:
    if not values:
        return 0.0
    index = min(max(int(math.ceil(len(values) * ratio)) - 1, 0), len(values) - 1)
    return round(float(values[index]), 3)


def build_row(
    *,
    endpoint: str,
    latencies_ms: list[float],
    candidate_counts: list[int],
    total_elapsed_s: float,
    failures: int,
    notes: str,
) -> BenchmarkRow:
    samples = len(latencies_ms) + failures
    sorted_latencies = sorted(latencies_ms)
    return BenchmarkRow(
        endpoint=endpoint,
        sample_size=samples,
        qps=round(samples / max(total_elapsed_s, 0.001), 3),
        error_rate=round(failures / float(max(samples, 1)), 4),
        avg_candidate_count=round(
            sum(candidate_counts) / float(max(len(candidate_counts), 1)),
            3,
        ),
        p50_latency_ms=percentile(sorted_latencies, 0.50),
        p95_latency_ms=percentile(sorted_latencies, 0.95),
        p99_latency_ms=percentile(sorted_latencies, 0.99),
        notes=notes,
    )


def build_task_row(
    *,
    endpoint: str,
    latency_ms: float,
    candidate_count: int,
    notes: str,
) -> BenchmarkRow:
    return BenchmarkRow(
        endpoint=endpoint,
        sample_size=1,
        qps=round(1000.0 / max(latency_ms, 1.0), 3),
        error_rate=0.0,
        avg_candidate_count=float(candidate_count),
        p50_latency_ms=round(latency_ms, 3),
        p95_latency_ms=round(latency_ms, 3),
        p99_latency_ms=round(latency_ms, 3),
        notes=notes,
    )


async def benchmark_requests(
    client: AsyncClient,
    *,
    endpoint: str,
    specs: list[dict[str, object]],
    notes: str,
    concurrency: int,
) -> BenchmarkRow:
    semaphore = asyncio.Semaphore(concurrency)
    latencies_ms: list[float] = []
    candidate_counts: list[int] = []
    failures = 0

    async def run_spec(spec: dict[str, object]) -> None:
        nonlocal failures
        async with semaphore:
            started_at = perf_counter()
            response = await client.request(
                method=str(spec["method"]),
                url=str(spec["url"]),
                headers=spec.get("headers"),
                params=spec.get("params"),
                json=spec.get("json"),
            )
            latency_ms = (perf_counter() - started_at) * 1000
            if response.status_code >= 400:
                failures += 1
                return
            try:
                body = response.json()
            except Exception:
                failures += 1
                return

            items = body.get("data", {}).get("items", [])
            if not isinstance(items, list):
                items = []
            latencies_ms.append(round(latency_ms, 3))
            candidate_counts.append(len(items))

    batch_started_at = perf_counter()
    await asyncio.gather(*(run_spec(spec) for spec in specs))
    total_elapsed_s = perf_counter() - batch_started_at
    return build_row(
        endpoint=endpoint,
        latencies_ms=latencies_ms,
        candidate_counts=candidate_counts,
        total_elapsed_s=total_elapsed_s,
        failures=failures,
        notes=notes,
    )


def resolve_request_count(explicit_count: int | None, user_count: int) -> int:
    if explicit_count is not None:
        return explicit_count
    return min(max(30, user_count // 10), 80)


def resolve_related_request_count(sample_count: int) -> int:
    return min(sample_count, 24)


def build_keyword_specs(
    *,
    users: list[BenchmarkUserContext],
    sample_count: int,
) -> list[dict[str, object]]:
    specs: list[dict[str, object]] = []
    for index in range(sample_count):
        user = users[index % len(users)]
        specs.append(
            {
                "method": "GET",
                "url": "/api/v1/search",
                "headers": user.headers,
                "params": {
                    "q": SEARCH_QUERIES[index % len(SEARCH_QUERIES)],
                    "page_size": 10,
                },
            }
        )
    return specs


def build_semantic_specs(
    *,
    users: list[BenchmarkUserContext],
    sample_count: int,
) -> list[dict[str, object]]:
    specs: list[dict[str, object]] = []
    for index in range(sample_count):
        user = users[index % len(users)]
        specs.append(
            {
                "method": "POST",
                "url": "/api/v1/search/semantic",
                "headers": user.headers,
                "json": {
                    "query": SEMANTIC_QUERIES[index % len(SEMANTIC_QUERIES)],
                    "limit": 10,
                },
            }
        )
    return specs


def build_recommendation_specs(
    *,
    users: list[BenchmarkUserContext],
    sample_count: int,
) -> list[dict[str, object]]:
    specs: list[dict[str, object]] = []
    for index in range(sample_count):
        user = users[index % len(users)]
        specs.append(
            {
                "method": "GET",
                "url": "/api/v1/recommendations",
                "headers": user.headers,
                "params": {"slot": "home", "limit": 6},
            }
        )
    return specs


def build_related_specs(
    *,
    product_ids: list[int],
    users: list[BenchmarkUserContext],
    sample_count: int,
) -> list[dict[str, object]]:
    specs: list[dict[str, object]] = []
    for index in range(sample_count):
        user = users[index % len(users)]
        product_id = product_ids[index % len(product_ids)]
        specs.append(
            {
                "method": "GET",
                "url": f"/api/v1/products/{product_id}/related",
                "headers": user.headers,
                "params": {"limit": 6},
            }
        )
    return specs


async def warm_up_endpoints(
    client: AsyncClient,
    *,
    users: list[BenchmarkUserContext],
    product_ids: list[int],
) -> None:
    if not users or not product_ids:
        return

    user = users[0]
    await client.get(
        "/api/v1/search",
        headers=user.headers,
        params={"q": SEARCH_QUERIES[0], "page_size": 10},
    )
    await client.post(
        "/api/v1/search/semantic",
        headers=user.headers,
        json={"query": SEMANTIC_QUERIES[0], "limit": 10},
    )
    await client.get(
        "/api/v1/recommendations",
        headers=user.headers,
        params={"slot": "home", "limit": 6},
    )
    await client.get(
        f"/api/v1/products/{product_ids[0]}/related",
        headers=user.headers,
        params={"limit": 6},
    )


async def run_http_benchmarks(
    *,
    users: list[BenchmarkUserContext],
    product_ids: list[int],
    sample_count: int,
    concurrency: int,
) -> list[BenchmarkRow]:
    related_sample_count = resolve_related_request_count(sample_count)
    app = create_app()
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(
        transport=transport,
        base_url="http://benchmark.local",
    ) as client:
        await warm_up_endpoints(
            client,
            users=users,
            product_ids=product_ids,
        )
        return [
            await benchmark_requests(
                client,
                endpoint="search_keyword",
                specs=build_keyword_specs(users=users, sample_count=sample_count),
                notes="GET /api/v1/search",
                concurrency=concurrency,
            ),
            await benchmark_requests(
                client,
                endpoint="search_semantic",
                specs=build_semantic_specs(users=users, sample_count=sample_count),
                notes="POST /api/v1/search/semantic",
                concurrency=concurrency,
            ),
            await benchmark_requests(
                client,
                endpoint="recommend_home",
                specs=build_recommendation_specs(users=users, sample_count=sample_count),
                notes="GET /api/v1/recommendations?slot=home",
                concurrency=concurrency,
            ),
            await benchmark_requests(
                client,
                endpoint="related_products",
                specs=build_related_specs(
                    product_ids=product_ids,
                    users=users,
                    sample_count=related_sample_count,
                ),
                notes=(
                    "GET /api/v1/products/{id}/related "
                    f"(sampled={related_sample_count})"
                ),
                concurrency=concurrency,
            ),
        ]


def render_markdown(
    rows: list[BenchmarkRow],
    *,
    products: int,
    users: int,
    sample_count: int,
    concurrency: int,
    dataset_result: dict[str, int],
    runtime_summary: dict[str, object],
    settings: AppSettings,
) -> str:
    lines = [
        "# Recommendation Performance Benchmark",
        "",
        "## Dataset",
        "",
        f"* target_products: `{products}`",
        f"* target_users: `{users}`",
        f"* requests_per_endpoint: `{sample_count}`",
        f"* concurrency: `{concurrency}`",
        f"* synthetic_catalog: `{dataset_result}`",
        (
            "* embedding_mode: "
            f"`dense={settings.embedding_provider}, "
            f"sparse={settings.sparse_embedding_provider}, "
            f"colbert={settings.colbert_embedding_provider}`"
        ),
        f"* runtime: `{runtime_summary}`",
        "",
        "## Metrics",
        "",
        (
            "| Endpoint | Samples | QPS | Error Rate | Avg Candidates | "
            "p50 ms | p95 ms | p99 ms | Notes |"
        ),
        "|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            "| {endpoint} | {sample_size} | {qps} | {error_rate} | "
            "{avg_candidate_count} | {p50_latency_ms} | {p95_latency_ms} | "
            "{p99_latency_ms} | {notes} |".format(**asdict(row))
        )
    return "\n".join(lines) + "\n"


def benchmark_recommendations(
    *,
    products: int,
    users: int,
    request_count: int | None,
    concurrency: int,
) -> dict[str, object]:
    session = get_session_factory()()
    suppress_http_logs()
    settings = build_benchmark_settings()
    apply_runtime_settings(settings)
    try:
        Base.metadata.create_all(bind=session.get_bind())
        seed_base_data(session)
        dataset_result = ensure_synthetic_catalog(session, target_products=products)
        product_ids = session.scalars(
            select(Product.id).where(Product.status == 1).order_by(Product.id.asc())
        ).all()
        benchmark_users = ensure_benchmark_users(
            session,
            target_users=users,
            product_ids=product_ids,
        )

        sync_started_at = perf_counter()
        sync_result = sync_products_to_qdrant(
            session,
            mode="full",
            settings=settings,
        )
        sync_latency_ms = round((perf_counter() - sync_started_at) * 1000, 3)

        collaborative_started_at = perf_counter()
        collaborative_result = build_collaborative_index(session, settings=settings)
        collaborative_latency_ms = round(
            (perf_counter() - collaborative_started_at) * 1000,
            3,
        )

        runtime_summary = probe_vector_store_runtime(settings).to_dict()
        sample_count = resolve_request_count(request_count, users)
        http_rows = asyncio.run(
            run_http_benchmarks(
                users=benchmark_users,
                product_ids=product_ids,
                sample_count=sample_count,
                concurrency=concurrency,
            )
        )
        task_rows = [
            build_task_row(
                endpoint="reindex_products_qdrant",
                latency_ms=sync_latency_ms,
                candidate_count=int(sync_result.get("indexed", 0)),
                notes="sync_products_to_qdrant(mode=full)",
            ),
            build_task_row(
                endpoint="build_collaborative_index",
                latency_ms=collaborative_latency_ms,
                candidate_count=int(collaborative_result.get("indexed_users", 0)),
                notes="build_collaborative_index",
            ),
        ]
        rows = [*http_rows, *task_rows]

        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_PATH.write_text(
            render_markdown(
                rows,
                products=products,
                users=users,
                sample_count=sample_count,
                concurrency=concurrency,
                dataset_result=dataset_result,
                runtime_summary=runtime_summary,
                settings=settings,
            ),
            encoding="utf-8",
        )
        return {
            "products": products,
            "users": users,
            "request_count": sample_count,
            "concurrency": concurrency,
            "runtime": runtime_summary,
            "dataset": dataset_result,
            "rows": [asdict(row) for row in rows],
            "output": str(OUTPUT_PATH),
        }
    finally:
        session.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark recommendation endpoints")
    parser.add_argument("--products", type=int, default=1000, help="Target total product count")
    parser.add_argument("--users", type=int, default=200, help="Synthetic user count")
    parser.add_argument(
        "--requests",
        type=int,
        default=None,
        help="Requests per endpoint; defaults to a size derived from --users",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=8,
        help="Concurrent request count for HTTP benchmarks",
    )
    args = parser.parse_args()

    result = benchmark_recommendations(
        products=args.products,
        users=args.users,
        request_count=args.requests,
        concurrency=max(args.concurrency, 1),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
