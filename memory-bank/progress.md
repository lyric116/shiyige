# Progress Log

## 2026-04-25

### 完成事项

* 修复了 `nginx/default.conf` 中 `/admin/` 的精确匹配配置错误。
* 原配置把 `location = /admin/` 直接 `alias` 到单个文件，导致 Nginx 在访问 `/admin/` 时拼出错误路径 `index.htmlindex.html` 并返回 `500`。
* 现改为显式跳转到 `/admin/index.html`，后台首页入口恢复可访问。

### 本次修改文件

* `nginx/default.conf`
* `memory-bank/progress.md`
* `memory-bank/architecture.md`

### 已执行验证

* `docker compose exec -T nginx nginx -t`
* `docker compose restart nginx`
* `curl -L -I http://127.0.0.1/admin/`

结果：

* Nginx 配置语法检查通过。
* `http://127.0.0.1/admin/` 已从原来的 `500` 变为 `302 -> /admin/index.html -> 200`。

### 关键发现

* 这一步只修复了后台静态入口的 Nginx 配置问题。
* API 当前仍未完成启动，`/api/v1/health` 还是 `502`，根因是数据库迁移卡在 `20260424_12_recommendation_logging`。

### 下一步起点

* 下一步应修复 `backend/alembic/versions/20260424_12_recommendation_logging.py`，让已有日志表但 Alembic 版本未前进的数据库也能顺利升级。

### 继续推进记录

* 已修复 `backend/alembic/versions/20260424_12_recommendation_logging.py`，把日志表迁移改为幂等升级。
* 新迁移逻辑会在升级时先检查表与索引是否存在：已存在的表跳过建表，缺失的索引补建，避免 PostgreSQL 数据卷处于“表已在库中、Alembic 版本仍停在旧 revision”时反复报 `DuplicateTable`。
* 重新构建并启动 `api` 容器后，当前数据库已从 `20260424_11` 成功升级到 `20260424_12`，`uvicorn` 已正常启动。

### 追加修改文件

* `backend/alembic/versions/20260424_12_recommendation_logging.py`

### 追加验证

* `docker compose up -d --build api`
* `docker compose logs --tail=200 api`
* `docker compose exec -T postgres psql -U shiyige -d shiyige -c "select version_num from alembic_version;"`
* `curl -i http://127.0.0.1/api/v1/health`
* `curl -L -I http://127.0.0.1/admin/`

结果：

* Alembic 已成功执行 `20260424_11 -> 20260424_12`。
* `alembic_version` 当前为 `20260424_12`。
* `http://127.0.0.1/api/v1/health` 返回 `200`。
* `http://127.0.0.1/admin/` 返回 `302 -> /admin/index.html -> 200`。

### 推荐增强计划与 Phase E1

* 新增了 `memory-bank/recommendation_enhancement_execution_plan.md`，把推荐升级计划里更适合当前仓库继续落地的增强项收敛成 5 个执行阶段。
* 已完成 Phase E1：推荐指标可观测页。
* 后端推荐指标聚合新增：
  * `unique_user_count`
  * `fallback_request_count`
  * `fallback_rate`
  * `average_impressions_per_request`
  * `channel_breakdown`
  * 搜索侧 `pipeline_breakdown`
* 新增后台页面 `admin/recommendation-metrics.html`，并在后台导航中加入“推荐指标”入口。
* `admin/js/app.js` 已接入新的推荐指标页渲染逻辑，可展示推荐 KPI、转化 KPI、运行时状态、槽位分布、召回通道分布、推荐 pipeline 分布和搜索 pipeline 分布。
* 新增自动化测试 `backend/tests/services/test_recommendation_admin_metrics.py`，覆盖推荐通道分布、fallback 统计和搜索 pipeline 分布。

### 本阶段修改文件

* `memory-bank/recommendation_enhancement_execution_plan.md`
* `backend/app/services/recommendation_admin.py`
* `backend/tests/services/test_recommendation_admin_metrics.py`
* `backend/tests/api/test_admin_recommendation_debug.py`
* `admin/recommendation-metrics.html`
* `admin/js/app.js`
* `memory-bank/progress.md`
* `memory-bank/architecture.md`

### 本阶段验证

* `./.venv/bin/python -m pytest backend/tests/services/test_recommendation_admin_metrics.py -q`
* `./.venv/bin/python -m pytest backend/tests/api/test_admin_dashboard.py backend/tests/api/test_admin_recommendation_debug.py -q`
* `./.venv/bin/python -m ruff check backend/app/services/recommendation_admin.py backend/tests/services/test_recommendation_admin_metrics.py backend/tests/api/test_admin_recommendation_debug.py`
* `node --check admin/js/app.js`
* `curl -I http://127.0.0.1/admin/recommendation-metrics.html`
* `curl -s http://127.0.0.1/api/v1/health`

结果：

* 新增服务测试 `2 passed`。
* 管理后台相关 API 测试 `5 passed`。
* `ruff check` 通过。
* 后台脚本语法检查通过。
* `http://127.0.0.1/admin/recommendation-metrics.html` 返回 `200`。
* API 健康检查返回 `200`。

### 当前结论

* 当前项目已经不只是“有推荐日志”，而是开始把日志变成后台可直接展示的指标资产。
* 这一步对答辩非常关键，因为它把“多路召回、fallback、实验版本、搜索后端是否真实生效”转成了可截图、可解释、可对比的后台证据。

### 下一步起点

* 下一步进入 `recommendation_enhancement_execution_plan.md` 的 **Phase E2：实验对比台增强**。

### Phase E2：实验对比台增强

* 已完成 `recommendation_enhancement_execution_plan.md` 中的 Phase E2。
* `backend/app/services/recommendation_admin.py` 现在会在实验配置接口里返回：
  * `runtime_summary`
  * `capability_catalog`
  * `comparison_notes`
* `admin/recommendation-config.html` 已升级为真正的实验对比台：
  * 增加当前运行时区块
  * 增加能力矩阵表
  * 增加答辩解释提示卡片
* `admin/js/app.js` 已支持实验页渲染能力矩阵和运行时降级说明。
* `backend/tests/api/test_admin_recommendation_debug.py` 已补充实验配置接口对新字段的断言。

### Phase E2 修改文件

* `backend/app/services/recommendation_admin.py`
* `backend/tests/api/test_admin_recommendation_debug.py`
* `admin/recommendation-config.html`
* `admin/js/app.js`
* `memory-bank/progress.md`
* `memory-bank/architecture.md`

### Phase E2 验证

* `./.venv/bin/python -m pytest backend/tests/api/test_admin_recommendation_debug.py -q`
* `./.venv/bin/python -m ruff check backend/app/services/recommendation_admin.py backend/tests/api/test_admin_recommendation_debug.py`
* `node --check admin/js/app.js`
* `curl -I http://127.0.0.1/admin/recommendation-config.html`

结果：

* `test_admin_recommendation_debug.py` 通过，实验接口现已覆盖新增返回字段。
* `ruff check` 通过。
* 后台脚本语法检查通过。
* `http://127.0.0.1/admin/recommendation-config.html` 返回 `200`。

### Phase E2 当前结论

* 后台实验页现在不再只是“卡片列表”，而是能直接说明：
  * 当前是否降级到 baseline
  * 当前搜索/推荐后端是什么
  * 每个实验方案到底启用了哪些能力
* 这一步把实验配置从“文档性页面”推进成了“答辩解释页面”。

### 下一步起点

* 下一步进入 `recommendation_enhancement_execution_plan.md` 的 **Phase E3：前台推荐证据展示增强**。

### Phase E3：前台推荐证据展示增强

* 已完成 `recommendation_enhancement_execution_plan.md` 中的 Phase E3。
* `front/js/main.js` 现在不只负责全站通用交互，还统一承担推荐卡片证据渲染：
  * 新增 `buildRecommendationHighlights()`
  * `renderEvidence()` 现会组合来源标签、解释标签和亮点标签
* 前台推荐证据会优先展示以下信息：
  * `feature_highlights`
  * `matched_terms`
  * `is_exploration`
  * `ltr_fallback_used`
  * `source_breakdown`
  * `diversity_result`
  * 首页推荐的 `recall_channels`
* 首页、商品详情页、购物车页和下单完成页都已经通过 `window.shiyigeRecommendationUI.renderProductCard()` 复用统一证据渲染逻辑，因此本阶段无需分别复制一套推荐理由 UI。

### Phase E3 修改文件

* `front/js/main.js`
* `memory-bank/progress.md`
* `memory-bank/architecture.md`
* `memory-bank/recommendation_enhancement_execution_plan.md`

### Phase E3 验证

* `./.venv/bin/python -m pytest backend/tests/api/test_recommendations.py -q`
* `./.venv/bin/python -m pytest backend/tests/api/test_related_products.py -q`
* `node --check front/js/main.js`
* `curl -L -I http://127.0.0.1/`
* `curl -L -I http://127.0.0.1/product.html`
* `curl -L -I http://127.0.0.1/cart.html`
* `curl -L -I http://127.0.0.1/checkout.html`

结果：

* 推荐接口测试 `2 passed`。
* 相似商品接口测试 `1 passed`。
* 前台通用脚本语法检查通过。
* 首页、商品详情页、购物车页和结算页入口均返回 `200`。

### Phase E3 当前结论

* 当前前台推荐模块已经从“只显示推荐结果”提升到“同时显示推荐证据”。
* 这一步对展示和答辩很关键，因为它把后台已经存在的召回通道、探索位、匹配词和排序回退信息前移到了用户界面。

### 下一步起点

* 下一步进入 `recommendation_enhancement_execution_plan.md` 的 **Phase E4：冷启动与探索位运营增强**。

## 2026-04-13

### 完成事项

* 阅读了 `memory-bank/design.md`、`memory-bank/implementation_plan.md`、`memory-bank/progress.md`、`memory-bank/architecture.md`。
* 按实施计划执行了 **Step 01. 冻结当前仓库现状**。
* 新增了 `docs/current_state.md`，盘点了现有页面、`localStorage` 使用点、缺失页面、假数据来源和与设计文档的差距。
* 没有开始 Step 02；`docs/page_api_matrix.md` 还未创建。

### 本次修改文件

* `docs/current_state.md`
* `memory-bank/progress.md`
* `memory-bank/architecture.md`

### 已执行验证

* `test -f docs/current_state.md`
* `rg -n "localStorage|orders\\.html|favorites\\.html" docs/current_state.md`
* `rg -n "index.html|product.html|cart.html|checkout.html|login.html|register.html|profile.html|membership.html" docs/current_state.md`

结果：

* 三条验证命令全部返回成功。
* Step 01 已通过验证，可作为后续开发起点。

### 关键发现

* 当前项目仍是静态前端原型，核心业务状态依赖 `localStorage`，覆盖登录、购物车、订单、会员和积分。
* `orders.html` 与 `favorites.html` 被引用但并不存在，当前导航和个人中心含死链。
* `front/category.html` 和 `front/product.html` 内联了主要商品/分类假数据；`front/js/checkout.js` 在本地生成订单并修改会员数据。
* `front/js/cart.js` 与 `front/cart.html` 各自维护一套购物车逻辑，后续接后端时需要合并职责。
* `front/js/main.js` 的图片失败兜底指向 `/static/images/banner1.svg`，但当前仓库没有该文件。

### 后续安全起点

* 下一位开发者如果继续实施计划，应从 **Step 02. 固化页面与接口映射** 开始。
* 在进入 Step 02 前，不要改写 `docs/current_state.md` 的结论，它是当前仓库基线盘点文档。

### 继续推进记录

在同一轮后续执行中，已经继续完成：

* **Step 02. 固化页面与接口映射**
* **Step 03. 清理死链与补齐占位页**
* **Step 04. 建立目录骨架**
* **Step 05. 初始化依赖与测试工具链**
* **Step 06. 建立 Docker Compose 骨架**
* **Step 07. 建立 FastAPI 应用骨架**

### 新增与修改的核心文件

Step 02:

* `docs/page_api_matrix.md`

Step 03:

* `front/orders.html`
* `front/js/auth.js`
* `front/profile.html`

Step 04:

* `backend/app/`
* `backend/tests/`
* `admin/`
* `tests/e2e/`

Step 05:

* `backend/requirements.txt`
* `backend/requirements-dev.txt`
* `pytest.ini`
* `ruff.toml`
* `docs/testing.md`
* `backend/tests/test_toolchain_smoke.py`

Step 07:

* `backend/__init__.py`
* `backend/app/main.py`
* `backend/app/api/router.py`
* `backend/app/api/v1/router.py`
* `backend/app/api/v1/health.py`
* `backend/tests/conftest.py`
* `backend/tests/api/test_health.py`

### 已通过的验证

Step 02:

* `test -f docs/page_api_matrix.md`
* `rg -n "/api/v1|front/" docs/page_api_matrix.md`

Step 03:

* `test -f front/orders.html`
* `! rg -n "favorites\\.html" front`
* `rg -n "orders\\.html" front`

Step 04:

* `test -d backend/app`
* `test -d backend/tests`
* `test -d admin`
* `test -d tests/e2e`

Step 05:

* `test -f backend/requirements.txt`
* `test -f backend/requirements-dev.txt`
* `UV_CACHE_DIR=.uv-cache uv run --with pytest pytest --collect-only`

Step 06:

* `test -f docker-compose.yml`
* `docker compose config --quiet`

Step 07:

* `UV_CACHE_DIR=.uv-cache uv run --with fastapi --with httpx --with pytest --with pytest-asyncio pytest backend/tests/api/test_health.py -q`
* `curl --noproxy '*' -f http://127.0.0.1:8000/api/v1/health`
* `curl --noproxy '*' -f http://127.0.0.1:8000/docs`

### 本轮关键环境决策

* 系统环境里没有全局 `pytest`，也没有 `python3 -m pytest` 可用，所以测试执行入口改为 `uv`。
* `uv` 默认缓存目录在当前沙箱不可写，因此统一改为项目内缓存：`UV_CACHE_DIR=.uv-cache`。
* 为了让后续开发稳定运行，本地创建了项目级 `.venv`，并通过 `uv pip install --python .venv/bin/python ...` 把 `fastapi`、`uvicorn`、`httpx`、`pytest`、`pytest-asyncio` 装进了项目环境。
* 本地绑定监听端口在普通沙箱中失败，Step 07 的 `uvicorn` 启动和最终 `curl` 验证是在提权上下文中完成的。

### 当前状态总结

* Phase 0 的 Step 01 到 Step 07 已完成并通过验证。
* 当前仓库已经不再只是纯静态前端盘点状态，而是具备了：
  * 页面与接口映射文档
  * 死链修复和订单占位页
  * 后端目录骨架
  * 测试工具链基线
  * Docker Compose 骨架
  * 可访问 `/api/v1/health` 和 `/docs` 的最小 FastAPI 应用

### 下一步起点

* 下一位开发者应从 **Step 08. 统一配置、日志、异常、响应结构** 继续。
* 继续前应注意：
  * 当前 `.venv` 与 `.uv-cache` 已可复用。
  * 运行本地 HTTP 服务或本地 `curl` 命中服务时，可能仍需要提权上下文。
  * `backend/tests/api/test_health.py` 已切换为 `httpx.ASGITransport` 异步测试，不要再退回到先前会卡住的 `TestClient` 写法。

## 2026-04-14

### 完成事项

* 继续按实施计划推进，补完并验证了 **Step 08 到 Step 14**。
* 已建立统一配置、日志、异常处理、统一响应结构和 `X-Request-ID` 中间件。
* 已建立数据库连接、Alembic 迁移基线、Redis/MinIO 客户端包装和基础测试夹具。
* 已补齐用户域模型：`users`、`user_profile`、`user_address`、`user_behavior_log`。
* 已建立前端统一请求入口 `front/js/api.js` 和统一会话入口 `front/js/session.js`。
* 已完成安全基础：密码哈希、密码校验、access token、refresh token、鉴权依赖、角色判断。

### 本次修改文件

* `backend/app/core/config.py`
* `backend/app/core/logger.py`
* `backend/app/core/error_codes.py`
* `backend/app/core/responses.py`
* `backend/app/core/exceptions.py`
* `backend/app/core/request_id.py`
* `backend/app/core/database.py`
* `backend/app/core/redis.py`
* `backend/app/core/minio.py`
* `backend/app/core/security.py`
* `backend/app/models/base.py`
* `backend/app/models/user.py`
* `backend/app/models/__init__.py`
* `backend/alembic.ini`
* `backend/alembic/env.py`
* `backend/alembic/script.py.mako`
* `backend/alembic/versions/20260413_01_baseline.py`
* `backend/alembic/versions/20260413_02_user_domain.py`
* `backend/tests/api/test_error_response.py`
* `backend/tests/integration/test_db_session.py`
* `backend/tests/integration/test_infra_clients.py`
* `backend/tests/models/test_user_models.py`
* `backend/tests/unit/test_settings.py`
* `backend/tests/unit/test_security.py`
* `front/js/api.js`
* `front/js/session.js`
* `memory-bank/progress.md`
* `memory-bank/architecture.md`

### 已执行验证

Step 08:

* `./.venv/bin/python -m pytest backend/tests/unit/test_settings.py -q`
* `./.venv/bin/python -m pytest backend/tests/api/test_error_response.py -q`

Step 09:

* `./.venv/bin/alembic -c backend/alembic.ini upgrade head`
* `./.venv/bin/python -m pytest backend/tests/integration/test_db_session.py -q`

Step 10:

* `docker compose up -d redis minio`
* `./.venv/bin/python -m pytest backend/tests/integration/test_infra_clients.py -q`

Step 11 到 Step 13:

* `./.venv/bin/python -m pytest --collect-only`
* `./.venv/bin/python -m pytest backend/tests/models/test_user_models.py -q`

Step 14:

* `./.venv/bin/python -m pytest backend/tests/unit/test_security.py -q`

结果：

* 第 14 步最新验证结果为 `5 passed`。
* 第 08 到第 14 步所要求的验证均已通过，当前可以从 **Step 15. 注册接口** 继续。

### 关键决策与交接提醒

* 当前本地测试统一使用项目级 `.venv`；命令入口优先写成 `./.venv/bin/python -m pytest ...`。
* 数据库默认仍落到 `sqlite:///./backend/dev.db`，这样能在未准备 PostgreSQL 前先推进接口开发和单元测试。
* `InfrastructureSettings` 仍要求真实环境变量完整存在；只有应用级 `AppSettings` 允许安全默认值。
* `backend/app/core/security.py` 的密码哈希已从 `bcrypt` 切换为 `pbkdf2_sha256`，原因是当前 Python 3.13 环境下 `passlib + bcrypt` 组合不稳定，会在测试里报错。
* 下一位开发者进入 Step 15 时，不要回退到 `bcrypt`，否则第 14 步会再次失败。

### 同日继续推进记录

已继续完成：

* **Step 15. 注册接口**

新增与修改：

* `backend/app/api/v1/auth.py`
* `backend/app/api/v1/router.py`
* `backend/app/schemas/__init__.py`
* `backend/app/schemas/auth.py`
* `backend/tests/api/test_auth_register.py`

第 15 步验证：

* `./.venv/bin/python -m pytest backend/tests/api/test_auth_register.py -q`

结果：

* 测试结果为 `2 passed`。
* `POST /api/v1/auth/register` 已可创建用户、自动创建一条资料记录、对密码做哈希存储，并对重复邮箱返回冲突错误。

下一步起点：

* 继续执行 **Step 16. 登录、刷新、退出**。

### 同日继续推进记录（二）

已继续完成：

* **Step 16. 登录、刷新、退出**

新增与修改：

* `backend/app/core/security.py`
* `backend/app/api/v1/auth.py`
* `backend/app/schemas/__init__.py`
* `backend/app/schemas/auth.py`
* `backend/tests/api/conftest.py`
* `backend/tests/api/test_auth_login.py`
* `backend/tests/api/test_auth_refresh.py`
* `backend/tests/api/test_auth_logout.py`
* `backend/tests/api/test_auth_register.py`
* `memory-bank/progress.md`
* `memory-bank/architecture.md`

第 16 步验证：

* `./.venv/bin/python -m pytest backend/tests/api/test_auth_login.py -q`
* `./.venv/bin/python -m pytest backend/tests/api/test_auth_refresh.py -q`
* `./.venv/bin/python -m pytest backend/tests/api/test_auth_logout.py -q`

结果：

* 登录验证结果为 `2 passed`。
* 刷新验证结果为 `2 passed`。
* 退出验证结果为 `1 passed`。
* `POST /api/v1/auth/login` 已返回 access token，并通过 HttpOnly Cookie 写入 `refresh_token`。
* `POST /api/v1/auth/refresh` 已只依赖 refresh cookie 签发新 access token，前端无需保存 refresh token。
* `POST /api/v1/auth/logout` 已清除 refresh cookie，退出后刷新接口会返回未登录错误。

交接提醒：

* 当前 refresh cookie 名称固定为 `refresh_token`，路径为 `/`，属性为 `HttpOnly + SameSite=Lax`。
* `front/js/session.js` 现在可以直接消费 `/api/v1/auth/refresh` 返回的 `data.access_token`。
* 当前测试里出现的 `datetime.utcnow()` 弃用警告来自模型默认时间戳实现，不影响第 16 步通过，但后续可以统一改成时区感知写法。

