# 拾遗阁实施计划 v2

## 一、版本目标

本版本以**计算机设计大赛 Web 应用开发小类可交付作品**为目标，不追求大而全，优先保证：

1. 后端链路完整；
2. 前台主流程真实可用；
3. 推荐系统与向量检索具备可演示能力；
4. 可通过 Docker Compose 一键启动；
5. 答辩时可清楚解释技术路线与设计取舍。

本版的核心策略是：

**先完成真实后端与推荐闭环，再补文化内容与后台增强。**

---

## 二、已锁定技术决策

### 2.1 后端框架

固定采用：

* **FastAPI**
* **SQLAlchemy 2.x**
* **Alembic**
* **PostgreSQL**
* **pgvector**
* **Redis**
* **MinIO**
* **Docker Compose**

不改 Django，不拆微服务。

---

### 2.2 认证方案

固定采用：

**Access Token 放前端统一会话模块；Refresh Token 放 HttpOnly Cookie。**

具体约定：

* 登录成功后：

  * 后端返回 `access_token`
  * 后端写入 `refresh_token` 到 HttpOnly Cookie
* 前端仅通过 `session.js` 管理 `access_token`
* 所有业务页面只通过统一 API 模块请求数据
* 访问令牌过期后，由前端自动调用刷新接口
* 禁止在业务页面直接操作 token
* 禁止继续把用户、订单、购物车、会员等业务数据存进 `localStorage`

推荐实现细则：

* `access_token`：放 `sessionStorage`
* `refresh_token`：放 `HttpOnly + SameSite=Lax` Cookie
* 退出登录时同时清除前端 access token 和后端 refresh cookie

---

### 2.3 商品与 SKU 策略

固定采用：

**统一 SKU 模型，但第一版只支持 1~2 个规格维度。**

例如：

* 颜色
* 尺码

约定如下：

* 所有商品都允许存在 SKU
* 无复杂规格的商品也保留一个默认 SKU
* 库存按 SKU 维度管理
* 商品列表页显示“最低售价”
* 商品详情页根据选中的 SKU 动态展示价格与库存
* 第一版不实现复杂联动规格矩阵编辑器

---

### 2.4 库存策略

固定采用：

**支付成功后扣库存。**

理由：

* 实现更稳
* 更适合比赛工期
* 避免订单锁库存与超时释放带来的额外复杂度

相应约定：

* 创建订单时校验库存
* 支付时再次校验库存
* 支付成功才正式扣减库存
* 若支付时库存不足，则支付失败并返回明确错误
* 订单创建接口必须支持幂等

---

### 2.5 后台策略

固定采用：

**首轮后台使用 `admin/` 下的静态 HTML + JS + API 方案。**

后续可迁移 Vue 3，但不进入首轮范围。

当前后台最小目标：

* 登录页
* 仪表盘
* 商品管理
* 订单管理
* 推荐重建任务页

文章/文化内容管理在首轮降级。

---

### 2.6 向量模型策略

固定采用：

**首轮默认本地离线中文 embedding 模型。**

要求：

* 可说明来源
* 可本地运行
* 不依赖外部闭源在线服务
* 比赛答辩时可明确说明模型用途仅为向量表示

首轮只做：

* 商品向量
* 搜索查询向量
* 用户兴趣向量

文化文章向量可以后置，先不作为主依赖。

---

### 2.7 文化内容优先级

固定采用：

**文化内容降为后置增强项。**

当前只做最小支撑：

* 商品保留 `culture_summary`
* 数据库预留文化内容表
* 商品详情页可展示简短文化说明
* 暂不投入大量写作精力做长文章体系

也就是说：

**首轮不是“文化电商内容平台”，而是“带文化属性的智能推荐古风商品网站”。**

---

### 2.8 演示环境策略

固定采用：

**云服务器为正式演示环境，本地 Docker Compose 为兜底环境。**

要求：

