# Search Pipeline

## Goal

Phase 6 upgrades semantic search from PostgreSQL-side full-table cosine traversal to a Qdrant-first hybrid retrieval pipeline, while keeping the old Python traversal as an explicit baseline fallback.

## Runtime behavior

`backend/app/services/vector_store.py` now marks search as `qdrant_hybrid` only when all of the following are true:

* `VECTOR_DB_PROVIDER=qdrant`
* Qdrant is reachable
* the product collection exists
* the collection schema matches the current embedding configuration
* the collection already contains indexed product points

If any of those checks fail, semantic search degrades to the baseline path and keeps the existing JSON-vector cosine traversal.

## Request filters

`POST /api/v1/search/semantic` now supports these structured filters:

* `category_id`
* `min_price`
* `max_price`
* `dynasty_style`
* `craft_type`
* `scene_tag`
* `festival_tag`
* `stock_only` (default `true`)

The same filter model is reused for:

* Qdrant payload filtering
* baseline fallback filtering
* semantic search behavior logs

## Hybrid retrieval stages

The Qdrant path is implemented in `backend/app/services/hybrid_search.py`:

1. normalize query text
2. build dense, sparse, and ColBERT query embeddings
3. apply Qdrant payload filter
4. dense recall top 100 from named vector `dense`
5. sparse recall top 100 from named vector `sparse`
6. fuse candidates in application code with RRF
7. fetch top 50 candidate ColBERT vectors from Qdrant
8. rerank with local ColBERT max-sim scoring
9. apply business bonuses and structured-match bonuses
10. load only final candidate products from PostgreSQL for serialization

This removes the old pattern of loading all active products into Python just to compute semantic search scores.

## Reason generation

Returned `reason` strings are assembled from these signals:

* semantic recall hit
* sparse keyword hit
* matched cultural attributes or tags
* ColBERT rerank promotion / hybrid precision confirmation

Example reason shapes:

* `与“香囊”语义相关，关键词命中“香囊”，文化特征匹配“香囊/端午”，经混合检索精排`
* `与“端午送礼”语义相关，关键词命中“端午/送礼”，文化特征匹配“端午/礼盒”，ColBERT 重排提升`

## Fallback contract

`backend/app/services/vector_search.py` still exposes:

* `semantic_search_products(...)` as the public search entry
* `baseline_semantic_search_products(...)` as the preserved old path

The baseline export script now passes `force_baseline=True`, so Phase 1 baseline reports remain stable even after hybrid search becomes the default runtime.
