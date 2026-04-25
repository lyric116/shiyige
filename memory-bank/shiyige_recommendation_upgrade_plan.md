# 「拾遗阁」项目推荐系统与向量数据库升级落地计划

> 适用项目：`lyric116/shiyige`  
> 原项目题目：基于向量数据库的古风文化商品智能推荐购物网站  
> 目标：把当前“JSON 向量 + Python 全量余弦计算 + 规则加分”的推荐雏形，升级为“独立向量数据库 + 混合召回 + 协同过滤 + 多阶段排序 + 可解释 + 可评估 + 可压测”的完整推荐系统。  
> 重要约束：本文只给落地计划、修改范围、验收方式和 AI 工作者指令，不包含具体代码实现。

---

## 0. 当前问题定位

### 0.1 老师批评点是否成立

当前项目存在以下问题：

1. **没有真正使用独立向量数据库。**
   - 当前 `docker-compose.yml` 使用的是 `pgvector/pgvector:pg16`。
   - `backend/app/models/recommendation.py` 中商品向量和用户兴趣向量是 `JSON` 字段。
   - `backend/app/services/vector_search.py` 中搜索逻辑会先把所有上架商品加载到 Python，再逐个计算余弦相似度。
   - 这更像“把向量存在业务库，再在应用层暴力遍历”，而不是“基于向量数据库的高性能检索”。

2. **推荐系统过于简单。**
   - 当前推荐主要由行为权重、用户画像文本、商品向量余弦相似度和标签命中加分组成。
   - 缺少独立召回层、混合检索、协同过滤、重排模型、冷启动、去重多样性、曝光日志、离线评估、性能压测和线上指标。

3. **不应只用余弦距离作为推荐算法。**
   - 改进后必须同时包含：
     - dense semantic retrieval
     - sparse/BM25 retrieval
     - ColBERT late interaction reranking
     - collaborative filtering
     - learning-to-rank 或可替换的高级排序器
     - 多样性、业务规则、冷启动和探索机制

---

## 1. 总体目标架构

### 1.1 最终架构

保留 PostgreSQL 作为业务数据库，但把向量检索迁移到独立向量数据库 Qdrant。

最终组件：

1. **PostgreSQL**
   - 用户、商品、订单、库存、评价、行为日志、推荐曝光日志、实验配置等业务数据。
   - 不再作为核心向量检索引擎。
   - 可以保留 `product_embedding` 表作为索引元数据和同步状态表，但不再依赖 JSON 向量做查询。

2. **Qdrant**
   - 独立向量数据库。
   - 存储商品 dense 向量、sparse/BM25 向量、ColBERT multivector。
   - 存储协同过滤 sparse user/item vectors。
   - 使用 payload filter 支持类目、价格、朝代、场景、工艺、库存状态等过滤。
   - 使用 HNSW、payload index、quantization、RRF fusion 和 rerank 提升性能与相关性。

3. **Redis**
   - 推荐结果缓存。
   - 热门榜、趋势榜、用户近期行为摘要缓存。
   - 防止每次请求都重建用户画像。

4. **Embedding / Recommendation Worker**
   - 商品向量离线构建。
   - 用户画像增量更新。
   - 协同过滤数据构建。
   - 离线评估任务。
   - 推荐榜单预计算任务。

5. **FastAPI**
   - 对前台提供搜索、首页推荐、相似商品、个性化推荐接口。
   - 对后台提供索引重建、推荐评估、召回调试、模型版本查看接口。

---

## 2. 技术选型

### 2.1 向量数据库选型

推荐主方案：**Qdrant**。

选择理由：

1. 是独立向量搜索引擎，不是关系型数据库扩展。
2. 支持 dense vector、sparse vector、named vectors 和 multivector。
3. 支持混合检索、RRF 融合、payload filter、payload index。
4. 支持 ColBERT late interaction reranking。
5. 支持量化和 HNSW 参数调优，适合展示性能优化。
6. 部署比 Milvus 轻，适合学校比赛和本地 Docker Compose 演示。

备选方案：

- Milvus：更偏大规模向量平台，答辩时听起来也“高级”，但本项目本地落地成本更高。
- Elasticsearch/OpenSearch：适合文本搜索，但不是本项目主打的向量推荐数据库。
- pgvector：不再作为主方案，仅作为对比基线。

最终建议：**使用 Qdrant 作为主向量数据库，保留 pgvector/当前实现作为 baseline 对比。**

---

## 3. 项目最终能力目标

### 3.1 推荐场景

最终至少实现 5 个推荐/搜索场景：

1. **首页个性化推荐**
   - 根据用户近期行为、长期兴趣、协同过滤和热门趋势生成推荐。

2. **搜索页智能检索**
   - 输入“宋代茶具”“中秋送礼”“汉服配饰”等 query 时，使用 dense + sparse + ColBERT rerank 的混合搜索。

3. **商品详情页相似商品推荐**
   - 当前商品向量相似、同类目、同朝代、同工艺、共购/共看协同特征结合。

4. **购物车/订单后推荐**
   - 根据购物车商品或已购商品做搭配推荐、补充推荐、文化套装推荐。

5. **冷启动推荐**
   - 未登录或新用户使用热门、节令、文化主题、新品、探索混排。

### 3.2 推荐系统应具备的完整链路

最终链路：

1. 数据采集
2. 商品内容建模
3. 用户行为建模
4. 商品向量索引
5. 用户兴趣画像
6. 多路召回
7. 候选融合
8. 高级重排
9. 业务规则约束
10. 多样性与探索
11. 解释文案
12. 缓存
13. 曝光/点击日志
14. 离线评估
15. 性能压测
16. 后台可视化与答辩材料

---

## 4. 分阶段落地计划总览

建议按 12 个阶段实施。

| 阶段 | 主题 | 目标 |
|---|---|---|
| Phase 1 | 基线冻结与问题确认 | 先保留旧逻辑作为 baseline，避免改完无法对比 |
| Phase 2 | Qdrant 基础设施 | 引入独立向量数据库 |
| Phase 3 | 商品索引数据模型 | 定义商品多向量 collection 和 payload |
| Phase 4 | Embedding 服务升级 | 从 local_hash 升级为真实语义模型 + sparse + ColBERT |
| Phase 5 | 商品索引构建 | 全量/增量写入 Qdrant |
| Phase 6 | 混合搜索改造 | 替换 Python 全量余弦遍历 |
| Phase 7 | 个性化画像与多路召回 | 实现完整推荐召回层 |
| Phase 8 | 协同过滤 | 补齐“用户相似/商品相似”的推荐能力 |
| Phase 9 | 高级排序与重排 | 不只看余弦，引入综合排序 |
| Phase 10 | 日志、评估、压测 | 用指标证明系统有效 |
| Phase 11 | 前后台展示 | 让答辩能看见推荐能力 |
| Phase 12 | 文档与答辩材料 | 形成可讲清楚的项目闭环 |

