# 搜索系统流程说明

## 1. 升级目标

旧版搜索的问题是：

* 语义搜索依赖 PostgreSQL 里的 JSON 向量与 Python 全量遍历；
* 关键词搜索和语义搜索之间没有统一解释层；
* 无法证明搜索是 hybrid retrieval，而不是“换个名字的 cosine 排序”。

升级后的目标是：

```text
Query -> dense recall + sparse recall -> RRF -> ColBERT rerank -> 解释生成
```

## 2. 总体流程图

```text
User Query
   |
   +-> normalize_text_piece()
   |
   +-> dense embedding
   +-> sparse embedding
   +-> optional ColBERT query vectors
   |
   +-> Qdrant payload filter
   |
   +-> dense recall topK
   +-> sparse recall topK
   |
   +-> RRF fusion
   +-> ColBERT rerank
   +-> business bonuses / cultural matches
   |
   +-> final score + reason + explanations
   |
   +-> front/category-page.js 可视化展示
```

## 3. 运行时切换

搜索正式入口：

* `backend/app/services/vector_search.py`

运行时就绪判断：

* `backend/app/services/vector_store.py`

只有满足以下条件时，系统才切到 `qdrant_hybrid`：

1. `VECTOR_DB_PROVIDER=qdrant`
2. Qdrant 可达
3. 商品 collection 已存在
4. collection schema 与当前 embedding 配置一致
5. collection 内已有 indexed points

否则搜索会显式退回 baseline，而不是静默报错。

## 4. 接口形态

当前搜索相关接口：

* `GET /api/v1/search`
* `GET /api/v1/search/suggestions`
* `POST /api/v1/search/semantic`

Phase 11 之后，前台展示直接消费以下字段：

* `reason`
* `search_mode`
* `score`
* `explanations`

因此搜索页可以直接显示：

* 语义相关
* 关键词命中
* 文化标签匹配

## 5. Hybrid 检索细节

Qdrant 路径位于：

* `backend/app/services/hybrid_search.py`

当前阶段的关键步骤是：

1. 归一化 query
2. 生成 dense query vector
3. 生成 sparse query vector
4. 生成 ColBERT query vectors
5. 下推 payload filter
6. dense recall top 100
7. sparse recall top 100
8. 使用 RRF 融合
9. 对前 50 候选做 ColBERT late interaction rerank
10. 叠加文化属性、标签、类目和业务 bonus
11. 回表加载最终商品

## 6. 过滤条件

当前语义搜索支持：

* `category_id`
* `min_price`
* `max_price`
* `dynasty_style`
* `craft_type`
* `scene_tag`
* `festival_tag`
* `stock_only`

这些条件同时复用在：

* Qdrant payload filter
* baseline fallback filtering
* 搜索日志记录

这保证了“混合检索”和“基线检索”在过滤语义上是对齐的。

## 7. RRF 与 ColBERT 的作用

### 7.1 为什么先做 RRF

RRF 负责解决：

* dense 语义召回偏泛化
* sparse 关键词召回偏精确

的问题。

它的作用是先把两种来源的候选合并到同一名单，再进入 rerank。

### 7.2 为什么再做 ColBERT rerank

ColBERT 负责解决：

* dense/sparse 候选融合后仍然不够细粒度
* query token 与商品 token 的 late interaction 需要更强的精排能力

因此当前搜索不是“dense 或 sparse 二选一”，而是：

```text
dense + sparse 召回 -> RRF -> ColBERT rerank
```

## 8. 理由与解释生成

当前 `reason` 文本由这些信号拼出：

* dense semantic hit
* sparse keyword hit
* 文化标签/工艺/朝代/场景命中
* ColBERT rerank 提升

返回给前台的 `explanations` 标签，主要用来做更简洁的 UI 证据展示。

## 9. 性能优化

当前已经做的优化：

* 候选召回放在 Qdrant，不再把全量商品先读进 Python
* 过滤条件下推到 payload filter
* 只对前 50 候选做 ColBERT rerank
* 只回表最终候选商品
* Qdrant 连接状态做短 TTL 缓存

当前仍然存在的性能边界：

* 大规模 rerank 仍受本地 CPU 限制
* 相似商品接口仍未完全走 ANN-only 路径
* 搜索页结果缓存目前仍较保守

## 10. 基线保留的意义

当前系统保留：

* `semantic_search_products(...)`
* `baseline_semantic_search_products(...)`

原因不是“舍不得删旧代码”，而是为了：

* 做 baseline 对照实验
* 做运行时降级
* 在答辩时明确说明旧版与新版差异

## 11. 与旧版本的对照结论

| 旧版 | 当前版本 |
| --- | --- |
| PostgreSQL JSON 向量 + Python cosine | Qdrant dense/sparse/multivector hybrid search |
| 全量商品进入 Python 参与排序 | 只回表最终候选 |
| 搜索页几乎没有解释 | 有 `reason`、`search_mode`、`explanations` |
| 结构化过滤与语义检索耦合松散 | 过滤条件统一下推到 payload filter |

## 12. 答辩时的核心结论

当前搜索系统可以明确回答：

* 不是简单 cosine search。
* 而是 dense + sparse 混合召回、RRF 融合、ColBERT 重排，再结合文化标签和业务规则生成最终解释的 hybrid search。
