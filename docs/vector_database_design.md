# 向量数据库设计

## 1. 升级背景

老师对旧版本的两个核心批评是：

| 旧版本问题 | 升级后方案 |
| --- | --- |
| 向量只存在业务库 JSON 字段里，检索时由 Python 全表扫描做余弦相似度 | 引入 Qdrant 作为独立向量数据库，商品索引迁移到 collection |
| 搜索和推荐本质上都还是“单向量 + 单阶段排序” | 商品索引同时维护 dense、sparse、ColBERT multivector，查询时走多阶段检索 |
| PostgreSQL 同时承担事务库和近似向量检索角色，职责混乱 | PostgreSQL 只保留业务事实和索引同步元数据，Qdrant 负责 ANN / hybrid retrieval |

这次升级后的目标不是“把 pgvector 换个壳”，而是把系统边界改成：

```text
业务事实层: PostgreSQL
向量检索层: Qdrant
运行时编排层: FastAPI services/tasks
展示层: 前台推荐卡片 + 后台索引/效果看板
```

## 2. 为什么不用 pgvector 作为主方案

当前项目没有把 pgvector 作为主检索方案，原因是：

1. 当前搜索和推荐已经不只是 dense 向量检索。
   需要同时承载 dense semantic vector、sparse keyword vector 和 ColBERT late-interaction multivector，Qdrant 对 named vectors 和 sparse/multivector 的支持更直接。
2. 需要把事务库和检索库解耦。
   PostgreSQL 更适合订单、用户、商品、行为日志等强一致业务写入；ANN 检索、payload filter 和 rerank 候选召回更适合放到专门的向量库。
3. 需要明确“降级”和“切换”状态。
   现在 `backend/app/services/vector_store.py` 会基于 Qdrant 连通性、collection schema 和 point count 明确判断是否切换到 `qdrant_hybrid` / `multi_recall`，而不是把所有逻辑继续塞进 SQL 查询里。
4. 需要答辩上能清楚证明“这不是只算余弦”。
   只在 PostgreSQL 里存 embedding 再做 cosine，很难证明系统是完整的多阶段检索架构；独立 Qdrant collection、payload index、索引状态看板和重建脚本能直接展示系统升级的工程化结果。

## 3. 为什么选择 Qdrant

Qdrant 在当前项目里的优势有四点：

1. 原生支持 dense / sparse / multivector。
2. 支持 payload filter，能把类目、价格、节令、工艺、库存状态直接下推到检索层。
3. 管理与答辩友好。
   当前后台已经能直接展示 Qdrant 连接状态、collection 状态、已索引商品数和失败商品数。
4. 与当前 Python 技术栈接线成本低。
   现有 `backend/app/services/qdrant_client.py`、`backend/app/tasks/qdrant_schema_tasks.py`、`backend/app/tasks/qdrant_index_tasks.py` 已把 schema 守护、数据同步和运行时探活都固定成可复用模块。

## 4. 当前总体架构

```text
Product / UserBehavior / Order / Review
        |
        v
PostgreSQL (业务事实库)
  - product
  - user_behavior_log
  - recommendation_experiment
  - product_embedding / user_interest_profile (同步元数据)
        |
        |  build embedding / build sparse interactions / sync payload
        v
Qdrant
  - shiyige_products_v1
  - shiyige_collaborative_v1
        |
        v
FastAPI Services
  - hybrid search
  - multi-recall recommendation
  - ranking / diversity / explanation
        |
        v
Front / Admin
  - 搜索解释
  - 推荐来源与理由
  - Qdrant 状态看板
```

## 5. Collection 设计

### 5.1 商品 collection

当前主 collection：

* `shiyige_products_v1`

point id 设计：

* 直接使用业务 `product_id`
* 同步元数据里的 `product_embedding.qdrant_point_id` 与 point id 一一对应

named vectors 设计：

| Vector | 维度 | 用途 |
| --- | ---: | --- |
| `dense` | `512` | 语义召回 |
| `sparse` | `0` | 关键词/BM25 通道 |
| `colbert` | `96` | late interaction rerank |

### 5.2 协同过滤 collection

当前协同过滤 collection：

* `shiyige_collaborative_v1`