* 本地能完整启动
* 云端能公网访问
* 两套环境使用同一套 Compose 和配置结构
* 答辩现场即使网络不稳定，也能本地演示

---

## 三、比赛版非目标范围

以下能力明确**不进入首轮主链路**：

* 收藏夹
* 第三方支付
* 优惠券/满减/复杂营销活动
* 即时聊天客服
* 社交分享裂变
* 多商户入驻
* 微服务拆分
* 大型 BI 报表系统
* 复杂文化文章运营系统
* Vue 版前台重构
* Vue 版后台重构
* 在线训练推荐模型平台

原则：

**凡是不能明显增强“后端闭环 + 推荐展示 + 比赛答辩”的能力，一律延后。**

---

## 四、统一工程约定

## 4.1 目录结构

```text
.
├── front/
├── admin/
├── backend/
│   ├── app/
│   ├── alembic/
│   ├── scripts/
│   ├── tests/
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   └── alembic.ini
├── docs/
├── tests/
│   └── e2e/
├── docker-compose.yml
└── nginx/
```

---

## 4.2 API 前缀

统一使用：

```text
/api/v1
```

---

## 4.3 统一响应结构

建议固定为：

```json
{
  "code": 0,
  "message": "ok",
  "data": {},
  "request_id": "uuid"
}
```

失败响应：

```json
{
  "code": 40001,
  "message": "stock not enough",
  "data": null,
  "request_id": "uuid"
}
```

---

## 4.4 分页结构

建议统一：

```json
{
  "items": [],
  "page": 1,
  "page_size": 20,
  "total": 100
}
```

---

## 4.5 错误码建议

至少预留以下错误码语义：

* `AUTH_INVALID`
* `AUTH_EXPIRED`
* `PERMISSION_DENIED`
* `PRODUCT_NOT_FOUND`
* `SKU_NOT_FOUND`
* `STOCK_NOT_ENOUGH`
* `ORDER_NOT_FOUND`
* `ORDER_STATUS_INVALID`
* `ADDRESS_NOT_FOUND`
* `REVIEW_NOT_ALLOWED`

---

## 4.6 运行环境基线

建议统一为：

* Python 3.11
* PostgreSQL 16
* Redis 7
* MinIO 稳定版
* Docker Compose v2

前端首轮不引入新的 Node 构建链。

---

## 五、总体实施顺序

本版改成下面这个主线：

### 主线阶段

1. **Phase 0：基线、脚手架、工程约定**
2. **Phase 1：认证、用户、地址**
3. **Phase 2：商品、SKU、搜索基础**
4. **Phase 3：购物车、订单、支付闭环**
5. **Phase 4：向量数据库、语义搜索、推荐系统**
6. **Phase 5：会员、评价、后台最小可用**
7. **Phase 6：部署、回归、比赛交付**

注意这里和你原计划最大的变化是：

**把“推荐系统与向量数据库”提前到会员和文化内容之前。**

因为你已经明确：

> 重点先把后端链路以及推荐系统和向量数据库完成

这是正确的。

---

# 六、详细实施计划

---

## Phase 0 基线、脚手架与统一规范

### Step 01. 冻结当前仓库现状

产出：

* `docs/current_state.md`

内容必须覆盖：

* 已存在页面
* `localStorage` 使用点
* 缺失页面
* 假数据来源
* 与设计文档差距

验证：

```bash
test -f docs/current_state.md
rg -n "localStorage|orders\.html|favorites\.html" docs/current_state.md
rg -n "index.html|product.html|cart.html|checkout.html|login.html|register.html|profile.html|membership.html" docs/current_state.md
```

退出条件：

* 核心页面全部盘点完成
* 至少三类问题被明确记录

---

### Step 02. 固化页面与接口映射

产出：

* `docs/page_api_matrix.md`

内容必须包括：

* 每个页面调用哪些接口
* 页面依赖哪些实体
* 哪些假数据要替换
* 哪些页面先不改

