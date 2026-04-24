# Indexing Operations

## Goal

Phase 5 moves product vectors from PostgreSQL-only storage into Qdrant point storage so search and recommendation can stop depending on ad hoc full-table scans in later phases.

## Current Write Path

- Dense vectors are still persisted in `product_embedding.embedding_vector` for baseline compatibility.
- Qdrant becomes the authoritative retrieval index for:
  - dense named vector: `dense`
  - sparse named vector: `sparse`
  - late interaction multivector: `colbert`
- PostgreSQL stores sync metadata:
  - `qdrant_point_id`
  - `qdrant_collection`
  - `index_status`
  - `index_error`
  - `last_indexed_at`

## Product Payload Fields

Each product point carries:

- `status`
- `category_id`
- `category_name`
- `dynasty_style`
- `craft_type`
- `scene_tag`
- `festival_tag`
- `tags`
- `price_min`
- `price_max`
- `stock_available`
- `embedding_model_version`
- `content_hash`
- `title_text`
- `semantic_text`
- `keyword_text`
- `rerank_text`

This is enough for later payload filtering, candidate explanation, and indexing diagnostics.

## CLI Commands

Full rebuild:

```bash
./.venv/bin/python backend/scripts/reindex_products_to_qdrant.py --mode full
```

Incremental sync for one product:

```bash
./.venv/bin/python backend/scripts/reindex_products_to_qdrant.py --mode incremental --product-id 3
```

Retry failed products:

```bash
./.venv/bin/python backend/scripts/reindex_products_to_qdrant.py --mode retry_failed
```

Delete points for removed or hidden products:

```bash
./.venv/bin/python backend/scripts/reindex_products_to_qdrant.py --mode delete --product-id 3
```

## Admin API

- `GET /api/v1/admin/vector-index/products/status`
  - returns collection status, active catalog size, indexed row count, Qdrant point count, and failed product list
- `POST /api/v1/admin/vector-index/products/sync`
  - payload:
    - `{"mode":"full"}`
    - `{"mode":"incremental","product_ids":[3]}`
    - `{"mode":"retry_failed"}`
    - `{"mode":"delete","product_ids":[3]}`

## Incremental Rules

- If text content changes, vectors and payload are rebuilt.
- If price, inventory, or status changes without text changes, payload can be updated without recomputing all vectors.
- If product status becomes inactive, the point is deleted from Qdrant and PostgreSQL metadata is marked `inactive`.
- If Qdrant writes fail, PostgreSQL metadata is marked `failed` with the error text so retry jobs have a stable source of truth.

## Validation Checklist

- `docker compose up -d`
- `./.venv/bin/python backend/scripts/reindex_products_to_qdrant.py --mode full`
- `curl -s http://127.0.0.1:6333/collections/shiyige_products_v1`
- `./.venv/bin/python -m pytest backend/tests/test_product_qdrant_indexing.py -q`

## Operational Note

`backend/.cache/fastembed` is ignored by Git and mounted to a named Docker volume, so model downloads are reused locally without polluting repository history.
