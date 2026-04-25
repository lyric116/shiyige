# 推荐系统流程说明

## 配套材料

* 评估结论：`docs/recommendation_evaluation.md`
* 最新评估原始产物：`docs/generated/recommendation_evaluation_latest.md`
* 压测结论：`docs/performance_benchmark.md`
* 最新压测原始产物：`docs/generated/performance_benchmark_latest.md`
* 答辩讲稿：`docs/defense_script.md`

## 1. 升级目标

旧版本的首页推荐本质上是：

```text
用户行为 -> 一份画像向量 -> 全量商品 cosine -> 规则加分 -> 返回结果
```

这套方案有三个问题：

1. 候选来源太单一。
2. 排序层不清晰，解释能力弱。
3. 冷启动、探索、多样性和协同过滤都没有形成正式模块。

升级后的目标是把它改造成：

```text
多路召回 -> 候选融合 -> 特征构建 -> 排序 -> 业务重排 -> 解释生成
```

## 2. 总体流程图

```text
UserBehaviorLog / SearchLog / Order / Cart
        |
        v
build_user_interest_profile()
        |
        +--------------------+
        |                    |
        v                    v
  content recall         sparse recall
        |                    |
        +----+----------+----+
             |          |
             v          v
     collaborative   related_products
             |          |
             +----+-----+
                  |
                  v
          trending / new_arrival / cold_start
                  |
                  v
            candidate_fusion.py
                  |
                  v
          ranking_features.py
                  |
                  v
           ranker.py / ltr_ranker.py
                  |
                  v
          business_rules.py / diversity
                  |
                  v
      recommendation_explainer.py
                  |
                  v
 /api/v1/recommendations + admin debug + 前台展示
```

## 3. 运行时入口

推荐系统的正式入口是：

* `backend/app/services/recommendation_pipeline.py`

接口出口是：

* `GET /api/v1/products/recommendations`
* `GET /api/v1/recommendations`
* `GET /api/v1/admin/recommendations/debug`

其中前台公开接口主要面向展示：

* `source_type`
* `source_label`
* `reason`
* `feature_highlights`

后台 debug 接口则额外暴露：

* `recall_channels`
* `channel_details`
* `ranking_features`
* `score_breakdown`
* `feature_summary`
* `ranker_name`

## 4. 多路召回

当前正式召回通道包括：

| 通道 | 作用 | 典型解释 |
| --- | --- | --- |
| `content_profile` | 基于用户画像 dense 语义召回 | 基于你近期关注的汉服/刺绣偏好推荐 |
| `sparse_interest` | 基于 `top_terms` 稀疏兴趣召回 | 命中你最近搜索或浏览过的关键词 |
| `related_products` | 以用户最近浏览/加购商品为种子找相似商品 | 与你最近看过的商品在工艺/朝代上相近 |
| `collaborative_user` | 相似用户召回 | 与你兴趣相似的用户也喜欢 |
| `item_cooccurrence` | item-item 共现召回 | 经常和你最近关注商品一起出现 |
| `trending` | 热门召回 | 近期站内热门 |
| `new_arrival` | 新品探索 | 新上架且可售商品 |
| `cold_start` | 行为不足时的冷启动分支 | 新用户先看热门与新品的混合结果 |

每个召回候选都会保留：

* `recall_channel`
* `recall_score`
* `rank_in_channel`
* `matched_terms`
* `reason_parts`

这意味着系统不会在召回阶段就丢失“这条候选是怎么来的”的证据。

## 5. 候选融合

融合层位于：

* `backend/app/services/candidate_fusion.py`

当前策略：

1. 汇总所有通道候选
2. 按通道权重做加权 RRF
3. 合并 matched terms 和 reason parts
4. 保留 per-channel detail rows

融合层的职责不是做最终排序，而是把“多来源候选”收成一份带证据的统一列表，为后续 ranker 提供干净输入。

## 6. 排序层

排序相关模块：

* `backend/app/services/ranking_features.py`
* `backend/app/services/ranker.py`
* `backend/app/services/ltr_ranker.py`
* `backend/app/services/recommendation_explainer.py`

### 6.1 特征组

当前会构造四大类特征：

* recall 特征
* 用户兴趣匹配特征
* 商品质量特征
* 业务规则特征

### 6.2 Ranker

当前线上默认：

* `weighted_ranker`

预留能力：

* `ltr_ranker`

最终分数会拆成：

* `recall_score`
* `interest_score`
* `quality_score`
* `business_total`
* `final_score`

因此系统当前已经不是“召回分最高就排第一”，而是进入正式排序阶段。

## 7. 多样性与业务后处理

业务后处理位于：

* `backend/app/services/business_rules.py`

当前主要处理：

* 近期曝光降权
* 同类目连续上限
* 朝代/工艺集中度控制
* 探索位注入
* 下架/库存过滤

这一步的意义是把“模型排序”与“业务约束”分层，而不是把所有启发式规则混在召回里。

## 8. 冷启动策略

冷启动不是兜底异常，而是正式策略：

* 用户行为少时，显式走 `cold_start`
* 结果由 `trending + new_arrival` 混合构成
* 仍然会带上 `source_label` 和 `reason`

这让系统能回答：

* 新用户为什么还能看到推荐？
* 为什么不是简单给一个热门榜？

## 9. 推荐理由生成

推荐解释链来自三层：

1. 召回阶段的 `reason_parts`
2. 排序阶段的 `feature_highlights`
3. 展示阶段的 `source_label`

最终前台会展示：

* 个性化
* 相似商品
* 热门
* 新品探索
* 节令主题

这正是 Phase 11 前台展示升级的关键。

## 10. 降级与缓存

### 10.1 降级

当 Qdrant 不可用或索引未就绪时：

* 推荐入口会退回 baseline
* 后台与健康检查会明确标记 `degraded_to_baseline`

### 10.2 当前缓存

当前已经有：

* 推荐接口结果缓存
* Qdrant 连接状态短 TTL 缓存

当前还没有完全做好的：

* 用户画像缓存分层
* 大规模候选缓存
* 相似商品 ANN-only 改造

这也是为什么 10k 商品规模下 `recommend_home` 和 `related_products` 依旧是性能瓶颈。

## 11. 与旧版本的对照结论

| 旧版 | 当前版本 |
| --- | --- |
| 单画像向量 + 全表 cosine | 多路召回 + 候选融合 + 排序 + 重排 |
| 推荐理由单薄 | 每条结果都有来源标签和解释 |
| 冷启动不正式 | 冷启动是独立召回分支 |
| 协同过滤只是轻量日志聚合 | 已有 sparse user index + item cooccurrence |
| 只在接口层返回商品列表 | 前台和后台都能看到推荐证据链 |

## 12. 答辩时的核心结论

当前推荐系统已经可以明确表述为：

* 不是只做余弦相似度；
* 而是先做多路召回，再做融合与排序，最后做业务重排与解释展示的完整推荐流水线。
