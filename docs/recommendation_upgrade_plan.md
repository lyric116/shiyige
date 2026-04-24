# 推荐系统升级执行说明

## 1. 文档定位

`memory-bank/shiyige_recommendation_upgrade_plan.md` 是完整的升级主文档，本文件只提炼当前执行时必须遵守的原则、阶段顺序和验收基线，避免后续开发时只看到代码看不到约束。

## 2. 升级原则

* 先冻结 baseline，再替换实现，禁止直接覆盖旧逻辑导致无法对比。
* PostgreSQL 继续承担业务数据，独立向量检索迁移到 Qdrant。
* 每一阶段都必须包含：
  * 代码实现
  * 自动化验证
  * `memory-bank/progress.md` 更新
  * `memory-bank/architecture.md` 更新
  * 独立 git 提交
* 在 Qdrant 能力稳定前，旧推荐逻辑必须保留为 fallback。

## 3. 阶段顺序

1. Phase 1：基线冻结与问题确认
2. Phase 2：引入 Qdrant 独立向量数据库
3. Phase 3：设计 Qdrant 商品 Collection
4. Phase 4：升级 Embedding 服务
5. Phase 5：构建商品向量索引任务
6. Phase 6：搜索页改造为混合检索
7. Phase 7：实现完整多路召回推荐系统
8. Phase 8：实现协同过滤推荐
9. Phase 9：实现高级排序与重排
10. Phase 10：补齐日志、离线评估与性能压测
11. Phase 11：前台和后台展示改造
12. Phase 12：文档、答辩材料与最终验收

## 4. 当前基线文件

本轮已补齐以下 baseline 资产：

* `docs/recommendation_baseline_analysis.md`
* `docs/recommendation_baseline_metrics.json`
* `backend/scripts/export_baseline_recommendation_metrics.py`
* `backend/tests/test_recommendation_baseline.py`

## 5. 当前阶段验收方法

Phase 1 的验收命令：

```bash
docker compose up -d
./.venv/bin/python -m pytest backend/tests/test_recommendation_baseline.py -q
./.venv/bin/python -m backend.scripts.export_baseline_recommendation_metrics
```

Phase 1 验收标准：

* 不修改现有推荐逻辑。
* 能稳定导出 baseline 指标文件。
* 指标文件包含固定 query、固定用户画像和 TopK 结果。
* 后续所有阶段都能继续复用这份 baseline 做对照。