---

# Phase 1：基线冻结与问题确认

## 1.1 目标

在正式升级前，先保留旧推荐系统作为 baseline，后续所有改进都要能和 baseline 对比。

## 1.2 需要修改什么

### 修改范围

- 新增文档：
  - `docs/recommendation_baseline_analysis.md`
  - `docs/recommendation_upgrade_plan.md`
- 新增测试或脚本：
  - `backend/tests/test_recommendation_baseline.py`
  - `backend/scripts/export_baseline_recommendation_metrics.py`

### 具体任务

1. 记录当前搜索逻辑：
   - 商品向量存储在 PostgreSQL JSON 字段。
   - 搜索时全量加载商品。
   - Python 逐个计算 cosine similarity。
   - 标签/类目/朝代/场景/工艺做规则加分。

2. 记录当前个性化推荐逻辑：
   - 行为日志生成用户画像文本。
   - 用户画像 embedding 与商品 embedding 做相似度。
   - top_terms 命中后加分。
   - 没有独立召回层，没有协同过滤，没有重排模型。

3. 创建 baseline 评估任务：
   - 固定一批搜索词。
   - 固定一批测试用户。
   - 记录 TopK 结果、耗时、命中原因。

## 1.3 给 AI 工作者的指令

> 你是项目审计和测试工程师。请不要改动现有推荐逻辑，只新增 baseline 文档和 baseline 测试脚本。请把当前 `vector_search.py`、`recommendations.py`、`recommendation.py` 中的推荐链路整理成文档，并建立可重复运行的 baseline 评估脚本。不得删除旧逻辑，旧逻辑后续要作为对照组。

## 1.4 如何验证

执行：

```bash
docker compose up -d
./.venv/bin/python -m pytest backend/tests -q
./.venv/bin/python backend/scripts/export_baseline_recommendation_metrics.py
```

验收标准：

- 能生成 baseline 结果文件。
- 文件中至少包含：
  - query
  - user_id
  - returned_product_ids
  - score
  - reason
  - latency_ms
- 后续升级后可以用同一批 query/user_id 做对比。

---

# Phase 2：引入 Qdrant 独立向量数据库

## 2.1 目标

把项目从“PostgreSQL/pgvector 相关方案”升级为“PostgreSQL + Qdrant 独立向量数据库”架构。

## 2.2 需要修改什么

### 修改范围

- `docker-compose.yml`
- `backend/app/core/config.py`
- `backend/requirements.txt` 或项目依赖文件
- `.env.example`
- `docs/deployment.md`
- 新增：
  - `backend/app/services/qdrant_client.py`
  - `backend/app/services/vector_store.py`
  - `backend/tests/test_qdrant_connection.py`

### 具体任务

1. 在 Docker Compose 中新增 Qdrant 服务。
   - 暴露 REST 端口 6333。
   - 暴露 gRPC 端口 6334。
   - 配置持久化 volume。
   - 保留 PostgreSQL 作为业务数据库。
   - Redis、MinIO 保持不变。

2. 后端配置新增：
   - `VECTOR_DB_PROVIDER=qdrant`
   - `QDRANT_URL=http://qdrant:6333`
   - `QDRANT_API_KEY=`
   - `QDRANT_COLLECTION_PRODUCTS=shiyige_products_v1`
   - `QDRANT_COLLECTION_USERS=shiyige_users_v1`
   - `QDRANT_COLLECTION_CF=shiyige_collaborative_v1`
   - `RECOMMENDATION_PIPELINE_VERSION=v1`

3. 新增 Qdrant client 封装。
   - 只负责连接、健康检查、collection 是否存在。
   - 不写业务推荐逻辑。

4. 启动检查。
   - API 启动时检查 Qdrant 是否可连接。
   - 如果 Qdrant 不可用，可以降级到旧 baseline，但必须打日志和返回降级标记。

## 2.3 给 AI 工作者的指令

> 你是后端基础设施工程师。请把 Qdrant 作为独立服务加入 Docker Compose，并为 FastAPI 新增 Qdrant 连接配置和健康检查。不要把业务推荐逻辑写进 client 文件。保留 PostgreSQL 作为业务库。保留旧推荐逻辑作为 fallback。完成后给出启动命令、健康检查命令和测试结果。

## 2.4 如何验证

执行：

```bash
docker compose down -v --remove-orphans
docker compose up -d
curl -s http://127.0.0.1:6333/collections
curl -s http://127.0.0.1/api/v1/health
./.venv/bin/python -m pytest backend/tests/test_qdrant_connection.py -q
```

验收标准：

- `curl http://127.0.0.1:6333/collections` 能返回 Qdrant collections 信息。
- API 健康检查包含 Qdrant 状态。
- 停掉 Qdrant 后，推荐接口能降级而不是直接崩溃。
- 旧测试仍通过。

---

# Phase 3：设计 Qdrant 商品 Collection

## 3.1 目标

定义一个真正适合搜索和推荐的商品向量 collection，而不是只存一个向量。

## 3.2 需要修改什么

### 修改范围

- 新增：
  - `backend/app/services/vector_schema.py`
  - `backend/app/tasks/qdrant_schema_tasks.py`
  - `backend/tests/test_qdrant_schema.py`
  - `docs/vector_database_design.md`
- 调整：
  - `backend/app/models/recommendation.py`
  - Alembic 迁移脚本

### 3.3 商品 Collection 设计

Collection 名称：

- `shiyige_products_v1`

每个 point 的 id：

- 使用 `product_id`。
- 保证业务库商品 id 与 Qdrant point id 一一对应。

Named vectors：

1. `dense`
   - 用于语义召回。
   - 推荐中文模型：`BAAI/bge-small-zh-v1.5` 或同等级中文模型。
   - 用于理解“古风礼物”“宋韵茶器”“适合中秋送礼”等语义。

2. `sparse`
   - 用于关键词召回。
   - 使用 BM25 或 SPLADE/miniCOIL 方案。
   - 用于保留“簪子”“香囊”“团扇”“宋代”等关键词精确匹配能力。

3. `colbert`
   - 用于 late interaction reranking。
   - 不作为第一阶段大规模召回。
   - 用于对 TopN 候选做更精细的 query-token 与商品文本匹配。

