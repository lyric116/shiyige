# Recommendation Performance Benchmark

## Dataset

* target_products: `10000`
* target_users: `1000`
* requests_per_endpoint: `80`
* concurrency: `8`
* synthetic_catalog: `{'existing_products': 20, 'created_products': 9980, 'target_products': 10000}`
* embedding_mode: `dense=local_hash, sparse=local_hash, colbert=local_hash`
* runtime: `{'configured_provider': 'qdrant', 'recommendation_pipeline_version': 'v1', 'configured_recommendation_ranker': 'weighted_ranker', 'qdrant_available': True, 'qdrant_url': 'http://127.0.0.1:6333', 'qdrant_collections': ['shiyige_collaborative_v1', 'shiyige_phase10_bench_full2_cf', 'shiyige_phase10_bench_full2_products', 'shiyige_phase10_bench_full3_cf', 'shiyige_phase10_bench_full3_products', 'shiyige_phase10_bench_full_products', 'shiyige_phase10_bench_smoke2_cf', 'shiyige_phase10_bench_smoke2_products', 'shiyige_phase10_bench_smoke_cf', 'shiyige_phase10_bench_smoke_products', 'shiyige_phase10_eval2_cf', 'shiyige_phase10_eval2_products', 'shiyige_phase10_eval_cf', 'shiyige_phase10_eval_products', 'shiyige_products_v1'], 'qdrant_error': None, 'degraded_to_baseline': False, 'active_search_backend': 'qdrant_hybrid', 'active_recommendation_backend': 'multi_recall'}`

## Metrics

| Endpoint | Samples | QPS | Error Rate | Avg Candidates | p50 ms | p95 ms | p99 ms | Notes |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| search_keyword | 80 | 4.61 | 0.0 | 7.25 | 1631.287 | 3214.436 | 3318.693 | GET /api/v1/search |
| search_semantic | 80 | 1.734 | 0.0 | 10.0 | 4653.092 | 5484.978 | 5705.362 | POST /api/v1/search/semantic |
| recommend_home | 80 | 0.246 | 0.0 | 6.0 | 32800.354 | 38565.256 | 41700.201 | GET /api/v1/recommendations?slot=home |
| related_products | 24 | 0.133 | 0.0 | 6.0 | 58277.055 | 65666.73 | 68787.423 | GET /api/v1/products/{id}/related (sampled=24) |
| reindex_products_qdrant | 1 | 0.004 | 0.0 | 9999.0 | 230869.141 | 230869.141 | 230869.141 | sync_products_to_qdrant(mode=full) |
| build_collaborative_index | 1 | 4.303 | 0.0 | 1000.0 | 232.405 | 232.405 | 232.405 | build_collaborative_index |
