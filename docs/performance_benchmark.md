# 推荐系统性能压测报告

## 1. 目标

这份报告回答三个问题：

1. 搜索和推荐在不同商品规模下是否还能正常工作？
2. 哪些链路已经适合答辩展示，哪些链路还是瓶颈？
3. 当前缓存和 Qdrant 参数对系统性能有什么影响？

## 2. 压测口径

### 2.1 运行模式

为避免把模型下载和真实 ONNX 推理时间混进结果，本报告统一采用：

* `dense=local_hash`
* `sparse=local_hash`
* `colbert=local_hash`

这意味着本报告主要度量的是：

* Qdrant 检索
* 候选融合
* 排序
* 回表
* 接口编排

而不是外部模型推理成本。

### 2.2 当前运行时

* `configured_provider=qdrant`
* `active_search_backend=qdrant_hybrid`
* `active_recommendation_backend=multi_recall`
* `configured_recommendation_ranker=weighted_ranker`

### 2.3 主要 Qdrant 参数

当前压测基于正式商品 collection 设计：

* collection: `shiyige_products_v1`
* named vectors:
  * `dense(512)`
  * `sparse`
  * `colbert(96)`
* payload filters:
  * `status`
  * `category_id`
  * `dynasty_style`
  * `craft_type`
  * `scene_tag`
  * `festival_tag`
  * `price_min`
  * `stock_available`

## 3. 各规模结果

### 3.1 100 商品

环境：

* `target_products=100`
* `target_users=50`
* `requests_per_endpoint=20`

| Endpoint | p50 ms | p95 ms | p99 ms | 说明 |
| --- | ---: | ---: | ---: | --- |
| `search_keyword` | 72.270 | 148.747 | 249.296 | 关键词检索基本流畅 |
| `search_semantic` | 2947.455 | 3951.732 | 4207.210 | 语义检索已明显重于关键词检索 |
| `recommend_home` | 2422.644 | 3459.140 | 3510.716 | 首页推荐可接受，仍有等待感 |
| `related_products` | 735.919 | 944.922 | 945.463 | 相似商品在小规模下表现良好 |
| `reindex_products_qdrant` | 2470.723 | 2470.723 | 2470.723 | 全量重建约 2.47 秒 |
| `build_collaborative_index` | 150.373 | 150.373 | 150.373 | 协同过滤索引构建开销低 |

### 3.2 1000 商品

环境：

* `target_products=1000`
* `target_users=200`
* `requests_per_endpoint=40`

| Endpoint | p50 ms | p95 ms | p99 ms | 说明 |
| --- | ---: | ---: | ---: | --- |
| `search_keyword` | 138.478 | 460.371 | 1079.255 | 关键词检索仍可用 |
| `search_semantic` | 2969.603 | 4383.970 | 4421.861 | 语义检索成本相对稳定 |
| `recommend_home` | 4108.839 | 5447.038 | 6646.117 | 首页推荐开始出现明显延迟 |
| `related_products` | 5465.368 | 6521.339 | 6761.157 | 相似商品已成为首个显著瓶颈 |
| `reindex_products_qdrant` | 21906.857 | 21906.857 | 21906.857 | 全量重建约 21.9 秒 |
| `build_collaborative_index` | 180.060 | 180.060 | 180.060 | 协同过滤仍然便宜 |

### 3.3 10000 商品

环境：

* `target_products=10000`
* `target_users=1000`
* `requests_per_endpoint=80`

| Endpoint | p50 ms | p95 ms | p99 ms | 说明 |
| --- | ---: | ---: | ---: | --- |
| `search_keyword` | 1117.695 | 2298.531 | 2538.575 | 关键词检索仍可工作，但已经不是“秒开” |
| `search_semantic` | 3039.086 | 4030.115 | 4161.453 | 语义检索仍保持在 4 秒级 |
| `recommend_home` | 28618.872 | 38891.419 | 41806.241 | 首页推荐已达到 30-40 秒级 |
| `related_products` | 53709.166 | 90946.377 | 91469.201 | 相似商品成为最严重瓶颈 |
| `reindex_products_qdrant` | 291951.650 | 291951.650 | 291951.650 | 全量重建约 4.87 分钟 |
| `build_collaborative_index` | 163.817 | 163.817 | 163.817 | 协同过滤构建仍然稳定 |

