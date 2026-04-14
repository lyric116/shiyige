# 测试报告

## 1. 执行范围

本轮报告覆盖最终交付前的关键回归：

* Compose 启动与访问验证
* 后端全量测试
* 主演示链路 e2e 回归

## 2. 执行命令

```bash
docker compose config --quiet
docker compose up -d
curl -f http://127.0.0.1/api/v1/health
curl -f http://127.0.0.1
./.venv/bin/python -m pytest backend/tests -q
./.venv/bin/python -m pytest tests/e2e/test_full_demo_flow.py -q
```

## 3. 结果

* `docker compose config --quiet`：通过
* `docker compose up -d`：通过
* `curl -f http://127.0.0.1/api/v1/health`：通过
* `curl -f http://127.0.0.1`：通过
* `./.venv/bin/python -m pytest backend/tests -q`：`103 passed`
* `./.venv/bin/python -m pytest tests/e2e/test_full_demo_flow.py -q`：`1 passed`

## 4. 本轮发现并修复的问题

* PostgreSQL 启动时迁移失败：会员、评价、后台管理员迁移中的布尔默认值使用了 `0/1`，已改为 `sa.false()` / `sa.true()`。
* 推荐结果不会随用户行为更新：首次访问推荐后会命中缓存，后续浏览、搜索、加购、下单、支付不会刷新结果，已补用户级推荐缓存失效逻辑并新增集成测试。

## 5. 当前剩余风险

* 测试通过但仍存在大量 `datetime.utcnow()` 相关弃用警告，后续建议统一迁移到 timezone-aware UTC 时间。
* E2E 依赖本地 Playwright 浏览器环境；首次在新机器执行前需确保浏览器依赖已安装。
