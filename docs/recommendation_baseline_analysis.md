# 推荐系统基线分析

## 1. 目的

本文件冻结 2026-04-24 之前项目当前推荐系统的真实实现方式，作为后续 Qdrant、多路召回、协同过滤与重排改造的 baseline。这里描述的是“当前代码如何工作”，不是目标架构。

## 2. 当前实现结论

### 2.1 向量存储方式

当前商品向量和用户兴趣向量仍然保存在 PostgreSQL/SQLite 业务表中：

* `backend/app/models/recommendation.py`
  * `ProductEmbedding.embedding_vector` 是 `JSON` 字段。
  * `UserInterestProfile.embedding_vector` 是 `JSON` 字段。

这意味着当前系统并没有使用独立向量数据库做 ANN 检索，而是把向量当作业务字段存储。

### 2.2 当前搜索链路

当前语义搜索主逻辑位于 `backend/app/services/vector_search.py` 的 `semantic_search_products()`：

1. 使用 `EmbeddingProvider.embed_query()` 生成 query 向量。
2. 通过 SQLAlchemy 一次性加载所有 `status == 1` 的商品及其类目、标签、SKU、embedding。
3. 在 Python 中逐个商品执行 `cosine_similarity()`。
4. 使用 `compute_semantic_bonus()` 叠加类目、朝代、场景、工艺、节令、标签命中的规则加分。
5. 最终按 `score` 排序并返回 TopK。

`find_related_products()` 也是同样模式：

1. 先加载所有上架商品。
2. 在 Python 中把当前商品向量与候选商品向量做余弦相似度比较。
3. 再叠加同类目、同朝代、同场景、同工艺和标签交集 bonus。

当前没有：

* 独立召回层
* 稀疏检索/BM25
* ColBERT late interaction rerank
* ANN/HNSW
* payload filter 下推到向量引擎

### 2.3 当前个性化推荐链路

当前个性化推荐主逻辑位于 `backend/app/services/recommendations.py`：

1. `load_user_behavior_logs()` 读取用户行为日志。
2. `build_profile_segments()` 把搜索词、浏览商品、加购商品、订单商品拼接成画像文本。
3. `build_user_interest_profile()` 使用当前 embedding provider 生成用户画像向量，并写回 `user_interest_profile.embedding_vector`。
4. `rank_recommendation_candidates()` 遍历所有上架商品。
5. `score_recommendation_candidate()` 计算：
   * 用户画像向量和商品向量的 cosine similarity
   * `top_terms` 命中类目/标签/朝代/场景/工艺后的 `term_bonus`
6. `recommend_products_for_user()` 取 TopK 作为“猜你喜欢”。

行为权重固定在 `BEHAVIOR_WEIGHTS`：

* `view_product = 1`
* `search = 2`
* `add_to_cart = 3`
* `create_order = 5`
* `pay_order = 5`

当前没有：

* 多路召回
* 协同过滤
* 重排模型
* 探索/多样性控制
* 曝光日志闭环
* 离线评估指标
* 压测结果

## 3. 当前 embedding 能力

当前 embedding 入口在 `backend/app/services/embedding.py`：

* 默认 provider 是 `local_hash`。
* 可选 `sentence_transformer`，但当前默认配置仍是本地 deterministic hash。
* 当前只有一类 dense vector，没有 sparse vector 和 colbert multivector。

## 4. 当前基线的核心限制

### 4.1 不是独立向量数据库

当前系统虽然有“向量”概念，但搜索与推荐都依赖业务数据库里的 JSON 字段和应用层遍历，无法证明系统已经具备独立向量数据库的检索能力。

### 4.2 规模放大后会退化

`semantic_search_products()` 和 `recommend_products_for_user()` 都要先把候选商品拉到应用层再逐条打分，商品规模扩大后会直接放大响应时间和内存占用。

### 4.3 解释性只停留在规则 bonus

当前 reason 主要来自：

* “语义相近”
* “命中某些标签/类目/朝代/场景”
* “基于近期偏好推荐”

它能解释当前规则，但还没有召回分层、模型版本、重排得分来源等更强证据链。

## 5. 基线评估样本

为了保证升级后可以对照，本轮新增脚本会固定以下样本：

### 5.1 固定搜索 query

* `适合春日出游的素雅汉服`
* `端午香囊送礼`
* `古风发簪饰品`
* `宋韵茶器雅致礼物`

### 5.2 固定推荐用户

* `baseline-hanfu@example.com`
  * 偏好：汉服、春日出游、明制
* `baseline-gift@example.com`
  * 偏好：香囊、发簪、节令送礼

## 6. 基线产物

运行 `python -m backend.scripts.export_baseline_recommendation_metrics` 后会生成：

* `docs/recommendation_baseline_metrics.json`

该文件记录：

* query
* user_id
* returned_product_ids
* top1 score
* top1 reason
* latency_ms
* 全部 TopK 明细

后续每个推荐系统升级阶段都应继续复用这批 query 和用户样本做前后对比。