下一步起点：

* 继续执行 **Step 17. 当前用户与资料维护**。

### 同日继续推进记录（三）

已继续完成：

* **Step 17. 当前用户与资料维护**

新增与修改：

* `backend/app/api/v1/users.py`
* `backend/app/api/v1/router.py`
* `backend/app/schemas/__init__.py`
* `backend/app/schemas/user.py`
* `backend/tests/api/conftest.py`
* `backend/tests/api/test_users_me.py`
* `backend/tests/api/test_users_profile.py`
* `backend/tests/api/test_users_password.py`
* `memory-bank/progress.md`
* `memory-bank/architecture.md`

第 17 步验证：

* `./.venv/bin/python -m pytest backend/tests/api/test_users_me.py -q`
* `./.venv/bin/python -m pytest backend/tests/api/test_users_profile.py -q`
* `./.venv/bin/python -m pytest backend/tests/api/test_users_password.py -q`

结果：

* 当前用户接口验证结果为 `1 passed`。
* 资料修改接口验证结果为 `2 passed`。
* 密码修改接口验证结果为 `2 passed`。
* `GET /api/v1/users/me` 已基于 access token 返回当前用户和资料数据。
* `PUT /api/v1/users/me` 已支持更新邮箱、用户名和资料字段，并校验邮箱/用户名唯一性。
* `PUT /api/v1/users/password` 已支持校验当前密码并更新密码哈希。

交接提醒：

* 当前用户详情返回中，资料字段统一放在 `data.user.profile` 下。
* 地址字段仍未并入 `users/me`，地址管理保持在下一步单独实现。
* `backend/tests/api/conftest.py` 现在已经提供 `auth_headers_factory()`，后续地址、购物车、订单接口测试都可直接复用。

下一步起点：

* 继续执行 **Step 18. 地址管理**。

### 同日继续推进记录（四）

已继续完成：

* **Step 18. 地址管理**
* **Step 19. 接通登录与注册页**
* **Step 20. 接通个人中心与导航登录态**

新增与修改：

* `backend/app/api/v1/users.py`
* `backend/app/schemas/__init__.py`
* `backend/app/schemas/address.py`
* `backend/tests/api/test_user_addresses.py`
* `front/js/auth-pages.js`
* `front/js/auth.js`
* `front/js/profile-page.js`
* `front/login.html`
* `front/register.html`
* `front/profile.html`
* `tests/e2e/conftest.py`
* `tests/e2e/test_auth_pages.py`
* `tests/e2e/test_profile_page.py`
* `memory-bank/progress.md`
* `memory-bank/architecture.md`

第 18 步验证：

* `./.venv/bin/python -m pytest backend/tests/api/test_user_addresses.py -q`

第 19 步验证：

* `./.venv/bin/python -m pytest tests/e2e/test_auth_pages.py -q`
* `rg -n "shiyige_user|localStorage" front/login.html front/register.html`

第 20 步验证：

* `./.venv/bin/python -m pytest tests/e2e/test_profile_page.py -q`
* `rg -n "shiyige_user|localStorage" front/profile.html front/js/auth.js`
* `rg -n "favorites\\.html" front/profile.html front/js/auth.js`

结果：

* 地址接口测试结果为 `2 passed`。
* 登录/注册页 e2e 测试结果为 `2 passed`。
* 个人中心页 e2e 测试结果为 `2 passed`。
* `GET/POST/PUT/DELETE /api/v1/users/addresses` 已接通，并实现默认地址切换与删除后的兜底规则。
* `front/login.html` 与 `front/register.html` 已改为通过真实认证接口工作，不再直接写浏览器本地用户对象。
* `front/profile.html` 与 `front/js/auth.js` 已改为通过 `session.js + /api/v1/users/me` 驱动，退出登录会清理 access token 与 refresh cookie。

交接提醒：

* `tests/e2e/conftest.py` 现在会把 `front/` 静态资源和 FastAPI API 挂在同一个本地测试服务上，后续页面级测试都可以复用它。
* 本地 Playwright Chromium 已安装；后续 e2e 测试直接走 `./.venv/bin/python -m pytest tests/e2e/... -q` 即可。
* `front/js/auth.js` 已不再允许读写 `localStorage`，后续页面如果要判断登录态，应复用 `window.shiyigeAuth.fetchCurrentUser()` 或 `session.js`。

下一步起点：

* 继续执行 **Step 21. 建立商品域表**。

### 同日继续推进记录（五）

已继续完成：

* **Step 21. 建立商品域表**
* **Step 22. 准备商品基础种子数据**
* **Step 23. 创建类目接口**
* **Step 24. 创建商品列表接口**
* **Step 25. 创建商品详情接口**
* **Step 26. 接通首页与分类页**
* **Step 27. 接通商品详情页**

新增与修改：

* `backend/app/models/product.py`
* `backend/alembic/versions/20260414_03_product_domain.py`
* `backend/scripts/__init__.py`
* `backend/scripts/seed_base_data.py`
* `backend/app/api/v1/products.py`
* `backend/app/api/v1/router.py`
* `backend/app/models/__init__.py`
* `backend/alembic/env.py`
* `backend/tests/models/test_product_models.py`
* `backend/tests/integration/test_seed_base_data.py`
* `backend/tests/integration/test_product_seed_counts.py`
* `backend/tests/api/test_categories.py`
* `backend/tests/api/test_products_list.py`
* `backend/tests/api/test_product_detail.py`
* `front/index.html`
* `front/category.html`
* `front/product.html`
* `front/js/home-page.js`
* `front/js/category-page.js`
* `front/js/product.js`
* `tests/e2e/test_home_and_category.py`
* `tests/e2e/test_product_page.py`
* `memory-bank/progress.md`
* `memory-bank/architecture.md`

第 21 步验证：

* `./.venv/bin/alembic -c backend/alembic.ini upgrade head`
* `./.venv/bin/python -m pytest backend/tests/models/test_product_models.py -q`

第 22 步验证：

* `./.venv/bin/python -m pytest backend/tests/integration/test_seed_base_data.py -q`
* `./.venv/bin/python -m pytest backend/tests/integration/test_product_seed_counts.py -q`

第 23 步验证：

* `./.venv/bin/python -m pytest backend/tests/api/test_categories.py -q`

第 24 步验证：

* `./.venv/bin/python -m pytest backend/tests/api/test_products_list.py -q`

第 25 步验证：

* `./.venv/bin/python -m pytest backend/tests/api/test_product_detail.py -q`

第 26 步验证：

* `./.venv/bin/python -m pytest tests/e2e/test_home_and_category.py -q`
* `rg -n "/api/v1/categories|/api/v1/products" front`

第 27 步验证：

* `./.venv/bin/python -m pytest tests/e2e/test_product_page.py -q`
* `rg -n "/api/v1/products/" front/product.html front/js/product.js`

结果：

* 商品域模型、迁移和基础种子数据已经落地，当前测试数据库会自动初始化 5 个类目、20 个商品。
* `GET /api/v1/categories`、`GET /api/v1/products`、`GET /api/v1/products/{id}` 已接通，并覆盖分页、类目过滤、价格过滤、标签过滤、排序和关键词过滤。
* 首页、分类页、商品详情页都已改为真实请求商品接口；第 27 步商品页验证结果为 `1 passed`。
* `front/product.html` 已删除页面内联 `productData` 大块假数据，`front/js/product.js` 现在负责商品详情、缩略图、相关推荐和当前阶段的加购交互。

交接提醒：

* 当前商品详情页已经解除了对页面内联 `productData` 的依赖，但购物车仍是 Phase 3 之前的本地实现，后续要在 Step 31 统一替换。
* `tests/e2e/test_product_page.py` 使用 `id=18` 的“上元灯会礼盒”做验证，这个商品不在旧假数据里，可持续防止页面退回静态详情。
* `backend/scripts/seed_base_data.py` 现在是 e2e 和本地初始化的共同数据入口，后续新增商品相关测试时优先复用它。

下一步起点：

* 继续执行 **Step 28. 实现关键词搜索**。

### 同日继续推进记录（六）

已继续完成：

* **Step 28. 实现关键词搜索**

新增与修改：

* `backend/app/api/v1/search.py`
* `backend/app/api/v1/router.py`
* `backend/tests/api/test_search_keyword.py`
* `front/js/search.js`
* `front/js/category-page.js`
* `tests/e2e/test_search_flow.py`
* `memory-bank/progress.md`
* `memory-bank/architecture.md`

第 28 步验证：

* `./.venv/bin/python -m pytest backend/tests/api/test_search_keyword.py -q`
* `./.venv/bin/python -m pytest tests/e2e/test_search_flow.py -q`

结果：

* `GET /api/v1/search` 已接通，并支持基于关键词的分页结果、类目过滤、价格过滤和排序。
* `GET /api/v1/search/suggestions` 已接通，可返回搜索框联想词。
* 导航搜索框现在会实时请求联想接口，并在提交后跳转到分类页，通过真实搜索接口展示匹配商品。
* 第 28 步验证结果为：后端搜索测试 `2 passed`，页面级搜索流测试 `1 passed`。

交接提醒：

* 当前分类页的“搜索模式”已经从直接调用商品列表接口切到 `/api/v1/search`，因此后续如果扩展搜索排序或召回逻辑，应优先改搜索接口而不是把逻辑散回前端。
* 联想建议当前使用 `datalist` 渲染，结构简单但足够覆盖本阶段验证；后续如果要做更复杂交互，可以在不破坏 `/api/v1/search/suggestions` 契约的前提下升级。

下一步起点：

* 继续执行 **Step 29. 建立购物车表**。

### 同日继续推进记录（七）

已继续完成：

* **Step 29. 建立购物车表**

新增与修改：

* `backend/app/models/cart.py`
* `backend/app/models/user.py`
* `backend/app/models/product.py`
* `backend/app/models/__init__.py`
* `backend/alembic/versions/20260414_04_cart_domain.py`
* `backend/tests/models/test_cart_models.py`
* `memory-bank/progress.md`
* `memory-bank/architecture.md`

第 29 步验证：

* `./.venv/bin/alembic -c backend/alembic.ini upgrade head`
* `./.venv/bin/python -m pytest backend/tests/models/test_cart_models.py -q`

结果：

* `cart`、`cart_item` 两张购物车表已经落地，并完成 Alembic 迁移。
* 购物车模型已经和 `users`、`product`、`product_sku` 建立关系，且同一用户只能拥有一个购物车、同一购物车内同一 SKU 只能出现一条记录。
* 第 29 步模型测试结果为 `2 passed`。

交接提醒：

* 当前购物车域只完成了表和关系，还没有 API；前端仍在继续使用本地购物车模拟，真正替换会发生在 Step 30 和 Step 31。
* `cart_item` 当前同时持有 `product_id` 和 `sku_id`，这是为了后续购物车页和订单创建都能稳定拿到商品主信息与具体 SKU。

下一步起点：

* 继续执行 **Step 30. 购物车接口**。

### 同日继续推进记录（八）

已继续完成：

* **Step 30. 购物车接口**
* **Step 31. 接通商品页加购与购物车页**

新增与修改：

* `backend/app/api/v1/cart.py`
* `backend/app/api/v1/router.py`
* `backend/app/schemas/cart.py`
* `backend/app/schemas/__init__.py`
* `backend/tests/api/test_cart_api.py`
* `front/js/auth.js`
* `front/js/cart.js`
* `front/js/product.js`
* `front/cart.html`
* `tests/e2e/test_cart_flow.py`
* `memory-bank/progress.md`
* `memory-bank/architecture.md`

第 30 步验证：

* `./.venv/bin/python -m pytest backend/tests/api/test_cart_api.py -q`

第 31 步验证：

* `./.venv/bin/python -m pytest tests/e2e/test_cart_flow.py -q`
* `! rg -n "shiyige_cart|localStorage" front/product.html front/cart.html front/js/cart.js`

结果：

* `/api/v1/cart`、`/api/v1/cart/items`、`/api/v1/cart/items/{id}` 已接通，覆盖购物车查询、加购、改数量和删除。
* 购物车接口已经处理商品不存在、SKU 不存在、数量非法、商品下架和库存不足等场景。
* 商品详情页加购和购物车页展示/改数量/删除都已切到真实购物车 API，不再依赖 `localStorage`。
* 第 30 步验证结果为 `3 passed`，第 31 步浏览器回归结果为 `1 passed`。

交接提醒：

* 当前 `front/js/cart.js` 已经不再保存浏览器本地购物车，而是负责商品卡片快捷加购、购物车页渲染和购物车角标更新。
* `front/js/product.js` 的主加购表单现在依赖已登录用户和 `/api/v1/cart/items`；未登录用户会被引导到登录页。
* 结算页还没有切到真实购物车，这会在 Step 36 再统一收口；当前先保证商品页加购与购物车页闭环可用。

下一步起点：

* 继续执行 **Step 32. 建立订单与支付记录表**。

### 同日继续推进记录（九）

已继续完成：

* **Step 32. 建立订单与支付记录表**

新增与修改：

* `backend/app/models/order.py`
* `backend/app/models/user.py`
* `backend/app/models/product.py`
* `backend/app/models/__init__.py`
* `backend/alembic/versions/20260414_05_order_domain.py`
* `backend/tests/models/test_order_models.py`
* `memory-bank/progress.md`
* `memory-bank/architecture.md`

第 32 步验证：

* `./.venv/bin/alembic -c backend/alembic.ini upgrade head`
* `./.venv/bin/python -m pytest backend/tests/models/test_order_models.py -q`

结果：

* `orders`、`order_item`、`payment_record` 三张订单域表已经落地，并完成 Alembic 迁移。
* 订单模型已包含订单号、状态、金额字段、收货地址快照、幂等键和支付记录关系，能够支撑后续下单与支付接口。
* 第 32 步模型测试结果为 `2 passed`。

交接提醒：

* 订单表当前已经预留 `idempotency_key`，这是为了 Step 33 的下单幂等控制直接复用，不要再重复加字段。
* `order_item` 当前会冗余保存 `product_name`、`sku_name`、`unit_price` 等快照字段，后续不要只依赖商品表实时数据，否则订单历史会被商品修改污染。

下一步起点：

* 继续执行 **Step 33. 创建订单接口**。

### 同日继续推进记录（十）

已继续完成：

* **Step 33. 创建订单接口**

新增与修改：

* `backend/app/api/v1/orders.py`
* `backend/app/api/v1/router.py`
* `backend/app/schemas/order.py`
* `backend/app/schemas/__init__.py`
* `backend/tests/api/test_order_create.py`
* `backend/tests/api/test_order_idempotency.py`
* `memory-bank/progress.md`
* `memory-bank/architecture.md`

第 33 步验证：

* `./.venv/bin/python -m pytest backend/tests/api/test_order_create.py -q`
* `./.venv/bin/python -m pytest backend/tests/api/test_order_idempotency.py -q`

结果：

* `POST /api/v1/orders` 已接通，并基于当前用户的真实购物车和地址生成订单。
* 下单接口已经实现地址校验、金额计算、订单明细写入，并在成功创建后清空购物车项。
* 同一 `idempotency_key` 重复提交时，会直接返回已有订单，避免重复落单。
* 第 33 步验证结果为：下单创建测试 `2 passed`，幂等测试 `1 passed`。

交接提醒：

* 当前下单金额计算规则还是首版固定逻辑：`goods_amount + shipping_amount(10)`；会员折扣和促销折扣还没有并入订单创建。
* 下单接口当前直接把地址字段快照写进订单，不再依赖地址表后续变化，这个约定后续不要回退。
* 下单成功后购物车明细会被清空，因此后续支付/取消/查询接口应围绕订单表而不是购物车表继续推进。

下一步起点：

* 继续执行 **Step 34. 支付、取消、查询接口**。

### 同日继续推进记录（十一）

已继续完成：

* **Step 34. 支付、取消、查询接口**

新增与修改：

* `backend/app/api/v1/cart.py`
* `backend/app/api/v1/orders.py`
* `backend/tests/api/test_order_pay.py`
* `backend/tests/api/test_order_cancel.py`
* `backend/tests/api/test_order_query.py`
* `memory-bank/progress.md`
* `memory-bank/architecture.md`

第 34 步验证：

* `./.venv/bin/python -m pytest backend/tests/api/test_order_pay.py -q`
* `./.venv/bin/python -m pytest backend/tests/api/test_order_cancel.py -q`
* `./.venv/bin/python -m pytest backend/tests/api/test_order_query.py -q`

结果：

* `POST /api/v1/orders/{id}/pay` 已接通，支付时会再次校验 SKU 与库存，成功后扣减库存、更新订单状态，并写入一条 `payment_record`。
* `POST /api/v1/orders/{id}/cancel` 已接通，仅允许当前用户取消待支付订单。
* `GET /api/v1/orders` 与 `GET /api/v1/orders/{id}` 已接通，当前用户可以查询自己的订单列表、订单详情和支付记录。
* 为解决同一 SQLAlchemy 会话里关系集合陈旧的问题，`backend/app/api/v1/cart.py` 与 `backend/app/api/v1/orders.py` 在提交后增加了 `db.expire_all()`，避免支付后 `payment_records` 或再次加购后的 `cart.items` 读取到旧状态。
* 第 34 步验证结果为：支付测试 `2 passed`，取消测试 `2 passed`，查询测试 `2 passed`。

交接提醒：

* 当前订单状态最小闭环已经形成：`PENDING_PAYMENT -> PAID` 或 `PENDING_PAYMENT -> CANCELLED`。
* 支付仍是“站内模拟支付”语义，没有接第三方支付；后续前端结算页应直接调用现有订单创建和支付接口，不要再保留本地订单生成逻辑。
* 订单查询接口已经按创建时间倒序返回，订单页可以直接基于该结构渲染列表与详情。

下一步起点：

* 继续执行 **Step 35. 升级订单页**。

### 同日继续推进记录（十二）

已继续完成：

* **Step 35. 升级订单页**

新增与修改：

* `front/orders.html`
* `front/js/orders-page.js`
* `front/css/style.css`
* `tests/e2e/test_orders_page.py`
* `memory-bank/progress.md`
* `memory-bank/architecture.md`

第 35 步验证：

* `./.venv/bin/python -m pytest tests/e2e/test_orders_page.py -q`

结果：

* `front/orders.html` 已从占位页升级为真实订单页，能展示订单统计、订单列表、订单详情、收货信息、金额汇总和支付记录。
* 订单页现在会调用 `/api/v1/orders` 和 `/api/v1/orders/{id}` 加载真实数据，并在待支付订单上直接触发 `/api/v1/orders/{id}/pay` 与 `/api/v1/orders/{id}/cancel`。
* 新增的页面级回归覆盖了两条场景：新用户空订单态，以及已有待支付订单时的真实支付流程。
* 第 35 步验证结果为 `2 passed`。

交接提醒：

* 订单页已经不再是死链占位页；后续结算页完成后，用户可以从购物车/结算直接进入这里查看最新订单。
* 订单页当前把支付方式固定为站内模拟的 `balance`，这是为了复用当前后端支付接口约定；真正的第三方支付不在首轮范围。
* 当前订单页已经消费真实订单接口，因此后续不要重新引入本地订单数组或 `localStorage` 订单态。

下一步起点：

* 继续执行 **Step 36. 接通结算页**。

### 同日继续推进记录（十三）

已继续完成：

* **Step 36. 接通结算页**

新增与修改：

* `front/checkout.html`
* `front/js/checkout.js`
* `front/css/style.css`
* `tests/e2e/test_checkout_flow.py`
* `memory-bank/progress.md`
* `memory-bank/architecture.md`

第 36 步验证：

* `./.venv/bin/python -m pytest tests/e2e/test_checkout_flow.py -q`
* `rg -n "shiyige_orders|shiyige_cart|shiyige_membership|localStorage" front/checkout.html front/js/checkout.js`

结果：

* `front/checkout.html` 与 `front/js/checkout.js` 已切到真实业务流：结算页会读取真实购物车、读取真实地址、创建真实订单，并继续调用真实支付接口完成站内模拟支付。
* 旧的本地订单、购物车、会员折扣与余额逻辑已从结算页移除，不再依赖 `localStorage`。
* 新增的页面级回归覆盖了从购物车进入结算、选择真实地址、提交订单并支付、校验订单状态与购物车清空的完整流程。
* 第 36 步验证结果为：结算页浏览器回归 `1 passed`，禁用词扫描无命中。

交接提醒：

* 当前结算页只消费“已保存地址”，还不支持在结算页内新建地址；如果用户没有地址，会被提示先去个人中心补充。
* 结算页支付方式仍然是首轮约定的站内模拟支付，默认走 `/api/v1/orders/{id}/pay`，并把当前选中的支付方式字符串写进 `payment_record`。
* 当前结算金额与后端保持一致：真实购物车金额加固定运费 `10`；会员折扣、积分与促销还未并入订单结算。

下一步起点：

* 继续执行 **Step 37. 核心行为日志**。

### 同日继续推进记录（十四）

已继续完成：

* **Step 37. 核心行为日志**

新增与修改：