Payload 字段：

- `product_id`
- `name`
- `subtitle`
- `category_id`
- `category_name`
- `tags`
- `dynasty_style`
- `craft_type`
- `scene_tag`
- `festival_tag`
- `price_min`
- `price_max`
- `stock_available`
- `status`
- `sales_count`
- `review_count`
- `rating_avg`
- `created_at`
- `updated_at`
- `content_hash`
- `embedding_model_version`
- `index_version`

需要建立 payload index 的字段：

- `status`
- `category_id`
- `category_name`
- `dynasty_style`
- `craft_type`
- `scene_tag`
- `festival_tag`
- `tags`
- `price_min`
- `stock_available`
- `embedding_model_version`

## 3.4 PostgreSQL 侧如何调整

不要再把 PostgreSQL 当向量检索库。

建议调整：

1. `product_embedding`
   - 保留 `product_id`
   - 保留 `embedding_text`
   - 保留 `content_hash`
   - 保留 `model_name`
   - 新增 `qdrant_point_id`
   - 新增 `qdrant_collection`
   - 新增 `index_status`
   - 新增 `last_indexed_at`
   - 新增 `index_error`
   - 可以删除或弃用 `embedding_vector` JSON 字段

2. `user_interest_profile`
   - 保留画像文本和摘要。
   - 不再依赖 JSON 向量字段做推荐查询。
   - 新增 `qdrant_user_point_id`
   - 新增 `profile_version`
   - 新增 `last_synced_at`

## 3.5 给 AI 工作者的指令

> 你是向量数据库架构师。请为商品推荐设计 Qdrant collection，不要只建一个 dense vector。必须包含 dense、sparse、colbert 三种 named vectors，并设计完整 payload 与 payload index。PostgreSQL 仅保留同步状态和业务元数据，不再承担向量检索。请新增 schema 初始化任务和测试，确保重复执行不会破坏已有 collection。

## 3.6 如何验证

执行：

```bash
docker compose up -d qdrant api
./.venv/bin/python -m pytest backend/tests/test_qdrant_schema.py -q
curl -s http://127.0.0.1:6333/collections/shiyige_products_v1
```

验收标准：

- Qdrant 中存在 `shiyige_products_v1`。
- collection 中能看到多个 named vectors。
- payload index 创建成功。
- 重复执行初始化任务不会报错。
- PostgreSQL 中推荐相关表能记录 Qdrant 同步状态。

---

# Phase 4：升级 Embedding 服务

## 4.1 目标

把当前默认的 `local_hash` 替换为真实的中文语义 embedding，并增加 sparse 和 ColBERT embedding 能力。

## 4.2 需要修改什么

### 修改范围

- `backend/app/services/embedding.py`
- 新增：
  - `backend/app/services/embedding_dense.py`
  - `backend/app/services/embedding_sparse.py`
  - `backend/app/services/embedding_colbert.py`
  - `backend/app/services/embedding_registry.py`
  - `backend/tests/test_embedding_providers.py`
  - `docs/embedding_model_design.md`
- 调整配置：
  - `backend/app/core/config.py`
  - `.env.example`
  - `docker-compose.yml`

### 4.3 模型方案

建议采用三类 embedding：

1. Dense 中文语义模型
   - 推荐：`BAAI/bge-small-zh-v1.5`
   - 备选：`BAAI/bge-base-zh-v1.5`
   - 目标：语义召回

2. Sparse 模型
   - 推荐：Qdrant BM25 / FastEmbed BM25
   - 备选：SPLADE/miniCOIL
   - 目标：关键词召回，避免语义模型漏掉专有词

3. Late interaction 模型
   - 推荐：ColBERT 系列轻量模型
   - 目标：对候选集做高精度重排

### 4.4 商品文本构建规则

商品索引文本不能只用商品名，应拼接结构化文化特征。

推荐字段：

- 商品名
- 副标题
- 文化说明
- 类目
- 标签
- 朝代风格
- 工艺
- 节令
- 使用场景
- 适合人群
- 价格区间描述
- 礼物属性
- 搭配属性

示例文本结构应在文档中定义，但不要把所有字段简单堆在一起。要区分：

- `title_text`
- `semantic_text`
- `keyword_text`
- `rerank_text`

其中：

- dense 使用 `semantic_text`
- sparse 使用 `keyword_text`
- colbert 使用更完整的 `rerank_text`

## 4.5 给 AI 工作者的指令

> 你是 NLP/推荐系统工程师。请将 embedding 服务从单一 `local_hash` 抽象升级为 dense、sparse、colbert 三类 provider。默认生产配置必须使用真实中文语义模型，不得继续默认使用 local_hash。local_hash 只能保留给单元测试。商品文本构建要显式包含古风文化字段：朝代、工艺、节令、场景、标签和文化说明。不要实现推荐排序，只负责 embedding 生成与模型注册。

## 4.6 如何验证

执行：

```bash
./.venv/bin/python -m pytest backend/tests/test_embedding_providers.py -q
./.venv/bin/python -m pytest backend/tests -q
```

人工验证：

- 输入“宋代茶具”和“宋韵点茶器具”，dense 向量检索相似度应明显高于无关文本。
- 输入“香囊”“簪子”等明确关键词时，sparse 表示应能保留关键词信息。
- ColBERT provider 只用于候选重排，不用于全库第一阶段召回。

验收标准：

- 测试环境可以用 fake provider。
- 本地演示环境可以下载并使用真实模型。
- 配置文件中清楚区分 test/local/dev/prod 模式。
- 文档说明模型名称、维度、用途和替换方式。

---

# Phase 5：构建商品向量索引任务

## 5.1 目标

实现商品全量索引、增量索引、删除同步和索引状态检查。

## 5.2 需要修改什么

### 修改范围

- `backend/app/tasks/embedding_tasks.py`
- 新增：
  - `backend/app/tasks/qdrant_index_tasks.py`
  - `backend/app/services/product_index_document.py`
  - `backend/app/api/v1/admin_vector_index.py`
  - `backend/tests/test_product_qdrant_indexing.py`
  - `backend/scripts/reindex_products_to_qdrant.py`
  - `docs/indexing_operations.md`

### 5.3 具体任务

1. 商品全量索引
   - 读取所有上架和可展示商品。
   - 生成 dense/sparse/colbert 三类向量。
   - 写入 Qdrant。
   - PostgreSQL 记录同步状态。

