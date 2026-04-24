# Recommendation Pipeline

## Goal

Phase 7 upgrades personalized recommendation from a single profile-vector cosine pass into a multi-channel recall pipeline that can expose where each candidate came from.

## Runtime contract

`backend/app/services/recommendations.py` now keeps two paths:

* `baseline_recommend_products_for_user(...)`
  The old PostgreSQL-side full-list traversal baseline.
* `recommend_products_for_user(...)`
  The public entry that prefers the multi-recall pipeline when Qdrant product search is ready, and falls back to the baseline on errors or when readiness checks fail.

The baseline export script explicitly passes `force_baseline=True` so Phase 1 snapshots stay comparable.

## Recall channels

The pipeline is orchestrated by `backend/app/services/recommendation_pipeline.py` and currently uses these channels:

* `content_profile`
  Dense Qdrant recall driven by the user interest profile embedding.
* `sparse_interest`
  Sparse Qdrant recall driven by `top_terms`.
* `collaborative`
  Similar-user recall from overlapping product behavior logs.
* `related_products`
  Qdrant dense recall seeded by the user's recent viewed/carted products.
* `trending`
  Recent site-wide hot products from weighted behavior logs.
* `new_arrival`
  Latest active and in-stock products.
* `cold_start`
  A fallback blend of trending and new-arrival candidates when the user has too little history.

Each recall item keeps:

* `product_id`
* `recall_channel`
* `recall_score`
* `rank_in_channel`
* `matched_terms`
* `reason_parts`

## Fusion and diversity

`backend/app/services/candidate_fusion.py` performs weighted RRF fusion and preserves:

* all contributing channels
* matched terms
* per-channel detail rows
* aggregate fusion score

`backend/app/services/diversity.py` then applies light category / dynasty / craft penalties so the final list does not collapse into a single narrow cluster.

## Debug output

`backend/app/api/v1/admin_recommendations.py` now consumes the pipeline run object directly and exposes:

* user profile text and `top_terms`
* consumed products
* recent behaviors
* candidate `recall_channels`
* per-channel `channel_details`
* fused score, vector score, and matched terms

This turns the admin debug endpoint into a recall-trace view instead of a single-score black box.

## Current scope boundary

This phase adds the multi-recall structure and a first collaborative channel, but does not yet implement the stronger collaborative indexing planned for Phase 8.