* `backend/app/services/__init__.py`
* `backend/app/services/behavior.py`
* `backend/app/api/v1/products.py`
* `backend/app/api/v1/search.py`
* `backend/app/api/v1/cart.py`
* `backend/app/api/v1/orders.py`
* `backend/tests/api/test_behavior_logging.py`
* `backend/tests/integration/test_behavior_events.py`
* `memory-bank/progress.md`
* `memory-bank/architecture.md`

第 37 步验证：

* `./.venv/bin/python -m pytest backend/tests/api/test_behavior_logging.py -q`
* `./.venv/bin/python -m pytest backend/tests/integration/test_behavior_events.py -q`

结果：

* 已建立统一行为日志服务，当前会在商品详情浏览、关键词搜索、加购、下单、支付成功五个动作上写入 `user_behavior_log`。
* 日志记录现在包含 `behavior_type`、目标对象类型与 ID，以及后续画像构建可复用的扩展字段，如搜索词、SKU、订单号、支付方式等。
* API 级测试已覆盖“浏览/搜索”和“加购/下单/支付”两个写入面；集成测试进一步校验了完整用户旅程事件顺序。
* 第 37 步验证结果为：API 行为日志测试 `2 passed`，行为事件集成测试 `1 passed`。

交接提醒：

* 搜索和商品详情接口当前只在“带有效 access token 的请求”上写行为日志；匿名浏览不会入库，这与后续用户画像只服务已登录用户的方向一致。
* 购物车加购、下单和支付日志与业务事务一起提交，因此后续不要把日志写入挪到事务提交之后，否则容易出现业务成功但日志丢失。
* 当前 `behavior_type` 已固定为 `view_product`、`search`、`add_to_cart`、`create_order`、`pay_order`，后续画像与推荐阶段应直接复用，不要再命名出第二套事件词表。

下一步起点：

* 继续执行 **Step 38. 向量模型适配层**。

### 同日继续推进记录（十五）

已继续完成：

* **Step 38. 向量模型适配层**

新增与修改：

* `backend/app/services/embedding.py`
* `backend/app/core/config.py`
* `backend/tests/unit/test_embedding_provider.py`
* `memory-bank/progress.md`
* `memory-bank/architecture.md`

第 38 步验证：

* `./.venv/bin/python -m pytest backend/tests/unit/test_embedding_provider.py -q`

结果：

* 已建立统一 embedding provider 抽象，当前提供离线可跑的 `local_hash` provider，以及可选的 `sentence_transformer` 本地模型包装器。
* 应用配置现在已经具备向量维度、模型名称、模型来源说明、revision、device、normalize 等元信息入口，后续生成任务与搜索服务可直接复用。
* 单元测试已经覆盖 deterministic provider 行为、模型包装器调用约定、配置到 descriptor 的映射，以及非法 provider 的错误处理。
* 第 38 步验证结果为 `4 passed`。

交接提醒：

* 当前默认 provider 是 `local_hash`，这是为了保证离线开发与测试稳定；后续如果要切到真实中文本地模型，可直接把 `EMBEDDING_PROVIDER` 切到 `sentence_transformer` 并补充模型依赖。
* `EmbeddingModelDescriptor` 已经是后续向量表、重建任务和推荐接口的统一模型元信息对象，不要再在其他模块各自拼装一套模型配置字典。
* `SentenceTransformerEmbeddingProvider` 当前按懒加载方式导入第三方依赖，这样不会影响未安装模型环境下的基础测试。

下一步起点：

* 继续执行 **Step 39. 建立向量表与画像表**。

### 同日继续推进记录（十六）

已继续完成：

* **Step 39. 建立向量表与画像表**

新增与修改：

* `backend/app/models/recommendation.py`
* `backend/app/models/product.py`
* `backend/app/models/user.py`
* `backend/app/models/__init__.py`
* `backend/app/services/embedding_text.py`
* `backend/alembic/versions/20260414_06_embedding_domain.py`
* `backend/tests/services/test_embedding_text_builder.py`
* `memory-bank/progress.md`
* `memory-bank/architecture.md`

第 39 步验证：

* `./.venv/bin/alembic -c backend/alembic.ini upgrade head`
* `./.venv/bin/python -m pytest backend/tests/services/test_embedding_text_builder.py -q`

结果：

* 推荐域表已经落地：`product_embedding` 用于保存商品向量文本、向量值与内容哈希，`user_interest_profile` 用于保存用户兴趣画像文本、向量值与行为统计信息。
* 商品模型和用户模型现在已分别挂接到 `embedding` 与 `interest_profile` 关系，后续索引任务和推荐接口可直接沿关系访问。
* 同时补齐了 `embedding_text` builder 与哈希工具，为下一步固定文本拼装规则和后续增量重建提供基础。
* 第 39 步验证结果为：Alembic 迁移成功升级到 `20260414_06`，builder 测试 `2 passed`。

交接提醒：

* 当前向量字段使用 JSON 持久化，优先保证本地 SQLite 开发与测试可用；后续如果切到 PostgreSQL/pgvector，可在不改上层接口的前提下替换底层存储实现。
* `content_hash` 已经进入表结构，这意味着后续增量重建不应只看更新时间，而应优先比较向量文本哈希。
* 由于实施计划把 Step 39 的验证直接绑定到 `embedding_text_builder`，第 40 步会在现有 builder 基础上继续固化规则，而不是另起一套文本生成逻辑。

下一步起点：

* 继续执行 **Step 40. 商品 embedding_text 拼装**。

### 同日继续推进记录（十七）

已继续完成：

* **Step 40. 商品 embedding_text 拼装**

新增与修改：

* `memory-bank/progress.md`
* `memory-bank/architecture.md`

第 40 步验证：

* `./.venv/bin/python -m pytest backend/tests/services/test_embedding_text_builder.py -q`

结果：

* 商品 `embedding_text` 规则已固定为：商品名称、类目、标签、描述、文化摘要、风格词、场景词、工艺词，且字段顺序稳定、空值自动跳过。
* 现有 builder 已保证同一商品内容可以稳定生成同一段向量文本和同一 `content_hash`，为后续增量重建提供可靠依据。
* 第 40 步验证结果为 `2 passed`。

交接提醒：

* `embedding_text` 现在已经是推荐域的核心合同，后续不要把商品长文、后台备注或无关展示字段混入向量文本，否则会破坏文本稳定性。
* 标签当前使用排序后的稳定输出，后续如果标签来源顺序变化，不需要再额外做补丁，builder 已经吸收这个波动。
* 因实施计划把 Step 39 与 Step 40 都绑定到了同一组 builder 测试，本步主要是确认规则冻结，而不是引入第二套 builder 实现。

下一步起点：

* 继续执行 **Step 41. 建立异步向量生成任务**。

### 同日继续推进记录（十八）

已继续完成：

* **Step 41. 建立异步向量生成任务**

新增与修改：

* `backend/app/tasks/embedding_tasks.py`
* `backend/app/services/embedding_text.py`
* `backend/scripts/reindex_embeddings.py`
* `backend/tests/tasks/test_embedding_tasks.py`
* `backend/tests/integration/test_reindex_command.py`
* `memory-bank/progress.md`
* `memory-bank/architecture.md`

第 41 步验证：

* `./.venv/bin/python -m pytest backend/tests/tasks/test_embedding_tasks.py -q`
* `./.venv/bin/python -m pytest backend/tests/integration/test_reindex_command.py -q`

结果：

* 已建立商品向量生成任务，支持单商品 upsert、增量重建和全量重建。
* 已新增 `backend/scripts/reindex_embeddings.py` 全量重建命令入口，后续后台任务页或运维脚本可直接复用。
* 任务测试已经覆盖首次全量建索引、无变更跳过、内容变更后单商品增量更新；命令级测试覆盖全量重建脚本的真实执行结果。
* 第 41 步验证结果为：任务测试 `2 passed`，重建命令集成测试 `1 passed`。

交接提醒：

* 当前“异步任务”还是以可复用任务函数和脚本命令为主，没有引入 Celery/RQ 运行时；这符合当前比赛工期，后续若接任务队列，应直接包裹现有任务函数。
* 增量重建逻辑当前基于 `content_hash` 与 `model_name` 判断是否需要重新生成向量，不应再退回到“每次全量都重算”的粗暴方式。
* 重建任务当前只覆盖商品向量，用户画像重建会在后续推荐阶段结合行为日志继续补齐。

下一步起点：

* 继续执行 **Step 42. 语义搜索接口**。

### 同日继续推进记录（十九）

已继续完成：

* **Step 42. 语义搜索接口**

新增与修改：

* `backend/app/services/vector_search.py`
* `backend/app/schemas/search.py`
* `backend/app/schemas/__init__.py`
* `backend/app/api/v1/search.py`
* `backend/tests/api/test_search_semantic.py`
* `backend/tests/integration/test_search_ranking.py`
* `memory-bank/progress.md`
* `memory-bank/architecture.md`

第 42 步验证：

* `./.venv/bin/python -m pytest backend/tests/api/test_search_semantic.py -q`
* `./.venv/bin/python -m pytest backend/tests/integration/test_search_ranking.py -q`

结果：

* `POST /api/v1/search/semantic` 已接通，支持自然语言查询、类目与价格过滤、向量相似度召回，并为每个命中商品返回一句推荐理由。
* 语义搜索底层已经建立成“向量相似度 + 规则特征加权”的混合排序，这样在当前离线 provider 条件下仍能稳定给出可解释结果。
* API 测试已覆盖语义搜索接口的返回结构、排序和命中理由；集成测试已覆盖排序质量与过滤条件。
* 第 42 步验证结果为：语义搜索 API 测试 `1 passed`，语义排序集成测试 `1 passed`。

交接提醒：

* 当前语义搜索会在查询前确保商品向量索引存在，因此在小数据集下可以直接工作；后续如果数据量继续增长，应把“确保索引存在”挪到后台任务或定时任务层。
* 当前推荐理由优先基于类目、标签、风格、场景、工艺等显式命中特征生成，这是为了保证答辩可解释性。
* 当前 semantic search 也会复用 `search` 行为日志入口，但 `ext_json.mode` 会标记为 `semantic`，后续用户画像可以据此区分关键词搜索与语义搜索。

下一步起点：

* 继续执行 **Step 43. 商品相似推荐接口**。

### 同日继续推进记录（二十）

已继续完成：

* **Step 43. 商品相似推荐接口**

新增与修改：

* `backend/app/services/vector_search.py`
* `backend/app/api/v1/products.py`
* `backend/tests/api/test_related_products.py`
* `memory-bank/progress.md`
* `memory-bank/architecture.md`

第 43 步验证：

* `./.venv/bin/python -m pytest backend/tests/api/test_related_products.py -q`

结果：

* `GET /api/v1/products/{id}/related` 已接通，基于商品向量与显式特征相似度返回相关推荐。
* 当前相关推荐已经排除商品自身和下架商品，并为每个命中商品返回一句“相近原因”。
* 第 43 步验证结果为 `1 passed`。

交接提醒：

* 当前相关推荐服务会在调用前确保商品向量索引存在，并在同一会话里执行 `db.expire_all()`，避免读到旧的 embedding 关系缓存。
* 相似推荐理由优先复用类目、风格、场景、工艺和标签的交集，不建议后续改成只显示黑盒分数。

下一步起点：

* 继续执行 **Step 44. 用户兴趣画像与猜你喜欢**。

### 同日继续推进记录（二十一）

已继续完成：

* **Step 44. 用户兴趣画像与猜你喜欢**

新增与修改：

* `backend/app/services/recommendations.py`
* `backend/app/api/v1/products.py`
* `backend/app/api/v1/orders.py`
* `backend/tests/integration/test_user_interest_profile.py`
* `backend/tests/api/test_recommendations.py`
* `memory-bank/progress.md`
* `memory-bank/architecture.md`

第 44 步验证：

* `./.venv/bin/python -m pytest backend/tests/integration/test_user_interest_profile.py -q`
* `./.venv/bin/python -m pytest backend/tests/api/test_recommendations.py -q`

结果：

* 已建立用户兴趣画像服务，会基于浏览、搜索、加购、下单、支付行为和固定权重生成 `user_interest_profile`。
* `GET /api/v1/products/recommendations` 已接通，能够根据当前用户画像返回“猜你喜欢”商品及简洁推荐理由。
* 集成测试已证明不同用户的画像文本与 top terms 会发生分化；API 测试已证明不同用户会得到不同的推荐结果集合。
* 第 44 步验证结果为：画像集成测试 `1 passed`，推荐 API 测试 `1 passed`。

交接提醒：

* 当前画像权重采用固定策略：浏览 `1`、搜索 `2`、加购 `3`、下单 `5`、支付 `5`；后续如果要微调，优先改服务层权重表，不要散改多处业务代码。
* 推荐接口当前会默认排除用户已经直接交互过的商品，这样首页推荐更像“继续探索”而不是“重复看过的商品”。
* 为了让画像能利用订单行为，订单日志的 `ext_json` 现在已经补充 `product_ids`，后续不要去掉这个字段。

下一步起点：

* 继续执行 **Step 45. 接通前端推荐与语义搜索入口**。

### 同日继续推进记录（二十二）

已继续完成：

* **Step 45. 接通前端推荐与语义搜索入口**

新增与修改：

* `front/index.html`
* `front/product.html`
* `front/category.html`
* `front/js/home-page.js`
* `front/js/product.js`
* `front/js/category-page.js`
* `tests/e2e/test_recommendation_ui.py`
* `memory-bank/progress.md`
* `memory-bank/architecture.md`

第 45 步验证：

* `./.venv/bin/python -m pytest tests/e2e/test_recommendation_ui.py -q`
* `rg -n "/api/v1/search|/api/v1/products/.*/related|/api/v1/products/recommendations" front admin`

结果：

* 首页“猜你喜欢”已接入 `GET /api/v1/products/recommendations`，登录用户可看到个性化推荐和推荐理由；未登录时回退到最新商品展示。
* 商品详情页“相关推荐”已接入 `GET /api/v1/products/{id}/related`，每张卡片都会显示一句相似原因。
* 分类页已新增显式的语义搜索入口，支持自然语言搜索并展示语义命中特征说明。
* 新增端到端测试覆盖两个账号首页推荐差异、商品详情相关推荐展示、分类页语义搜索展示三条答辩路径。
* 第 45 步验证结果为：`1 passed`，`rg` 校验通过。

交接提醒：

* 分类页语义搜索接口的 `limit` 必须保持在后端 schema 允许范围内，当前前端固定为 `20`，不要再改回超限值。
* 分类页的筛选与搜索入口存在并发交互风险，当前通过“请求 token”避免旧请求覆盖新结果，后续改造时不要删除这层保护。
* 搜索方式切换时必须先保留用户当前输入，再同步控件状态，否则会把刚输入的自然语言查询清空。

下一步起点：

* 继续执行 **Step 46. 会员与积分表**。

### 同日继续推进记录（二十三）

已继续完成：

* **Step 46. 会员与积分表**

新增与修改：

* `backend/app/models/membership.py`
* `backend/app/models/user.py`
* `backend/app/models/__init__.py`
* `backend/alembic/env.py`
* `backend/alembic/versions/20260415_07_membership_domain.py`
* `backend/scripts/seed_base_data.py`
* `backend/tests/integration/test_member_seed.py`
* `memory-bank/progress.md`
* `memory-bank/architecture.md`

第 46 步验证：

* `./.venv/bin/alembic -c backend/alembic.ini upgrade head`
* `./.venv/bin/python -m pytest backend/tests/integration/test_member_seed.py -q`

结果：

* 已新增 `member_level`、`point_account`、`point_log` 三张会员域基础表，并完成 Alembic 迁移。
* 已把会员等级默认种子接入 `seed_base_data`，当前默认会写入青铜、白银、黄金、铂金四档等级。
* 已建立用户到积分账户的关系，以及积分账户到等级、积分日志的关系，为后续积分累计和等级更新预留稳定数据合同。
* 第 46 步验证结果为：迁移成功，会员种子集成测试 `1 passed`。

交接提醒：

* `seed_base_data` 现在不再只看商品种子，它会先确保会员等级存在；后续如果扩展基础种子，不要再把整个函数提前短路掉。
* 语义上当前“当前等级”落在 `point_account.member_level_id`，后续积分变更后要同步更新该字段，不要只改积分余额。
* `point_log.balance_after` 已经预留给积分流水展示，后续写积分日志时必须填入变更后的余额，避免会员中心只能展示增减值不能展示余额快照。

下一步起点：

* 继续执行 **Step 47. 会员资料与积分接口**。

### 同日继续推进记录（二十四）

已继续完成：

* **Step 47. 会员资料与积分接口**

新增与修改：

* `backend/app/services/member.py`
* `backend/app/api/v1/member.py`
* `backend/app/api/v1/router.py`
* `backend/app/api/v1/orders.py`
* `backend/tests/api/test_member_profile.py`
* `backend/tests/api/test_point_accrual.py`
* `memory-bank/progress.md`
* `memory-bank/architecture.md`

第 47 步验证：

* `./.venv/bin/python -m pytest backend/tests/api/test_member_profile.py -q`
* `./.venv/bin/python -m pytest backend/tests/api/test_point_accrual.py -q`

结果：

* 已接通 `GET /api/v1/member/profile`、`GET /api/v1/member/points`、`GET /api/v1/member/benefits` 三个会员接口。
* 已在订单支付成功后自动创建积分账户、累加积分、写入积分流水，并根据积分余额同步会员等级。
* 会员资料接口会返回当前等级、下一等级、进度百分比和累计消费；积分接口会返回汇总与积分流水；权益接口会返回全部等级及当前等级权益。
* 第 47 步验证结果为：会员资料测试 `2 passed`，积分累计测试 `1 passed`。

交接提醒：

* 当前积分累计规则是 `floor(payable_amount * 当前等级 points_rate)`，后续如果要调整倍率或改成只按商品金额累计，优先改 `backend/app/services/member.py`，不要散改订单和接口层。
* 当前等级升级依据是 `points_balance`，因为暂时没有积分抵扣场景；如果后续引入积分消费，再评估是否切到 `lifetime_points` 作为升级基准。
* `GET /api/v1/member/*` 当前会在用户首次访问时懒创建积分账户，因此这些接口是“读接口带初始化副作用”，后续如果要挪到注册流程，记得同步更新测试假设。

下一步起点：

* 继续执行 **Step 48. 接通会员中心**。

### 同日继续推进记录（二十五）

已继续完成：

* **Step 48. 接通会员中心**

新增与修改：

* `front/membership.html`
* `front/js/membership.js`
* `tests/e2e/test_membership_page.py`
* `memory-bank/progress.md`
* `memory-bank/architecture.md`

第 48 步验证：

* `./.venv/bin/python -m pytest tests/e2e/test_membership_page.py -q`
* `rg -n "shiyige_membership|localStorage" front/membership.html front/js/membership.js`
  结果为无匹配，符合 `! rg ...` 预期。

结果：

* 会员中心已切到真实会员接口，页面会读取真实等级、真实积分、真实积分流水，不再依赖本地存储。
* 会员中心当前会展示当前等级、累计积分、累计消费、下一等级进度，以及当前等级对应的折扣和积分倍率。
* 会员充值区已明确降级为“后续实现”提示，不再保留伪造充值和本地积分写入逻辑。
* 商品详情页会员价继续沿用真实商品详情接口字段，端到端验证已证明页面会显示真实会员价。
* 第 48 步验证结果为：会员中心 e2e `1 passed`，`localStorage` 残留校验通过。

交接提醒：

* `front/js/membership.js` 当前只负责展示真实会员数据，不再暴露 `window.membership` 这类本地状态对象；后续如果扩展充值功能，应该新接 API，不要回退到本地缓存模型。
* 会员中心“在线充值”区域目前是刻意禁用的占位提示，原因是后端尚未提供真实充值接口；在对应后端能力落地前不要恢复提交按钮。
* 会员页现在依赖 `/member/profile`、`/member/points`、`/member/benefits` 三个接口并行加载，后续如果优化性能，可以考虑服务端聚合，但不要牺牲当前接口边界清晰度。

下一步起点：

* 继续执行 **Step 49. 评价表与评价接口**。

### 同日继续推进记录（二十六）

已继续完成：

* **Step 49. 评价表与评价接口**

新增与修改：

* `backend/app/models/review.py`
* `backend/app/models/product.py`
* `backend/app/models/user.py`
* `backend/app/models/__init__.py`
* `backend/app/schemas/review.py`
* `backend/app/api/v1/reviews.py`
* `backend/app/api/v1/router.py`
* `backend/alembic/env.py`
* `backend/alembic/versions/20260415_08_review_domain.py`
* `backend/tests/models/test_review_models.py`
* `backend/tests/api/test_reviews_create.py`
* `backend/tests/api/test_reviews_list.py`
* `backend/tests/api/test_reviews_permissions.py`
* `memory-bank/progress.md`
* `memory-bank/architecture.md`

第 49 步验证：

* `./.venv/bin/python -m pytest backend/tests/models/test_review_models.py -q`
* `./.venv/bin/python -m pytest backend/tests/api/test_reviews_create.py -q`
* `./.venv/bin/python -m pytest backend/tests/api/test_reviews_list.py -q`
* `./.venv/bin/python -m pytest backend/tests/api/test_reviews_permissions.py -q`

结果：