2. 商品增量索引
   - 商品名称、描述、类目、标签、价格、库存、状态变化时触发。
   - 通过 `content_hash` 判断是否需要重新生成向量。
   - 价格、库存、状态变化只更新 payload，不一定重算向量。

3. 商品下架/删除同步
   - 下架商品不应出现在推荐结果中。
   - 删除商品时删除 Qdrant point 或把 payload status 标记为 inactive。
   - 推荐接口必须 filter `status=active` 和 `stock_available=true`。

4. 索引状态后台接口
   - 查询 collection 状态。
   - 查询已索引商品数量。
   - 查询失败商品列表。
   - 支持重试失败任务。

## 5.4 给 AI 工作者的指令

> 你是数据索引工程师。请把原有 `reindex_product_embeddings` 升级为 Qdrant 商品索引任务。索引任务必须支持全量、增量、单商品重建、失败重试、删除同步和状态查询。请保证商品 payload 能支持类目、价格、朝代、场景、工艺、节令、库存过滤。不要在搜索接口里临时生成全库索引，索引必须由后台任务或管理接口触发。

## 5.5 如何验证

执行：

```bash
docker compose up -d
./.venv/bin/python backend/scripts/reindex_products_to_qdrant.py --mode full
curl -s http://127.0.0.1:6333/collections/shiyige_products_v1
./.venv/bin/python -m pytest backend/tests/test_product_qdrant_indexing.py -q
```

验收标准：

- Qdrant point 数量与上架商品数量一致。
- 每个 point 有 dense、sparse、colbert 向量。
- 每个 point 有完整 payload。
- 修改商品标签后，增量索引能更新对应 point。
- 商品下架后，推荐和搜索结果不再返回该商品。
- 索引任务失败时能记录错误并重试。

---

# Phase 6：搜索页改造为混合检索

## 6.1 目标

把 `semantic_search_products` 从 Python 全量遍历改成 Qdrant 混合检索。

## 6.2 需要修改什么

### 修改范围

- `backend/app/services/vector_search.py`
- 新增：
  - `backend/app/services/hybrid_search.py`
  - `backend/app/services/search_filters.py`
  - `backend/app/services/search_reranker.py`
  - `backend/tests/test_hybrid_search.py`
  - `backend/tests/test_search_filters.py`
  - `docs/search_pipeline.md`

### 6.3 新搜索链路

搜索请求：

1. 用户输入 query。
2. 解析筛选条件：
   - 类目
   - 价格区间
   - 朝代风格
   - 工艺
   - 使用场景
   - 节令
   - 是否有库存
3. 生成 dense query vector。
4. 生成 sparse query vector。
5. Qdrant 第一阶段召回：
   - dense recall top 100
   - sparse recall top 100
   - 可选：热门/新品补充 top 20
6. 使用 RRF 融合 dense 和 sparse 候选。
7. 对 Top 50 使用 ColBERT multivector rerank。
8. 应用业务排序：
   - 有库存优先
   - 商品状态正常
   - 评分较高
   - 销量合理
   - 价格符合筛选
9. 返回 TopK。
10. 写入搜索日志。

### 6.4 为什么能反驳“只算余弦”

改造后搜索不是单一余弦：

- dense：语义匹配
- sparse/BM25：关键词匹配
- RRF：多路召回融合
- ColBERT：token-level late interaction rerank
- payload filter：结构化过滤
- business rerank：库存、评分、销量、价格等业务排序

## 6.5 给 AI 工作者的指令

> 你是搜索系统工程师。请把 `semantic_search_products` 改造成 Qdrant hybrid search。严禁再从 PostgreSQL 全量加载商品后逐个计算余弦相似度。搜索必须包含 dense 召回、sparse 召回、RRF 融合、ColBERT 重排和 payload 过滤。保留旧方法为 baseline fallback，但默认路径必须走 Qdrant。请补齐搜索过滤、日志和测试。

## 6.6 如何验证

执行：

```bash
./.venv/bin/python -m pytest backend/tests/test_hybrid_search.py -q
./.venv/bin/python -m pytest backend/tests/test_search_filters.py -q
curl "http://127.0.0.1/api/v1/products/search?q=宋代茶具"
curl "http://127.0.0.1/api/v1/products/search?q=中秋送礼&min_price=100&max_price=300"
```

人工验收：

- 搜索“宋代茶具”时，不只返回包含“宋代茶具”字面词的商品，也能返回宋韵、点茶、茶器等语义相关商品。
- 搜索“香囊”时，关键词精确匹配商品应靠前。
- 加价格过滤后，结果严格在价格区间内。
- 下架或无库存商品不出现。
- 返回 reason 中能说明：
  - 语义相关
  - 关键词命中
  - 文化特征匹配
  - ColBERT 重排提升

性能验收：

- 小数据：p95 < 200ms。
- 1 万商品模拟数据：p95 < 300ms。
- 10 万商品模拟数据：p95 < 500ms。
- 搜索接口不能出现全表商品加载。

---

# Phase 7：实现完整多路召回推荐系统

## 7.1 目标

把 `recommend_products_for_user` 从“遍历所有商品 + 余弦 + 规则加分”升级为多路召回系统。

## 7.2 需要修改什么

### 修改范围

- `backend/app/services/recommendations.py`
- 新增：
  - `backend/app/services/recommendation_pipeline.py`
  - `backend/app/services/recall_content.py`
  - `backend/app/services/recall_sparse_interest.py`
  - `backend/app/services/recall_collaborative.py`
  - `backend/app/services/recall_trending.py`
  - `backend/app/services/recall_new_arrival.py`
  - `backend/app/services/candidate_fusion.py`
  - `backend/app/services/diversity.py`
  - `backend/tests/test_recommendation_pipeline.py`
  - `docs/recommendation_pipeline.md`

### 7.3 多路召回设计

推荐接口不再只靠一个用户画像向量。

至少实现以下召回通道：

1. **内容语义召回**
   - 用户近期行为文本生成 dense profile。
   - 用 dense profile 去 Qdrant 检索商品。

2. **关键词兴趣召回**
   - 根据用户 top_terms 构造 sparse query。
   - 召回类目、标签、朝代、工艺、节令相关商品。

3. **协同过滤召回**
   - 根据相似用户喜欢的商品召回。
   - 根据用户已看/已购商品的共看、共购关系召回。

4. **相似商品召回**
   - 对用户最近浏览或加购商品找相似商品。

5. **热门趋势召回**
   - 最近 7 天浏览、加购、购买趋势。
   - 节日/季节主题，比如中秋、七夕、春节。