验证：

```bash
test -f docs/page_api_matrix.md
rg -n "/api/v1|front/" docs/page_api_matrix.md
```

退出条件：

* 核心页面全部有映射关系

---

### Step 03. 清理死链与补齐占位页

动作：

* 新增 `front/orders.html`
* 移除 `favorites.html` 的入口
* 明确当前只有真实存在页面可跳转

验证：

```bash
test -f front/orders.html
! rg -n "favorites\.html" front
rg -n "orders\.html" front
```

---

### Step 04. 建立目录骨架

动作：

* 创建 `backend/`、`admin/`、`docs/`、`tests/e2e/`

验证：

```bash
test -d backend/app
test -d backend/tests
test -d admin
test -d tests/e2e
```

---

### Step 05. 初始化依赖与测试工具链

新增：

* `backend/requirements.txt`
* `backend/requirements-dev.txt`
* `pytest.ini` 或等价配置
* 格式检查与测试说明

建议首轮测试工具：

* pytest
* httpx
* pytest-asyncio
* pytest-cov
* playwright 或 selenium 二选一做烟雾测试

验证：

```bash
test -f backend/requirements.txt
test -f backend/requirements-dev.txt
pytest --collect-only
```

---

### Step 06. 建立 Docker Compose 骨架

服务先固定为：

* postgres
* redis
* minio
* api
* worker

验证：

```bash
test -f docker-compose.yml
docker compose config --quiet
```

---

### Step 07. 建立 FastAPI 应用骨架

必须提供：

* `/api/v1/health`
* `/docs`
* 基本路由注册

验证：

```bash
pytest backend/tests/api/test_health.py -q
curl -f http://127.0.0.1:8000/api/v1/health
curl -f http://127.0.0.1:8000/docs
```

---

### Step 08. 统一配置、日志、异常、响应结构

必须实现：

* `config.py`
* `logger.py`
* 统一异常中间件
* 统一响应结构
* request_id

验证：

```bash
pytest backend/tests/unit/test_settings.py -q
pytest backend/tests/api/test_error_response.py -q
```

---

### Step 09. 数据库连接与迁移基线

必须实现：

* SQLAlchemy 会话管理
* Alembic 基线迁移
* 测试数据库连接

验证：

```bash
alembic -c backend/alembic.ini upgrade head
pytest backend/tests/integration/test_db_session.py -q
```

---

### Step 10. Redis 与 MinIO 基础连通

先只做：

* 客户端封装
* 连通性检查
* 不做业务逻辑

验证：

```bash
pytest backend/tests/integration/test_infra_clients.py -q
docker compose ps redis minio
```

---

### Step 11. 后端测试夹具

必须完成：

* 数据库夹具
* 用户夹具
* 鉴权夹具
* HTTP 客户端夹具
* 种子数据夹具

验证：

```bash
pytest backend/tests/api/test_health.py -q
pytest --collect-only
```

---

### Step 12. 前端统一 API 与会话模块

新增：

* `front/js/api.js`
* `front/js/session.js`

职责：

* 发请求
* 自动带 token
* 自动刷新 access token
* 统一处理 401
* 统一退出登录

验证：

```bash
test -f front/js/api.js
test -f front/js/session.js
rg -n "api.js|session.js" front
```

---

### Phase 0 阶段产物

必须产出：

* `docs/current_state.md`
* `docs/page_api_matrix.md`
* `backend/` 基础骨架
* `admin/` 基础骨架
* `docker-compose.yml`
* FastAPI 健康接口
* 统一配置、日志、异常处理
* 测试夹具基线
* 前端 `api.js` 与 `session.js`

### Phase 0 退出条件

只有同时满足以下条件才能进入下一阶段：

* 后端服务能启动
* 数据库迁移可执行
* 测试可收集
* 前端已有统一 API 和会话入口
* 死链问题已清理

