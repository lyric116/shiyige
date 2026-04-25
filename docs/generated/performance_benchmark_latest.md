# Recommendation Performance Benchmark

## Dataset

* target_products: `20000`
* target_users: `400`
* mode: `light`
* requests_by_endpoint: `{'search_keyword': 20, 'search_semantic': 10, 'recommend_home': 10, 'related_products': 10}`
* concurrency: `8`
* synthetic_catalog: `{'existing_products': 20, 'created_products': 19980, 'target_products': 20000}`
* embedding_mode: `dense=local_hash, sparse=local_hash, colbert=local_hash`
* runtime: `{'configured_provider': 'qdrant', 'recommendation_pipeline_version': 'v1', 'configured_recommendation_ranker': 'weighted_ranker', 'qdrant_available': True, 'qdrant_url': 'http://127.0.0.1:6333', 'qdrant_collections': ['shiyige_collaborative_v1', 'shiyige_products_v1'], 'qdrant_error': None, 'degraded_to_baseline': False, 'active_search_backend': 'qdrant_hybrid', 'active_recommendation_backend': 'multi_recall'}`

## Preparation

* preparation: `{'seed_base_data_ms': 63.396, 'dataset_generation_ms': 15582.811, 'benchmark_user_seed_ms': 2305.205, 'reindex_products_qdrant_ms': 0.0, 'build_collaborative_index_ms': 0.0, 'heavy_prep_enabled': False, 'mode': 'light'}`

## Metrics

| Endpoint | Samples | QPS | Error Rate | Avg Candidates | p50 ms | p95 ms | p99 ms | Notes |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| search_keyword | 20 | 2.078 | 0.0 | 7.5 | 3324.345 | 6301.349 | 6975.095 | GET /api/v1/search |
| search_semantic | 10 | 2.941 | 0.0 | 10.0 | 2475.024 | 3399.928 | 3399.928 | POST /api/v1/search/semantic |
| recommend_home | 10 | 0.088 | 0.0 | 6.0 | 101830.522 | 103226.541 | 103226.541 | GET /api/v1/recommendations?slot=home |
| related_products | 10 | 6.232 | 0.0 | 6.0 | 1284.741 | 1433.977 | 1433.977 | GET /api/v1/products/{id}/related (sampled=10) |
| reindex_products_qdrant | 1 | 1000.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | skipped: light mode disables heavy prep steps |
| build_collaborative_index | 1 | 1000.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | skipped: light mode disables heavy prep steps |