6. **新品探索召回**
   - 新上架商品。
   - 低曝光但高质量商品。
   - 防止推荐系统只推老热门商品。

7. **冷启动召回**
   - 未登录用户或行为少于阈值的用户使用：
     - 热门
     - 新品
     - 节令
     - 随机探索
     - 后台精选

### 7.4 候选融合

每个召回通道返回候选和召回分。

候选字段：

- `product_id`
- `recall_channel`
- `recall_score`
- `rank_in_channel`
- `matched_terms`
- `reason_parts`

融合规则：

1. 同一个商品可来自多个通道。
2. 合并后保留所有召回来源。
3. 使用 RRF 或加权融合。
4. 控制每个通道最大占比，避免热门通道垄断。
5. 进入排序层前保留 Top 200 候选。

## 7.5 给 AI 工作者的指令

> 你是推荐系统召回层工程师。请把个性化推荐改成多路召回架构，至少包含内容语义、关键词兴趣、协同过滤、相似商品、热门趋势、新品探索、冷启动兜底。每个召回通道必须返回召回来源、召回分、候选商品和解释片段。不得在推荐接口中全量遍历商品。请保证最终候选合并后可以进入统一排序层。

## 7.6 如何验证

执行：

```bash
./.venv/bin/python -m pytest backend/tests/test_recommendation_pipeline.py -q
curl "http://127.0.0.1/api/v1/recommendations?slot=home&limit=12"
```

人工验收：

- 老用户推荐中能看到与近期浏览/搜索相关的商品。
- 新用户推荐不为空。
- 未登录用户推荐不为空。
- 购买过的商品默认不重复推荐。
- 每个结果包含推荐理由。
- 调试模式下能看到每个商品来自哪些召回通道。

性能验收：

- 首页推荐 p95 < 300ms。
- 开启 Redis 缓存后 p95 < 150ms。
- 推荐接口不全表扫描商品。

---

# Phase 8：实现协同过滤推荐

## 8.1 目标

补齐“其他用户也喜欢”“共看共购”“用户相似度”能力，让推荐不只是内容相似。

## 8.2 需要修改什么

### 修改范围

- 新增：
  - `backend/app/services/collaborative_filtering.py`
  - `backend/app/tasks/collaborative_index_tasks.py`
  - `backend/app/models/recommendation_experiment.py`
  - `backend/tests/test_collaborative_filtering.py`
  - `backend/scripts/build_collaborative_index.py`
  - `docs/collaborative_filtering_design.md`

### 8.3 行为权重

建议行为权重：

| 行为 | 权重 | 说明 |
|---|---:|---|
| 曝光未点击 | -0.1 | 弱负反馈 |
| 浏览商品 | 1.0 | 弱正反馈 |
| 搜索后点击 | 2.0 | 中等正反馈 |
| 收藏 | 3.0 | 强正反馈 |
| 加购 | 4.0 | 强正反馈 |
| 下单 | 5.0 | 强正反馈 |
| 支付成功 | 6.0 | 最强正反馈 |
| 退款/取消 | -2.0 | 负反馈 |

当前项目没有的行为可以先补日志字段或预留。

### 8.4 两种协同过滤实现

必须至少完成一种，建议完成两种：

#### 方案 A：Qdrant sparse user vector 协同过滤

1. 把每个用户表示为 sparse vector。
2. 维度索引是 `product_id`。
3. 值是行为权重和时间衰减后的分数。
4. 在 Qdrant 中搜索相似用户。
5. 汇总相似用户喜欢但当前用户未消费的商品。

优点：

- 直观。
- 可解释。
- 不需要复杂训练。
- 适合答辩展示。

#### 方案 B：item-item 共现召回

1. 统计用户会话中的共看、共购、共加购商品。
2. 生成商品相似关系。
3. 用户最近行为商品作为种子。
4. 找 co-view/co-buy 相似商品。

优点：

- 很适合商城。
- 效果容易解释。
- 冷启动商品可结合内容召回。

### 8.5 时间衰减

推荐加入时间衰减，避免很久以前的兴趣长期影响。

规则：

- 7 天内行为权重大。
- 30 天内行为中等。
- 90 天后逐渐衰减。
- 支付/收藏类强行为衰减慢于浏览行为。

## 8.6 给 AI 工作者的指令

> 你是推荐算法工程师。请基于 `user_behavior_log` 实现协同过滤召回。至少实现 Qdrant sparse user vector 相似用户召回，并实现 item-item 共现召回。行为权重必须区分浏览、搜索点击、加购、下单、支付，并加入时间衰减。召回结果必须排除用户已购/已强消费商品，并返回可解释原因。

## 8.7 如何验证

执行：

```bash
./.venv/bin/python backend/scripts/build_collaborative_index.py
./.venv/bin/python -m pytest backend/tests/test_collaborative_filtering.py -q
curl "http://127.0.0.1/api/v1/recommendations?slot=home&debug=true"
```

人工验收：

- 构造两个兴趣相似用户，他们应互相影响推荐。
- 用户 A 加购茶具后，用户 B 若与 A 相似，应能收到茶具或茶文化相关商品。
- 已购买商品不重复推荐。
- 调试信息里能看到 `collaborative_user` 或 `item_cooccurrence` 召回通道。

---

# Phase 9：实现高级排序与重排

## 9.1 目标

让最终推荐不只是“向量分数排序”，而是由召回分、语义分、关键词分、协同过滤分、业务特征和学习排序共同决定。

## 9.2 需要修改什么

### 修改范围

- 新增：
  - `backend/app/services/ranking_features.py`
  - `backend/app/services/ranker.py`
  - `backend/app/services/ltr_ranker.py`
  - `backend/app/services/business_rules.py`
  - `backend/app/services/recommendation_explainer.py`
  - `backend/tests/test_ranking_features.py`
  - `backend/tests/test_ranker.py`
  - `docs/ranking_design.md`

### 9.3 排序特征设计

至少构造以下特征：

#### 召回相关特征

- dense recall score
- sparse recall score
- ColBERT rerank score
- collaborative score
- item cooccurrence score
- RRF fusion score
- recall_channel_count
- best_channel_rank

#### 用户兴趣特征

- category_match
- tag_match_count
- dynasty_match
- craft_match
- scene_match
- festival_match
- price_affinity
- user_recent_interest_score
- user_long_term_interest_score

#### 商品质量特征

- sales_count
- conversion_rate
- add_to_cart_rate
- rating_avg
- review_count
- stock_available
- return_rate
- freshness_score
- content_quality_score

#### 业务规则特征