---

## Phase 1 认证、用户、地址

### Step 13. 建立用户域表

表：

* `users`
* `user_profile`
* `user_address`
* `user_behavior_log`

验证：

```bash
alembic -c backend/alembic.ini upgrade head
pytest backend/tests/models/test_user_models.py -q
```

---

### Step 14. 实现安全基础

实现：

* 密码哈希
* 密码校验
* access token
* refresh token
* 鉴权依赖
* 角色判断

验证：

```bash
pytest backend/tests/unit/test_security.py -q
```

---

### Step 15. 注册接口

接口：

* `POST /api/v1/auth/register`

验证：

```bash
pytest backend/tests/api/test_auth_register.py -q
```

---

### Step 16. 登录、刷新、退出

接口：

* `POST /api/v1/auth/login`
* `POST /api/v1/auth/refresh`
* `POST /api/v1/auth/logout`

额外要求：

* 登录接口写 refresh cookie
* 刷新接口依赖 refresh cookie
* 前端不直接存 refresh token

验证：

```bash
pytest backend/tests/api/test_auth_login.py -q
pytest backend/tests/api/test_auth_refresh.py -q
pytest backend/tests/api/test_auth_logout.py -q
```

---

### Step 17. 当前用户与资料维护

接口：

* `GET /api/v1/users/me`
* `PUT /api/v1/users/me`
* `PUT /api/v1/users/password`

验证：

```bash
pytest backend/tests/api/test_users_me.py -q
pytest backend/tests/api/test_users_profile.py -q
pytest backend/tests/api/test_users_password.py -q
```

---

### Step 18. 地址管理

接口：

* `GET /api/v1/users/addresses`
* `POST /api/v1/users/addresses`
* `PUT /api/v1/users/addresses/{id}`
* `DELETE /api/v1/users/addresses/{id}`

验证：

```bash
pytest backend/tests/api/test_user_addresses.py -q
```

---

### Step 19. 接通登录与注册页

动作：

* 替换 `localStorage` 假登录逻辑
* 接入真实注册与登录

验证：

```bash
pytest tests/e2e/test_auth_pages.py -q
! rg -n "shiyige_user|localStorage" front/login.html front/register.html
```

---

### Step 20. 接通个人中心与导航登录态

动作：

* `profile.html`
* `front/js/auth.js`
* 退出登录流程
* 导航栏用户态

验证：

```bash
pytest tests/e2e/test_profile_page.py -q
! rg -n "shiyige_user|localStorage" front/profile.html front/js/auth.js
! rg -n "favorites\.html" front/profile.html front/js/auth.js
```

---

### Phase 1 阶段产物

* 完整认证链路
* 用户资料与地址能力
* 登录页、注册页、个人中心可用
* 会话刷新机制可用

### Phase 1 退出条件

必须跑通：

**注册 -> 登录 -> 获取当前用户 -> 修改资料 -> 新增地址 -> 退出登录**

---

## Phase 2 商品、SKU、搜索基础

### Step 21. 建立商品域表

表：

* `category`
* `product`
* `product_sku`
* `product_media`
* `product_tag`
* `inventory`

关键约定：

* 商品列表显示最低价
* 库存按 SKU
* 默认 SKU 必须存在

验证：

```bash
alembic -c backend/alembic.ini upgrade head
pytest backend/tests/models/test_product_models.py -q
```

---

### Step 22. 导入首批演示商品

重点：

* 不追求内容丰富
* 先保证商品数据完整能支撑后端流程与推荐测试

建议至少准备：

* 类目：汉服、文创、非遗、饰品、礼盒
* 商品：20~30 个
* 每个商品有：

  * 基础信息
  * 1~3 张图
  * 至少 1 个 SKU
  * 简短文化摘要
  * 标签
  * 场景词
  * 风格词

验证：

```bash
pytest backend/tests/integration/test_seed_base_data.py -q
pytest backend/tests/integration/test_product_seed_counts.py -q
```