* 已新增 `review`、`review_image` 两张评价域表，并补齐商品、用户到评价的关系。
* 已接通商品评价创建、评价列表、评价统计三个接口，路径统一挂在 `/api/v1/products/{id}/reviews` 族上。
* 后端已强制执行“必须已支付购买过该商品才能评价”，并且限制同一用户对同一商品只能评价一次。
* 评价列表会返回匿名展示名、图片 URL 列表和创建时间；统计接口会返回平均分、总条数和星级分布。
* 第 49 步验证结果为：模型测试 `2 passed`，创建测试 `1 passed`，列表/统计测试 `1 passed`，权限测试 `2 passed`。

交接提醒：

* 当前评价权限依赖 `orders.status == "PAID"` 和 `order_item.product_id` 命中，不要把“下单未支付”也算作可评价。
* 当前唯一性约束是 `(user_id, product_id)`，也就是一个用户对一个商品只能留一条评价；如果后续要支持“多次购买多次评价”，需要同时调整数据库约束和权限测试。
* 评价图片当前只保存 URL 字符串，真正的上传与文件限制在后续媒体上传阶段处理，不要在这一阶段把图片二进制逻辑混进评价接口。

下一步起点：

* 继续执行 **Step 50. 接通商品评价区域**。

### 同日继续推进记录（二十七）

已继续完成：

* **Step 50. 接通商品评价区域**

新增与修改：

* `front/product.html`
* `front/js/product.js`
* `tests/e2e/test_product_reviews.py`
* `memory-bank/progress.md`
* `memory-bank/architecture.md`

第 50 步验证：

* `./.venv/bin/python -m pytest tests/e2e/test_product_reviews.py -q`

结果：

* 商品详情页评价区已从静态示例切换为真实接口，页面会读取 `/api/v1/products/{id}/reviews/stats` 和 `/api/v1/products/{id}/reviews` 的真实数据。
* 评价摘要现在会展示真实平均分、真实总评价数和真实星级分布，不再保留硬编码示例统计。
* 评价列表现在按接口返回的时间倒序渲染，支持匿名展示名、真实评价图片预览和“查看更多评价”真实分页加载。
* 第 50 步验证结果为：商品评价页 e2e `1 passed`。

交接提醒：

* `front/js/product.js` 当前把评价分页大小固定为 `2`，目的是让“查看更多评价”在演示和自动化测试里稳定可见；如果后续要调整页大小，需要同步评估 UI 节奏和 `tests/e2e/test_product_reviews.py` 的断言。
* 商品详情页评价区当前只接通了“展示链路”，并没有在前端开放评价提交入口；如果后续补评价表单，应直接走现有后端评价接口，不要再引入本地假数据。
* 评价图片区当前直接消费后端返回的 URL 字段并沿用已有全屏预览逻辑，因此后续如果接入真实上传服务，优先保证 URL 稳定，而不是改动商品页的展示协议。

下一步起点：

* 继续执行 **Step 51. 后台用户与鉴权**。

### 同日继续推进记录（二十八）

已继续完成：

* **Step 51. 后台用户与鉴权**

新增与修改：

* `backend/app/models/admin.py`
* `backend/app/models/__init__.py`
* `backend/app/api/v1/admin_auth.py`
* `backend/app/api/v1/router.py`
* `backend/alembic/env.py`
* `backend/alembic/versions/20260415_09_admin_auth.py`
* `backend/scripts/seed_base_data.py`
* `backend/tests/api/conftest.py`
* `backend/tests/api/test_admin_auth.py`
* `memory-bank/progress.md`
* `memory-bank/architecture.md`

第 51 步验证：

* `./.venv/bin/alembic -c backend/alembic.ini upgrade head`
* `./.venv/bin/python -m pytest backend/tests/api/test_admin_auth.py -q`

结果：

* 已新增 `admin_user` 和 `operation_log` 两张后台域表，后台账号与前台普通用户账号正式分离。
* 已接通 `/api/v1/admin/auth/login`、`/api/v1/admin/auth/me`、`/api/v1/admin/auth/logout` 三个后台鉴权接口。
* 后台登录成功后会更新最近登录时间，并写入一条 `operation_log` 登录记录，便于后续后台操作审计继续扩展。
* 基础数据种子现在会确保存在一个默认后台管理员，供后续后台页面联调使用。
* 第 51 步验证结果为：迁移升级通过，后台鉴权测试 `4 passed`。

交接提醒：

* 后台 access token 的 `sub` 当前固定采用 `admin:{id}` 前缀，这和前台普通用户 token 的纯数字 `sub` 是刻意分开的；后续解析后台 token 时不要直接复用前台 `get_user_from_token`。
* 后台角色当前只放开 `super_admin` 和 `ops_admin` 两类，`operation_log` 目前仅记录登录成功事件，后续后台 CRUD 和重建任务应继续沿用这张表，不要新起一套审计模型。
* `backend/scripts/seed_base_data.py` 当前会确保默认后台管理员存在，默认账号是 `admin@shiyige-demo.com`，默认密码是 `admin123456`；后续若修改种子凭据，记得同步更新后台 e2e 测试和文档说明。
* 后台鉴权当前只返回 access token，没有单独实现后台 refresh cookie；后续如果后台页面需要长会话，再在这条独立后台链路上扩展，不要复用前台 refresh cookie 名称。

下一步起点：

* 继续执行 **Step 52. 后台核心接口**。

### 同日继续推进记录（二十九）

已继续完成：

* **Step 52. 后台核心接口**

新增与修改：

* `backend/app/schemas/admin.py`
* `backend/app/api/v1/admin_products.py`
* `backend/app/api/v1/admin_orders.py`
* `backend/app/api/v1/admin_dashboard.py`
* `backend/app/api/v1/admin_reindex.py`
* `backend/app/api/v1/router.py`
* `backend/tests/api/test_admin_products.py`
* `backend/tests/api/test_admin_orders.py`
* `backend/tests/api/test_admin_reindex.py`
* `memory-bank/progress.md`
* `memory-bank/architecture.md`

第 52 步验证：

* `./.venv/bin/python -m pytest backend/tests/api/test_admin_products.py -q`
* `./.venv/bin/python -m pytest backend/tests/api/test_admin_orders.py -q`
* `./.venv/bin/python -m pytest backend/tests/api/test_admin_reindex.py -q`

结果：

* 已接通后台商品管理接口，支持商品列表查询、按单默认 SKU 创建商品、更新商品基本信息、标签、媒体和库存。
* 已接通后台订单管理接口，支持订单列表、订单详情和后台仪表盘概览汇总。
* 已接通后台推荐重建触发接口，能够直接复用现有 embedding 任务重建商品向量索引。
* 后台商品创建、商品更新、重建任务触发都会写入 `operation_log`，审计链路开始复用第 51 步的数据底座。
* 第 52 步验证结果为：后台商品测试 `2 passed`，后台订单/概览测试 `1 passed`，后台重建测试 `1 passed`。

交接提醒：

* `backend/app/api/v1/admin_products.py` 当前明确采用“一个商品只维护一个默认 SKU”的后台管理模型，这是为了匹配首轮比赛范围；如果后续放开多 SKU 编辑器，不能只改前端页面，必须同步改后台请求结构和测试断言。
* 后台仪表盘汇总接口 `/api/v1/admin/dashboard/summary` 当前统计的是前台 `users` 表、`orders` 表和 `product` 表，不把 `admin_user` 算进用户总数，这一点在做后台首页文案时要说明清楚。
* 后台重建接口 `/api/v1/admin/reindex/products` 当前直接同步执行 embedding 重建任务，适合比赛演示但不适合重负载生产场景；如果后续改成异步队列，需要保留当前返回结构或同步调整页面和测试。

下一步起点：

* 继续执行 **Step 53. 后台最小页面集合**。

### 同日继续推进记录（三十）

已继续完成：

* **Step 53. 后台最小页面集合**

新增与修改：

* `admin/login.html`
* `admin/index.html`
* `admin/products.html`
* `admin/orders.html`
* `admin/reindex.html`
* `admin/css/admin.css`
* `admin/js/app.js`
* `tests/e2e/conftest.py`
* `tests/e2e/test_admin_basic.py`
* `backend/scripts/seed_base_data.py`
* `memory-bank/progress.md`
* `memory-bank/architecture.md`

第 53 步验证：

* `./.venv/bin/python -m pytest tests/e2e/test_admin_basic.py -q`
* `test -f admin/index.html`

结果：

* 已补齐 `admin/` 下五个最小后台页面：登录、仪表盘、商品管理、订单管理、推荐重建。
* 后台页面已经接通真实后台鉴权与管理接口，管理员可以通过真实后台登录后查看仪表盘、商品列表、订单列表，并触发真实商品向量重建。
* e2e 夹具现在会在测试服务里挂载 `/admin` 静态目录，因此后台页面也能和前台页面一样走同源真实接口联调。
* 默认后台管理员邮箱已修正为合法邮箱域名 `admin@shiyige-demo.com`，避免被 `EmailStr` 判为保留域名而导致登录请求 422。
* 第 53 步验证结果为：后台页面 e2e `1 passed`，`admin/index.html` 文件存在性校验通过。

交接提醒：

* `admin/js/app.js` 当前承担了后台会话、鉴权守卫、导航渲染和各页面数据加载的全部职责，属于“单文件最小后台前端壳”；后续如果后台页面继续扩张，可以按页面拆 JS，但不要在页面内重新复制鉴权逻辑。
* 后台页面当前用 `sessionStorage` 保存后台 access token，并通过 `/api/v1/admin/auth/me` 做受保护页面校验；因为后台还没有 refresh 机制，长时间停留后需要重新登录，这是当前有意保留的简化。
* `tests/e2e/conftest.py` 对 `/admin` 的静态挂载目前只存在于测试夹具中，真正的生产托管会在 Step 56 交给 Nginx；在那之前不要误以为 FastAPI 主应用已经负责正式托管后台静态资源。

下一步起点：

* 继续执行 **Step 54. 媒体上传**。

### 同日继续推进记录（三十一）

已继续完成：

* **Step 54. 媒体上传**

新增与修改：

* `backend/app/services/media.py`
* `backend/app/api/v1/admin_media.py`
* `backend/app/api/v1/media.py`
* `backend/app/api/v1/router.py`
* `backend/tests/api/test_media_upload.py`
* `backend/tests/api/test_upload_limits.py`
* `memory-bank/progress.md`
* `memory-bank/architecture.md`

第 54 步验证：

* `./.venv/bin/python -m pytest backend/tests/api/test_media_upload.py -q`
* `./.venv/bin/python -m pytest backend/tests/api/test_upload_limits.py -q`

结果：

* 已新增统一媒体存储服务，默认走 MinIO，并会在上传时自动确保商品图桶与评价图桶存在。
* 已接通后台商品图上传接口 `/api/v1/admin/media/products`，供管理员上传商品图片。
* 已接通前台评价图上传接口 `/api/v1/media/reviews`，供登录用户上传评价图片。
* 已补齐图片类型限制与文件大小限制，并通过接口测试验证“支持上传”和“限制拦截”两条链路。
* 第 54 步验证结果为：媒体上传测试 `2 passed`，上传限制测试 `2 passed`。

交接提醒：

* `backend/app/services/media.py` 现在是媒体上传的唯一入口，后续不要在接口层各自拼接对象名、桶名和公开 URL，避免上传协议散落。
* 当前上传接口只返回对象 URL 和元数据，不落数据库表；商品图和评价图的最终持久化关系仍然由商品编辑接口和评价创建接口自己保存 URL。
* Step 54 的测试通过依赖可覆盖的 `get_media_storage` 依赖，而不是强制连接真实 MinIO；后续继续补媒体能力时，优先保持这个可替换结构，避免测试直接绑死外部对象存储服务。

下一步起点：

* 继续执行 **Step 55. 缓存与安全加固**。

### 同日继续推进记录（三十二）

已继续完成：

* **Step 55. 缓存与安全加固**

新增与修改：

* `backend/app/services/cache.py`
* `backend/app/core/rate_limit.py`
* `backend/app/main.py`
* `backend/app/api/v1/products.py`
* `backend/app/api/v1/search.py`
* `backend/tests/integration/test_cache_behavior.py`
* `backend/tests/api/test_rate_limit.py`
* `backend/tests/api/test_security_guards.py`
* `memory-bank/progress.md`
* `memory-bank/architecture.md`

第 55 步验证：

* `./.venv/bin/python -m pytest backend/tests/integration/test_cache_behavior.py -q`
* `./.venv/bin/python -m pytest backend/tests/api/test_rate_limit.py -q`
* `./.venv/bin/python -m pytest backend/tests/api/test_security_guards.py -q`

结果：

* 已为商品详情、首页推荐、搜索建议三类高频读接口接入统一 JSON 缓存层。
* 已新增基础限流中间件，对前台登录、后台登录、评价图上传、后台商品图上传等敏感写接口做按路径和客户端标识的固定窗口限流。
* 已通过安全守卫测试锁定“前台 token 不得访问后台上传口”“伪造后台 subject 前缀无效”“空文件上传直接拒绝”等关键边界。
* 第 55 步验证结果为：缓存集成测试 `1 passed`，限流测试 `1 passed`，安全守卫测试 `3 passed`。

交接提醒：

* `backend/app/services/cache.py` 当前缓存的是已经过 JSON 编码兼容化的数据结构，缓存命中时不会再重新序列化数据库对象；后续如果改动响应结构，记得同步调整缓存内容，而不是只改查询逻辑。
* `backend/app/core/rate_limit.py` 目前使用应用进程内的固定窗口限流器，适合比赛版单实例部署；如果后续变成多实例或需要共享限流状态，应把这一层换成 Redis/网关侧实现。
* 商品详情接口即使命中缓存，仍会保留登录用户的浏览行为记录；这是刻意保留的推荐链路副作用，后续不要为了缓存命中率把行为日志一起裁掉。

下一步起点：

* 继续执行 **Step 56. Nginx 与完整编排**。

### 同日继续推进记录（三十三）

已继续完成：

* **Step 56. Nginx 与完整编排**

新增与修改：

* `docker-compose.yml`
* `nginx/default.conf`
* `backend/Dockerfile`
* `backend/.dockerignore`
* `backend/scripts/start_api.sh`
* `backend/alembic/versions/20260415_07_membership_domain.py`
* `backend/alembic/versions/20260415_08_review_domain.py`
* `backend/alembic/versions/20260415_09_admin_auth.py`
* `memory-bank/progress.md`
* `memory-bank/architecture.md`

第 56 步验证：

* `docker compose config --quiet`
* `docker compose up -d`
* `curl -f http://127.0.0.1/api/v1/health`
* `curl -f http://127.0.0.1`

结果：

* 已由 `nginx` 正式托管 `front/` 前台静态站点，并把 `/admin` 正式映射到 `admin/` 后台静态目录，不再只依赖 e2e 夹具中的临时静态挂载。
* 已由 `nginx` 把 `/api` 反向代理到 `api` 容器中的 FastAPI 服务，前台、后台和接口现在可以通过同一个 `http://127.0.0.1` 入口联动访问。
* `api` 容器启动时现在会自动执行 Alembic 迁移并执行基础种子，因此 Compose 启动完成后即具备默认管理员、会员等级、类目和商品数据。
* 在 Compose 首次落地时暴露出 SQLite 与 PostgreSQL 的迁移兼容性差异，已把会员、评价、后台管理员三份迁移中的布尔默认值从 `0/1` 修正为 `sa.false()/sa.true()`，避免 PostgreSQL 启动时卡死在迁移阶段。
* 第 56 步验证结果为：Compose 配置检查通过，容器可一键启动，`/api/v1/health` 返回 200，前台首页根路径返回 200。

交接提醒：

* `backend/scripts/start_api.sh` 当前是 Compose 下 API 启动的唯一入口，负责“迁移 -> 基础种子 -> Uvicorn”；后续如果补预热、演示数据初始化或后台任务进程，不要把这些动作再散回 `docker-compose.yml` 的长命令里。
* 当前 Compose 已切到 PostgreSQL 真实运行路径，因此后续新增迁移时不要再写 `Boolean DEFAULT 0/1` 这种只在 SQLite 宽松通过的写法，统一使用 `sa.false()` / `sa.true()`。
* `nginx/default.conf` 当前已额外代理 `/docs`、`/redoc` 与 `/openapi.json`，便于同一入口下调试 API 文档；如果后续改动文档路径，要一起维护这里的反代规则。
* Compose 启动目前只会灌入基础种子，不会自动创建“演示普通用户、演示订单、推荐行为数据”；这些属于 **Step 57** 的内容，不要误判为已经完成。

下一步起点：

* 继续执行 **Step 57. 演示数据与全链路回归**。

### 同日继续推进记录（三十四）

已继续完成：

* **Step 57. 演示数据与全链路回归**

新增与修改：

* `backend/scripts/seed_demo_data.py`
* `backend/scripts/start_api.sh`
* `backend/app/services/cache.py`
* `backend/app/api/v1/products.py`
* `backend/app/api/v1/search.py`
* `backend/app/api/v1/cart.py`
* `backend/app/api/v1/orders.py`
* `backend/tests/integration/test_seed_demo_data.py`
* `backend/tests/integration/test_cache_behavior.py`
* `tests/e2e/test_full_demo_flow.py`
* `memory-bank/progress.md`
* `memory-bank/architecture.md`

第 57 步验证：

* `./.venv/bin/python -m pytest backend/tests -q`
* `./.venv/bin/python -m pytest tests/e2e/test_full_demo_flow.py -q`

结果：

* 已新增独立的演示数据种子脚本 `backend/scripts/seed_demo_data.py`，可稳定创建演示普通用户、默认收货地址、已支付样例订单、待支付样例订单和推荐行为数据。
* Compose 下 API 启动现在会在基础种子之后继续执行演示数据种子，因此本地一键启动后的环境已经自带演示管理员、演示普通用户、演示商品、演示订单和推荐画像基础数据。
* 已新增 `backend/tests/integration/test_seed_demo_data.py`，锁定演示用户积分、会员等级、样例订单、行为日志和兴趣画像的幂等性。
* 已新增 `tests/e2e/test_full_demo_flow.py`，把“注册登录 -> 关键词搜索 -> 语义搜索 -> 浏览商品 -> 加购 -> 结算支付 -> 订单查询 -> 评价 -> 积分变化 -> 推荐变化”串成一条真实页面回归链。
* 第 57 步过程中暴露出“用户推荐缓存不会随行为变化自动刷新”的问题，已在浏览商品、关键词搜索、语义搜索、加购、创建订单、支付订单这些行为点统一做用户级推荐缓存失效，并补了缓存集成测试回归保护。
* 第 57 步验证结果为：`backend/tests` 全量测试 `103 passed`，`tests/e2e/test_full_demo_flow.py` 测试 `1 passed`。

交接提醒：

* 当前默认演示普通用户账号为 `user@shiyige-demo.com`，默认密码为 `user123456`；默认演示管理员账号仍是 `admin@shiyige-demo.com`，默认密码为 `admin123456`。
* `backend/scripts/seed_demo_data.py` 和 `backend/scripts/seed_base_data.py` 是两层不同职责：前者负责答辩/演示数据，后者负责最小业务基础种子；后续不要把两者重新揉成一份不可区分的大脚本。
* 推荐缓存现在依赖显式失效，而不是自动感知数据库变化；后续如果再新增会影响用户兴趣画像的行为类型，记得同步调用推荐缓存失效逻辑，否则首页“猜你喜欢”会再次出现旧数据回放。
* 当前测试全部通过，但仍保留大量 `datetime.utcnow()` 的三方和现有代码弃用警告；这不阻塞 Step 57 完成，但后续若做 Python 3.13+ 清理，可以统一替换为 timezone-aware UTC 时间。

下一步起点：

* 继续执行 **Step 58. 交付文档**。

### 同日继续推进记录（三十五）

已继续完成：

* **Step 58. 交付文档**

新增与修改：

* `docs/database_design.md`
* `docs/api_guide.md`
* `docs/deployment.md`
* `docs/test_report.md`
* `docs/ai_usage_boundary.md`
* `memory-bank/progress.md`
* `memory-bank/architecture.md`

第 58 步验证：

* `test -f docs/database_design.md`
* `test -f docs/api_guide.md`
* `test -f docs/deployment.md`
* `test -f docs/test_report.md`
* `test -f docs/ai_usage_boundary.md`

结果：

* 已补齐数据库设计说明，明确 PostgreSQL、Redis、MinIO 的职责边界和核心业务表关系。
* 已补齐 API 使用指南，整理前后台接口分组、鉴权方式和演示账号。
* 已补齐部署说明，覆盖 Docker Compose 一键启动、访问入口、测试命令和重置方式。
* 已补齐测试报告，记录最终回归命令、通过结果以及本轮实际修复的问题。
* 已补齐 AI 使用边界说明，明确 AI 可参与范围、不可跳过的验证要求和人工复核重点。
* 第 58 步验证结果为：五份交付文档文件存在性校验全部通过。

交接提醒：

* 当前计划文件中的 Step 01 到 Step 58 已全部执行完成，并且第 56 到第 58 步都已补回 `progress.md` 与 `architecture.md`。
* 如后续继续演进，优先把新增事实同步写入 `memory-bank/progress.md` 和 `memory-bank/architecture.md`，保持当前交接链路不断裂。
* 若后续要做公网部署或答辩包装，优先从 `docs/deployment.md`、`docs/test_report.md` 和 `docs/ai_usage_boundary.md` 继续，而不是重新写一套平行文档。