- 是否上架
- 是否有库存
- 是否符合价格筛选
- 是否近期已曝光
- 是否已购买
- 是否后台精选
- 是否节令主题

### 9.4 排序器分两阶段

#### 阶段 1：可解释加权排序器

在日志不足时使用。

排序目标：

- 容易解释。
- 容易调参。
- 答辩时可以清楚展示每个分数来源。

#### 阶段 2：Learning-to-Rank

日志积累后使用。

建议：

- 使用 LightGBM LambdaMART 或 XGBoost ranker。
- label 来自点击、加购、支付等行为。
- query group 可以是一次推荐请求或一次搜索请求。
- 输出 ranking model version。
- 支持 fallback 到加权排序器。

### 9.5 多样性与探索

排序后必须做 post-processing：

1. 去重。
2. 已购过滤。
3. 连续同类目商品不超过阈值。
4. 同朝代/同工艺不过度集中。
5. 保留 10%-20% 新品/探索商品。
6. 曝光过多但未点击的商品降权。
7. 库存不足商品降权或过滤。

## 9.6 给 AI 工作者的指令

> 你是推荐排序工程师。请建立统一 ranking 层。排序输入是多路召回候选，排序输出是最终商品列表和解释信息。排序不能只使用向量相似度，必须综合 dense、sparse、ColBERT、协同过滤、用户兴趣、商品质量、业务规则和多样性约束。先实现可解释加权排序器，再预留 Learning-to-Rank 训练和加载接口。所有排序特征必须能在 debug 模式中输出。

## 9.7 如何验证

执行：

```bash
./.venv/bin/python -m pytest backend/tests/test_ranking_features.py -q
./.venv/bin/python -m pytest backend/tests/test_ranker.py -q
curl "http://127.0.0.1/api/v1/recommendations?slot=home&debug=true"
```

验收标准：

- 每个推荐商品能看到特征摘要。
- 结果不是简单按余弦分排序。
- 同一类目不会完全霸屏。
- 无库存、下架、已购商品被过滤。
- 新品探索位能稳定出现。
- 排序层可切换 `weighted_ranker` 和 `ltr_ranker`。

---

# Phase 10：补齐日志、离线评估与性能压测

## 10.1 目标

用数据证明推荐系统有效，避免答辩时只有“我感觉效果更好”。

## 10.2 需要修改什么

### 修改范围

- 新增数据表：
  - `recommendation_request_log`
  - `recommendation_impression_log`
  - `recommendation_click_log`
  - `recommendation_conversion_log`
  - `search_request_log`
  - `search_result_log`
- 新增：
  - `backend/app/services/recommendation_logging.py`
  - `backend/scripts/evaluate_recommendations.py`
  - `backend/scripts/benchmark_recommendations.py`
  - `backend/scripts/generate_synthetic_catalog.py`
  - `backend/tests/test_recommendation_logging.py`
  - `docs/recommendation_evaluation.md`
  - `docs/performance_benchmark.md`

### 10.3 必须记录的日志

每次推荐请求记录：

- request_id
- user_id
- slot
- pipeline_version
- model_version
- candidate_count
- final_product_ids
- latency_ms
- fallback_used
- created_at

每次曝光记录：

- request_id
- product_id
- rank_position
- recall_channels
- final_score
- reason
- created_at

每次点击/加购/支付记录：

- request_id
- product_id
- user_id
- action_type
- created_at

### 10.4 离线评估指标

必须至少包含：

| 指标 | 含义 |
|---|---|
| Precision@K | TopK 推荐中命中的比例 |
| Recall@K | 用户真实感兴趣商品被召回的比例 |
| NDCG@K | 排名质量 |
| MRR | 第一个命中结果位置 |
| Coverage | 商品覆盖率 |
| Diversity | 推荐多样性 |
| Novelty | 新颖性 |
| CTR | 点击率 |
| CVR | 转化率 |
| Add-to-cart Rate | 加购率 |
| p50/p95/p99 latency | 响应性能 |

### 10.5 对比实验

必须输出对比表：

1. baseline：旧 Python 余弦 + 规则加分
2. Qdrant dense only
3. Qdrant dense + sparse
4. Qdrant dense + sparse + ColBERT
5. 多路召回 + 加权排序
6. 多路召回 + Learning-to-Rank
7. 多路召回 + LTR + 多样性

### 10.6 性能压测

数据规模：

- 100 商品：演示数据
- 1,000 商品：小规模测试
- 10,000 商品：比赛展示推荐规模
- 100,000 商品：性能证明用模拟数据

压测接口：

- 搜索接口
- 首页推荐接口
- 相似商品接口
- 索引重建任务

## 10.7 给 AI 工作者的指令

> 你是推荐系统评估工程师。请补齐推荐请求日志、曝光日志、点击/转化日志，并实现离线评估和性能压测脚本。评估必须能比较旧 baseline、dense only、hybrid、hybrid + rerank、多路召回、多路召回 + 排序器等方案。压测必须输出 p50、p95、p99、QPS、错误率和候选数量。不要只输出准确率，必须同时输出覆盖率、多样性和延迟。

## 10.8 如何验证

执行：

```bash
./.venv/bin/python backend/scripts/evaluate_recommendations.py --scenario all
./.venv/bin/python backend/scripts/benchmark_recommendations.py --products 10000 --users 1000
./.venv/bin/python -m pytest backend/tests/test_recommendation_logging.py -q
```

验收标准：

- 能生成评估报告。
- 能生成性能报告。
- 报告中有 baseline vs 新系统对比。
- 搜索和推荐接口有 p95/p99 统计。
- 每次推荐能追踪曝光到点击/加购/支付。

---

# Phase 11：前台和后台展示改造

## 11.1 目标

让答辩老师能直接看到“这个推荐系统确实完整且高级”。

## 11.2 需要修改什么

### 前台

修改范围：

- `front/`
- 搜索页
- 商品详情页
- 首页推荐区域
- 购物车页推荐区域
- 订单完成页推荐区域

前台需要展示：

1. 推荐理由
   - “因为你最近浏览了宋韵茶器”
   - “与当前商品在工艺/朝代上相近”
   - “与你兴趣相似的用户也喜欢”
   - “中秋节令热门推荐”

2. 搜索解释
   - 语义相关
   - 关键词命中
   - 文化标签匹配

3. 推荐来源标识
   - 个性化
   - 相似商品
   - 热门
   - 新品探索
   - 节令主题

### 后台

新增推荐管理页面：

1. 向量索引状态
   - Qdrant 连接状态
   - collection 状态
   - 已索引商品数
   - 索引失败商品数
   - 重建按钮