---

### Step 23. 类目列表接口

接口：

* `GET /api/v1/categories`

验证：

```bash
pytest backend/tests/api/test_categories.py -q
```

---

### Step 24. 商品列表接口

接口：

* `GET /api/v1/products`

支持：

* 分页
* 类目筛选
* 价格区间
* 标签
* 排序
* 关键词过滤

验证：

```bash
pytest backend/tests/api/test_products_list.py -q
```

---

### Step 25. 商品详情接口

接口：

* `GET /api/v1/products/{id}`

必须返回：

* 基础信息
* 媒体
* SKU
* 库存
* 标签
* 会员价
* 简短文化说明

验证：

```bash
pytest backend/tests/api/test_product_detail.py -q
```

---

### Step 26. 接通首页与分类页

动作：

* 首页真实拉取类目与商品
* 分类页真实拉取商品列表

验证：

```bash
pytest tests/e2e/test_home_and_category.py -q
rg -n "/api/v1/categories|/api/v1/products" front
```

---

### Step 27. 接通商品详情页

动作：

* `product.html`
* `front/js/product.js`

验证：

```bash
pytest tests/e2e/test_product_page.py -q
rg -n "/api/v1/products/" front/product.html front/js/product.js
```

---

### Step 28. 实现关键词搜索

接口：

* `GET /api/v1/search`
* `GET /api/v1/search/suggestions`

注意：

* 这里先做关键词检索基础
* 为 Phase 4 语义搜索预留接口形态

验证：

```bash
pytest backend/tests/api/test_search_keyword.py -q
pytest tests/e2e/test_search_flow.py -q
```

---

### Phase 2 阶段产物

* 商品域数据结构
* 商品种子数据
* 首页、分类页、商品详情页接通
* 关键词搜索可用

### Phase 2 退出条件

必须跑通：

**浏览首页 -> 进入分类 -> 搜索商品 -> 打开详情 -> 选择 SKU**

---

## Phase 3 购物车、订单、支付闭环

### Step 29. 建立购物车表

表：

* `cart`
* `cart_item`

验证：

```bash
alembic -c backend/alembic.ini upgrade head
pytest backend/tests/models/test_cart_models.py -q
```

---

### Step 30. 购物车接口

接口：

* `GET /api/v1/cart`
* `POST /api/v1/cart/items`
* `PUT /api/v1/cart/items/{id}`
* `DELETE /api/v1/cart/items/{id}`

必须处理：

* 商品不存在
* SKU 不存在
* 数量非法
* 商品下架
* 库存不足

验证：

```bash
pytest backend/tests/api/test_cart_api.py -q
```

---

### Step 31. 接通商品页加购与购物车页

动作：

* 替换所有购物车本地存储逻辑

验证：

```bash
pytest tests/e2e/test_cart_flow.py -q
! rg -n "shiyige_cart|localStorage" front/product.html front/cart.html front/js/cart.js
```

---

### Step 32. 建立订单与支付记录表

表：

* `orders`
* `order_item`
* `payment_record`

状态建议：

* `PENDING_PAYMENT`
* `PAID`
* `CANCELLED`

首轮不用把状态做太多。

验证：

```bash
alembic -c backend/alembic.ini upgrade head
pytest backend/tests/models/test_order_models.py -q
```

---

### Step 33. 创建订单接口

接口：

* `POST /api/v1/orders`

必须实现：

* 地址校验
* 金额计算
* 订单明细写入
* 幂等控制

验证：

```bash
pytest backend/tests/api/test_order_create.py -q
pytest backend/tests/api/test_order_idempotency.py -q
```

---

### Step 34. 支付、取消、查询接口

接口：

* `POST /api/v1/orders/{id}/pay`
* `POST /api/v1/orders/{id}/cancel`
* `GET /api/v1/orders`
* `GET /api/v1/orders/{id}`

