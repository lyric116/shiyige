# Collaborative Filtering Design

## Goal

Phase 8 upgrades the recommendation system from a lightweight behavior-overlap heuristic into two explicit collaborative signals:

* `collaborative_user`
  Similar-user recall from Qdrant sparse user vectors.
* `item_cooccurrence`
  Item-item recall from offline co-occurrence artifacts.

## User sparse vectors

`backend/app/services/collaborative_filtering.py` maps each user into a sparse vector where:

* vector index = `product_id`
* vector value = behavior weight x time decay

Current weights include:

* `view_product = 1.0`
* `search_click = 2.0` (reserved)
* `favorite = 3.0` (reserved)
* `add_to_cart = 4.0`
* `create_order = 5.0`
* `pay_order = 6.0`
* `refund_order / cancel_order = -2.0` (reserved)

Time decay is stronger for old weak signals and slower for strong purchase-intent signals.

## Qdrant collection

`backend/app/tasks/collaborative_index_tasks.py` creates the collaborative collection as a sparse-only Qdrant collection:

* collection: `QDRANT_COLLECTION_CF`
* sparse vector name: `interactions`
* payload: `user_id`, `behavior_count`, `updated_at`

The build task upserts one point per user who has at least one product interaction.

## Item co-occurrence

The same build task computes a co-occurrence map from grouped user product interactions and stores it in `recommendation_experiment`:

* experiment key: `collaborative_item_cooccurrence_v1`
* strategy: `item_cooccurrence`
* artifact: `item_cooccurrence` adjacency map plus build metadata

This makes the item graph durable and inspectable without forcing each request to rebuild it.

## Runtime usage

`backend/app/services/recall_collaborative.py` now delegates to two collaborative services:

* `recall_collaborative_user_candidates(...)`
  Query similar users from Qdrant and aggregate their positive interactions.
* `recall_item_cooccurrence_candidates(...)`
  Expand the current user's recent seed products through the offline co-occurrence graph.

Both channels return standard `RecallItem` objects, so the main recommendation pipeline can fuse them just like dense, sparse, trending, and new-arrival candidates.

## Build entry

Offline build command:

```bash
./.venv/bin/python backend/scripts/build_collaborative_index.py
```

The script writes:

* Qdrant sparse user vectors
* `recommendation_experiment` item co-occurrence artifact

## Scope boundary

This phase adds collaborative retrieval and offline index building, but the final ranking layer still belongs to Phase 9.