2. 推荐效果看板
   - CTR
   - 加购率
   - 转化率
   - 覆盖率
   - 平均延迟

3. 推荐调试页
   - 输入 user_id
   - 查看召回通道
   - 查看排序特征
   - 查看最终理由

4. 实验配置页
   - baseline
   - hybrid
   - hybrid_rerank
   - full_pipeline

## 11.3 给 AI 工作者的指令

> 你是全栈工程师。请把推荐系统能力展示到前台和后台。前台必须显示推荐理由和推荐来源，后台必须显示 Qdrant 索引状态、推荐效果指标、召回调试信息和实验方案。不要只做接口，答辩需要可视化页面。所有新增页面要保持当前项目静态前端风格，不引入过重前端框架。

## 11.4 如何验证

执行：

```bash
docker compose up -d
./.venv/bin/python -m pytest tests/e2e/test_full_demo_flow.py -q
```

人工验收：

- 首页能看到个性化推荐。
- 商品详情页能看到相似商品。
- 搜索页能看到混合检索结果。
- 后台能看到 Qdrant 索引状态。
- 后台能输入 user_id 查看推荐解释。
- 页面上能区分推荐来源，而不是所有商品都显示同一句理由。

---

# Phase 12：文档、答辩材料与最终验收

## 12.1 目标

把项目包装成“可答辩、可演示、可证明”的完整系统。

## 12.2 需要新增文档

建议新增：

1. `docs/vector_database_design.md`
   - 为什么不用 pgvector 作为主方案
   - 为什么选择 Qdrant
   - collection 设计
   - payload index
   - dense/sparse/multivector 设计

2. `docs/recommendation_pipeline.md`
   - 多路召回
   - 候选融合
   - 排序
   - 多样性
   - 冷启动
   - 推荐理由

3. `docs/search_pipeline.md`
   - hybrid search
   - RRF
   - ColBERT rerank
   - filter
   - 性能优化

4. `docs/recommendation_evaluation.md`
   - 评估数据
   - 评估指标
   - baseline 对比
   - 实验结果

5. `docs/performance_benchmark.md`
   - 100 / 1000 / 10000 / 100000 商品规模压测
   - p50/p95/p99
   - Qdrant 参数
   - 缓存效果

6. `docs/defense_script.md`
   - 答辩讲稿
   - 老师可能追问
   - 如何回答“是不是只算余弦”
   - 如何回答“为什么是向量数据库”
   - 如何回答“推荐系统完整性”

## 12.3 答辩时建议表达

可以这样讲：

> 旧版本只是把商品 embedding 存在业务库中，并在 Python 层做余弦相似度排序，所以它只能算推荐雏形。升级后我将向量检索迁移到独立向量数据库 Qdrant，商品索引包含 dense 语义向量、sparse 关键词向量和 ColBERT multivector。搜索和推荐时先通过 dense/sparse 多路召回，再通过 RRF 融合和 ColBERT late interaction 重排，最后结合协同过滤、用户行为、商品质量、库存、价格、节令和多样性策略做最终排序。因此系统不再是单一余弦距离，而是完整的多阶段推荐系统。

## 12.4 给 AI 工作者的指令

> 你是项目答辩材料工程师。请根据已实现功能补齐所有推荐系统文档和答辩讲稿。文档必须包含架构图说明、数据流、推荐流程、向量数据库设计、算法模块、评估指标、性能对比和答辩 FAQ。请把“旧版本问题”和“升级后解决方式”对应起来写，重点回应老师提出的两个批评：没有真正向量数据库、推荐系统过于简单。

## 12.5 最终验收命令

```bash
docker compose down -v --remove-orphans
docker compose up -d
curl -s http://127.0.0.1:6333/collections
curl -s http://127.0.0.1/api/v1/health
./.venv/bin/python backend/scripts/reindex_products_to_qdrant.py --mode full
./.venv/bin/python backend/scripts/build_collaborative_index.py
./.venv/bin/python backend/scripts/evaluate_recommendations.py --scenario all
./.venv/bin/python backend/scripts/benchmark_recommendations.py --products 10000 --users 1000
./.venv/bin/python -m pytest backend/tests -q
./.venv/bin/python -m pytest tests/e2e/test_full_demo_flow.py -q
```

最终验收标准：

- Qdrant 正常运行。
- 商品索引完整。
- 搜索接口默认走 hybrid search。
- 推荐接口默认走多路召回 + 排序。
- 旧 baseline 仍可作为对照。
- 后台可查看索引状态和推荐指标。
- 前台显示推荐理由。
- 离线评估报告生成成功。
- 性能压测报告生成成功。
- 文档完整说明“不只是 pgvector、不只是余弦”。

---

# 13. 推荐系统最终接口规划

## 13.1 搜索接口

建议接口：

- `GET /api/v1/products/search`

参数：

- `q`
- `category_id`
- `min_price`
- `max_price`
- `dynasty_style`
- `craft_type`
- `scene_tag`
- `festival_tag`
- `limit`
- `debug`

返回必须包含：

- 商品基本信息
- final_score
- dense_score
- sparse_score
- rerank_score
- matched_terms
- reason
- pipeline_version

## 13.2 首页推荐接口

建议接口：

- `GET /api/v1/recommendations`

参数：

- `slot=home`
- `limit`
- `debug`

返回必须包含：

- 商品基本信息
- recall_channels
- final_score
- reason
- is_exploration
- rank_features，debug=true 时返回

## 13.3 相似商品接口

建议接口：

- `GET /api/v1/products/{product_id}/related`

返回必须包含：

- dense similarity 来源
- co-view/co-buy 来源
- 文化标签匹配来源
- 多样性处理结果

## 13.4 后台索引接口

建议接口：

- `GET /api/v1/admin/vector-index/status`
- `POST /api/v1/admin/vector-index/rebuild`
- `POST /api/v1/admin/vector-index/products/{product_id}/reindex`
- `GET /api/v1/admin/recommendation/debug?user_id=...`
- `GET /api/v1/admin/recommendation/metrics`

---

# 14. 推荐排序公式建议

注意：这不是具体代码，只是实现目标。

## 14.1 加权排序器目标

最终分数应综合：

- 召回融合分
- ColBERT 重排分
- 协同过滤分
- 用户兴趣匹配分
- 商品质量分
- 新鲜度
- 热门趋势
- 价格偏好
- 库存状态
- 多样性调整
- 曝光疲劳惩罚

建议权重初始值：