支付逻辑固定：

* 支付时再次校验库存
* 支付成功后扣库存
* 写 `payment_record`

验证：

```bash
pytest backend/tests/api/test_order_pay.py -q
pytest backend/tests/api/test_order_cancel.py -q
pytest backend/tests/api/test_order_query.py -q
```

---

### Step 35. 升级订单页

动作：

* 把 `front/orders.html` 升级成真实页面

验证：

```bash
pytest tests/e2e/test_orders_page.py -q
```

---

### Step 36. 接通结算页

动作：

* 真实地址
* 真实购物车
* 真实订单创建
* 模拟支付

验证：

```bash
pytest tests/e2e/test_checkout_flow.py -q
! rg -n "shiyige_orders|shiyige_cart|shiyige_membership|localStorage" front/checkout.html front/js/checkout.js
```

---

### Step 37. 核心行为日志

记录行为：

* 浏览商品
* 搜索
* 加购
* 下单
* 支付成功

这一步非常重要，因为 Phase 4 推荐要用。

验证：

```bash
pytest backend/tests/api/test_behavior_logging.py -q
pytest backend/tests/integration/test_behavior_events.py -q
```

---

### Phase 3 阶段产物

* 真实购物车
* 真实订单
* 模拟支付
* 真实订单页
* 行为日志

### Phase 3 退出条件

必须跑通主链路：

**注册登录 -> 浏览商品 -> 搜索 -> 加购 -> 结算 -> 创建订单 -> 模拟支付 -> 查看订单**

这是比赛主演示链路的最低要求。

---

## Phase 4 向量数据库、语义搜索、推荐系统

这是本版最核心的增强阶段。

### 本阶段 MVP 范围固定为 3 件事

1. **自然语言语义搜索**
2. **商品详情页相似商品推荐**
3. **首页猜你喜欢**

其余都延后。

---

### Step 38. 向量模型适配层

实现：

* embedding provider 抽象
* 本地模型调用封装
* 模型来源说明配置
* 向量维度配置

验证：

```bash
pytest backend/tests/unit/test_embedding_provider.py -q
```

---

### Step 39. 建立向量表与画像表

表：

* `product_embedding`
* `user_interest_profile`

注意：

* 首轮可不启用 `content_embedding`
* 先保证商品与用户画像跑起来

验证：

```bash
alembic -c backend/alembic.ini upgrade head
pytest backend/tests/services/test_embedding_text_builder.py -q
```

---

### Step 40. 商品 embedding_text 拼装

规则建议固定：

```text
商品名称 + 类目 + 标签 + 描述 + culture_summary + 风格词 + 场景词 + 工艺词
```

要求：

* 规则写死到 builder 中
* 同一个商品可重复稳定生成同类向量文本
* 不依赖文化长文内容

验证：

```bash
pytest backend/tests/services/test_embedding_text_builder.py -q
```

---

### Step 41. 建立异步向量生成任务

实现：

* 商品向量生成任务
* 增量更新任务
* 全量重建命令

验证：

```bash
pytest backend/tests/tasks/test_embedding_tasks.py -q
pytest backend/tests/integration/test_reindex_command.py -q
```

---

### Step 42. 语义搜索接口

接口：

* `POST /api/v1/search/semantic`

必须支持：

* 自然语言查询
* 基础过滤条件
* 相似度召回
* 返回命中原因

命中原因示例：

* “与‘适合春日出游的素雅汉服’语义相近”
* “命中‘明制/清雅/摄影场景’标签”
* “与你近期浏览的明制商品偏好相似”

验证：

```bash
pytest backend/tests/api/test_search_semantic.py -q
pytest backend/tests/integration/test_search_ranking.py -q
```

---

### Step 43. 商品相似推荐接口

接口：

* `GET /api/v1/products/{id}/related`

要求：

* 基于商品向量
* 排除自己
* 排除下架商品
* 返回推荐原因

