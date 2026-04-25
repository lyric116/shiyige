from backend.app.core.config import AppSettings
from backend.scripts.benchmark_recommendations import (
    BenchmarkRow,
    build_arg_parser,
    render_markdown,
    resolve_sample_plan,
)


def test_build_arg_parser_accepts_large_scale_benchmark_flags() -> None:
    parser = build_arg_parser()
    args = parser.parse_args(
        [
            "--products",
            "100000",
            "--users",
            "1000",
            "--requests",
            "40",
            "--search-requests",
            "60",
            "--semantic-requests",
            "24",
            "--recommendation-requests",
            "18",
            "--related-requests",
            "12",
            "--mode",
            "light",
            "--concurrency",
            "16",
        ]
    )

    assert args.products == 100000
    assert args.users == 1000
    assert args.requests == 40
    assert args.search_requests == 60
    assert args.semantic_requests == 24
    assert args.recommendation_requests == 18
    assert args.related_requests == 12
    assert args.mode == "light"
    assert args.concurrency == 16


def test_resolve_sample_plan_supports_light_mode_and_endpoint_overrides() -> None:
    plan = resolve_sample_plan(
        user_count=400,
        request_count=None,
        mode="light",
        search_requests=18,
        semantic_requests=None,
        recommendation_requests=9,
        related_requests=7,
    )

    assert plan == {
        "search_keyword": 18,
        "search_semantic": 16,
        "recommend_home": 9,
        "related_products": 7,
    }


def test_render_markdown_includes_mode_sample_plan_and_preparation() -> None:
    markdown = render_markdown(
        [
            BenchmarkRow(
                endpoint="recommend_home",
                sample_size=8,
                qps=1.25,
                error_rate=0.0,
                avg_candidate_count=6.0,
                p50_latency_ms=120.0,
                p95_latency_ms=180.0,
                p99_latency_ms=220.0,
                notes="GET /api/v1/recommendations?slot=home",
            )
        ],
        products=20000,
        users=400,
        sample_plan={
            "search_keyword": 20,
            "search_semantic": 16,
            "recommend_home": 12,
            "related_products": 10,
        },
        concurrency=8,
        mode="light",
        dataset_result={
            "existing_products": 20,
            "created_products": 19980,
            "target_products": 20000,
        },
        preparation={
            "seed_base_data_ms": 12.5,
            "dataset_generation_ms": 230.0,
            "benchmark_user_seed_ms": 66.0,
            "reindex_products_qdrant_ms": 0.0,
            "build_collaborative_index_ms": 0.0,
            "heavy_prep_enabled": False,
            "mode": "light",
        },
        runtime_summary={"active_recommendation_backend": "baseline"},
        settings=AppSettings(
            embedding_provider="local_hash",
            sparse_embedding_provider="local_hash",
            colbert_embedding_provider="local_hash",
        ),
    )

    assert "* mode: `light`" in markdown
    assert "* requests_by_endpoint: `{'search_keyword': 20" in markdown
    assert "## Preparation" in markdown
    assert "heavy_prep_enabled" in markdown
    assert "| recommend_home | 8 | 1.25 | 0.0 | 6.0 |" in markdown