| 特征组 | 初始权重 |
|---|---:|
| hybrid retrieval score | 0.25 |
| ColBERT rerank score | 0.20 |
| collaborative score | 0.15 |
| user interest match | 0.15 |
| product quality | 0.10 |
| trend/freshness | 0.05 |
| business constraints | 0.05 |
| diversity/exploration adjustment | 0.05 |

后续用离线评估调参。

## 14.2 Learning-to-Rank 目标

LTR 训练目标：

- 点击作为弱 label
- 加购作为中 label
- 支付作为强 label
- 曝光未点击作为弱负反馈

模型输出：

- `ltr_score`

上线策略：

- 如果训练数据少于阈值，用加权排序器。
- 如果模型加载失败，降级到加权排序器。
- 所有模型版本写入日志，方便对比。

---

# 15. 性能优化计划

## 15.1 Qdrant 侧优化

1. 使用 HNSW 索引。
2. 对高频过滤字段建立 payload index。
3. 对大规模商品向量开启 quantization。
4. ColBERT multivector 只用于重排，不做全量 ANN。
5. 控制每个召回通道 topN，避免候选过大。
6. 对热门 query 缓存搜索结果。
7. 对首页推荐缓存最终结果和中间用户画像。
8. 定期清理下架商品 point。

## 15.2 API 侧优化

1. 推荐接口拆分：
   - 在线召回
   - 预计算推荐
   - 缓存兜底
2. 新用户走预计算热门榜。
3. 老用户读取 Redis 中的近期画像。
4. 排序特征批量查询，避免 N+1。
5. 商品详情批量加载。
6. debug 模式默认关闭。

## 15.3 验收指标

建议：

| 场景 | p95 目标 |
|---|---:|
| 搜索，1 万商品 | < 300ms |
| 搜索，10 万商品 | < 500ms |
| 首页推荐，缓存命中 | < 150ms |
| 首页推荐，缓存未命中 | < 400ms |
| 相似商品 | < 250ms |
| Qdrant 单次 hybrid query | < 200ms |

---

# 16. 答辩 FAQ

## Q1：你是不是只是算了余弦相似度？

回答：

> 不是。旧版本确实主要依赖余弦相似度，所以我把它作为 baseline 保留。新版本使用 Qdrant 独立向量数据库，搜索阶段包含 dense 语义召回、sparse/BM25 关键词召回、RRF 融合、ColBERT late interaction 重排；推荐阶段还加入协同过滤、多路召回、学习排序、多样性和冷启动策略。余弦相似度只是一部分，不再是整个推荐系统。

## Q2：为什么不用 pgvector？

回答：

> pgvector 更适合作为 PostgreSQL 的向量扩展，但老师指出我的题目强调“向量数据库”，因此我把主检索引擎切换为独立向量数据库 Qdrant。PostgreSQL 只保留业务数据，Qdrant 负责向量索引、混合检索、payload filter、multivector rerank 和性能优化。

## Q3：推荐系统完整性体现在哪里？

回答：

> 完整性体现在链路上：数据采集、商品索引、用户画像、多路召回、候选融合、重排、业务规则、多样性、冷启动、推荐解释、日志追踪、离线评估和性能压测都有实现，而不是只写一个返回相似商品的函数。

## Q4：怎么证明推荐更好？

回答：

> 我保留了旧系统作为 baseline，并实现评估脚本，对比 Precision@K、Recall@K、NDCG@K、Coverage、Diversity、CTR 代理指标和 p95 延迟。答辩时可以展示旧版本、dense only、hybrid、hybrid + rerank、完整多路推荐的对比表。

## Q5：如何解决冷启动？

回答：

> 新用户使用热门、节令、新品、后台精选和探索混排；新商品通过内容向量和文化标签进入内容召回，同时在探索位获得曝光；当行为数据积累后，再进入协同过滤和学习排序。

---

# 17. 最小可提交版本与增强版本

## 17.1 最小可提交版本

如果时间有限，至少完成：

1. Qdrant 接入。
2. 商品 dense/sparse/colbert 索引。
3. 搜索 hybrid + rerank。
4. 推荐多路召回。
5. 协同过滤基础版。
6. 加权排序器。
7. 推荐日志。
8. baseline 对比报告。
9. 前台推荐理由。
10. 后台索引状态。

## 17.2 增强版本

如果时间充足，再完成：

1. LightGBM LambdaMART 排序。
2. 10 万商品压测。
3. 推荐实验平台。
4. Redis 预计算推荐。
5. 更完整的节令/文化知识图谱。
6. A/B 实验看板。
7. 多模态商品图像 embedding。

---

# 18. 给 AI 编程助手的总控提示词

可以把下面这段作为给 Cursor、Trae、GitHub Copilot Chat 或其他 AI 编程助手的总指令：

> 你是资深推荐系统工程师和 FastAPI 后端工程师。请基于当前 `shiyige` 项目进行推荐系统升级。项目目标是“基于向量数据库的古风文化商品智能推荐购物网站”。当前问题是：商品向量存储在 PostgreSQL JSON 字段中，搜索和推荐在 Python 层全量遍历并计算余弦相似度，推荐逻辑过于简单。请将系统升级为独立 Qdrant 向量数据库方案，保留 PostgreSQL 作为业务库。必须实现商品 dense/sparse/ColBERT 多向量索引、Qdrant payload filter、hybrid search、RRF 融合、ColBERT rerank、多路召回、协同过滤、统一排序、多样性、冷启动、推荐解释、日志、离线评估和性能压测。请分阶段提交，每阶段都要新增或更新测试和文档。不要删除旧推荐逻辑，旧逻辑作为 baseline fallback。不得只实现余弦相似度排序，不得在接口中全量加载商品后循环计算相似度。每次提交后运行测试并说明验证结果。

---

# 19. 参考资料

- 当前项目仓库：`https://github.com/lyric116/shiyige`
- Qdrant Hybrid Search with Reranking：`https://qdrant.tech/documentation/tutorials-search-engineering/reranking-hybrid-search/`
- Qdrant Hybrid Queries：`https://qdrant.tech/documentation/search/hybrid-queries/`
- Qdrant Multivectors and Late Interaction：`https://qdrant.tech/documentation/tutorials-search-engineering/using-multivector-representations/`
- Qdrant Collaborative Filtering：`https://qdrant.tech/documentation/tutorials-search-engineering/collaborative-filtering/`
- Qdrant Quantization：`https://qdrant.tech/documentation/manage-data/quantization/`
- Qdrant Payload / Filtering：`https://qdrant.tech/documentation/manage-data/payload/`