验证：

```bash
pytest backend/tests/api/test_related_products.py -q
```

---

### Step 44. 用户兴趣画像与猜你喜欢

接口：

* `GET /api/v1/products/recommendations`

用户画像来源：

* 浏览
* 搜索
* 加购
* 下单

权重建议：

* 浏览 1
* 搜索 2
* 加购 3
* 下单 5

要求：

* 不同用户有不同结果
* 推荐理由简洁明确

验证：

```bash
pytest backend/tests/integration/test_user_interest_profile.py -q
pytest backend/tests/api/test_recommendations.py -q
```

---

### Step 45. 接通前端推荐与语义搜索入口

接通位置：

* 首页猜你喜欢
* 商品详情页相关推荐
* 搜索页语义搜索入口

界面要求：

* 每个推荐卡片可显示一句推荐理由
* 不追求花哨，只求答辩时看得见

验证：

```bash
pytest tests/e2e/test_recommendation_ui.py -q
rg -n "/api/v1/search|/api/v1/products/.*/related|/api/v1/products/recommendations" front admin
```

---

### Phase 4 阶段产物

* 本地 embedding 模型接入
* 商品向量表
* 用户兴趣画像
* 语义搜索
* 相似商品推荐
* 首页猜你喜欢

### Phase 4 退出条件

必须演示通过：

1. 输入自然语言能搜到合理商品
2. 商品详情页能展示相关推荐
3. 两个不同账号能看到不同的首页推荐
4. 推荐结果能解释原因

---

## Phase 5 会员、评价、后台最小可用

这一阶段不再做重文化，依然围绕比赛展示增强。

---

### Step 46. 会员与积分表

表：

* `member_level`
* `point_account`
* `point_log`

验证：

```bash
alembic -c backend/alembic.ini upgrade head
pytest backend/tests/integration/test_member_seed.py -q
```

---

### Step 47. 会员资料与积分接口

接口：

* `GET /api/v1/member/profile`
* `GET /api/v1/member/points`
* `GET /api/v1/member/benefits`

支付成功后：

* 积分增加
* 等级更新

验证：

```bash
pytest backend/tests/api/test_member_profile.py -q
pytest backend/tests/api/test_point_accrual.py -q
```

---

### Step 48. 接通会员中心

动作：

* `membership.html`
* 真实积分
* 真实等级
* 商品详情真实会员价

验证：

```bash
pytest tests/e2e/test_membership_page.py -q
! rg -n "shiyige_membership|localStorage" front/membership.html front/js/membership.js
```

---

### Step 49. 评价表与评价接口

表：

* `review`
* `review_image`

接口：

* 创建评价
* 查询评价列表
* 查询评价统计

限制：

* 必须购买后可评价

验证：

```bash
pytest backend/tests/models/test_review_models.py -q
pytest backend/tests/api/test_reviews_create.py -q
pytest backend/tests/api/test_reviews_list.py -q
pytest backend/tests/api/test_reviews_permissions.py -q
```

---

### Step 50. 接通商品评价区域

动作：

* 详情页评分和评价区改为真实接口

验证：

```bash
pytest tests/e2e/test_product_reviews.py -q
```

---

### Step 51. 后台用户与鉴权

表：

* `admin_user`
* `operation_log`

角色：

* 超级管理员
* 运营管理员

首轮可先不做内容管理员单独能力。

验证：

```bash
alembic -c backend/alembic.ini upgrade head
pytest backend/tests/api/test_admin_auth.py -q
```

---

### Step 52. 后台核心接口

首轮只做四类：

* 商品管理
* 订单管理
* 用户概览
* 推荐重建任务触发

验证：

```bash
pytest backend/tests/api/test_admin_products.py -q
pytest backend/tests/api/test_admin_orders.py -q
pytest backend/tests/api/test_admin_reindex.py -q
```

---

### Step 53. 后台最小页面集合