当前状态：

* 实施计划已全部完成。

### 同日继续推进记录（三十六）

已继续完成：

* 后台推荐调试证据页

新增与修改：

* `backend/app/services/recommendations.py`
* `backend/app/api/v1/admin_recommendations.py`
* `backend/app/api/v1/router.py`
* `backend/tests/api/test_admin_recommendation_debug.py`
* `admin/recommendation-debug.html`
* `admin/js/app.js`
* `admin/css/admin.css`
* `tests/e2e/test_admin_basic.py`
* `memory-bank/progress.md`
* `memory-bank/architecture.md`

验证命令：

* `./.venv/bin/python -m pytest backend/tests/api/test_recommendations.py backend/tests/api/test_admin_recommendation_debug.py backend/tests/api/test_admin_reindex.py tests/e2e/test_admin_basic.py -q`

结果：

* 已新增后台推荐调试接口 `GET /api/v1/admin/recommendations/debug`，管理员可按用户邮箱查看真实推荐画像、最近行为、候选商品分数拆解、embedding 文本片段和向量预览。
* 已新增后台页面 `admin/recommendation-debug.html`，可直接输入用户邮箱并渲染 PPT 可截图的推荐证据，不再需要只看接口返回 JSON。
* 推荐调试页展示的候选商品分数复用了 `backend/app/services/recommendations.py` 中与首页“猜你喜欢”相同的打分逻辑，而不是单独拼装一份展示用假数据。
* 已新增 `backend/tests/api/test_admin_recommendation_debug.py`，锁定管理员查询推荐调试数据的接口结构、候选分数信息和操作日志写入。
* 已扩展 `tests/e2e/test_admin_basic.py`，锁定后台最小链路现在不仅能看仪表盘/商品/订单/重建，还能真实渲染推荐调试页。
* 本轮验证结果为：4 个聚焦测试全部通过。

交接提醒：

* 当前推荐调试页查询入口是“前台用户邮箱”，不是用户 ID，目的是方便答辩时直接对照账号切换。
* 调试页里展示的是“向量检索与兴趣词加权”的真实拆解结果：`vector_similarity`、`vector_score`、`term_bonus`、`matched_terms` 和 `reason` 都来自同一套后端推荐逻辑。
* 如果后续再调整首页推荐公式，必须同步关注 `backend/app/services/recommendations.py` 的共享候选打分函数，否则后台调试页和前台“猜你喜欢”会失真。

### 同日继续推进记录（三十七）

已继续完成：

* Recommendation Upgrade Phase 1：基线冻结与问题确认

新增与修改：

* `docs/recommendation_baseline_analysis.md`
* `docs/recommendation_upgrade_plan.md`
* `docs/recommendation_baseline_metrics.json`
* `backend/scripts/export_baseline_recommendation_metrics.py`
* `backend/tests/test_recommendation_baseline.py`
* `memory-bank/progress.md`
* `memory-bank/architecture.md`

验证命令：

* `docker compose up -d`
* `./.venv/bin/python -m pytest backend/tests/test_recommendation_baseline.py -q`
* `./.venv/bin/python -m pytest backend/tests/api/test_recommendations.py backend/tests/api/test_search_semantic.py backend/tests/integration/test_search_ranking.py backend/tests/integration/test_user_interest_profile.py -q`
* `./.venv/bin/python -m pytest backend/tests -q`
* `./.venv/bin/python -m backend.scripts.export_baseline_recommendation_metrics`
* `./.venv/bin/python -m ruff check backend/scripts/export_baseline_recommendation_metrics.py backend/tests/test_recommendation_baseline.py`

结果：

* 已冻结当前推荐系统 baseline，并明确记录当前实现仍然是“JSON 向量 + Python 全量余弦遍历 + 规则加分”的链路，而不是独立向量数据库检索。
* 已新增 `docs/recommendation_baseline_analysis.md`，把 `vector_search.py`、`recommendations.py`、`recommendation.py` 的当前搜索和推荐流程、限制与固定评估样本整理成文档。
* 已新增 `docs/recommendation_upgrade_plan.md`，把 `memory-bank/shiyige_recommendation_upgrade_plan.md` 收敛成当前执行用的阶段说明和 Phase 1 验收入口。
* 已新增 `backend/scripts/export_baseline_recommendation_metrics.py`，可固定 4 个搜索 query 和 2 个基线用户画像，导出当前 TopK 结果、top1 分数、推荐理由和耗时。
* 已新增 `backend/tests/test_recommendation_baseline.py`，锁定 baseline 导出脚本能够在临时数据库中稳定生成可复用的 JSON 报告。
* 已生成 `docs/recommendation_baseline_metrics.json`，后续所有推荐升级阶段都可以基于同一批 query 和用户样本做前后对比。
* 本轮验证结果为：新增 baseline 测试、推荐相关回归测试、后端全量测试和新增 Python 文件的 `ruff check` 全部通过。

交接提醒：

* Phase 1 只冻结现状，没有改写任何搜索和推荐打分逻辑；后续 Phase 2 及之后的改造必须保留旧逻辑作为 fallback/baseline。
* 当前 baseline 报告默认会使用当前应用配置里的 embedding provider；在本地未额外配置时，仍然是 `local_hash`，这是当前真实基线的一部分，不要在 Phase 1 回避这一点。
* `docs/recommendation_baseline_metrics.json` 是本轮导出的对照快照，后续如果重新导出导致数值变化，需要在提交说明里明确为什么变化以及是否属于预期。

### 同日继续推进记录（三十八）

已继续完成：

* Recommendation Upgrade Phase 2：引入 Qdrant 独立向量数据库

新增与修改：

* `docker-compose.yml`
* `.env.example`
* `.gitignore`
* `backend/requirements.txt`
* `backend/app/core/config.py`
* `backend/app/main.py`
* `backend/app/api/v1/health.py`
* `backend/app/api/v1/products.py`
* `backend/app/api/v1/search.py`
* `backend/app/services/qdrant_client.py`
* `backend/app/services/vector_store.py`
* `backend/tests/test_qdrant_connection.py`
* `backend/tests/api/test_health.py`
* `backend/tests/api/test_recommendations.py`
* `backend/tests/api/test_search_semantic.py`
* `backend/tests/unit/test_settings.py`
* `docs/deployment.md`
* `memory-bank/progress.md`
* `memory-bank/architecture.md`

验证命令：

* `UV_CACHE_DIR=.uv-cache uv pip install --python .venv/bin/python -r backend/requirements-dev.txt`
* `./.venv/bin/python -m ruff check backend/app/core/config.py backend/app/main.py backend/app/api/v1/health.py backend/app/api/v1/products.py backend/app/api/v1/search.py backend/app/services/qdrant_client.py backend/app/services/vector_store.py backend/tests/api/test_health.py backend/tests/api/test_recommendations.py backend/tests/api/test_search_semantic.py backend/tests/unit/test_settings.py backend/tests/test_qdrant_connection.py`
* `docker compose config --quiet`
* `./.venv/bin/python -m pytest backend/tests/unit/test_settings.py backend/tests/api/test_health.py backend/tests/api/test_recommendations.py backend/tests/api/test_search_semantic.py backend/tests/test_qdrant_connection.py -q`
* `docker compose down -v --remove-orphans`
* `docker compose up -d --build`
* `curl --noproxy '*' -s http://127.0.0.1:6333/collections`
* `curl --noproxy '*' -s http://127.0.0.1/api/v1/health`
* `./.venv/bin/python -m pytest backend/tests/test_qdrant_connection.py -q`
* `./.venv/bin/python -m pytest backend/tests -q`

结果：

* 已在 `docker-compose.yml` 中引入独立 `qdrant` 服务，开放 `6333/6334` 端口并挂载持久化 volume，同时保留 PostgreSQL、Redis、MinIO 作为原有业务基础设施。
* 已在 `backend/app/core/config.py` 增加 `VECTOR_DB_PROVIDER`、`QDRANT_URL`、collection 名称和 `RECOMMENDATION_PIPELINE_VERSION` 等配置，并补齐 `.env.example`。
* 已新增 `backend/app/services/qdrant_client.py`，负责 Qdrant 连接、健康探测和 collection 存在性判断，没有掺入业务检索逻辑。
* 已新增 `backend/app/services/vector_store.py`，统一暴露当前向量存储运行时信息；当 Qdrant 不可达时，系统会明确标记 `degraded_to_baseline=true`，而不是让接口崩溃。
* 已把 Qdrant 启动探测接入 `backend/app/main.py`，并把运行时状态暴露到 `GET /api/v1/health`。
* 已把当前推荐和语义搜索接口的数据体补充 `pipeline` 标记，能够说明“当前配置的是 Qdrant，但这一步仍使用 baseline 搜索/推荐后端”。
* 已新增 `backend/tests/test_qdrant_connection.py`，覆盖 Qdrant 可达和不可达两种状态；旧接口测试和后端全量测试仍全部通过。
* 本轮真实环境验证中，`curl http://127.0.0.1:6333/collections` 返回 `status=ok` 且 collections 为空数组，`curl http://127.0.0.1/api/v1/health` 返回 `qdrant_available=true`、`degraded_to_baseline=false` 和 `active_*_backend=baseline`。

交接提醒：

* 当前 Phase 2 只是把 Qdrant 作为基础设施接入，并没有把搜索或推荐真正切到 Qdrant；因此健康检查里会出现“Qdrant 可用，但 active backend 仍是 baseline”的状态，这是刻意保守的阶段结果。
* `docker compose up -d --build` 首次构建 API 镜像时，Docker BuildKit 出现过一次 snapshot 导出异常；直接重试后命中缓存并成功完成构建，当前代码本身没有因此回滚。
* 由于 `.gitignore` 原先会忽略 `.env.*`，本轮额外加入了 `!.env.example`，后续如果再添加新的环境模板文件，记得确认不会被忽略。

### 同日继续推进记录（三十九）

已继续完成：

* Recommendation Upgrade Phase 3：设计 Qdrant 商品 Collection

新增与修改：

* `backend/app/models/recommendation.py`
* `backend/app/tasks/embedding_tasks.py`
* `backend/app/services/recommendations.py`
* `backend/app/services/vector_schema.py`
* `backend/app/tasks/qdrant_schema_tasks.py`
* `backend/tests/test_qdrant_schema.py`
* `backend/tests/test_qdrant_connection.py`
* `backend/alembic/env.py`
* `backend/alembic/versions/20260424_10_qdrant_vector_metadata.py`
* `backend/app/main.py`
* `docs/vector_database_design.md`
* `memory-bank/progress.md`
* `memory-bank/architecture.md`

验证命令：

* `./.venv/bin/python -m ruff check backend/app/models/recommendation.py backend/app/tasks/embedding_tasks.py backend/app/services/recommendations.py backend/alembic/env.py backend/app/services/vector_schema.py backend/app/tasks/qdrant_schema_tasks.py backend/tests/test_qdrant_schema.py backend/alembic/versions/20260424_10_qdrant_vector_metadata.py backend/app/main.py`
* `./.venv/bin/python -m pytest backend/tests/test_qdrant_schema.py -q`
* `./.venv/bin/python -m pytest backend/tests/tasks/test_embedding_tasks.py backend/tests/api/test_recommendations.py backend/tests/api/test_search_semantic.py -q`
* `DATABASE_URL=postgresql+psycopg://shiyige:shiyige@127.0.0.1:5432/shiyige ./.venv/bin/alembic -c backend/alembic.ini upgrade head`
* `docker compose up -d --build api nginx`
* `curl --noproxy '*' --retry 10 --retry-delay 1 -s http://127.0.0.1:6333/collections/shiyige_products_v1`
* `curl --noproxy '*' --retry 10 --retry-delay 1 -s http://127.0.0.1/api/v1/health`
* `docker compose logs api --tail=40`
* `./.venv/bin/python -m pytest backend/tests -q`

结果：

* 已新增 `backend/app/services/vector_schema.py`，明确 `shiyige_products_v1` 的 named vectors 结构：`dense(384)`、`sparse` 和 `colbert(128, multivector)`。
* 已新增 `backend/app/tasks/qdrant_schema_tasks.py`，实现商品 collection 和 payload index 的幂等初始化。
* 已新增 `docs/vector_database_design.md`，把 Qdrant collection、payload 字段和 PostgreSQL 侧同步元数据职责固定成文档。
* 已在 `product_embedding` 中新增 `qdrant_point_id`、`qdrant_collection`、`index_status`、`index_error`；已在 `user_interest_profile` 中新增 `qdrant_user_point_id`、`profile_version`、`last_synced_at`。
* 已新增 Alembic 迁移 `20260424_10_qdrant_vector_metadata.py`，并真实升级到当前 PostgreSQL 数据库。
* 已把 Qdrant schema 初始化接到 API 启动流程：Qdrant 可达时，API 启动会自动确保 `shiyige_products_v1` collection 和 payload index 存在。
* 真实环境验证中，`curl http://127.0.0.1:6333/collections/shiyige_products_v1` 已返回 collection 详情，能看到 `dense`、`colbert`、`sparse` 和 11 个 payload index；`/api/v1/health` 也已返回 `qdrant_collections=[\"shiyige_products_v1\"]`。
* 本轮最终验证结果为：Qdrant schema 测试、推荐相关回归、Alembic 升级、真实 collection 查询和后端全量测试全部通过。

交接提醒：

* 当前 collection 只完成 schema 与 payload index 初始化，还没有写入商品 points；真正的商品全量/增量索引属于下一阶段 Phase 5。
* `backend/tests/test_qdrant_connection.py` 的断言已经调整为和真实 collections 列表对齐，因为从 Phase 3 开始，`shiyige_products_v1` 可能在 API 启动后自动存在。
* 目前仍保留 `embedding_vector` JSON 字段，以免 baseline 和现有推荐链路在 Phase 3 就被切断；后续如果完全迁移到 Qdrant，再考虑是否彻底弃用。

### 同日继续推进记录（四十）

已继续完成：

* Recommendation Upgrade Phase 4：升级 Embedding 服务

新增与修改：

* `backend/app/services/embedding.py`
* `backend/app/services/embedding_dense.py`
* `backend/app/services/embedding_sparse.py`
* `backend/app/services/embedding_colbert.py`
* `backend/app/services/embedding_registry.py`
* `backend/app/services/embedding_text.py`
* `backend/app/core/config.py`
* `backend/app/services/vector_schema.py`
* `backend/app/tasks/embedding_tasks.py`
* `backend/requirements.txt`
* `.env.example`
* `docker-compose.yml`
* `backend/tests/test_embedding_providers.py`
* `backend/tests/services/test_embedding_text_builder.py`
* `backend/tests/unit/test_settings.py`
* `backend/tests/conftest.py`
* `backend/tests/api/conftest.py`
* `tests/e2e/conftest.py`
* `docs/embedding_model_design.md`
* `memory-bank/progress.md`
* `memory-bank/architecture.md`

验证命令：

* `./.venv/bin/python -m ruff check backend/app/services/embedding.py backend/app/services/embedding_dense.py backend/app/services/embedding_sparse.py backend/app/services/embedding_colbert.py backend/app/services/embedding_registry.py backend/app/services/embedding_text.py backend/app/core/config.py backend/app/services/vector_schema.py backend/app/tasks/embedding_tasks.py backend/tests/test_embedding_providers.py backend/tests/services/test_embedding_text_builder.py backend/tests/unit/test_settings.py backend/tests/conftest.py backend/tests/api/conftest.py tests/e2e/conftest.py`
* `./.venv/bin/python -m pytest backend/tests/test_embedding_providers.py -q`
* `./.venv/bin/python -m pytest backend/tests/services/test_embedding_text_builder.py -q`
* `./.venv/bin/python -m pytest backend/tests/unit/test_embedding_provider.py -q`
* `./.venv/bin/python -m pytest backend/tests/unit/test_settings.py -q`
* `./.venv/bin/python -m pytest backend/tests -q`
* `docker compose config --quiet`
* `./.venv/bin/python - <<'PY' ... get_embedding_provider(AppSettings(...fastembed_dense...)) ... PY`

结果：

* 已把默认 dense provider 从 `local_hash` 切换为 `fastembed_dense + BAAI/bge-small-zh-v1.5(512)`，并新增 `fastembed_sparse + Qdrant/bm25`、`fastembed_colbert + answerdotai/answerai-colbert-small-v1(96)` 的独立配置。
* 已新增 `backend/app/services/embedding_dense.py`、`embedding_sparse.py`、`embedding_colbert.py` 和 `embedding_registry.py`，把 dense、sparse、ColBERT 三类 provider 的实现和注册缓存拆开；`backend/app/services/embedding.py` 现在只保留公共契约和兼容 facade。
* 已把商品文本构建升级为四路输出：`title_text`、`semantic_text`、`keyword_text`、`rerank_text`；现有 `embedding_text` 继续作为 `semantic_text` 别名，避免旧搜索/推荐链路在 Phase 4 被打断。
* 已在文本构建中显式纳入类目、文化说明、朝代风格、工艺、节令、场景、标签，以及从价格、礼赠和搭配语义推导出的补充字段。
* 已把 Qdrant schema 中的 ColBERT 维度从硬编码常量改为配置驱动，并把 Compose 环境补齐 embedding 配置和 `api-model-cache` volume。
* 已把后端测试和 e2e 测试环境固定为 `local_hash` dense/sparse/colbert，保证测试环境不依赖真实模型下载；生产默认值仍保持为真实模型配置。
* 已新增 `docs/embedding_model_design.md`，记录默认模型、维度、用途、测试环境覆写方式和文本构建规则。
* 真实模型验证中，`BAAI/bge-small-zh-v1.5` 对“宋代茶具”和“宋韵点茶器具”的相似度为 `0.821397`，明显高于与“现代蓝牙耳机”的 `0.320658`，说明默认 dense 语义模型已可在本地演示环境运行。
* 本轮最终验证结果为：新增 provider 测试、文本构建测试、原有 embedding 单测、配置单测、后端全量测试和 Compose 配置检查全部通过。

交接提醒：

* 当前 Phase 4 只负责“生成哪三类 embedding、用什么模型、文本怎么构造”，还没有把商品真正写入 Qdrant；Qdrant point 写入、状态查询和失败重试属于下一阶段 Phase 5。
* `backend/tests/conftest.py`、`backend/tests/api/conftest.py` 和 `tests/e2e/conftest.py` 现在会在导入 `create_app()` 之前先注入测试 embedding 环境变量，后续不要把这些覆盖逻辑移到 fixture 内部，否则全局 `AppSettings` 缓存会重新暴露真实模型默认值。
* `backend/app/services/embedding_text.py` 目前会根据现有商品字段推导价格带、礼赠属性和搭配属性；如果后续商品模型新增显式字段，应优先改成读取真实字段，而不是继续扩大启发式推导。

### 同日继续推进记录（四十一）

已继续完成：

* Recommendation Upgrade Phase 5：构建商品向量索引任务

新增与修改：

* `backend/app/services/product_index_document.py`
* `backend/app/tasks/qdrant_index_tasks.py`
* `backend/app/tasks/qdrant_schema_tasks.py`
* `backend/app/api/v1/admin_vector_index.py`
* `backend/app/api/v1/router.py`
* `backend/app/schemas/admin.py`
* `backend/app/tasks/embedding_tasks.py`
* `backend/app/services/vector_search.py`
* `backend/app/services/recommendations.py`
* `backend/scripts/reindex_products_to_qdrant.py`
* `backend/tests/test_product_qdrant_indexing.py`
* `backend/tests/api/test_admin_vector_index.py`
* `docs/indexing_operations.md`
* `memory-bank/progress.md`
* `memory-bank/architecture.md`

验证命令：

* `./.venv/bin/python -m ruff check backend/app/services/product_index_document.py backend/app/tasks/qdrant_index_tasks.py backend/app/tasks/qdrant_schema_tasks.py backend/app/api/v1/admin_vector_index.py backend/scripts/reindex_products_to_qdrant.py backend/app/schemas/admin.py backend/app/api/v1/router.py backend/app/tasks/embedding_tasks.py backend/app/services/vector_search.py backend/app/services/recommendations.py backend/tests/test_product_qdrant_indexing.py backend/tests/api/test_admin_vector_index.py`
* `./.venv/bin/python -m pytest backend/tests/test_product_qdrant_indexing.py -q`
* `./.venv/bin/python -m pytest backend/tests/api/test_admin_vector_index.py -q`
* `./.venv/bin/python -m pytest backend/tests/tasks/test_embedding_tasks.py backend/tests/api/test_recommendations.py backend/tests/api/test_search_semantic.py backend/tests/api/test_admin_reindex.py -q`
* `./.venv/bin/python -m pytest backend/tests/test_qdrant_schema.py backend/tests/test_product_qdrant_indexing.py -q`
* `docker compose up -d --build`
* `docker compose exec -T api python -m backend.scripts.reindex_products_to_qdrant --mode full`
* `curl --noproxy '*' -s http://127.0.0.1:6333/collections/shiyige_products_v1`
* `./.venv/bin/python - <<'PY' ... client.count('shiyige_products_v1') / client.retrieve(... with_vectors=True) ... PY`
* `./.venv/bin/python -m pytest backend/tests -q`

