# Recommendation Performance Benchmark

## Dataset

* target_products: `10000`
* target_users: `200`
* requests_per_endpoint: `30`
* concurrency: `8`
* synthetic_catalog: `{'existing_products': 20, 'created_products': 9980, 'target_products': 10000}`
* embedding_mode: `dense=local_hash, sparse=local_hash, colbert=local_hash`
* runtime: `{'configured_provider': 'qdrant', 'recommendation_pipeline_version': 'v1', 'configured_recommendation_ranker': 'weighted_ranker', 'qdrant_available': True, 'qdrant_url': 'http://127.0.0.1:6333', 'qdrant_collections': ['shiyige_collaborative_v1', 'shiyige_products_v1'], 'qdrant_error': None, 'degraded_to_baseline': False, 'active_search_backend': 'qdrant_hybrid', 'active_recommendation_backend': 'multi_recall'}`

## Metrics

| Endpoint | Samples | QPS | Error Rate | Avg Candidates | p50 ms | p95 ms | p99 ms | Notes |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| search_keyword | 30 | 4.492 | 0.0 | 7.333 | 1812.153 | 2713.216 | 3332.066 | GET /api/v1/search |
| search_semantic | 30 | 4.097 | 0.0 | 10.0 | 866.413 | 5500.107 | 5626.913 | POST /api/v1/search/semantic |
| recommend_home | 30 | 0.2 | 0.0 | 6.0 | 31747.117 | 66545.548 | 68090.467 | GET /api/v1/recommendations?slot=home |
| related_products | 24 | 5.721 | 0.0 | 6.0 | 1296.907 | 1702.53 | 1736.894 | GET /api/v1/products/{id}/related (sampled=24) |
| reindex_products_qdrant | 1 | 0.003 | 0.0 | 9997.0 | 331574.515 | 331574.515 | 331574.515 | sync_products_to_qdrant(mode=full) |
| build_collaborative_index | 1 | 4.654 | 0.0 | 200.0 | 214.854 | 214.854 | 214.854 | build_collaborative_index |