页面：

* `admin/login.html`
* `admin/index.html`
* `admin/products.html`
* `admin/orders.html`
* `admin/reindex.html`

验证：

```bash
pytest tests/e2e/test_admin_basic.py -q
test -f admin/index.html
```

---

### Phase 5 阶段产物

* 会员中心
* 评价系统
* 最小后台
* 推荐重建控制页

### Phase 5 退出条件

必须能完成：

* 支付后积分变化
* 商品详情页评价展示
* 管理员登录后台
* 管理商品与触发推荐重建

---

## Phase 6 部署、回归、比赛交付

### Step 54. 媒体上传

实现：

* 商品图上传
* 评价图上传
* MinIO 管理
* 文件大小与类型限制

验证：

```bash
pytest backend/tests/api/test_media_upload.py -q
pytest backend/tests/api/test_upload_limits.py -q
```

---

### Step 55. 缓存与安全加固

缓存优先级：

* 商品详情
* 首页推荐
* 搜索建议

安全优先级：

* 鉴权校验
* 基础限流
* 参数校验
* 上传限制
* 统一异常

验证：

```bash
pytest backend/tests/integration/test_cache_behavior.py -q
pytest backend/tests/api/test_rate_limit.py -q
pytest backend/tests/api/test_security_guards.py -q
```

---

### Step 56. Nginx 与完整编排

必须实现：

* Nginx 托管 `front/`
* Nginx 托管 `admin/`
* `/api` 反向代理到 FastAPI
* Compose 一键启动

验证：

```bash
docker compose config --quiet
docker compose up -d
curl -f http://127.0.0.1/api/v1/health
curl -f http://127.0.0.1
```

---

### Step 57. 演示数据与全链路回归

必须准备：

* 演示普通用户
* 演示管理员
* 演示商品
* 演示订单
* 演示推荐行为数据

验证：

```bash
pytest backend/tests -q
pytest tests/e2e/test_full_demo_flow.py -q
```

---

### Step 58. 交付文档

必须产出：

* `docs/database_design.md`
* `docs/api_guide.md`
* `docs/deployment.md`
* `docs/test_report.md`
* `docs/ai_usage_boundary.md`

验证：

```bash
test -f docs/database_design.md
test -f docs/api_guide.md
test -f docs/deployment.md
test -f docs/test_report.md
test -f docs/ai_usage_boundary.md
```

---

### Phase 6 阶段产物

* 可启动的完整比赛环境
* 本地与云端双演示方案
* 完整文档材料
* 回归测试结果

### Phase 6 退出条件

必须满足：

1. `docker compose up -d` 可启动
2. 前台、后台、接口都可访问
3. 主演示链路通过
4. 推荐与语义搜索可展示
5. 文档齐全

---

# 七、最终验收口径 v2

本版最终验收以以下 6 条为准：

## 1. 前台闭环

必须跑通：

**注册登录 -> 浏览商品 -> 关键词搜索/语义搜索 -> 加购 -> 结算 -> 模拟支付 -> 订单查询 -> 评价 -> 积分变化 -> 推荐变化**

---

## 2. 商品详情页

必须同时展示：

* 商品基础信息
* SKU 与库存
* 会员价
* 简短文化说明
* 用户评价
* 相似商品推荐

首轮不强制要求文化长文。

---

## 3. 推荐系统

至少必须支持：

* 自然语言语义搜索
* 商品详情页相似推荐
* 首页猜你喜欢

并且每个推荐结果必须能解释原因。

---

## 4. 后台

至少必须支持：

* 商品管理
* 订单管理
* 推荐重建任务
* 后台登录

---

## 5. 部署

必须支持：

* 本地 Docker Compose 一键启动
* 云端公网可访问版本

---

## 6. 文档

必须覆盖：

* 设计文档
* 数据库设计
* 接口文档
* 测试报告
* 部署文档
* AI 使用边界说明

---