## 4. 100000 商品容量推演

当前机器上没有再继续执行 100000 商品的真实全量压测，因为 10000 商品时已经明确暴露两个事实：

1. `recommend_home` 仍缺画像缓存和候选缓存。
2. `related_products` 仍保留明显的全量相似度计算边界。

因此 100000 商品规模的结论不是“暂时没测”，而是：

* 在现有实现下，直接扩到 100000 商品不会是健康的答辩演示配置；
* 必须先完成以下优化，100000 规模才有现实意义：
  * `related_products` 改成 ANN-only 或缓存化
  * 用户画像缓存 / 推荐结果缓存分层
  * 更严格的 rerank 候选上限
  * 增量索引替代高频 full rebuild

换句话说，100000 商品不是“再跑一遍脚本”的问题，而是架构优化门槛。

## 5. 趋势结论

### 5.1 搜索链路比推荐链路健康得多

从 100 到 10000 商品：

* `search_keyword p95`: `148.747 -> 2298.531`
* `search_semantic p95`: `3951.732 -> 4030.115`

说明：

* Qdrant hybrid search 的规模弹性总体可接受；
* semantic search 的主要成本来自 embedding/rerank，而不只是商品规模放大。

### 5.2 首页推荐是当前主要性能风险

`recommend_home p95` 从：

* `3459.140 ms` 提升到
* `38891.419 ms`

说明多路召回和排序虽然功能完整，但：

* 画像构建
* 候选准备
* 最终排序与去重

仍然没有做到足够缓存化。

### 5.3 相似商品接口是最急需优化的旧边界

`related_products p95`：

* `944.922 ms -> 6521.339 ms -> 90946.377 ms`

这组数据很直接地说明：

* 相似商品接口已经不适合继续保留全量扫描思路；
* 如果要继续扩大商品规模，优先级最高的技术债就是把它迁到纯向量库候选路径。

### 5.4 协同过滤构建不是瓶颈

`build_collaborative_index` 始终维持在 `150-180 ms` 左右，说明：

* sparse user index + item cooccurrence 的当前离线构建方式是轻量的；
* 当前性能问题主要不在协同过滤层，而在内容推荐和相似商品的在线计算路径。

## 6. 缓存效果

当前已经生效的缓存：

* Qdrant 连接状态短 TTL 缓存
* 推荐接口结果缓存

当前缓存产生的实际效果：

* 后台状态页和前台推荐页不再因为重复探活而明显抖动
* Phase 11 修复后的并发首写不会再因为重复探测/重复建索引而直接触发唯一键冲突

但需要明确：

* 当前缓存主要解决的是运行时稳定性和局部重复请求；
* 并没有根本解决 10k 商品下 `recommend_home` 和 `related_products` 的算法级瓶颈。

## 7. 对答辩的意义

这份压测报告最重要的价值，不是证明“系统足够快”，而是证明：

1. 系统已经能稳定跑到 10k 商品级别。
2. 搜索链路已经完成 Qdrant hybrid 化。
3. 性能瓶颈已经被量化定位，而不是停留在主观感受。

因此答辩时可以明确说：

* 这个系统已经不是 demo 级脚本；
* 它有正式的压测数据、明确的瓶颈定位和下一步优化路线。

## 8. 下一步优化优先级

建议按这个顺序继续优化：

1. `related_products` 迁移到 ANN-only 检索或预计算缓存。
2. 首页推荐增加画像缓存和候选缓存。
3. 将 full rebuild 更多地替换为 incremental / retry_failed。
4. 若继续做大规模演示，再补真实 FastEmbed 推理成本报告。