结果：

* 已新增 `backend/app/services/product_index_document.py`，把商品 payload、dense/sparse/colbert 三类向量和 Qdrant `PointStruct` 组装逻辑集中到一个地方，不再在任务层散落拼字段。
* 已新增 `backend/app/tasks/qdrant_index_tasks.py`，实现商品全量索引、增量索引、失败重试、显式删除同步和索引状态查询；PostgreSQL 侧会同步维护 `index_status`、`index_error` 和 `last_indexed_at`。
* 已新增 `backend/app/api/v1/admin_vector_index.py` 和 `backend/scripts/reindex_products_to_qdrant.py`，把商品索引变成正式的后台接口与命令行入口，不再依赖搜索请求临时触发全库向量准备。
* 已新增 `backend/tests/test_product_qdrant_indexing.py`，覆盖了全量写入、标签变更后的增量更新、下架商品删除同步、失败回写与重试，以及“无库存商品不出现在搜索/推荐结果”。
* 已新增 `backend/tests/api/test_admin_vector_index.py`，验证后台状态接口和同步接口的路由分发、统一响应和操作日志写入。
* 已新增 `docs/indexing_operations.md`，固定了 CLI 命令、后台接口、payload 字段和增量规则。
* 已把 baseline 搜索与推荐补上库存过滤：当前即使还没切到 Qdrant 检索，也不会再把 `stock_available=false` 的商品返回给语义搜索和猜你喜欢接口。
* 已在 `backend/app/tasks/qdrant_schema_tasks.py` 增加 schema drift 检测：当商品 collection 维度仍停留在旧版 `dense=384 / colbert=128` 时，full 模式索引会自动重建 collection；incremental 模式则会明确报错，避免静默写坏索引。
* 真实 Compose 环境验证中，`docker compose exec -T api python -m backend.scripts.reindex_products_to_qdrant --mode full` 返回 `indexed=20`、`failed=0`；`curl /collections/shiyige_products_v1` 显示 collection 已切到 `dense=512`、`colbert=96`、`points_count=20`；后续直接读取 point 也能看到 `vector_keys=['colbert', 'dense', 'sparse']` 和 `payload_status='active'`。
* 本轮最终验证结果为：Phase 5 专项测试、后台接口测试、推荐/搜索相关回归、真实容器索引脚本验证、Qdrant collection 查询和后端全量测试全部通过。

交接提醒：

* 当前 Phase 5 已经把商品 points 正式写入 Qdrant，但搜索接口本身仍然走 baseline 检索逻辑；真正把搜索切到 Qdrant hybrid recall 是下一阶段 Phase 6。
* `sync_products_to_qdrant(mode=\"full\")` 现在会在检测到 collection 维度漂移时自动重建商品 collection，这对“模型升级后第一次全量重建”是必要的；如果后续要做更细粒度的生产迁移，应把这一步变成显式运维动作。
* `backend/app/services/product_index_document.py` 现在把 `status` 和 `stock_available` 分开维护：下架商品会从 Qdrant 删除，缺货但仍上架的商品会保留 point 但被搜索/推荐过滤；后续 Phase 6/7 的 payload filter 应继续沿用这套语义，不要再混回单一状态字段。

### 同日继续推进记录（四十二）

已继续完成：

* Recommendation Upgrade Phase 6：搜索页改造为混合检索

新增与修改：

* `backend/app/services/search_filters.py`
* `backend/app/services/search_reranker.py`
* `backend/app/services/hybrid_search.py`
* `backend/app/services/vector_search.py`
* `backend/app/services/vector_store.py`
* `backend/app/api/v1/search.py`
* `backend/app/schemas/search.py`
* `backend/scripts/export_baseline_recommendation_metrics.py`
* `backend/tests/test_search_filters.py`
* `backend/tests/test_hybrid_search.py`
* `docs/search_pipeline.md`
* `memory-bank/progress.md`
* `memory-bank/architecture.md`

验证命令：

* `./.venv/bin/python -m ruff check backend/app/services/search_filters.py backend/app/services/search_reranker.py backend/app/services/hybrid_search.py backend/app/services/vector_search.py backend/app/services/vector_store.py backend/app/api/v1/search.py backend/app/schemas/search.py backend/scripts/export_baseline_recommendation_metrics.py backend/tests/test_search_filters.py backend/tests/test_hybrid_search.py`
* `./.venv/bin/python -m pytest backend/tests/test_search_filters.py -q`
* `./.venv/bin/python -m pytest backend/tests/test_hybrid_search.py -q`
* `./.venv/bin/python -m pytest backend/tests/api/test_search_semantic.py -q`
* `./.venv/bin/python -m pytest backend/tests/test_qdrant_connection.py backend/tests/test_product_qdrant_indexing.py backend/tests/integration/test_search_ranking.py backend/tests/api/test_health.py -q`
* `./.venv/bin/python -m pytest backend/tests -q`
* `docker compose up -d --build`
* `docker compose exec -T api python -m backend.scripts.reindex_products_to_qdrant --mode full`
* `curl --noproxy '*' -s http://127.0.0.1:6333/collections/shiyige_products_v1`
* `curl --noproxy '*' -s -X POST http://127.0.0.1/api/v1/search/semantic -H 'Content-Type: application/json' -d '{"query":"香囊","limit":5}'`
* `curl --noproxy '*' -s -X POST http://127.0.0.1/api/v1/search/semantic -H 'Content-Type: application/json' -d '{"query":"端午送礼","limit":5,"festival_tag":"端午","max_price":200}'`

结果：

* 已新增 `backend/app/services/search_filters.py`，把 `category_id`、价格区间、朝代、工艺、场景、节令和 `stock_only` 统一成同一份过滤模型，并同时复用于 Qdrant payload filter、baseline fallback 和行为日志。
* 已新增 `backend/app/services/search_reranker.py`，集中承载 RRF 分数、ColBERT max-sim、payload 语义 bonus、业务 bonus 和搜索 reason 拼装逻辑，不再把精排规则散落在搜索主函数里。
* 已新增 `backend/app/services/hybrid_search.py`，实现 dense recall top 100、sparse recall top 100、本地 RRF 融合、Top 50 ColBERT 重排，以及只回表加载最终候选商品的搜索路径。
* 已把 `backend/app/services/vector_search.py` 改成“双路径入口”：默认在 Qdrant collection 已建好、schema 正常且已有 points 时走 `qdrant_hybrid`；否则回退到保留的 `baseline_semantic_search_products()`。
* 已把 `backend/app/services/vector_store.py` 的运行时标记从“Qdrant 是否可达”升级为“Qdrant 搜索是否真正就绪”。现在只有在 collection 存在、schema 无漂移且已有索引 points 时，`active_search_backend` 才会切到 `qdrant_hybrid`。
* 已扩展 `POST /api/v1/search/semantic` 的请求模型与日志字段，支持 `dynasty_style`、`craft_type`、`scene_tag`、`festival_tag` 和 `stock_only=true` 的结构化过滤，并把过滤条件写入 `semantic_search` 行为日志。
* 已更新 baseline 导出脚本，让 `backend/scripts/export_baseline_recommendation_metrics.py` 在 Phase 6 之后仍显式使用 `force_baseline=True`，保证 Phase 1 的对照结果不会因为默认搜索后端切到 Qdrant 而被污染。
* 真实 Compose 环境验证中，`/api/v1/search/semantic` 返回的 `pipeline.active_search_backend` 已切为 `qdrant_hybrid`、`degraded_to_baseline=false`；搜索“香囊”时 Top1 为 `故宫宫廷香囊`，reason 为 `与“香囊”语义相关，关键词命中“香囊”，文化特征匹配“香囊”，经混合检索精排`；搜索“端午送礼”并加 `festival_tag=端午,max_price=200` 时只返回价格符合条件的 `故宫宫廷香囊`。
* 本轮最终验证结果为：Phase 6 专项测试、搜索/索引/运行时回归、后端全量测试、容器重建、Qdrant collection 检查和真实 API 请求验证全部通过；后端全量测试结果为 `127 passed`。

交接提醒：

* 当前只有搜索链路默认切到了 `qdrant_hybrid`，个性化推荐接口仍然保持 baseline；推荐侧的多路召回属于下一阶段 Phase 7。
* `probe_vector_store_runtime()` 现在会额外检查 product collection 是否存在 points，因此在“刚建 collection 但尚未 full reindex”的环境里仍会回退 baseline；如果后续要进一步压缩接口延迟，可考虑把这部分 readiness 探测做短 TTL 缓存。
* `semantic_search_products()` 仍然保留 `force_baseline=True` 与 `provider=` 的测试/脚本注入能力，后续如果要继续做 baseline 对照或离线审计，不要删除这条显式回退路径。

### 同日继续推进记录（四十三）

已继续完成：

* Recommendation Upgrade Phase 7：实现完整多路召回推荐系统

新增与修改：

* `backend/app/services/candidate_fusion.py`
* `backend/app/services/diversity.py`
* `backend/app/services/recall_content.py`
* `backend/app/services/recall_sparse_interest.py`
* `backend/app/services/recall_collaborative.py`
* `backend/app/services/recall_trending.py`
* `backend/app/services/recall_new_arrival.py`
* `backend/app/services/recommendation_pipeline.py`
* `backend/app/services/recommendations.py`
* `backend/app/services/vector_store.py`
* `backend/app/api/v1/admin_recommendations.py`
* `backend/scripts/export_baseline_recommendation_metrics.py`
* `backend/tests/test_recommendation_pipeline.py`
* `backend/tests/api/test_admin_recommendation_debug.py`
* `docs/recommendation_pipeline.md`
* `memory-bank/progress.md`
* `memory-bank/architecture.md`

验证命令：

* `./.venv/bin/python -m ruff check backend/app/services/candidate_fusion.py backend/app/services/diversity.py backend/app/services/recall_content.py backend/app/services/recall_sparse_interest.py backend/app/services/recall_collaborative.py backend/app/services/recall_trending.py backend/app/services/recall_new_arrival.py backend/app/services/recommendation_pipeline.py backend/app/services/recommendations.py backend/app/services/vector_store.py backend/app/api/v1/admin_recommendations.py backend/scripts/export_baseline_recommendation_metrics.py backend/tests/test_recommendation_pipeline.py backend/tests/api/test_admin_recommendation_debug.py backend/tests/api/test_recommendations.py`
* `./.venv/bin/python -m pytest backend/tests/test_recommendation_pipeline.py -q`
* `./.venv/bin/python -m pytest backend/tests/api/test_recommendations.py backend/tests/api/test_admin_recommendation_debug.py backend/tests/test_qdrant_connection.py -q`
* `./.venv/bin/python -m pytest backend/tests/test_recommendation_pipeline.py backend/tests/api/test_recommendations.py backend/tests/api/test_admin_recommendation_debug.py backend/tests/test_qdrant_connection.py -q`
* `./.venv/bin/python -m pytest backend/tests -q`
* `docker compose up -d --build`
* `docker compose exec -T api python -m backend.scripts.reindex_products_to_qdrant --mode full`
* `curl --noproxy '*' -s -X POST http://127.0.0.1/api/v1/auth/register -H 'Content-Type: application/json' -d '{"email":"phase7-user@example.com","username":"phase7user","password":"phase7-pass-123"}'`
* `curl --noproxy '*' -s http://127.0.0.1/api/v1/products/1 -H 'Authorization: Bearer <phase7-user-token>'`
* `curl --noproxy '*' -s 'http://127.0.0.1/api/v1/search?q=春日汉服' -H 'Authorization: Bearer <phase7-user-token>'`
* `curl --noproxy '*' -s -X POST http://127.0.0.1/api/v1/cart/items -H 'Authorization: Bearer <phase7-user-token>' -H 'Content-Type: application/json' -d '{"product_id":1,"sku_id":1,"quantity":1}'`
* `curl --noproxy '*' -s http://127.0.0.1/api/v1/products/recommendations -H 'Authorization: Bearer <phase7-user-token>'`
* `curl --noproxy '*' -s 'http://127.0.0.1/api/v1/admin/recommendations/debug?email=phase7-user@example.com&limit=3' -H 'Authorization: Bearer <admin-token>'`

结果：

* 已新增 `backend/app/services/recommendation_pipeline.py`，把用户画像构建、冷启动判断、多路召回调用、候选融合、多样性控制和最终推荐结果组装集中到同一条推荐管线上。
* 已新增 `backend/app/services/recall_content.py`、`recall_sparse_interest.py`、`recall_collaborative.py`、`recall_trending.py` 和 `recall_new_arrival.py`，分别承载内容语义召回、关键词兴趣召回、相似商品召回、基于用户行为重叠的协同过滤召回、热门趋势召回和新品探索召回。
* 已新增 `backend/app/services/candidate_fusion.py` 与 `diversity.py`，把多路候选统一成带 `recall_channels`、`channel_details`、`matched_terms`、`vector_score` 和 `term_bonus` 的融合候选，并在最终结果前做轻量的类目/朝代/工艺去同质化。
* 已把 `backend/app/services/recommendations.py` 改成双路径入口：当 Qdrant product collection ready 时默认走 `multi_recall`；否则保留 `baseline_recommend_products_for_user()` 作为显式回退路径。Phase 1 baseline 导出脚本现在也会对推荐显式传入 `force_baseline=True`。
* 已把 `backend/app/services/vector_store.py` 的 `active_recommendation_backend` 从固定 `baseline` 改成 readiness 驱动：在 Qdrant collection 存在、schema 正确且已有 points 时切换为 `multi_recall`。
* 已把 `backend/app/api/v1/admin_recommendations.py` 接到新的推荐管线，并在调试响应中补充 `recall_channels` 和 `channel_details`，让后台能直接看到每个推荐商品来自哪些召回通道。
* 已新增 `backend/tests/test_recommendation_pipeline.py`，覆盖“有行为用户触发多路召回”和“冷启动用户仍然返回非空推荐”两条关键链路；同时更新 `backend/tests/api/test_admin_recommendation_debug.py`，验证后台调试接口真的返回召回通道明细。
* 真实 Compose 环境验证中，新注册用户对 `明制襦裙` 产生浏览、搜索和加购行为后，请求 `/api/v1/products/recommendations` 返回的 `pipeline.active_recommendation_backend` 已切为 `multi_recall`、`degraded_to_baseline=false`；Top1 推荐为 `云肩披帛扣`，reason 为 `来自内容语义召回、关键词兴趣召回、相似商品召回，匹配“汉服/明制/日常”`。
* 同一真实环境下，请求 `/api/v1/admin/recommendations/debug?email=phase7-user@example.com&limit=3` 已能返回每个候选的 `recall_channels` 和 `channel_details`；例如 `云肩披帛扣` 同时带有 `content_profile`、`sparse_interest`、`related_products` 和 `new_arrival` 四条召回来源，说明多路召回融合已真实生效。
* 本轮最终验证结果为：Phase 7 专项测试、推荐相关 API 回归、后端全量测试、容器重建、Qdrant 全量重建、真实登录用户推荐请求和后台调试接口验证全部通过；后端全量测试结果为 `129 passed`。

交接提醒：

* 当前协同过滤召回还是基于 `user_behavior_log` 的轻量相似用户/共同行为聚合，真正的“用户 sparse vector / item-item 共现索引化”属于下一阶段 Phase 8。
* `recommendation_pipeline.py` 里的内容语义、关键词兴趣和相似商品召回依赖 Qdrant；当这些调用失败时，当前实现会保留协同过滤、热门和新品通道继续工作，因此后台调试接口即使在 Qdrant 短暂异常时也不会直接空白。
* 当前首页推荐接口已经不再全量扫描商品，但 `build_user_interest_profile()` 仍会在构建画像时更新 PostgreSQL 侧 profile 元数据；如果后续要继续压缩 p95，应优先考虑缓存画像和 Phase 8 的协同过滤索引，而不是重新退回全量遍历。

### 同日继续推进记录（四十四）

已继续完成：

* Recommendation Upgrade Phase 8：实现协同过滤召回索引

新增与修改：

* `backend/app/models/recommendation_experiment.py`
* `backend/alembic/env.py`
* `backend/alembic/versions/20260424_11_recommendation_experiment.py`
* `backend/app/models/__init__.py`
* `backend/app/services/collaborative_filtering.py`
* `backend/app/tasks/collaborative_index_tasks.py`
* `backend/app/services/recall_collaborative.py`
* `backend/app/services/candidate_fusion.py`
* `backend/app/services/recommendation_pipeline.py`
* `backend/scripts/build_collaborative_index.py`
* `backend/tests/test_collaborative_filtering.py`
* `backend/tests/test_recommendation_pipeline.py`
* `docs/collaborative_filtering_design.md`
* `memory-bank/progress.md`
* `memory-bank/architecture.md`

验证命令：

* `./.venv/bin/python -m ruff check backend/app/models/recommendation_experiment.py backend/app/services/collaborative_filtering.py backend/app/tasks/collaborative_index_tasks.py backend/app/services/recall_collaborative.py backend/app/services/candidate_fusion.py backend/app/services/recommendation_pipeline.py backend/scripts/build_collaborative_index.py backend/tests/test_collaborative_filtering.py backend/tests/test_recommendation_pipeline.py`
* `./.venv/bin/python -m pytest backend/tests/test_collaborative_filtering.py backend/tests/test_recommendation_pipeline.py backend/tests/api/test_recommendations.py backend/tests/api/test_admin_recommendation_debug.py -q`
* `./.venv/bin/python -m pytest backend/tests -q`
* `docker compose up -d --build`
* `docker compose exec -T api python -m backend.scripts.reindex_embeddings`
* `docker compose exec -T api python - <<'PY' ... # 写入 phase8-cf-a@example.com / phase8-cf-b@example.com 的相似兴趣行为样本`
* `docker compose exec -T api python backend/scripts/build_collaborative_index.py`
* `./.venv/bin/python - <<'PY' ... # 管理员登录并请求 /api/v1/admin/recommendations/debug?email=phase8-cf-b@example.com&limit=5`

结果：

* 已新增 `backend/app/models/recommendation_experiment.py` 和迁移 `20260424_11_recommendation_experiment.py`，把协同过滤离线产物从“只在内存里临时计算”升级成可以持久化在数据库中的正式元数据实体。
* 已新增 `backend/app/services/collaborative_filtering.py`，实现行为权重、时间衰减、Qdrant sparse user vector 相似用户召回，以及基于用户行为聚合的 item-item 共现图构建。
* 已新增 `backend/app/tasks/collaborative_index_tasks.py`，负责创建 sparse-only 的 `shiyige_collaborative_v1` collection、写入每个用户的 `interactions` sparse vector，并把 `collaborative_item_cooccurrence_v1` 工件持久化到 `recommendation_experiment`。
* 已把 `backend/app/services/recall_collaborative.py` 从 Phase 7 的轻量相似行为聚合改为双通道委托层，正式输出 `collaborative_user` 和 `item_cooccurrence` 两条协同过滤召回来源。
* 已把 `backend/app/services/candidate_fusion.py` 与 `backend/app/services/recommendation_pipeline.py` 扩展到新的协同过滤通道，使融合结果和后台调试响应能保留两条通道的分数、原因和元信息。
* 已新增 `backend/scripts/build_collaborative_index.py` 作为离线构建入口；脚本支持直接从仓库根目录执行，并在本地 Qdrant 地址与 Compose 内部地址之间自动择优连接。
* 已新增 `backend/tests/test_collaborative_filtering.py`，覆盖 sparse user vector 建索引、相似用户召回和 item cooccurrence 召回；同时更新 `backend/tests/test_recommendation_pipeline.py`，验证多路召回中确实出现新的协同过滤通道。
* 真实 Compose 环境验证中，API 容器已自动执行 `20260424_11` 迁移；`docker compose exec -T api python -m backend.scripts.reindex_embeddings` 返回 `indexed=20 skipped=0 model=BAAI/bge-small-zh-v1.5`，说明商品向量索引正常可用。
* 同一真实环境下，执行 `docker compose exec -T api python backend/scripts/build_collaborative_index.py` 返回 `indexed_users=4 qdrant_points=4 item_nodes=2`，说明协同过滤 sparse 用户索引和 item 共现工件都已真实落地。
* 进一步人工构造 `phase8-cf-a@example.com` 与 `phase8-cf-b@example.com` 两位兴趣相似用户后，请求 `/api/v1/admin/recommendations/debug?email=phase8-cf-b@example.com&limit=5` 的首条推荐为 `宋风褙子套装`；调试明细同时出现 `collaborative_user` 和 `item_cooccurrence`，且已消费的 `明制襦裙` 没有重复推荐，符合 Phase 8 的人工验收要求。
* 本轮最终验证结果为：Phase 8 专项测试、推荐相关 API 回归、后端全量测试、容器重建、商品向量重建、协同过滤离线构建和真实后台调试接口验证全部通过；后端全量测试结果为 `130 passed`。

交接提醒：

* Phase 8 之后，协同过滤已经依赖离线构建步骤；如果演示环境里新增了大量行为数据，应重新执行 `backend/scripts/build_collaborative_index.py`，不要假设请求时会自动刷新 Qdrant sparse 用户索引。
* `recommendation_experiment` 现在承载 item-item 共现图工件；后续如果要扩展离线评估、A/B 实验或排序特征缓存，应优先复用这张表，而不是再散落到新的 JSON 文件或临时表。
* 下一阶段应进入 Phase 9 的高级排序与重排，把当前多路召回结果进一步转成显式特征和统一排序分数，而不是继续在召回层堆叠更多启发式规则。

