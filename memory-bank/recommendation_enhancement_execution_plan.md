# 拾遗阁推荐系统增强执行计划

> 基于 `memory-bank/shiyige_recommendation_upgrade_plan.md` 中已经进入实现阶段的增强方向整理。  
> 本文件不重复主升级计划，而是只聚焦“当前仓库还值得继续做、且能直接提升答辩展示与系统完整性”的增强项。  
> 执行要求：每一阶段都要先实现、再验证、再更新 `progress.md`/`architecture.md`，最后单独 git 提交后进入下一阶段。

---

## 一、当前判断

当前仓库已经具备以下能力骨架：

* Qdrant 独立向量数据库已接入。
* 搜索已经具备 hybrid search 与 rerank 能力。
* 推荐已经具备多路召回、候选融合、排序器、协同过滤、日志与评估脚本。
* 后台已经具备仪表盘、推荐调试页、实验配置页、索引状态页。

当前更值得继续增强的，不是重复造推荐算法模块，而是把已有能力：

* 做得更可观测；
* 做得更可展示；
* 做得更可运营；
* 做得更可答辩。

---

## 二、增强主线

### Phase E1：推荐指标可观测页

**目标**

把现有推荐日志、搜索日志和运行时状态，整理成后台可直接展示的推荐指标页，补齐“通道拆解、fallback 状态、槽位分布、实验版本分布”等答辩关键证据。

**具体任务**

1. 增强 `backend/app/services/recommendation_admin.py` 的指标汇总：
   * 新增 `unique_user_count`
   * 新增 `fallback_request_count`
   * 新增 `fallback_rate`
   * 新增 `average_impressions_per_request`
   * 新增 `channel_breakdown`
   * 搜索指标新增 `pipeline_breakdown`
2. 新增后台页面：
   * `admin/recommendation-metrics.html`
3. 扩展后台脚本：
   * `admin/js/app.js`
   * 导航增加“推荐指标”
   * 渲染推荐 KPI、槽位分布、通道分布、Pipeline 分布、运行时状态
4. 补充测试：
   * 新增推荐指标服务测试，覆盖通道分布与 fallback 统计

**验证**

```bash
./.venv/bin/python -m pytest backend/tests/services/test_recommendation_admin_metrics.py -q
./.venv/bin/python -m pytest backend/tests/api/test_admin_dashboard.py -q
curl -I http://127.0.0.1/admin/recommendation-metrics.html
curl -s http://127.0.0.1/api/v1/health
```

**建议提交信息**

```bash
git commit -m "admin: add recommendation metrics page"
```

---

### Phase E2：实验对比台增强

**目标**

把当前只读的实验配置页增强为“实验能力对比台”，让答辩时能直接解释 baseline、hybrid、hybrid_rerank、full_pipeline 的差异。

**具体任务**

1. 在后台实验配置页增加能力矩阵视图：
   * dense recall
   * sparse recall
   * ColBERT rerank
   * collaborative filtering
   * weighted ranker / LTR
   * diversity / exploration
2. 增加实验摘要字段：
   * 当前运行时是否降级到 baseline
   * 当前排序器
   * 当前 collection 状态
3. 把 `docs/recommendation_evaluation.md` 与 `docs/performance_benchmark.md` 的关键信息提炼成后台说明卡片。

**验证**

```bash
./.venv/bin/python -m pytest backend/tests/api/test_admin_recommendation_debug.py -q
curl -I http://127.0.0.1/admin/recommendation-config.html
```

**建议提交信息**

```bash
git commit -m "admin: enhance recommendation experiment comparison"
```

---

### Phase E3：前台推荐证据展示增强

**目标**

让前台首页、购物车推荐、下单完成推荐、相似商品推荐，不只“有结果”，还明显展示“为什么推荐”“来自哪些召回通道”。

**具体任务**

1. 统一前台推荐卡片证据展示：
   * source chips
   * 推荐理由
   * 特征亮点摘要
2. 梳理各入口一致性：
   * `front/js/home-page.js`
   * `front/js/cart.js`
   * `front/js/checkout.js`
   * `front/js/product.js`
   * `front/js/main.js`
3. 明确 slot 文案差异：
   * `home`
   * `cart`
   * `order_complete`
   * `related`

**验证**

```bash
./.venv/bin/python -m pytest backend/tests/api/test_recommendations.py -q
./.venv/bin/python -m pytest backend/tests/api/test_related_products.py -q
curl -L -I http://127.0.0.1/
curl -L -I http://127.0.0.1/front/product.html
```

**建议提交信息**

```bash
git commit -m "front: strengthen recommendation evidence display"
```

---

### Phase E4：冷启动与探索位运营增强

**目标**

把计划里已经存在的“新品探索、冷启动、热点趋势”从算法实现，提升为后台和调试接口可见、可解释、可截图的能力。

**具体任务**

1. 在推荐调试接口中补充：
   * exploration 命中标记
   * diversity 调整结果
   * cold start 召回命中说明
2. 后台指标页增加：
   * 冷启动请求数
   * exploration 命中率
   * 新品召回占比
3. 调试页增加：
   * 每个候选是否因探索位保留
   * 是否触发类目去重

**验证**

```bash
./.venv/bin/python -m pytest backend/tests/test_ranker.py -q
./.venv/bin/python -m pytest backend/tests/test_recommendation_pipeline.py -q
```

**建议提交信息**

```bash
git commit -m "backend: expose exploration and cold-start evidence"
```

---

### Phase E5：评估与答辩收口

**目标**

把离线评估、性能压测、推荐升级文档与后台页面串起来，形成“可运行 + 可展示 + 可解释 + 可证明”的最终答辩材料。

**具体任务**

1. 整理并补强：
   * `docs/recommendation_pipeline.md`
   * `docs/recommendation_evaluation.md`
   * `docs/performance_benchmark.md`
2. 新增答辩引导文档：
   * `docs/defense_script.md`
3. 在后台加入：
   * 报告入口说明
   * 当前评估产物更新时间

**验证**

```bash
./.venv/bin/python backend/scripts/evaluate_recommendations.py
./.venv/bin/python backend/scripts/benchmark_recommendations.py --products 10000 --users 200
./.venv/bin/python -m pytest backend/tests -q
```

**建议提交信息**

```bash
git commit -m "docs: finalize recommendation enhancement artifacts"
```

---

## 三、执行顺序

当前按以下顺序推进：

1. Phase E1：推荐指标可观测页
2. Phase E2：实验对比台增强
3. Phase E3：前台推荐证据展示增强
4. Phase E4：冷启动与探索位运营增强
5. Phase E5：评估与答辩收口

---

## 四、当前执行项

当前正在执行：

* **Phase E4：冷启动与探索位运营增强**

当前阶段完成标准：

* 推荐调试接口能直接看出候选是否命中探索位、冷启动逻辑和多样性调整；
* 后台指标页能展示冷启动请求、探索位命中率和新品召回占比；
* 至少有一组自动化测试覆盖探索位或冷启动相关的新字段；
* 通过验证后更新 `memory-bank/progress.md` 与 `memory-bank/architecture.md`；
* 单独 git 提交。
