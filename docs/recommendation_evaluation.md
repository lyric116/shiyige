# Recommendation Evaluation

## Runtime

* qdrant_ready: `True`
* qdrant_url: `http://127.0.0.1:6333`
* scenarios: `3`
* top_k: `5`
* qdrant_sync: `{'mode': 'full', 'indexed': 20, 'payload_updates': 0, 'deleted': 0, 'skipped': 0, 'failed': 0, 'product_ids': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20], 'failed_product_ids': [], 'collection_name': 'shiyige_phase10_eval2_products', 'dense_model_name': 'BAAI/bge-small-zh-v1.5', 'sparse_model_name': 'Qdrant/bm25', 'colbert_model_name': 'answerdotai/answerai-colbert-small-v1'}`
* collaborative_index: `{'collection_name': 'shiyige_phase10_eval2_cf', 'indexed_users': 0, 'qdrant_points': 0, 'item_nodes': 0, 'built_at': '2026-04-24T18:27:16.067120'}`
* preparation_latency_ms: `4871.213`

## Comparison

| Mode | P@5 | R@5 | NDCG@5 | MRR | Coverage | Diversity | Novelty | CTR | CVR | Add-to-cart | p50 ms | p95 ms | p99 ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline | 0.4667 | 0.7778 | 0.6763 | 0.6667 | 0.55 | 0.6667 | 1.0 | 0.2667 | 0.1333 | 0.2667 | 70.618 | 163.335 | 163.335 |
| dense_only | 0.4667 | 0.7778 | 0.6763 | 0.6667 | 0.55 | 0.6667 | 1.0 | 0.2667 | 0.1333 | 0.2667 | 219.449 | 231.403 | 231.403 |
| dense_sparse | 0.5333 | 0.8889 | 0.7545 | 0.6667 | 0.6 | 0.7 | 1.0 | 0.3333 | 0.2 | 0.3333 | 221.622 | 350.927 | 350.927 |
| dense_sparse_colbert | 0.5333 | 0.8889 | 0.7945 | 0.8333 | 0.6 | 0.7333 | 1.0 | 0.4 | 0.2 | 0.4 | 234.726 | 235.236 | 235.236 |
| multi_recall_weighted | 0.5333 | 0.8889 | 0.815 | 0.8333 | 0.65 | 0.7 | 1.0 | 0.4 | 0.2 | 0.4 | 223.046 | 225.987 | 225.987 |
| multi_recall_ltr | 0.6 | 1.0 | 1.0 | 1.0 | 0.7 | 0.6667 | 1.0 | 0.4 | 0.2 | 0.4 | 215.553 | 222.123 | 222.123 |
| multi_recall_ltr_diversity | 0.4 | 0.6667 | 0.7654 | 1.0 | 0.65 | 0.8333 | 1.0 | 0.2 | 0.1333 | 0.2 | 218.163 | 230.919 | 230.919 |

## Notes

* `baseline`: 旧版 Python 余弦 + 规则加分路径。
* `dense_only`: 仅使用 dense 内容召回结果。
* `dense_sparse`: 使用 dense + sparse 混合召回结果。
* `dense_sparse_colbert`: dense + sparse 召回后接排序层作为 hybrid + rerank 对照。
* `multi_recall_weighted`: 多路召回 + 当前线上加权排序器。
* `multi_recall_ltr`: 多路召回 + LTR，关闭探索位并放宽类目连续约束。
* `multi_recall_ltr_diversity`: 多路召回 + LTR + 默认多样性与探索规则。
* `dense_sparse_colbert` 是 hybrid + rerank 的近似实验，复用了 dense+sparse 召回后接排序层。
* `multi_recall_ltr` 与 `multi_recall_ltr_diversity` 的差异在于是否保留默认探索位和类目连续约束。