### 同日继续推进记录（四十五）

已继续完成：

* Recommendation Upgrade Phase 9：实现高级排序与重排

新增与修改：

* `backend/app/core/config.py`
* `backend/app/services/ranking_features.py`
* `backend/app/services/business_rules.py`
* `backend/app/services/ltr_ranker.py`
* `backend/app/services/ranker.py`
* `backend/app/services/recommendation_explainer.py`
* `backend/app/services/recommendation_pipeline.py`
* `backend/app/services/vector_store.py`
* `backend/app/api/v1/products.py`
* `backend/app/api/v1/admin_recommendations.py`
* `backend/tests/test_ranking_features.py`
* `backend/tests/test_ranker.py`
* `backend/tests/test_recommendation_pipeline.py`
* `backend/tests/api/test_recommendations.py`
* `backend/tests/api/test_admin_recommendation_debug.py`
* `docs/ranking_design.md`
* `memory-bank/progress.md`
* `memory-bank/architecture.md`

验证命令：

* `./.venv/bin/python -m ruff check backend/app/core/config.py backend/app/services/ranking_features.py backend/app/services/business_rules.py backend/app/services/ltr_ranker.py backend/app/services/ranker.py backend/app/services/recommendation_explainer.py backend/app/services/recommendation_pipeline.py backend/app/services/vector_store.py backend/app/api/v1/products.py backend/app/api/v1/admin_recommendations.py backend/tests/test_ranking_features.py backend/tests/test_ranker.py backend/tests/test_recommendation_pipeline.py backend/tests/api/test_recommendations.py backend/tests/api/test_admin_recommendation_debug.py`
* `./.venv/bin/python -m pytest backend/tests/test_ranking_features.py backend/tests/test_ranker.py backend/tests/test_recommendation_pipeline.py backend/tests/api/test_admin_recommendation_debug.py -q`
* `./.venv/bin/python -m pytest backend/tests -q`
* `docker compose up -d --build`
* `docker compose exec -T api python -m backend.scripts.reindex_embeddings`
* `docker compose exec -T api python backend/scripts/build_collaborative_index.py`
* `./.venv/bin/python - <<'PY' ... # 登录 phase8-cf-b@example.com 后请求 /api/v1/recommendations?slot=home&debug=true`
* `./.venv/bin/python - <<'PY' ... # 管理员登录后请求 /api/v1/admin/recommendations/debug?email=phase8-cf-b@example.com&limit=5`

结果：

* 已新增 `backend/app/services/ranking_features.py`，为多路召回候选统一构造 recall、用户兴趣、商品质量和业务规则四大类排序特征，并在 debug 输出中保留完整原始特征值。
* 已新增 `backend/app/services/business_rules.py`，把上架/库存过滤、近期曝光降权、同类目连续上限、朝代/工艺集中度控制和探索位注入从召回阶段剥离成正式 post-processing 层。
* 已新增 `backend/app/services/ranker.py`，实现可解释的 `weighted_ranker`；当前最终分数明确拆成 `recall_score`、`interest_score`、`quality_score`、`business_total` 和 `final_score`，不再只是融合分或向量分排序。
* 已新增 `backend/app/services/ltr_ranker.py`，预留 `ltr_ranker` 切换入口；当存在 JSON 模型权重文件时可直接加载，否则会安全回退到 `weighted_ranker` 并在 debug 响应里标记 `ltr_fallback_used`。
* 已新增 `backend/app/services/recommendation_explainer.py`，统一生成 `feature_summary`、`feature_highlights` 和排序解释文本，使公开调试接口与后台调试接口能共享相同的解释口径。
* 已把 `backend/app/services/recommendation_pipeline.py` 从“召回后直接做 diversity”改成“召回 -> 特征构建 -> ranker -> 业务重排”的 Phase 9 流水线，并在 `RecommendationPipelineRun` 中新增 `active_ranker`、`ranker_model_version` 和 `ltr_fallback_used`。
* 已把 `backend/app/api/v1/products.py` 扩展为同时支持原有 `/api/v1/products/recommendations` 和新的 `/api/v1/recommendations` 别名；当 `debug=true` 时，公开接口会返回 `ranking_features`、`feature_summary`、`feature_highlights`、`score_breakdown` 和 `ranker_name`。
* 已把 `backend/app/api/v1/admin_recommendations.py` 扩展成完整排序调试视图；每个候选除了召回通道，还会返回排序特征、打分拆解和当前 ranker 版本。
* 已新增 `backend/tests/test_ranking_features.py` 与 `backend/tests/test_ranker.py`，分别固定特征构建正确性和“排序不是简单按原始召回分走”的关键行为；同时更新了推荐 API 与后台 debug API 测试，保证新的 debug 字段被正式回归覆盖。
* 本地专项测试全部通过，后端全量测试结果提升为 `134 passed`。
* 真实 Compose 环境验证中，`docker compose exec -T api python -m backend.scripts.reindex_embeddings` 返回 `indexed=20 skipped=0 model=BAAI/bge-small-zh-v1.5`；`docker compose exec -T api python backend/scripts/build_collaborative_index.py` 返回 `indexed_users=4 qdrant_points=4 item_nodes=2`，说明排序层依赖的向量与协同过滤数据都已重建到最新代码。
* 同一真实环境下，用户 `phase8-cf-b@example.com` 请求 `/api/v1/recommendations?slot=home&debug=true` 后，`pipeline.active_ranker=weighted_ranker`、`ranker_model_version=weighted-ranker-v1`、`degraded_to_baseline=false`；Top1 推荐仍为 `宋风褙子套装`，并且公开响应里能看到 `feature_summary` 的 `recall/interest/quality/business` 四组摘要以及 `score_breakdown.final_score=1.109793`。
* 后台 `/api/v1/admin/recommendations/debug?email=phase8-cf-b@example.com&limit=5` 也返回了相同的 `weighted_ranker` 和分解明细；Top1 候选同时带有 `content_profile`、`sparse_interest`、`related_products`、`collaborative_user`、`item_cooccurrence`、`trending` 和 `new_arrival` 七条召回来源，说明当前最终排序已明确建立在多路召回之上，而不是简单按单一相似度分排序。

交接提醒：

* 当前 `ltr_ranker` 只完成了模型加载接口和回退机制，默认仍会使用 `weighted_ranker`；后续如果进入 Phase 10 的离线评估与训练，优先补 `recommendation_request_log` 等日志表，再生成真实 LTR 训练样本。
* `ranking_features.py` 里部分业务特征仍是基于现有表结构推导出的启发式近似值，例如后台精选和 ColBERT 对齐分；如果后续新增了更明确的数据源，应直接替换这些推导逻辑，而不是再新增一套并行特征。
* 下一阶段应进入 Phase 10 的日志、离线评估和性能压测，把现在的多路召回与排序结果转化成可量化指标，而不是只停留在 debug 可解释层。

### 同日继续推进记录（四十六）

已继续完成：

* Recommendation Upgrade Phase 10：补齐日志、离线评估与性能压测

新增与修改：

* `backend/app/models/recommendation_analytics.py`
* `backend/alembic/versions/20260424_12_recommendation_logging.py`
* `backend/app/models/__init__.py`
* `backend/app/services/recommendation_logging.py`
* `backend/app/api/v1/products.py`
* `backend/app/api/v1/search.py`
* `backend/app/api/v1/cart.py`
* `backend/app/api/v1/orders.py`
* `backend/scripts/generate_synthetic_catalog.py`
* `backend/scripts/evaluate_recommendations.py`
* `backend/scripts/benchmark_recommendations.py`
* `backend/tests/api/test_recommendation_logging.py`
* `docs/recommendation_evaluation.md`
* `docs/performance_benchmark.md`
* `memory-bank/progress.md`
* `memory-bank/architecture.md`

验证命令：

* `./.venv/bin/python -m ruff check backend/app/models/recommendation_analytics.py backend/app/models/__init__.py backend/app/services/recommendation_logging.py backend/app/api/v1/products.py backend/app/api/v1/search.py backend/app/api/v1/cart.py backend/app/api/v1/orders.py backend/alembic/versions/20260424_12_recommendation_logging.py backend/tests/api/test_recommendation_logging.py backend/scripts/generate_synthetic_catalog.py backend/scripts/evaluate_recommendations.py backend/scripts/benchmark_recommendations.py`
* `./.venv/bin/python -m pytest backend/tests/api/test_recommendation_logging.py -q`
* `DATABASE_URL=sqlite:////tmp/shiyige_phase10_eval2.db QDRANT_URL=http://127.0.0.1:6333 QDRANT_COLLECTION_PRODUCTS=shiyige_phase10_eval2_products QDRANT_COLLECTION_CF=shiyige_phase10_eval2_cf ./.venv/bin/python backend/scripts/evaluate_recommendations.py --scenario all`
* `DATABASE_URL=sqlite:////tmp/shiyige_phase10_bench_full3.db QDRANT_URL=http://127.0.0.1:6333 QDRANT_COLLECTION_PRODUCTS=shiyige_phase10_bench_full3_products QDRANT_COLLECTION_CF=shiyige_phase10_bench_full3_cf ./.venv/bin/python backend/scripts/benchmark_recommendations.py --products 10000 --users 1000`
* `./.venv/bin/python -m pytest backend/tests -q`

结果：

* 已新增 `recommendation_request_log`、`recommendation_impression_log`、`recommendation_click_log`、`recommendation_conversion_log`、`search_request_log` 和 `search_result_log` 六张日志表，并通过迁移 `20260424_12_recommendation_logging.py` 接入正式 schema。
* 已新增 `backend/app/services/recommendation_logging.py`，把推荐请求、曝光、详情点击、加购、下单、支付以及搜索请求与结果的落库逻辑统一收敛到单一服务层；接口层不再自己拼装日志记录。
* 已把 `backend/app/api/v1/products.py`、`backend/app/api/v1/search.py`、`backend/app/api/v1/cart.py` 和 `backend/app/api/v1/orders.py` 接到新日志服务上，形成“推荐曝光 -> 商品点击 -> 加购 -> 下单 -> 支付”的完整归因链。
* 已新增 `backend/tests/api/test_recommendation_logging.py`，覆盖推荐请求/曝光日志、点击与转化日志，以及关键词/语义搜索日志；专项测试结果为 `3 passed`。
* 已新增 `backend/scripts/evaluate_recommendations.py`，可生成 `docs/recommendation_evaluation.md`；当前对比表已覆盖 `baseline`、`dense_only`、`dense_sparse`、`dense_sparse_colbert`、`multi_recall_weighted`、`multi_recall_ltr` 和 `multi_recall_ltr_diversity` 七种方案。
* 离线评估报告显示：在当前三组评测场景下，`multi_recall_ltr` 的 `Precision@5=0.6`、`Recall@5=1.0`、`NDCG@5=1.0`，优于 `baseline` 的 `0.4667 / 0.7778 / 0.6763`；而 `multi_recall_ltr_diversity` 的多样性提升到 `0.8333`，但精确率回落到 `0.4`，说明探索/多样性规则已经开始显著影响排序收益。
* 已新增 `backend/scripts/generate_synthetic_catalog.py`，支持直接从仓库根目录执行 `python backend/scripts/generate_synthetic_catalog.py --products ...` 扩容商品集，并固定只从非 synthetic 模板商品复制，避免后续数据越滚越脏。
* 已新增 `backend/scripts/benchmark_recommendations.py`，可输出 `p50/p95/p99 latency`、`QPS`、`error_rate` 和平均候选数量，并把结果写入 `docs/performance_benchmark.md`。
* 为了让 `10000` 商品级别的合成压测在当前仓库里可稳定完成，压测脚本显式切到了 `local_hash` dense/sparse/colbert provider；报告中已把该 embedding 模式写明，避免后续开发者误把这份报告当成 FastEmbed 编码成本。
* 当前 10k 商品 / 1k 用户压测结果显示：`search_keyword` 的 `p95=3214.436ms`，`search_semantic` 的 `p95=5484.978ms`，`recommend_home` 的 `p95=38565.256ms`，`related_products` 的 `p95=65666.73ms`；`sync_products_to_qdrant(mode=full)` 全量重建耗时 `230869.141ms`。这说明 Phase 10 已经能量化证明系统行为，但也明确暴露出首页推荐和相似商品接口在 10k 规模下仍然过慢。
* 后端全量测试结果为 `137 passed`；结合专项测试、离线评估脚本和正式压测脚本，Phase 10 的代码与文档已经形成完整交付物。

交接提醒：

* `docs/performance_benchmark.md` 当前是“合成数据 + local_hash embedding”基准，不是 FastEmbed 真实编码成本报告；如果后续要展示模型真实推理时延，需要额外跑一版保留 `fastembed_*` provider 的报告。
* `backend/app/api/v1/products.py` 的 `related_products` 仍沿用全量 SQL embedding 相似度计算，10k 规模下已经成为明显瓶颈；如果继续推进 Phase 11 之前的性能优化，应优先把相似商品接口接到 Qdrant 或缓存层。
* `recommend_home` 在 10k 商品压测下 `p95` 已接近 39 秒，说明多路召回和排序层虽然功能完整，但候选构建与画像计算还没有做缓存分层；后续如果要进入前后台展示改造，建议先补 profile cache / candidate cache，再继续放大演示数据。

### 同日继续推进记录（四十七）

已继续完成：

* Recommendation Upgrade Phase 11：前台和后台展示改造

新增与修改：

* `backend/app/services/recommendation_admin.py`
* `backend/app/api/v1/admin_dashboard.py`
* `backend/app/api/v1/admin_recommendations.py`
* `backend/app/api/v1/products.py`
* `backend/app/api/v1/search.py`
* `backend/app/services/qdrant_client.py`
* `backend/app/services/vector_store.py`
* `backend/app/tasks/embedding_tasks.py`
* `backend/tests/api/conftest.py`
* `backend/tests/api/test_admin_dashboard.py`
* `backend/tests/api/test_admin_recommendation_debug.py`
* `backend/tests/api/test_recommendations.py`
* `backend/tests/api/test_search_keyword.py`
* `backend/tests/api/test_search_semantic.py`
* `backend/tests/tasks/test_embedding_tasks.py`
* `front/cart.html`
* `front/checkout.html`
* `front/css/style.css`
* `front/js/main.js`
* `front/js/home-page.js`
* `front/js/category-page.js`
* `front/js/product.js`
* `front/js/cart.js`
* `front/js/checkout.js`
* `admin/index.html`
* `admin/reindex.html`
* `admin/recommendation-debug.html`
* `admin/recommendation-config.html`
* `admin/js/app.js`
* `admin/css/admin.css`
* `tests/e2e/conftest.py`
* `tests/e2e/test_admin_basic.py`
* `tests/e2e/test_recommendation_ui.py`
* `tests/e2e/test_cart_flow.py`
* `tests/e2e/test_checkout_flow.py`
* `tests/e2e/test_full_demo_flow.py`
* `memory-bank/progress.md`
* `memory-bank/architecture.md`

验证命令：

* `docker compose up -d`
* `./.venv/bin/python -m ruff check backend/app/tasks/embedding_tasks.py backend/tests/tasks/test_embedding_tasks.py backend/app/api/v1/admin_dashboard.py backend/app/api/v1/admin_recommendations.py backend/app/api/v1/products.py backend/app/api/v1/search.py backend/app/services/recommendation_admin.py backend/app/services/qdrant_client.py backend/app/services/vector_store.py backend/tests/api/test_admin_dashboard.py backend/tests/api/test_admin_recommendation_debug.py backend/tests/api/test_recommendations.py backend/tests/api/test_search_keyword.py backend/tests/api/test_search_semantic.py backend/tests/api/conftest.py tests/e2e/conftest.py`
* `./.venv/bin/python -m pytest backend/tests/tasks/test_embedding_tasks.py backend/tests/api/test_admin_dashboard.py backend/tests/api/test_admin_recommendation_debug.py backend/tests/api/test_recommendations.py backend/tests/api/test_search_keyword.py backend/tests/api/test_search_semantic.py -q`
* `./.venv/bin/python -m pytest tests/e2e/test_admin_basic.py tests/e2e/test_recommendation_ui.py tests/e2e/test_cart_flow.py tests/e2e/test_checkout_flow.py tests/e2e/test_full_demo_flow.py -q`

结果：

* 已新增 `backend/app/services/recommendation_admin.py`，把推荐效果指标、搜索指标、Qdrant 运行状态、索引摘要和实验方案聚合成后台首页可直接消费的单一服务输出。
* 已把 `backend/app/api/v1/admin_dashboard.py` 扩展成包含 `runtime`、`vector_index`、`recommendation_metrics`、`search_metrics` 和 `experiments` 的完整答辩看板接口；`backend/app/api/v1/admin_recommendations.py` 同时支持通过 `user_id` 或 `email` 调试用户推荐，并新增实验配置读取接口。
* 已把 `backend/app/api/v1/products.py` 和 `backend/app/api/v1/search.py` 的响应结构升级为前台展示友好的形态：推荐结果统一带 `source_type/source_label`，搜索结果统一带 `reason`、`search_mode`、`score` 和解释标签，前台不再需要硬编码同一句推荐文案。
* 已把 `front/js/main.js` 提升为推荐展示共享层，提供来源徽章、搜索解释标签、推荐证据块和统一商品卡片渲染；首页、搜索页、商品详情页、购物车页和订单完成弹窗都已改为复用这套展示组件。
* 已新增购物车推荐区和下单成功推荐区，`front/js/cart.js` 会优先基于购物车商品拉取相似商品，失败时回退到个性化 `slot=cart`；`front/js/checkout.js` 会优先基于下单商品拉取关联推荐，失败时回退到 `slot=order_complete`。
* 后台静态站点已从“最小管理壳”升级到完整展示层：`admin/index.html` 可直接展示推荐 KPI、搜索指标和 Qdrant 状态，`admin/reindex.html` 可展示向量索引健康度并支持 full/retry_failed，`admin/recommendation-debug.html` 新增 `user_id` 调试入口，`admin/recommendation-config.html` 可直观看到 `baseline / hybrid / hybrid_rerank / full_pipeline` 实验方案。
* 为减少后台和前台页面反复探测 Qdrant 带来的卡顿，`backend/app/services/qdrant_client.py` 新增了短 TTL 连接状态缓存，`backend/app/services/vector_store.py` 也避免在同一轮运行时判定里重复发起状态探测。
* 在整体验证中稳定复现了一个真实缺陷：登录后首页会自动请求个性化推荐，如果此时测试代码再并发请求 `/api/v1/products/recommendations`，旧版 `upsert_product_embedding()` 会因并发首次写入同一 `product_id` 而触发 `UNIQUE constraint failed: product_embedding.product_id`。
* 已把 `backend/app/tasks/embedding_tasks.py` 修成“显式按 `product_id` 回查现有 embedding + 数据库原子 upsert”的幂等写入路径，并新增 `backend/tests/tasks/test_embedding_tasks.py` 的跨 session 回归用例，确认 stale relation 和并发首写都不会再打穿推荐接口。
* 最终验证结果为：推荐相关后端回归 `12 passed`，关键前后台 e2e 组合验证 `5 passed`；其中 `tests/e2e/test_full_demo_flow.py` 已在与其他 e2e 同批执行时稳定通过，说明 Phase 11 的展示层和并发幂等修复都已落稳。

交接提醒：

* 首页登录后会自动请求 `/api/v1/products/recommendations?slot=home&debug=true`；后续如果继续改商品 embedding 初始化、推荐缓存或首页加载顺序，必须保持 `backend/app/tasks/embedding_tasks.py` 的并发幂等语义，否则很容易在真实浏览器和 e2e 里再次触发双请求竞争。
* `admin/reindex.html` 当前在 Qdrant 不可用或 collection 尚未就绪时，会对 full rebuild 自动回退到旧的 `/api/v1/admin/reindex/products`；这个兼容分支是为了保证本地和答辩环境都能演示，不要在未替换验证方案前删掉。
* `front/index.html` 在本地工作区里有用户自己的未提交修改，本轮 Phase 11 提交不会携带它；同样，`memory-bank/shiyige_recommendation_upgrade_plan.md` 仍作为未跟踪的计划输入保留，不应被提交进代码历史。

### 同日继续推进记录（四十八）

已继续完成：

* Recommendation Upgrade Phase 12：补齐答辩文档、最终验收与最终收尾

新增与修改：

* `docs/vector_database_design.md`
* `docs/recommendation_pipeline.md`
* `docs/search_pipeline.md`
* `docs/recommendation_evaluation.md`
* `docs/performance_benchmark.md`
* `docs/defense_script.md`
* `backend/app/services/qdrant_client.py`
* `backend/app/tasks/qdrant_index_tasks.py`
* `backend/tests/unit/test_settings.py`
* `memory-bank/progress.md`
* `memory-bank/architecture.md`

验证命令：