用途：

* 保存用户侧 sparse interaction vector
* 支持 `collaborative_user` 召回

## 6. Payload 设计

商品 collection 当前最重要的 payload 字段包括：

* `product_id`
* `name`
* `subtitle`
* `category_id`
* `category_name`
* `tags`
* `dynasty_style`
* `craft_type`
* `scene_tag`
* `festival_tag`
* `price_min`
* `price_max`
* `stock_available`
* `status`
* `sales_count`
* `review_count`
* `rating_avg`
* `created_at`
* `updated_at`
* `content_hash`
* `embedding_model_version`
* `index_version`
* `semantic_text`

这意味着 Qdrant 不只是“放一个向量”，而是能直接参与：

* 结构化过滤
* 文化标签解释
* rerank 候选回表前的业务约束
* 后台索引状态展示

## 7. Payload Index 设计

当前已经建立或要求建立的 payload index 主要覆盖：

* `status`
* `category_id`
* `category_name`
* `dynasty_style`
* `craft_type`
* `scene_tag`
* `festival_tag`
* `tags`
* `price_min`
* `stock_available`
* `embedding_model_version`

这些索引的作用不是“追求理论完整”，而是支撑答辩时能明确说明：

* 搜索不是先全量取回再 Python 过滤；
* 结构化筛选是下推到向量库完成的；
* 节令、工艺、价格和库存这些业务条件与向量检索是同一条运行链。

## 8. PostgreSQL 与 Qdrant 的职责边界

### 8.1 PostgreSQL 负责

* 商品主数据、订单、用户、行为日志、评论等事务事实
* 推荐实验配置和离线工件元数据
* 索引同步状态

### 8.2 Qdrant 负责

* dense / sparse / multivector 检索
* hybrid search 候选召回
* payload filter
* collaborative sparse retrieval

### 8.3 同步元数据落点

`product_embedding` 里当前保留：

* `model_name`
* `content_hash`
* `qdrant_point_id`
* `qdrant_collection`
* `index_status`
* `index_error`
* `last_indexed_at`

`user_interest_profile` 里当前保留：

* `profile_version`
* `qdrant_user_point_id`
* `last_synced_at`

这些字段说明 PostgreSQL 不再承担主检索，而是承担“业务对象与向量索引之间的同步事实表”角色。

## 9. 数据流

### 9.1 商品入索引

```text
product / tags / skus / inventory
    -> embedding_text.py 生成稳定文本与 hash
    -> embedding_tasks.py 生成 dense embedding 元数据
    -> qdrant_index_tasks.py 写入 named vectors + payload
    -> admin/reindex.html 展示状态
```

### 9.2 搜索查询

```text
query
  -> dense embedding
  -> sparse embedding
  -> payload filter
  -> Qdrant dense recall + sparse recall
  -> RRF 融合
  -> ColBERT rerank
  -> 回表加载最终商品
```

### 9.3 推荐查询

```text
user behavior
  -> user_interest_profile
  -> content/sparse/collaborative/trending/new channels
  -> candidate fusion
  -> ranker
  -> business rules / diversity
  -> source_label + reason 返回前台/后台
```

## 10. 运行时降级策略

当前系统不是强行要求 Qdrant 永远可用，而是显式支持降级：

* Qdrant 不可达时，`active_search_backend=baseline`
* collection 不存在或 point count 为 0 时，保持 baseline
* 推荐链路会退回旧版 baseline 推荐

这也是为什么后台和健康检查里会直接返回：

* `qdrant_available`
* `degraded_to_baseline`
* `active_search_backend`
* `active_recommendation_backend`

答辩时可以明确说明：当前系统不是“把所有希望都压在向量库上”，而是有可观测、可回退的运行时策略。

## 11. 结论

升级后的系统已经完成从“业务库里存 embedding + Python 余弦排序”到“独立向量数据库 + 多向量索引 + 运行时切换 + 后台可视化”的架构跃迁。

因此当前项目可以明确回答：

* 不是只用 pgvector。
* 不是只算余弦相似度。
* 而是 PostgreSQL 负责业务事实，Qdrant 负责多向量检索，FastAPI 负责检索编排与解释展示的完整推荐系统。
