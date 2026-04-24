# Ranking Design

## Goal

Phase 9 adds a unified ranking layer on top of multi-recall recommendation candidates.

The ranking layer is responsible for:

* combining recall, user-interest, product-quality, and business-rule signals
* making the final order explainable in debug output
* supporting `weighted_ranker` now and `ltr_ranker` later
* enforcing diversity and exploration after scoring

## Feature groups

`backend/app/services/ranking_features.py` builds one feature vector per candidate.

Current feature groups include:

* recall features
  * dense recall score
  * sparse recall score
  * ColBERT-style text alignment score
  * collaborative score
  * item cooccurrence score
  * RRF fusion score
  * recall channel count
  * best channel rank
* user-interest features
  * category / tag / dynasty / craft / scene / festival matches
  * price affinity
  * recent-interest score
  * long-term-interest score
* product-quality features
  * sales count
  * conversion rate
  * add-to-cart rate
  * rating average
  * review count
  * stock availability
  * return rate
  * freshness score
  * content quality score
* business-rule features
  * listed / stock / price pass
  * recently exposed
  * already purchased
  * editorial-pick heuristic
  * festival-theme match
  * exploration candidate

## Rankers

`backend/app/services/ranker.py` currently provides the default `weighted_ranker`.

Its score is split into:

* recall score
* interest score
* quality score
* business boost / penalty
* exploration boost

`backend/app/services/ltr_ranker.py` reserves the `ltr_ranker` entry.

Current behavior:

* if `RECOMMENDATION_RANKER=weighted_ranker`, use the weighted ranker directly
* if `RECOMMENDATION_RANKER=ltr_ranker` and a JSON model file exists, load the JSON feature weights
* if `RECOMMENDATION_RANKER=ltr_ranker` but the model file is absent, fall back to `weighted_ranker`

## Post-processing

`backend/app/services/business_rules.py` applies post-ranking constraints:

* duplicate avoidance
* no-stock and already-purchased demotion
* same-category consecutive cap
* same dynasty / craft concentration control
* exploration-slot injection for fresh or `new_arrival` candidates

## Debug output

Both public and admin debug responses now expose:

* `ranker_name`
* `ranker_model_version`
* `ranking_features`
* `feature_summary`
* `feature_highlights`
* `score_breakdown`
* `ltr_fallback_used`

This makes the ranking layer auditable instead of a single opaque score.