* `docker compose down -v --remove-orphans`
* `docker compose up -d`
* `curl -s http://127.0.0.1:6333/collections`
* `curl -s http://127.0.0.1/api/v1/health`
* `DATABASE_URL=postgresql+psycopg://shiyige:shiyige@127.0.0.1:5432/shiyige QDRANT_URL=http://127.0.0.1:6333 ./.venv/bin/python -m backend.scripts.reindex_products_to_qdrant --mode full`
* `DATABASE_URL=postgresql+psycopg://shiyige:shiyige@127.0.0.1:5432/shiyige QDRANT_URL=http://127.0.0.1:6333 ./.venv/bin/python backend/scripts/build_collaborative_index.py`
* `curl -s http://127.0.0.1/api/v1/health`
* `DATABASE_URL=postgresql+psycopg://shiyige:shiyige@127.0.0.1:5432/shiyige QDRANT_URL=http://127.0.0.1:6333 ./.venv/bin/python backend/scripts/evaluate_recommendations.py --scenario all`
* `DATABASE_URL=sqlite:////tmp/shiyige_phase12_bench_100.db QDRANT_URL=http://127.0.0.1:6333 QDRANT_COLLECTION_PRODUCTS=shiyige_phase12_bench_100_products QDRANT_COLLECTION_CF=shiyige_phase12_bench_100_cf ./.venv/bin/python backend/scripts/benchmark_recommendations.py --products 100 --users 50 --requests 20`
* `DATABASE_URL=sqlite:////tmp/shiyige_phase12_bench_1000.db QDRANT_URL=http://127.0.0.1:6333 QDRANT_COLLECTION_PRODUCTS=shiyige_phase12_bench_1000_products QDRANT_COLLECTION_CF=shiyige_phase12_bench_1000_cf ./.venv/bin/python backend/scripts/benchmark_recommendations.py --products 1000 --users 200 --requests 40`
* `DATABASE_URL=postgresql+psycopg://shiyige:shiyige@127.0.0.1:5432/shiyige QDRANT_URL=http://127.0.0.1:6333 ./.venv/bin/python backend/scripts/benchmark_recommendations.py --products 10000 --users 1000`
* `./.venv/bin/python -m ruff check backend/app/services/qdrant_client.py backend/app/tasks/qdrant_index_tasks.py backend/tests/unit/test_settings.py`
* `./.venv/bin/python -m pytest backend/tests/test_hybrid_search.py backend/tests/test_product_qdrant_indexing.py backend/tests/unit/test_settings.py -q`
* `./.venv/bin/python -m pytest backend/tests -q`
* `./.venv/bin/python -m pytest tests/e2e/test_full_demo_flow.py -q`

结果：

* 已重写 `docs/vector_database_design.md`、`docs/recommendation_pipeline.md`、`docs/search_pipeline.md`，把“旧版本问题 vs 升级后方案”、架构图、数据流、算法模块、运行时降级和答辩表述统一整理成可直接展示的文档，而不是只保留脚本原始输出。
* 已新增 `docs/defense_script.md`，把开场讲稿、演示顺序、老师高频追问以及“不是只算余弦 / 为什么不是 pgvector / 为什么要向量数据库 / 推荐系统完整性”这些回答固定成统一口径。
* 已把 `docs/recommendation_evaluation.md` 升级为正式评估报告；当前保留 3 个场景、7 组模式对比和指标解释，其中 `multi_recall_ltr` 达到 `P@5=0.6`、`R@5=1.0`、`NDCG@5=1.0`，明显优于 `baseline` 的 `0.4667 / 0.7778 / 0.6763`。
* 已把 `docs/performance_benchmark.md` 升级为可答辩版压测报告；当前明确写入了 100、1000、10000 商品规模的真实结果，并对 100000 规模给出容量推演。最新 10k 结果为：`search_keyword p95=2298.531ms`、`search_semantic p95=4030.115ms`、`recommend_home p95=38891.419ms`、`related_products p95=90946.377ms`。
* Compose 重建后，首次 `curl http://127.0.0.1/api/v1/health` 返回 `degraded_to_baseline=true` 和 `qdrant_error=Qdrant product collection has no indexed points`；在商品索引重建和协同过滤构建完成后，同一健康检查已切换为 `active_search_backend=qdrant_hybrid`、`active_recommendation_backend=multi_recall`，证明最终验收链路完整有效。
* 最终验收中发现一个真实运行时问题：`backend/app/services/qdrant_client.py` 的短 TTL 状态缓存只按 URL 缓存，不会在 collection 刚创建或 point 刚写入后立即失效，导致后续几秒内 runtime marker 可能误判“collection 不存在”或“没有 indexed points”，从而错误退回 baseline。
* 已新增 `invalidate_qdrant_connection_status(...)` 并在 `backend/app/tasks/qdrant_index_tasks.py` 的 full sync / delete 成功提交后主动失效缓存；这修复了全量测试里暴露出的两个问题：Hybrid search 刚建索引后仍走 baseline，以及失败重试后 `qdrant_point_count` 被错误读成 `0`。
* 同时修正了 `backend/tests/unit/test_settings.py` 对 `QDRANT_URL` 环境变量的隔离，避免在全量测试时被其他测试模块的 `os.environ.setdefault("QDRANT_URL", "http://127.0.0.1:6333")` 污染。
* 最终回归结果为：Qdrant 集合查询、Nginx 健康检查、商品全量重建、协同过滤构建、离线评估、100/1000/10000 压测、后端全量测试 `141 passed`、完整 e2e `test_full_demo_flow` 全部通过。

交接提醒：

* 第 12 步最终验收里，本地默认 `backend/dev.db` 暴露出 schema 落后于当前 Alembic 的问题，所以本轮把重建脚本切到了 Compose PostgreSQL：`DATABASE_URL=postgresql+psycopg://shiyige:shiyige@127.0.0.1:5432/shiyige`。后续如果继续用仓库根目录脚本做正式验收，优先沿用 Compose PostgreSQL，而不要假设本地 SQLite 一定已迁移到最新 schema。
* `docs/performance_benchmark.md` 里的所有结果都明确基于 `local_hash` provider，用来隔离检索和排序开销；如果后续要展示真实 embedding 模型推理耗时，需要额外单独跑一版保留 `fastembed_*` provider 的报告。
* 当前 10k 结果已经证明 `related_products` 是最急需优化的旧边界；如果后续继续推进 100000 商品规模演示，应优先把该接口迁到 ANN-only 路径，并补用户画像/候选缓存层。

### 同日继续推进记录（四十九）

已继续完成：

* Recommendation Upgrade Phase 13：对齐最终接口规划

新增与修改：

* `backend/app/services/hybrid_search.py`
* `backend/app/services/vector_search.py`
* `backend/app/api/v1/search.py`
* `backend/app/api/v1/products.py`
* `backend/app/api/v1/admin_vector_index.py`
* `backend/app/api/v1/admin_recommendations.py`
* `backend/app/api/v1/router.py`
* `backend/tests/api/test_search_keyword.py`
* `backend/tests/api/test_search_semantic.py`
* `backend/tests/api/test_recommendations.py`
* `backend/tests/api/test_related_products.py`
* `backend/tests/api/test_admin_vector_index.py`
* `backend/tests/api/test_admin_recommendation_debug.py`
* `memory-bank/progress.md`
* `memory-bank/architecture.md`

验证命令：

* `./.venv/bin/python -m ruff check backend/app/api/v1/search.py backend/app/api/v1/products.py backend/app/api/v1/admin_vector_index.py backend/app/api/v1/admin_recommendations.py backend/app/api/v1/router.py backend/app/services/hybrid_search.py backend/app/services/vector_search.py backend/tests/api/test_search_keyword.py backend/tests/api/test_search_semantic.py backend/tests/api/test_recommendations.py backend/tests/api/test_related_products.py backend/tests/api/test_admin_vector_index.py backend/tests/api/test_admin_recommendation_debug.py`
* `./.venv/bin/python -m pytest backend/tests/api/test_search_keyword.py backend/tests/api/test_search_semantic.py backend/tests/api/test_recommendations.py backend/tests/api/test_related_products.py backend/tests/api/test_admin_vector_index.py backend/tests/api/test_admin_recommendation_debug.py -q`

结果：

* 已在 `backend/app/api/v1/search.py` 新增 `GET /api/v1/products/search`，把第 13.1 节要求的 `final_score`、`dense_score`、`sparse_score`、`rerank_score`、`matched_terms`、`reason` 和 `pipeline_version` 正式暴露为公开接口字段，同时保留原有 `/api/v1/search` 与 `/api/v1/search/semantic` 兼容入口。
* 已把 `backend/app/services/hybrid_search.py` 与 `backend/app/services/vector_search.py` 的中间打分链路补成显式元数据透传，Qdrant hybrid 路径现在不会在 API 层丢掉 dense/sparse/ColBERT 分数；baseline 语义搜索也会返回 `matched_terms`、`dense_score` 和独立 `pipeline_version`。
* 已把 `backend/app/api/v1/products.py` 的推荐接口扩成第 13.2 节要求的形态：首页推荐现在默认返回 `recall_channels`、`final_score`、`reason` 和 `is_exploration`；当 `debug=true` 时，还会同时返回 `rank_features` 与现有 `ranking_features`，兼顾新协议和旧前端兼容性。
* 已把相似商品接口补成第 13.3 节要求的来源拆解结构：`GET /api/v1/products/{product_id}/related` 现在会返回 `dense_similarity`、`co_view_co_buy`、`cultural_match`、完整 `source_breakdown` 和 `diversity_result`，而不是只给一个总分和一句理由。
* 已在 `backend/app/api/v1/admin_vector_index.py` 增加 `GET /api/v1/admin/vector-index/status`、`POST /api/v1/admin/vector-index/rebuild` 和 `POST /api/v1/admin/vector-index/products/{product_id}/reindex`；在 `backend/app/api/v1/admin_recommendations.py` 增加 `GET /api/v1/admin/recommendation/debug` 与 `GET /api/v1/admin/recommendation/metrics`，从而与第 13.4 节建议接口保持一致，同时保留旧的 plural 路径。
* 在联调中暴露出一个真实路由问题：`/api/v1/products/search` 最初被 `/api/v1/products/{product_id}` 抢先匹配并返回 `422`。已通过调整 `backend/app/api/v1/router.py` 的装载顺序修复，保证固定路径优先于参数路径注册。
* 本轮专项回归结果为 `14 passed`，覆盖了搜索新别名、推荐字段扩展、相似商品来源拆解、后台索引别名接口和后台推荐 metrics/debug 别名接口，说明第 13 节的公开协议已经稳定可用。

交接提醒：

* `GET /api/v1/products/search` 是新增的最终展示型搜索接口，后续如果再改搜索协议，优先保持它的字段口径稳定，不要只改旧的 `/api/v1/search` 或 `/api/v1/search/semantic`。
* 当前 `/api/v1/products/{product_id}/related` 的来源拆解已经齐全，但底层仍以 baseline 相似度计算为主，性能优化应留到后续第 15 节单独推进，不要在未补测试前直接改成另一套不可解释返回。
* 新增的 admin singular 别名路径已经进入测试覆盖；后续如果重构后台 router，必须同时保住 plural 和 singular 两套入口，否则会把文档接口和现有后台页面联调一起打断。

### 同日继续推进记录（五十）

已继续完成：

* Recommendation Upgrade Phase 14：落实排序公式建议与 LTR 回退阈值

新增与修改：

* `backend/app/core/config.py`
* `backend/app/services/ltr_ranker.py`
* `backend/app/services/ranker.py`
* `backend/tests/unit/test_settings.py`
* `backend/tests/test_ranker.py`
* `docs/ranking_design.md`
* `memory-bank/progress.md`
* `memory-bank/architecture.md`

验证命令：

* `./.venv/bin/python -m ruff check backend/app/core/config.py backend/app/services/ltr_ranker.py backend/app/services/ranker.py backend/tests/unit/test_settings.py backend/tests/test_ranker.py docs/ranking_design.md`
* `./.venv/bin/python -m pytest backend/tests/unit/test_settings.py backend/tests/test_ranker.py backend/tests/test_recommendation_pipeline.py backend/tests/api/test_recommendations.py backend/tests/api/test_admin_recommendation_debug.py -q`

结果：

* 已在 `backend/app/services/ranker.py` 把 `weighted_ranker` 改成 8 个分组权重结构，显式对齐第 14.1 节建议：`hybrid_retrieval_score=0.25`、`colbert_rerank_score=0.20`、`collaborative_group_score=0.15`、`user_interest_score=0.15`、`product_quality_score=0.10`、`trend_freshness_score=0.05`、`business_constraints_score=0.05`、`diversity_exploration_score=0.05`。
* 旧的 `recall_score / interest_score / quality_score / business_total / final_score` 兼容字段仍然保留，但 `score_breakdown` 现在会同时输出新的分组原始分与 contribution，答辩和后台调试都能直接对应到排序公式，而不是只能看到三段粗粒度分数。
* 已在 `backend/app/services/ranker.py` 前移一个更强的业务约束：未上架或无库存候选不会再只靠惩罚分“尽量排后”，而是直接在 ranker 阶段剔除。专项回归里正是这个调整修复了“无库存候选仍可能进入 TopN”的真实问题。
* 已在 `backend/app/core/config.py` 新增 `recommendation_ltr_min_training_samples`，并在 `backend/app/services/ltr_ranker.py` 增加 `training_sample_count` 阈值判断；当 JSON LTR 模型声明的训练样本量低于阈值时，系统现在会自动回退到 `weighted_ranker`，符合第 14.2 节的上线策略。
* `backend/app/services/ltr_ranker.py` 同时新增了未来离线训练要用的 `LTR_EVENT_LABEL_WEIGHTS` 预留常量，已把 `impression_no_click / click / add_to_cart / pay_order` 的弱负样本、弱正样本、中正样本和强正样本权重固定下来，避免后续训练脚本再另起一套口径。
* 已更新 `docs/ranking_design.md`，把新的 8 组权重、LTR 最小样本阈值回退规则和保留训练标签写进正式文档，不再只在代码里隐式存在。
* 本轮专项回归结果为 `14 passed`，覆盖配置默认值、weighted ranker 行为、LTR 模型缺失回退、LTR 样本阈值回退、推荐流水线和推荐调试 API，说明第 14 节改动已经稳定落地。

交接提醒：

* 当前 `weighted_ranker` 已经具备计划里的 8 组显式权重，但 `WEIGHTED_RANKER_MODEL_VERSION` 仍保留旧值 `weighted-ranker-v1` 以避免打穿现有日志与页面联调；如果后续要正式升级模型版本号，需要同步评估脚本和答辩材料中的口径。
* `recommendation_ltr_min_training_samples` 只在模型 JSON 明确写入 `training_sample_count` 时才会生效；这保证旧模型文件仍可兼容，但也意味着后续训练脚本若想启用阈值保护，必须显式写出该元数据。
* 现在无库存候选会在 ranker 阶段被跳过；后续如果新增“预售可推荐”之类业务模式，不要直接回退成只靠惩罚分，而应显式扩展 `business_rules` 和 ranker 过滤条件。

### 同日继续推进记录（五十一）

已继续完成：

* Recommendation Upgrade Phase 15：落实缓存与相似商品性能优化

新增与修改：

* `backend/app/services/cache.py`
* `backend/app/services/recommendations.py`
* `backend/app/services/vector_search.py`
* `backend/app/api/v1/products.py`
* `backend/app/api/v1/search.py`
* `backend/tests/integration/test_cache_behavior.py`
* `backend/tests/test_hybrid_search.py`
* `memory-bank/progress.md`
* `memory-bank/architecture.md`

验证命令：

* `./.venv/bin/python -m ruff check backend/app/services/cache.py backend/app/services/recommendations.py backend/app/api/v1/products.py backend/app/api/v1/search.py backend/app/services/vector_search.py backend/tests/integration/test_cache_behavior.py backend/tests/test_hybrid_search.py`
* `./.venv/bin/python -m pytest backend/tests/integration/test_cache_behavior.py backend/tests/test_hybrid_search.py backend/tests/api/test_related_products.py backend/tests/api/test_recommendations.py backend/tests/api/test_search_semantic.py -q`

结果：

* 已在 `backend/app/services/cache.py` 新增 `SEMANTIC_SEARCH_CACHE_TTL`、`RELATED_PRODUCTS_CACHE_TTL`、`USER_PROFILE_CACHE_TTL`，并把推荐缓存键扩成 `user_id + slot + backend + limit`，修复了旧实现里 `home/cart/order_complete` 可能共用同一条缓存的结构性问题。
* 已在 `backend/app/services/cache.py` 把所有 cache key 加上基于 `DATABASE_URL` 的命名空间前缀。这个改动源自本轮真实暴露的问题：测试进程共用同一个 Redis 时，新增的用户画像缓存会把不同数据库实例里相同 `user_id` 的画像串起来；现在这个跨环境污染已经被隔离。
* 已在 `backend/app/services/recommendations.py` 给 `UserInterestProfile` 增加可序列化缓存快照，`build_user_interest_profile()` 现在会优先读取缓存命中的画像，并在用户行为导致 `invalidate_recommendation_cache_for_user()` 时一起失效，从而落实第 15.1.7 节里“缓存最终结果和中间用户画像”的要求。
* 已在 `backend/app/api/v1/search.py` 给语义搜索和最终搜索别名接口接入结果缓存；相同 query + filter + backend 的请求在非 debug 模式下会直接命中缓存，同时仍然保留行为日志与搜索日志落库，避免性能优化把评估链路打断。
* 已在 `backend/app/api/v1/products.py` 给相关推荐接入缓存，并把推荐列表缓存键修成 slot-aware 结构；专项测试已经验证 `home` 与 `cart` 会落成不同 cache key，不再相互覆盖。
* 已在 `backend/app/services/vector_search.py` 增加 `find_related_products_with_qdrant()`，当向量库 ready 时，`/api/v1/products/{product_id}/related` 会优先走 Qdrant dense 召回，再补 co-view/co-buy 和文化匹配分，最后保留已有的 `source_breakdown` 与 `diversity_result` 协议；Qdrant 不可用时仍自动回退 baseline。
* 已扩展 `backend/tests/integration/test_cache_behavior.py`，现在会同时验证语义搜索缓存、推荐缓存 slot 隔离、相关推荐缓存以及用户画像缓存命中行为；并在 `backend/tests/test_hybrid_search.py` 新增了 `qdrant_related` 路径的回归测试。
* 本轮专项回归结果为 `12 passed`，说明第 15 节的缓存层、Qdrant 相似商品优化和命名空间隔离都已经稳定落地。

交接提醒：

* 现在所有 cache key 都带数据库命名空间，这能避免本地多测试库或多环境共用 Redis 时互相污染；后续如果单独写脚本直接读 Redis，请不要再假设 key 以 `products:` 或 `search:` 开头。
* `find_related_products()` 现在是“Qdrant 优先，baseline 回退”的双路径实现；如果后续继续优化 10k/100k 规模，不要再把协议层改掉，直接继续在 `find_related_products_with_qdrant()` 内部扩大候选控制和缓存策略即可。
* 推荐缓存键已经按 slot 拆开，`invalidate_recommendation_cache_for_user()` 也同步删除旧格式与新格式 key；后续若再新增推荐展示位，记得把新 slot 加进 `RECOMMENDATION_CACHE_SLOTS`，否则行为发生后该展示位的缓存不会被及时清掉。

### 同日继续推进记录（五十二）

已继续完成：

* Recommendation Upgrade Phase 16：补齐答辩 FAQ 并完成最终回归

新增与修改：

* `docs/defense_script.md`
* `memory-bank/progress.md`
* `memory-bank/architecture.md`

验证命令：

* `rg -n "怎么证明推荐更好|如何解决冷启动" docs/defense_script.md`
* `./.venv/bin/python -m pytest backend/tests -q`
* `./.venv/bin/python -m pytest tests/e2e/test_full_demo_flow.py -q`

结果：

* 已在 `docs/defense_script.md` 补齐第 16 节计划里缺失的两条核心 FAQ：一条回答“怎么证明推荐更好”，明确引用 `Precision@K / Recall@K / NDCG@K / Coverage / Diversity / latency` 这些对比指标；另一条回答“如何解决冷启动”，把 `cold_start` 通道、热门/新品/节令混排和新商品探索位写成统一口径。
* 当前答辩文档里的高频问题已经覆盖：是不是只算余弦、为什么不是 pgvector、推荐系统完整性、怎么证明更好、如何解决冷启动；与 `memory-bank/shiyige_recommendation_upgrade_plan.md` 第 16 节的问答目标已经对齐。
* 本轮把 FAQ 补齐后，额外执行了一轮更宽的最终回归，而不是只做文档 grep：后端全量测试结果为 `147 passed`，完整 e2e `tests/e2e/test_full_demo_flow.py` 结果为 `1 passed`，说明前面第 13、14、15 节连续改动后，系统整体仍然稳定。

交接提醒：

* `docs/defense_script.md` 现在已经不只是讲稿，而是推荐系统答辩 FAQ 的统一事实来源；后续如果评估指标、排序器版本或冷启动策略继续变动，优先先改这份文档，再去改其他展示材料，避免口径漂移。
* 第 16 步的最终回归已经把当前代码状态重新跑到 `backend/tests` 全量和 `test_full_demo_flow`，因此后续如果继续推进第 17 节的增强版本，应从这个提交点往后迭代，不要回退到更早的中间提交再做功能叠加。
