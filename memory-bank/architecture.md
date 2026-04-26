# 当前架构洞察

## 2026-04-26 补充洞察

* 根目录 `README.md` 现在应该被视为“运行入口文档”，而不只是一个极简项目名片。
  它需要同时覆盖目录职责、关键文件、环境基线、Compose 启动、宿主机直跑后端、演示账号和常用验证命令；否则后续开发者很容易只看到仓库名，却不知道该从 `docker-compose.yml` 还是 `uvicorn` 入口启动项目。
* 当前仓库的测试收集命令有一个容易踩坑的细节：使用 `uv run` 时要显式带上 `PYTHONPATH=.`。
  原因不是 pytest 本身有问题，而是仓库根目录下的 `backend/` 是源码包目录；如果不把根目录放进 Python 模块搜索路径，`backend/tests/conftest.py` 在导入 `backend.app...` 时就会失败。
* SQLAlchemy 模型层现在更明确地采用了 `from __future__ import annotations` + `TYPE_CHECKING` + 字符串前向引用的组合。
  这让 `backend/app/models/cart.py`、`membership.py`、`order.py`、`product.py`、`review.py`、`user.py` 之间的双向关系既能保持模块拆分，又不会再因为导入环或未解析名称卡住 `ruff`。
* 前台多个页面页脚过去仍残留 `categories.html` 这一旧页面名，而真实分类页已经固定为 `category.html`。
  这类问题不会在后端测试里暴露，但会直接形成用户可见死链，所以后续凡是改页面名或路由名，都应该追加一次全仓文本扫描，而不是只依赖业务测试。
* 当前 `tests/e2e/conftest.py` 的浏览器夹具直接调用 `playwright.chromium.launch()`。
  这意味着 e2e 的稳定性不只依赖前后端逻辑，还依赖执行环境能否正常运行 Playwright 自带的 Chromium headless shell；在受限沙箱里，测试可能会在夹具启动阶段失败，而不是在页面行为阶段失败。

## 1. 记忆文档的作用

* `memory-bank/design.md`：项目目标、比赛定位、系统能力边界和推荐思路的源文档。
* `memory-bank/implementation_plan.md`：当前执行顺序的主合同，后续开发按这里的 Step 编号推进。
* `memory-bank/progress.md`：执行日志，记录已经完成的步骤、验证结果和交接信息。
* `memory-bank/architecture.md`：当前仓库结构、文件职责、耦合关系和新的架构洞察。
* `memory-bank/recommendation_enhancement_execution_plan.md`：推荐增强执行合同；在主升级计划之外，专门承接当前仓库仍值得继续落地的推荐可观测、可展示、可运营增强项。

## 2. 当前仓库的真实结构

当前仓库已经进入“前台静态站点 + 后台静态站点 + FastAPI 服务 + Docker Compose 编排”阶段：

* `front/`：现有展示层和交互层。
* `backend/`：FastAPI 后端与业务实现，已经具备认证、用户、商品、购物车、订单、推荐、后台管理、上传、缓存与安全模块。
* `admin/`：最小后台静态站点，由 Nginx 在 `/admin` 下正式托管。
* `nginx/`：生产编排使用的静态托管与反向代理配置目录。
* `tests/e2e/`：前后台端到端测试目录。
* `docs/`：实施过程中生成的事实文档和测试说明。
* `memory-bank/`：长期上下文存储，用于让后续开发者理解设计、计划、进度和架构。
* `docker-compose.yml`：当前完整本地编排入口，负责拉起 PostgreSQL、Redis、MinIO、FastAPI 和 Nginx。
* `pytest.ini` 与 `ruff.toml`：测试和格式检查的全局配置入口。

## 3. `docs/` 文件作用

* `docs/current_state.md`：记录现有页面、`localStorage` 使用点、假数据来源、缺页和与设计文档的差距；它不是设计文档，而是“当前基线事实表”。
* `docs/page_api_matrix.md`：记录 `front/` 页面到 `/api/v1` 接口、实体和假数据替换点的映射关系，是前后端接线图。
* `docs/testing.md`：记录当前依赖入口、测试目录和基础命令，告诉后续开发者该用什么方式跑测试。
* `docs/database_design.md`：数据库与基础设施设计说明，概括业务表分层、关系和关键约束。
* `docs/api_guide.md`：接口使用说明，整理前后台接口分组、鉴权方式和演示账号。
* `docs/deployment.md`：部署与运行说明，覆盖 Compose 一键启动、访问入口、测试命令和重置方式。
* `docs/test_report.md`：最终测试报告，记录执行命令、通过结果和已修复问题。
* `docs/ai_usage_boundary.md`：AI 使用边界说明，定义 AI 可参与范围、验证要求和人工复核重点。

## 3.1 工程级配置文件作用

* `docker-compose.yml`：当前完整 Compose 编排文件；定义 `postgres`、`redis`、`minio`、`api`、`nginx` 五类服务，并把主入口暴露在宿主机 `80` 端口。
* `nginx/default.conf`：Nginx 主站配置；负责托管 `front/`、托管 `admin/`，并把 `/api`、`/docs`、`/redoc`、`/openapi.json` 反向代理到 FastAPI。当前 `location = /admin/` 采用显式跳转到 `/admin/index.html`，避免把精确匹配 URI 直接 `alias` 到单文件时触发 `index.htmlindex.html` 的错误拼接。
* `backend/Dockerfile`：后端运行镜像定义；负责安装运行依赖、复制后端代码并指定 API 容器默认启动入口。
* `backend/.dockerignore`：后端镜像构建忽略规则；避免把测试目录、缓存和本地数据库文件带进运行镜像上下文。
* `pytest.ini`：全仓测试收集入口，目前指向 `backend/tests` 和 `tests/e2e`。
* `ruff.toml`：当前最小格式检查配置。

## 3.2 Python 依赖入口

* `backend/requirements.txt`：运行时依赖基线。
* `backend/requirements-dev.txt`：开发和测试依赖基线。

## 3.3 本地运行时资产

* `.venv/`：项目内 Python 虚拟环境；当前已经装入 `fastapi`、`uvicorn`、`httpx`、`pytest`、`pytest-asyncio`。
* `.uv-cache/`：项目内 `uv` 缓存目录；后续用 `UV_CACHE_DIR=.uv-cache` 运行，避免写到沙箱不可写的默认缓存目录。

## 4. `front/` 页面文件作用

* `front/index.html`：首页；负责品牌首屏、轮播、节令专题、全站导航，以及通过 `front/js/home-page.js` 真实拉取类目和推荐商品。
* `front/category.html`：分类页；负责侧栏筛选、排序和商品卡片展示，当前已通过 `front/js/category-page.js` 真实请求商品列表。
* `front/product.html`：商品详情页；负责商品信息、文化背景、评价、相关推荐和加购动作，当前通过 `front/js/product.js` 真实请求商品接口并提交加购接口。
* `front/cart.html`：购物车页；负责展示购物车条目、数量修改和金额汇总，当前已移除页面内联购物车脚本，改由 `front/js/cart.js` 通过购物车接口驱动。
* `front/checkout.html`：结算页；负责真实地址选择、真实购物车汇总、订单备注、支付方式选择和提交流程，当前已通过真实订单接口驱动。
* `front/login.html`：登录页；负责登录表单、错误提示和成功后跳转，当前已通过真实认证接口工作。
* `front/register.html`：注册页；负责注册表单、字段校验和注册成功后跳转，当前已通过真实认证接口工作。
* `front/profile.html`：个人中心；负责用户资料展示、资料修改和密码修改交互，当前已通过 `/api/v1/users/me` 等接口驱动。
* `front/orders.html`：订单页；负责订单统计、订单列表、订单详情、支付记录以及支付/取消动作，当前已通过真实订单接口驱动。
* `front/membership.html`：会员中心；负责等级、权益、充值和积分记录展示，当前通过全局会员脚本读取本地会员数据。

## 4.1 `admin/` 页面文件作用

* `admin/index.html`：后台仪表盘；展示业务总览、推荐 KPI、搜索 KPI、向量索引概况和实验摘要。
* `admin/products.html`：后台商品管理页。
* `admin/orders.html`：后台订单管理页。
* `admin/reindex.html`：向量索引状态与重建页。
* `admin/recommendation-debug.html`：推荐调试台；按用户查看画像、候选拆解、最终打分证据，以及探索位保留和类目去重轨迹。
* `admin/recommendation-config.html`：推荐实验配置页；展示 baseline、hybrid、hybrid_rerank、full_pipeline 等方案能力，并通过运行时摘要、能力矩阵和答辩提示卡片把实验方案变成可解释的对比页面。
* `admin/recommendation-metrics.html`：推荐指标页；聚合推荐请求、曝光、点击、加购、支付转化、槽位分布、召回通道分布和搜索/推荐 pipeline 分布，并继续展示冷启动请求数、Exploration 命中率和新品召回占比，是推荐系统可观测层的后台展示入口。

## 5. `front/js/` 脚本文件作用

* `front/js/main.js`：全站通用脚本；负责时钟、导航高亮、工具提示、日期、返回顶部、图片失败兜底和滚动动画，同时提供 `window.shiyigeRecommendationUI` 作为前台推荐 UI 的统一渲染层，集中封装来源标签、解释标签、亮点标签和推荐证据卡片。
* `front/js/auth.js`：全站认证与导航脚本；负责基于 `session.js` 和 `/users/me` 更新导航用户态、统一退出登录和当前用户缓存。
* `front/js/cart.js`：购物车前端控制器；负责商品卡片快捷加购、购物车页渲染、数量修改、删除和购物车角标更新，当前全部通过购物车 API 工作。
* `front/js/checkout.js`：结算页控制器；负责读取真实购物车和真实地址、提交真实订单、调用支付接口完成模拟支付，并展示订单成功模态框。
* `front/js/product.js`：商品详情页控制器；负责读取 URL 商品 ID、请求 `/api/v1/products/{id}`、渲染详情/相关推荐、处理缩略图和数量，并通过购物车 API 提交主加购表单。
* `front/js/membership.js`：会员脚本；负责会员等级规则、积分倍率、充值规则、余额扣减和会员卡展示。
* `front/js/search.js`：搜索框行为脚本；当前会请求 `/api/v1/search/suggestions` 获取联想词，并把关键词写入 `category.html?search=...` 进入搜索结果页。
* `front/js/promotion.js`：促销规则脚本；负责满减规则计算和促销进度条。
* `front/js/validation.js`：表单校验脚本；负责用户名、邮箱、手机号、密码等输入校验。
* `front/js/carousel.js`：轮播增强脚本；负责首页等轮播表现层交互。
* `front/js/petals.js`：花瓣动效脚本；负责页面背景的装饰性动态效果。
* `front/js/api.js`：前端统一 API 入口；负责统一补齐 `/api/v1` 前缀、自动附带 access token、`401` 后触发刷新重试。
* `front/js/session.js`：前端统一会话入口；负责把 access token 存在 `sessionStorage`，并通过 refresh cookie 获取新 token。
* `front/js/auth-pages.js`：登录页/注册页脚本；负责真实注册、真实登录、游客页守卫和第三方按钮的占位提示。
* `front/js/profile-page.js`：个人中心页脚本；负责加载当前用户、提交资料修改、提交密码修改和展示默认地址摘要。
* `front/js/orders-page.js`：订单页控制器；负责加载真实订单列表与详情、渲染订单统计，并在待支付订单上触发真实支付和取消接口。

## 5.1 `admin/js/` 脚本文件作用

* `admin/js/app.js`：后台统一前端编排层；负责管理员登录态、导航、仪表盘、商品页、订单页、推荐调试页、推荐指标页、实验配置页和索引状态页的数据请求与渲染。当前还承担冷启动/探索/去重标签、业务规则、保留轨迹和冷启动 KPI 的展示编排。

## 6. `front/css/` 样式文件作用

* `front/css/style.css`：主入口样式文件；通过 `@import` 汇总其余 CSS，并补充商品详情页、评价等页面级样式。
* `front/css/base.css`：全局变量、基础重置、字体和底层背景风格。
* `front/css/navbar.css`：导航栏、搜索框、购物车入口等顶部区域样式。
* `front/css/layout.css`：轮播和主要布局容器样式。
* `front/css/components.css`：商品卡片等可复用组件样式。
* `front/css/footer.css`：页脚区域样式。
* `front/css/responsive.css`：响应式断点和移动端适配规则。

## 7. 资源目录作用

* `front/images/汉服/`：汉服类商品静态图片。
* `front/images/文创产品/`：文创商品静态图片。
* `front/images/非遗手工艺/`：非遗商品静态图片。
* `front/images/背景/`：花瓣与背景装饰图片。
* `front/images/logo.svg` 与首页横幅图片：品牌和分类入口的静态展示素材。

## 8. `backend/` 文件作用

### 8.1 顶层包

* `backend/__init__.py`：把 `backend` 标记为可导入包，保证测试里能以 `backend.app...` 方式导入。

### 8.2 应用入口

* `backend/app/main.py`：FastAPI 应用创建入口；负责配置日志、注册异常处理与请求 ID 中间件、挂载总路由，并在 `lifespan` 中预留基础设施启动检查。

### 8.3 路由分层

* `backend/app/api/router.py`：后端总 API 路由入口；负责聚合版本路由。
* `backend/app/api/v1/router.py`：`/api/v1` 版本路由入口；当前已挂载认证路由、用户路由、商品目录路由、购物车路由、搜索路由和健康检查路由。
* `backend/app/api/v1/auth.py`：认证路由文件；当前实现注册、登录、刷新、退出四个接口，负责认证入口、refresh cookie 写入/清理和初始资料创建。
* `backend/app/api/v1/cart.py`：购物车路由文件；当前实现购物车查询、加购、改数量和删除，并做商品/SKU/库存校验。
* `backend/app/api/v1/orders.py`：订单路由文件；当前已实现订单创建、支付、取消、列表查询和详情查询，负责地址校验、金额计算、订单快照写入、幂等返回、支付扣库存和支付记录落库。
* `backend/app/api/v1/users.py`：用户路由文件；当前实现当前用户读取、资料更新、密码修改和地址管理，并内聚“从 access token 解析当前用户”的依赖。
* `backend/app/api/v1/products.py`：商品目录与推荐路由文件；当前实现类目列表、商品列表、商品详情、相似商品推荐和猜你喜欢接口，并内聚筛选、排序和序列化逻辑。
* `backend/app/api/v1/search.py`：搜索路由文件；当前实现关键词搜索、联想建议和语义搜索接口，并复用商品列表序列化输出。
* `backend/app/api/v1/health.py`：健康检查路由；返回统一成功响应结构，证明最小 API 和响应包装已接通。

### 8.4 基础设施层

* `backend/app/core/config.py`：配置入口；`AppSettings` 提供应用级安全默认值，`InfrastructureSettings` 强制要求数据库、Redis、MinIO、密钥等环境变量。
* `backend/app/core/logger.py`：日志配置入口；统一日志格式并提供 `get_logger()`。
* `backend/app/core/error_codes.py`：统一错误码常量定义。
* `backend/app/core/responses.py`：统一 JSON 响应构造器；负责输出 `code/message/data/request_id` 结构。
* `backend/app/core/exceptions.py`：统一异常处理层；把校验错误、HTTP 错误和未捕获异常都转换为统一响应。
* `backend/app/core/request_id.py`：请求 ID 中间件；负责读写 `X-Request-ID` 并把 request id 注入 `request.state`。
* `backend/app/core/database.py`：数据库连接入口；提供默认 SQLite URL、SQLAlchemy engine、session factory、`get_db()` 依赖和测试重置函数。
* `backend/app/core/redis.py`：Redis 客户端包装；负责读取环境变量、创建缓存客户端和做连通性测试。
* `backend/app/core/minio.py`：MinIO 客户端包装；负责对象存储客户端初始化和连通性测试。
* `backend/app/core/security.py`：安全基础模块；负责密码哈希/校验、JWT access/refresh token、refresh cookie 辅助、当前 token 依赖和角色权限检查。

### 8.4.1 服务层

* `backend/app/services/behavior.py`：行为日志服务；负责从请求中解析可选当前用户，并把浏览、搜索、加购、下单、支付等动作统一写入 `user_behavior_log`。
* `backend/app/services/__init__.py`：服务层包入口占位。
* `backend/app/services/embedding.py`：向量 provider 服务；负责统一 embedding provider 抽象、离线 fallback、本地模型包装以及模型元信息描述。
* `backend/app/services/embedding_text.py`：向量文本构建服务；负责生成稳定的商品 `embedding_text` 与对应 `content_hash`。
* `backend/app/services/recommendation_admin.py`：后台聚合服务；负责把推荐日志、搜索日志、实验配置、向量索引状态和运行时信息整理成后台仪表盘/推荐后台页面可直接消费的数据结构。当前还承担推荐 KPI、fallback 比例、召回通道分布、搜索/推荐 pipeline 分布、冷启动请求数、Exploration 命中率、新品召回占比，以及实验页运行时摘要和能力矩阵目录的聚合职责。
* `backend/app/services/vector_search.py`：向量检索服务；负责商品 embedding 保障、向量相似度计算、语义排序和推荐理由生成。
* `backend/app/services/recommendations.py`：推荐服务；负责从行为日志构建用户兴趣画像，并基于画像向量和兴趣词返回猜你喜欢结果。

### 8.4.2 任务层

* `backend/app/tasks/embedding_tasks.py`：商品向量任务层；负责商品向量 upsert、增量重建与全量重建，是后续异步任务和后台操作的统一底座。

### 8.5 数据模型与迁移

* `backend/app/models/base.py`：SQLAlchemy 声明基类与命名约定；同时提供通用时间戳字段。
* `backend/app/models/user.py`：用户域模型定义；当前包含用户、用户资料、地址、行为日志四张核心表。
* `backend/app/models/product.py`：商品域模型定义；当前包含类目、商品、SKU、库存、媒体和标签等目录表结构。
* `backend/app/models/cart.py`：购物车域模型定义；当前包含购物车主表与购物车明细表，并连接用户、商品和 SKU。
* `backend/app/models/order.py`：订单域模型定义；当前包含订单主表、订单明细表和支付记录表，并保存地址与金额快照。
* `backend/app/models/recommendation.py`：推荐域模型定义；当前包含商品向量表和用户兴趣画像表，并为后续索引任务与推荐服务提供持久化落点。
* `backend/app/models/__init__.py`：模型包入口；用于集中暴露模型模块并帮助 Alembic 导入元数据。
* `backend/app/schemas/__init__.py`：Schema 包入口；集中暴露认证等请求体模型。
* `backend/app/schemas/auth.py`：认证相关请求模型；当前定义注册和登录接口的输入结构与字段约束。
* `backend/app/schemas/address.py`：地址相关请求模型；当前定义用户地址增改接口的输入结构与字段约束。
* `backend/app/schemas/cart.py`：购物车请求模型；当前定义加购和改数量的输入结构。
* `backend/app/schemas/order.py`：订单请求模型；当前定义下单接口的地址、幂等键和买家备注输入结构。
* `backend/app/schemas/search.py`：搜索请求模型；当前定义语义搜索接口的自然语言查询和过滤条件。
* `backend/app/schemas/user.py`：用户相关请求模型；当前定义资料更新和密码修改的输入结构与字段约束。
* `backend/alembic.ini`：Alembic 配置入口。
* `backend/alembic/env.py`：Alembic 运行环境；负责读取当前数据库 URL 并加载模型元数据。
* `backend/alembic/script.py.mako`：Alembic 新迁移模板。
* `backend/alembic/versions/20260413_01_baseline.py`：迁移基线版本，占位首个 revision。
* `backend/alembic/versions/20260413_02_user_domain.py`：用户域迁移；创建 `users`、`user_profile`、`user_address`、`user_behavior_log` 表及索引约束。
* `backend/alembic/versions/20260414_03_product_domain.py`：商品域迁移；创建类目、商品、SKU、库存、媒体和标签表。
* `backend/alembic/versions/20260414_04_cart_domain.py`：购物车域迁移；创建 `cart`、`cart_item` 表和唯一约束。
* `backend/alembic/versions/20260414_05_order_domain.py`：订单域迁移；创建 `orders`、`order_item`、`payment_record` 表和订单/支付唯一键。
* `backend/alembic/versions/20260414_06_embedding_domain.py`：推荐域迁移；创建 `product_embedding`、`user_interest_profile` 两张向量/画像表及索引。
* `backend/scripts/seed_base_data.py`：目录基础数据种子脚本；负责初始化 5 个类目和 20 个商品，是本地测试与 e2e 的统一种子入口。
* `backend/scripts/seed_demo_data.py`：演示数据种子脚本；负责在基础商品数据之上继续创建演示普通用户、默认地址、样例订单、积分与推荐行为画像。
* `backend/scripts/start_api.sh`：Compose 下 API 容器启动脚本；负责等待迁移成功、执行基础种子并启动 Uvicorn。
* `backend/scripts/reindex_embeddings.py`：商品向量全量/增量重建命令入口；负责调用向量任务并输出重建结果摘要。
* `backend/dev.db`：当前默认本地 SQLite 数据库文件；方便在未拉起 PostgreSQL 前先推进接口实现和测试。

### 8.6 测试文件

* `backend/tests/conftest.py`：后端测试夹具入口；负责创建 `app`、`AsyncClient`、临时数据库、数据库会话和部分占位测试数据。
* `backend/tests/test_toolchain_smoke.py`：测试收集链路的烟雾测试。
* `backend/tests/api/conftest.py`：API 测试共享夹具；负责认证接口测试所需的临时数据库、应用实例、测试客户端和用户种子函数。
* `backend/tests/api/test_health.py`：健康检查接口测试。
* `backend/tests/api/test_error_response.py`：统一异常响应测试；校验错误码、消息体结构和 `X-Request-ID`。
* `backend/tests/api/test_auth_register.py`：注册接口测试；校验注册成功、密码哈希、初始资料创建和重复邮箱冲突。
* `backend/tests/api/test_auth_login.py`：登录接口测试；校验 access token 返回、refresh cookie 写入和错误凭证处理。
* `backend/tests/api/test_auth_refresh.py`：刷新接口测试；校验 refresh cookie 换发 access token 和缺少 cookie 时的错误响应。
* `backend/tests/api/test_auth_logout.py`：退出接口测试；校验 refresh cookie 被清除，且退出后刷新失败。
* `backend/tests/api/test_users_me.py`：当前用户接口测试；校验 access token 能映射到当前用户和资料数据。
* `backend/tests/api/test_users_profile.py`：资料更新接口测试；校验用户字段与资料字段更新，以及重复邮箱冲突。
* `backend/tests/api/test_users_password.py`：密码修改接口测试；校验当前密码检查与新密码哈希更新。
* `backend/tests/api/test_user_addresses.py`：地址接口测试；校验地址 CRUD、默认地址切换和缺失地址错误。
* `backend/tests/unit/test_settings.py`：配置层测试；校验默认值和必填环境变量行为。
* `backend/tests/unit/test_security.py`：安全基础测试；覆盖密码哈希、JWT、鉴权依赖和角色检查。
* `backend/tests/integration/test_db_session.py`：数据库连接与会话可用性测试。
* `backend/tests/integration/test_infra_clients.py`：Redis 与 MinIO 连通性测试。
* `backend/tests/models/test_user_models.py`：用户域模型建表与字段关系测试。
* `backend/tests/models/test_product_models.py`：商品域模型测试；校验商品、SKU、库存、媒体和标签的关系结构。
* `backend/tests/models/test_cart_models.py`：购物车域模型测试；校验购物车表、购物车明细关系和唯一约束。
* `backend/tests/models/test_order_models.py`：订单域模型测试；校验订单、订单明细、支付记录和快照字段关系。
* `backend/tests/integration/test_seed_base_data.py`：基础种子幂等性测试；校验重复执行不会重复灌数。
* `backend/tests/integration/test_seed_demo_data.py`：演示数据种子测试；校验演示用户、样例订单、积分等级和兴趣画像会被稳定初始化且重复执行不重复灌数。
* `backend/tests/integration/test_product_seed_counts.py`：基础种子数量测试；校验类目和商品总数符合预期。
* `backend/tests/api/test_categories.py`：类目接口测试；校验 `GET /api/v1/categories` 的返回结构。
* `backend/tests/api/test_products_list.py`：商品列表接口测试；校验分页、筛选、排序和关键词过滤。
* `backend/tests/api/test_product_detail.py`：商品详情接口测试；校验详情结构和商品不存在时的 `404`。
* `backend/tests/api/test_search_keyword.py`：搜索接口测试；校验关键词搜索结果和联想建议输出。
* `backend/tests/api/test_cart_api.py`：购物车接口测试；校验购物车 CRUD 和商品/SKU/库存错误场景。
* `backend/tests/api/test_order_create.py`：订单创建接口测试；校验地址快照、金额计算、明细写入和下单后清空购物车。
* `backend/tests/api/test_order_idempotency.py`：订单幂等测试；校验重复提交同一幂等键不会重复创建订单。
* `backend/tests/api/test_order_pay.py`：订单支付接口测试；校验支付成功后的库存扣减、支付记录写入和库存不足错误。
* `backend/tests/api/test_order_cancel.py`：订单取消接口测试；校验待支付订单取消和非法状态拦截。
* `backend/tests/api/test_order_query.py`：订单查询接口测试；校验当前用户订单列表、详情展示和越权访问拦截。
* `backend/tests/api/test_behavior_logging.py`：行为日志 API 测试；校验浏览、搜索、加购、下单、支付动作会写入正确的行为事件。
* `backend/tests/unit/test_embedding_provider.py`：embedding provider 单元测试；校验 deterministic provider、模型包装器和配置映射行为。
* `backend/tests/services/test_embedding_text_builder.py`：embedding 文本构建测试；校验商品向量文本的固定字段顺序和内容哈希稳定性。
* `backend/tests/services/test_recommendation_admin_metrics.py`：推荐后台指标聚合测试；校验 fallback 统计、召回通道分布和搜索 pipeline 分布的聚合结果。
* `backend/tests/api/test_search_semantic.py`：语义搜索接口测试；校验自然语言搜索、排序和推荐理由输出。
* `backend/tests/tasks/test_embedding_tasks.py`：向量任务测试；校验全量建索引、增量跳过与内容变更后的单商品重建。
* `backend/tests/api/test_related_products.py`：相似商品接口测试；校验排除自身、排除下架商品和推荐理由输出。
* `backend/tests/api/test_recommendations.py`：猜你喜欢接口测试；校验不同用户会得到不同的推荐结果集合。
* `tests/e2e/conftest.py`：页面级测试共享夹具；负责启动“静态前端 + FastAPI API”的同源测试服务，并提供浏览器实例。
* `tests/e2e/test_auth_pages.py`：登录页/注册页页面级测试；校验真实注册、真实登录和会话写入。
* `tests/e2e/test_profile_page.py`：个人中心页面级测试；校验导航用户态、资料修改和退出登录。
* `tests/e2e/test_home_and_category.py`：首页/分类页页面级测试；校验类目和商品列表来自真实商品接口。
* `tests/e2e/test_product_page.py`：商品详情页页面级测试；校验详情页能加载真实种子商品，并继续命中相关推荐。
* `tests/e2e/test_search_flow.py`：搜索页面流测试；校验搜索联想、搜索跳转和结果页展示来自真实搜索接口。
* `tests/e2e/test_full_demo_flow.py`：完整演示链路回归测试；覆盖注册登录、关键词/语义搜索、商品浏览、加购、结算支付、订单查询、评价、积分变化和推荐变化。
* `tests/e2e/test_cart_flow.py`：购物车页面流测试；校验登录后商品页加购、购物车页改数量和删除都命中真实购物车接口。
* `tests/e2e/test_orders_page.py`：订单页页面级测试；校验空订单态、订单列表详情渲染以及页内支付流程都基于真实订单接口。
* `tests/e2e/test_checkout_flow.py`：结算页页面级测试；校验购物车进入结算、真实地址加载、真实下单支付和购物车清空流程。
* `backend/tests/integration/test_behavior_events.py`：行为事件集成测试；校验完整用户旅程的行为日志顺序、目标类型和关键扩展字段。
* `backend/tests/integration/test_reindex_command.py`：重建命令集成测试；校验商品向量全量重建命令能真实落索引。
* `backend/tests/integration/test_search_ranking.py`：语义排序集成测试；校验向量检索排序与价格过滤行为。
* `backend/tests/integration/test_user_interest_profile.py`：用户画像集成测试；校验不同行为历史会形成不同的画像文本与 top terms。

## 9. 当前最重要的架构洞察

### 9.1 当前是“订单后端闭环完成，剩余前端页面继续接线”状态

现在系统已经不再是“后端骨架 + 静态前端分离”的早期状态，而是进入：

* 认证页、个人中心、首页、分类页、商品详情页、购物车页已经与真实后端接口接通；
* 订单 API 已经覆盖下单、支付、取消、列表和详情查询，后端交易主链路已具备可演示闭环；
* 会员页仍保留浏览器本地模拟逻辑；
* 后续重点开始从“补基础接口”转向“把剩余本地业务状态替换成真实业务流”。

### 9.2 前端仍是“页面内联数据 + 全局脚本 + `localStorage`”架构

这意味着现在的系统没有真正的数据层、接口层和状态边界，很多业务只是浏览器本地模拟。

### 9.3 购物车与结算前端职责已经收敛

当前购物车相关职责已经收敛为：

* `front/js/product.js` 负责商品详情页主加购表单；
* `front/js/cart.js` 负责商品卡片快捷加购、购物车页渲染和角标更新；
* `front/js/checkout.js` 负责读取购物车、选择地址、创建订单并模拟支付；
* `/api/v1/cart`、`/api/v1/orders` 共同负责持久化状态与交易推进。

这意味着“商品页加购 -> 购物车 -> 结算 -> 订单页”这条主演示链路已经打通。

### 9.3.1 订单后端状态已经完整，订单页也已开始消费

当前订单域已经形成完整后端边界：

* `/api/v1/orders` 负责创建订单与幂等返回；
* `/api/v1/orders/{id}/pay` 负责模拟支付、再次校验库存并扣库存；
* `/api/v1/orders/{id}/cancel` 负责取消待支付订单；
* `/api/v1/orders` 和 `/api/v1/orders/{id}` 负责订单列表与详情查询。

现在订单页已经开始直接消费这组接口，因此结算页后续不需要再定义新的本地订单模型，而应直接复用现有接口结构。

### 9.3.2 Phase 3 的主营演示链路已经闭环

当前系统已经具备：

* 登录后浏览真实商品详情；
* 使用真实关键词搜索；
* 加购到真实购物车；
* 从购物车进入真实结算；
* 创建真实订单并完成站内模拟支付；
* 在真实订单页查看支付结果。

这意味着 Phase 3 计划里的主链路退出条件已经满足，后续可以把注意力转到推荐系统需要的向量与画像能力。

### 9.4 商品详情页的“内联假数据耦合”已经拆除

`front/product.html` 不再内联 `productData` 和详情加载逻辑，`front/js/product.js` 现在直接请求 `/api/v1/products/{id}`。这让商品详情页第一次具备了稳定的数据边界，也让 e2e 可以用真实种子商品做回归。

### 9.5 登录态与通知系统也有重复实现

* `front/js/auth.js` 有自己的 `showNotification`。
* `front/js/main.js` 也有自己的 `showNotification`。
* 登录、注册、个人中心中还存在页面内联调用。

后续需要统一通知系统和会话系统，避免全站出现多个近似但不兼容的实现。

### 9.6 当前后端已经进入“用户域 + 商品目录域”并行阶段

### 9.7 前台推荐证据层已经完成统一抽象

当前首页、商品详情页、购物车页和下单完成页虽然入口不同，但推荐卡片渲染边界已经收敛到 `front/js/main.js`：

* `renderProductCard()` 负责统一商品卡片骨架。
* `renderEvidence()` 负责统一推荐理由与标签区。
* `buildRecommendationHighlights()` 负责把 `feature_highlights`、`matched_terms`、探索位、LTR 回退、召回通道拆解和多样性打散状态整理成前台可展示的证据标签。

这意味着后续如果继续增强推荐说明，不应分别改四个页面脚本，而应优先扩展 `window.shiyigeRecommendationUI` 的输出契约。

现在 `/api/v1` 不再只有健康检查和认证，而是已经具备：

* 认证接口
* 当前用户与地址接口
* 类目列表接口
* 商品列表接口
* 商品详情接口
* 搜索接口
* 语义搜索接口
* 相似商品推荐接口
* 猜你喜欢接口
* 购物车接口

这意味着 Phase 2 之后的重点不再是“有没有 API”，而是“购物车、订单、搜索这些业务流如何沿用现有约定继续扩展”。

### 9.7 当前测试体系已经从“入口存在”升级到“业务回归”

### 9.8 Compose 启动对迁移状态和 Nginx 精确路由都很敏感

当前本地启动链路里有两个容易把系统卡死的点：

* `nginx/default.conf` 中 `location = /admin/` 不能直接把精确匹配 URI `alias` 到单个文件，否则访问 `/admin/` 时会触发错误的目录索引拼接；当前实现改为显式跳转到 `/admin/index.html`。
* `backend/scripts/start_api.sh` 会在启动时循环执行 `alembic upgrade head`，因此只要任意一个迁移对“已有表但旧 revision”的数据库不兼容，整个 API 容器就会一直停在迁移阶段，外部表现为 `/api/*` 统一 `502`。
* `backend/alembic/versions/20260424_12_recommendation_logging.py` 现在承担的不只是“新库建表”，还承担“修复旧数据卷升级路径”的职责；它的 `upgrade()` 已经按表和索引做幂等处理，能从 `20260424_11` 平滑恢复到 `20260424_12`。

现在测试不再只是证明服务能启动，而是已经覆盖：

* 用户域 API 回归
* 商品目录 API 回归
* 首页、分类页、商品详情页的 Playwright 页面回归
* 购物车、订单创建、订单支付/取消/查询的 API 回归

这意味着后续每一步都应该继续保持“先落测试，再放行业务实现”的节奏。

### 9.7.1 SQLAlchemy 关系缓存已经成为当前实现细节风险点

在购物车和订单接口里，提交事务后立即复用同一 `Session` 读取关系集合时，会遇到 `cart.items`、`order.payment_records` 等关联列表停留在旧值的问题。当前处理方式是在关键提交后显式执行 `db.expire_all()`，让后续序列化基于数据库最新状态。后续如果继续沿用“提交后马上回查并返回”的接口模式，需要保留这一约定。

### 9.7.2 行为日志已经成为后续推荐系统的固定输入层

当前 `user_behavior_log` 已经不再只是预留表，而是开始真实落数据。现有固定事件词表为：

* `view_product`
* `search`
* `add_to_cart`
* `create_order`
* `pay_order`

后续用户兴趣画像、猜你喜欢和推荐理由如果需要利用行为数据，应直接围绕这套事件类型和 `ext_json` 字段扩展，而不要再平行引入另一套埋点模型。

### 9.7.3 向量能力的当前入口已经固定为 provider 抽象

当前向量相关能力不再直接依赖具体模型实现，而是先收敛到 `EmbeddingProvider` 抽象和 `EmbeddingModelDescriptor` 元信息对象。它带来的好处是：

* 开发和测试环境可以先用 `local_hash` provider 保持离线稳定；
* 需要切到真实中文本地模型时，只需要改配置和依赖，不必改调用方接口；
* 后续向量表、重建任务、搜索排序和推荐服务都可以只依赖统一的 `embed_texts()` / `embed_query()` 入口。

这一步等于把 Phase 4 的“模型层接口合同”先固定了，后面每一层实现都不应再绕开它。

### 9.7.4 推荐域已经有了可持续扩展的数据落点

现在推荐系统不再停留在“未来会有向量”的概念阶段，而是已经有了两张明确的数据表：

* `product_embedding`：承载单商品的向量文本、向量值、模型名和内容哈希；
* `user_interest_profile`：承载单用户的兴趣画像文本、向量值、行为计数和扩展元数据。

这意味着后续的重建任务、语义搜索、相似商品和猜你喜欢能力，都应该围绕这两张表扩展，而不是把向量暂存在临时缓存或内存结构里。

### 9.7.5 商品向量文本规则已经冻结

当前 `backend/app/services/embedding_text.py` 已把商品向量文本的来源字段固定为：

* 商品名称
* 类目
* 标签
* 描述
* 文化摘要
* 风格词
* 场景词
* 工艺词

同时它已经保证：

* 字段顺序固定；
* 空字段自动跳过；
* 标签排序稳定；
* `content_hash` 基于最终文本生成。

这意味着后续只要商品这些核心内容不变，向量文本和哈希就应保持稳定；增量重建逻辑应直接建立在这个前提上。

### 9.7.6 向量重建路径已经具备“任务层 + 命令层”双入口

当前商品向量生成不再是散落在脚本里的临时逻辑，而是已经分成两层：

* `backend/app/tasks/embedding_tasks.py` 负责真正的索引更新逻辑；
* `backend/scripts/reindex_embeddings.py` 负责把任务逻辑暴露成可执行命令。

这意味着后续无论是接后台“重建索引”按钮、接定时任务，还是接真实任务队列，都应该复用任务层，而不是重新写一遍索引生成过程。

### 9.7.7 语义搜索已经采用“向量召回 + 规则加权 + 理由生成”三段式结构

当前 `POST /api/v1/search/semantic` 不是单纯按向量分数硬排，而是由三层组成：

* 先确保商品向量索引存在；
* 再计算 query 向量与商品向量的相似度；
* 最后结合类目、标签、风格、场景、工艺等显式特征做加权，并生成一句命中理由。

这使得当前系统即使在离线 fallback provider 条件下，也能给出相对稳定、可解释的答辩结果。后续相似商品和猜你喜欢能力应优先复用这套排序与理由框架。

### 9.7.8 用户画像已经成为首页推荐的真实中间层

当前“猜你喜欢”不再是临时规则列表，而是已经通过 `backend/app/services/recommendations.py` 形成明确链路：

* 先读取 `user_behavior_log`；
* 再按固定权重构建 `user_interest_profile`；
* 再用画像向量与兴趣词对候选商品做排序；
* 最后返回一句简洁的推荐理由。

这意味着后续首页推荐、用户分群和推荐解释都应建立在画像服务之上，而不是绕开画像直接在接口里拼规则。

### 9.8 `uv` 已经成为当前项目的实际执行入口

当前环境没有全局 `pytest`，普通沙箱里还存在：

* 默认 `uv` 缓存目录不可写
* 本地监听端口不可绑定

所以当前可复用约定是：

* 测试优先用 `UV_CACHE_DIR=.uv-cache uv ...`
* 或直接用 `.venv/bin/python ...`
* 绑定本地 HTTP 服务或从本地 `curl` 命中服务时，可能需要提权上下文

后续开发者不要再假设“系统里自带 pytest 并且 8000 端口可直接监听”。

### 9.9 有一处明确的静态资源错误假设

`front/js/main.js` 的图片加载失败兜底写死为 `/static/images/banner1.svg`，但当前仓库中不存在该文件。这说明部分脚本来自早期不同目录结构，后续整理时要优先校正资源路径假设。

### 9.10 当前最适合的落地路线

正确路线不是先重写样式，也不是先迁移前端框架，而是：

1. 先补真实后端与统一 API。
2. 再把 `localStorage` 业务状态逐步替换为接口。
3. 最后再整理共享脚本、去除内联数据、补后台和推荐系统。

### 9.11 当前安全实现的边界

现在已经有可复用的安全基础，但它仍停留在“基础能力就绪”阶段：

* 密码已通过 `pbkdf2_sha256` 哈希，不再依赖当前环境下不稳定的 `bcrypt` 后端。
* Access token 与 refresh token 的生成、解析、权限检查接口已经固定。
* 注册、登录、刷新、退出接口已经接通，refresh token 已收敛到 HttpOnly Cookie。
* 用户资料接口、地址接口和前端登录/个人中心接线已经完成，但订单、购物车、会员等业务流还没进入统一鉴权边界。

因此后续认证步骤应优先复用 `backend/app/core/security.py`，不要再各自写一套 token 或密码逻辑。

### 9.12 当前认证链路的真实边界

现在后端认证链路已经形成一个稳定约定：

* 登录接口返回 `data.access_token` 给前端会话模块。
* refresh token 不进入 JSON 响应体，只通过 Cookie 传递。
* 刷新接口完全从 Cookie 读 refresh token。
* 退出接口的职责是清 Cookie，而不是让前端自行删除 refresh token。

这意味着接下来的 `front/js/session.js`、`front/js/auth.js` 和 `GET /api/v1/users/me` 都应该围绕这个约定实现，不要再回到 `localStorage` 登录态模型。

### 9.13 当前用户模型的接口边界

现在“用户主信息”和“资料信息”的边界已经固定为：

* `users` 表负责账号主字段：`email`、`username`、`role`、`password_hash`、`is_active`。
* `user_profile` 表负责可编辑资料字段：`display_name`、`phone`、`birthday`、`bio`、`avatar_url`。
* `GET /api/v1/users/me` 返回时，会把资料对象收敛到 `data.user.profile`。

这对后续前端接线很重要，因为 `profile.html` 里的手机号、生日、头像等字段不应该再继续塞回 `shiyige_user`，而应该映射到 `user_profile`。

### 9.14 当前前端认证链路的真实形态

现在前端已经不再通过 `localStorage` 保存用户对象，而是分成三层：

* `front/js/session.js`：只负责 access token 与 refresh 流程。
* `front/js/auth.js`：只负责导航用户态、当前用户缓存和统一退出。
* 页面脚本如 `front/js/auth-pages.js`、`front/js/profile-page.js`：只负责页面自己的表单与交互。

这意味着后续任何新页面如果需要登录态，不应该重新发明一套 `shiyige_user` 对象，而应建立在这三层之上。

### 9.15 当前页面级测试已经具备同源集成能力

现在 `tests/e2e/conftest.py` 会在测试里启动一个同源服务，把：

* `/api/v1/...` 指向 FastAPI 后端；
* `/login.html`、`/register.html`、`/profile.html` 等页面指向 `front/` 静态文件。

因此后续前台页面接线不必退回字符串断言，可以继续用 Playwright 做真实浏览器流程验证。

### 9.16 商品目录域的当前合同已经基本固定

当前目录域已经形成稳定合同：

* `GET /api/v1/categories` 返回类目列表；
* `GET /api/v1/products` 返回分页商品列表，并支持 `category_id`、价格区间、`tag`、`sort`、`q`；
* `GET /api/v1/products/{id}` 返回商品详情、媒体、标签和 SKU/库存；
* `backend/scripts/seed_base_data.py` 提供固定的目录测试样本。

后续搜索、购物车、订单如果要依赖商品目录，应该优先沿用这套接口结构，不要重新发明另一套商品序列化格式。

### 9.17 搜索域目前是“目录域上的轻封装”

当前搜索能力没有单独建立全文索引，而是：

* 用 `/api/v1/search` 对商品目录做关键词召回、排序和筛选；
* 用 `/api/v1/search/suggestions` 给前端搜索框提供联想；
* 让分类页在“搜索模式”下复用同一张商品结果页。

这符合当前阶段的目标：先把搜索闭环走通，并为后续 Phase 4 语义搜索保留单独的搜索接口形态。

### 9.18 购物车域已经形成前后端闭环

当前购物车相关状态已经进入“后端持久化 + 前端页面接线完成”的状态：

* `cart` 保证一个用户一辆购物车；
* `cart_item` 保证一辆购物车里同一 SKU 只有一条记录；
* `/api/v1/cart` 系列接口已经落地；
* 商品详情页和购物车页都已经切到真实购物车接口。

当前剩余问题不再是购物车本身，而是 checkout、订单和支付流程还没接上这套真实购物车。

### 9.19 订单域的持久化结构已经先行就绪

当前订单相关状态已经具备一个可扩展的数据库合同：

* `orders` 保存订单号、状态、金额和收货地址快照；
* `order_item` 保存商品、SKU、数量和单价快照；
* `payment_record` 保存支付流水和支付状态；
* `idempotency_key` 已经直接建在订单表上，为下单接口幂等控制留好落点。

这意味着接下来的下单和支付接口主要是“把业务规则写进去”，而不是再回头补表。

### 9.20 订单创建已经开始接管购物车闭环

现在系统已经形成新的业务链路：

* 商品页/购物车页通过 `/api/v1/cart` 维护持久化购物车；
* `/api/v1/orders` 从购物车和地址生成订单；
* 订单创建成功后会清空购物车明细；
* `idempotency_key` 让前端重复提交不会重复创建订单。

这意味着后续 checkout 页面接线时，核心风险已经不再是“如何计算金额”，而是“如何把支付、取消、订单查询和前端页面串起来”。

### 9.21 推荐前端入口已经形成“三处接线、一个测试闭环”

Phase 4 的前端展示层现在已经补齐三个明确入口：

* `front/js/home-page.js`：负责首页“猜你喜欢”区域。它会优先调用 `GET /api/v1/products/recommendations`，失败或未登录时回退到最新商品列表，并把 `reason` 渲染到卡片文案里。
* `front/js/product.js`：负责商品详情页“相关推荐”区域。它不再走同类目兜底列表，而是直接命中 `GET /api/v1/products/{id}/related`，把推荐理由随卡片一并展示。
* `front/js/category-page.js`：负责分类页搜索入口和结果页模式切换。当前同时承载商品列表、关键词搜索和语义搜索三种模式，并通过请求 token 防止旧请求覆盖新结果。
* `front/index.html`、`front/product.html`、`front/category.html`：分别为三处入口补充了最小可见的标题、说明文案和语义搜索控件容器。
* `tests/e2e/test_recommendation_ui.py`：负责验证这三个入口的真实浏览器行为，特别是“两个账号首页推荐不同”“推荐理由可见”“语义搜索结果可见”这三条答辩路径。

这里有一个重要实现约束：`front/js/category-page.js` 里的搜索控件同步不能盲目回写输入框，否则在用户切换搜索模式时会把尚未提交的自然语言查询清空；因此当前实现会先保留输入，再同步控件状态。

### 9.22 会员域现在已经有独立的数据底座

从第 46 步开始，会员和积分不再适合继续挂在前端 `localStorage` 里模拟，当前后端已经具备最小可用的数据底座：

* `backend/app/models/membership.py`：定义会员域的三张核心表。
  `MemberLevel` 负责等级静态配置。
  `PointAccount` 负责用户当前积分余额、累计积分、当前等级。
  `PointLog` 负责不可变的积分流水记录。
* `backend/app/models/user.py`：现在 `User` 已经和 `PointAccount` 建立一对一关系，后续会员 API 可以直接从用户侧挂载积分账户。
* `backend/scripts/seed_base_data.py`：现在会先确保默认会员等级存在，再处理商品目录种子，因此“基础数据”已经包含目录域和会员域两个维度。
* `backend/alembic/versions/20260415_07_membership_domain.py`：把会员域表结构固化为可迁移合同，而不是只存在于测试或运行时建表逻辑里。
* `backend/tests/integration/test_member_seed.py`：负责验证默认等级种子、积分账户、积分流水三者能在同一数据库里真实跑通。

当前一个关键架构约束是：`point_account.member_level_id` 代表“当前等级快照”，而 `member_level.min_points` 代表“等级规则”。后续积分变更流程必须同时维护积分余额和等级快照，不能假设前端每次都自己重新推导等级。

### 9.23 会员接口与订单支付已经形成联动

第 47 步之后，会员域不再只是数据库表结构，已经形成一条完整的后端链路：

* `backend/app/services/member.py`：是会员域的核心服务层。
  它负责积分账户懒创建、当前等级解析、下一等级计算、积分流水序列化，以及订单支付后的积分累计与等级更新。
* `backend/app/api/v1/member.py`：提供会员中心依赖的三个真实接口。
  `GET /api/v1/member/profile` 返回当前等级、积分余额、升级进度。
  `GET /api/v1/member/points` 返回积分汇总和流水。
  `GET /api/v1/member/benefits` 返回全部等级权益与当前等级标识。
* `backend/app/api/v1/orders.py`：现在支付成功不只写 `payment_record`，还会调用会员服务把积分和等级一起落账。
* `backend/tests/api/test_member_profile.py`：验证会员账户可以懒创建，以及会员资料/权益/积分接口的默认返回结构。
* `backend/tests/api/test_point_accrual.py`：验证订单支付后积分会增加，会员等级会随积分变化而升级。

当前有一个重要实现决定：支付积分基于“支付时的当前等级倍率”来计算，也就是先按旧等级算本次积分，再判断是否升级。这保证了单次支付行为的积分规则可解释，避免同一笔订单因为支付后立即升级而反向影响本次积分倍率。

### 9.24 会员中心前端已经完全切到真实接口

第 48 步之后，会员中心不再是一个独立的前端沙盒页面，而是正式接入后端会员域：

* `front/js/membership.js`：现在是纯展示层脚本。
  它会并行请求 `/member/profile`、`/member/points`、`/member/benefits`，然后分别渲染会员卡、权益区、积分流水表和充值区提示。
* `front/membership.html`：已经移除原先依赖 `window.membership` 的内联逻辑，只保留页面骨架与容器，页面行为全部交给外部脚本。
* `tests/e2e/test_membership_page.py`：负责验证会员中心显示真实等级/积分、积分流水，以及商品详情页会员价来自真实接口。

这里有一个明确的边界：会员中心当前已经不再维护任何本地会员状态，所以后续功能扩展应该继续走“前端请求真实接口 -> 渲染结果”这条路，不能再把积分、余额、等级写回 `localStorage` 做伪状态同步。

### 9.25 评价域已经具备“已购后评价”的后端合同

第 49 步把评价系统的后端合同完整立起来了：

* `backend/app/models/review.py`：定义 `Review` 和 `ReviewImage`。
  `Review` 记录用户、商品、订单、评分、内容和匿名标记。
  `ReviewImage` 记录评价图片 URL 和排序。
* `backend/app/api/v1/reviews.py`：把创建、列表、统计三个接口统一放在 `/products/{product_id}/reviews` 路径族下，便于商品详情页直接复用。
* `backend/app/schemas/review.py`：固定了创建评价时的评分、内容、匿名标记和图片 URL 请求结构。
* `backend/tests/api/test_reviews_permissions.py`：明确锁定“必须是已支付订单中的商品才能评价，并且同一用户对同一商品只能评价一次”这两个权限边界。

当前一个关键设计决定是：评价权限不是简单看“买过这个 SKU”或“有过这个订单号”，而是看“当前用户是否存在 `PAID` 状态的订单明细命中过该商品”。这个约束对后续前端展示很重要，因为它意味着商品详情页可以公开展示评价列表，但评价入口必须由后端实时判定，而不是由前端缓存某个“已购买商品列表”。

### 9.26 商品详情页评价展示已经切到真实读接口

第 50 步之后，商品详情页里的评价区域不再是静态演示块，而是成为商品详情页上的第二条真实读取链路：

* `front/product.html`：现在只保留评价摘要容器、评价列表容器和“查看更多评价”按钮容器，不再内嵌示例统计和示例评价。
  这意味着商品详情模板已经进一步收敛为“骨架 + 挂载点”，页面真实内容由脚本统一注入。
* `front/js/product.js`：现在除了加载商品详情和相关推荐，还负责拉取评价统计与评价分页列表，并渲染平均分、星级分布、匿名昵称、评价图片和分页按钮状态。
  其中评价分页大小当前固定为 `2`，是一个明确的前端演示约束，不是后端默认值。
* `tests/e2e/test_product_reviews.py`：通过真实注册、真实下单、真实支付、真实创建评价，再打开商品详情页验证评价展示、分页和图片预览入口是否接通。

这里形成了一个新的页面级边界：

* 商品详情页的“商品主信息”“相关推荐”“评价展示”三块内容现在都由 `front/js/product.js` 聚合，但它们依赖的是三组彼此独立的只读接口。
* 评价展示链路当前只依赖 `/reviews/stats` 和 `/reviews`，并不承担“是否可评价”的决策；后续若补评价提交入口，应该新增独立的可评价态判断或直接让提交接口返回权限错误，而不是把展示接口和提交权限耦合在一起。

当前一个重要实现约束是：如果后续改动评价分页大小、排序方式或首屏加载策略，需要同步修改 `front/js/product.js` 和 `tests/e2e/test_product_reviews.py`，否则很容易出现“页面看起来能用，但自动化测试不再覆盖真实分页行为”的隐性回归。

### 9.27 后台鉴权已经和前台用户链路正式分叉

第 51 步之后，后台不再依赖 `users.role == admin` 这种混合模式，而是有了独立的后台身份域：

* `backend/app/models/admin.py`：定义 `AdminUser` 和 `OperationLog`。
  `AdminUser` 负责后台账号本身。
  `OperationLog` 负责后台审计日志，目前已用于记录登录事件，后续可继续承接后台商品、订单、推荐重建等操作日志。
* `backend/app/api/v1/admin_auth.py`：提供后台登录、当前账号查询和退出接口。
  它会校验后台账号密码，签发后台 access token，并在成功登录时写入操作日志。
* `backend/app/api/v1/router.py`：已经把后台鉴权入口挂到 `/api/v1/admin/auth/*` 路径族下，和前台 `/api/v1/auth/*` 保持并行但隔离。
* `backend/scripts/seed_base_data.py`：现在会确保默认后台管理员存在，这使后续 `admin/` 静态页面和 e2e 用例可以直接建立在固定后台账号之上。
* `backend/tests/api/conftest.py`：新增了 `create_admin_user` 和 `admin_auth_headers_factory`，为后续后台接口测试提供独立的后台身份夹具。
* `backend/tests/api/test_admin_auth.py`：锁定后台登录、后台当前身份解析、普通用户 token 不得访问后台接口等关键边界。

当前后台鉴权合同里有两个关键约束：

* 后台 token 的 `sub` 固定采用 `admin:{id}` 前缀，而前台用户 token 仍然使用纯数字用户 ID。
  这个前缀是后台/前台身份隔离的核心哨兵，后续任何后台依赖都应该沿用这个约定。
* 后台当前只实现 access token，没有实现独立后台 refresh cookie。
  这意味着后续 `admin/` 页面如果需要长会话，应扩展后台自己的刷新链路，而不是和前台共享 `refresh_token` Cookie。

这里还有一个很实用的演示约定：`seed_base_data` 会注入默认后台管理员 `admin@shiyige-demo.com`。这不是为了生产可用性，而是为了让比赛演示和 e2e 测试在同一套初始化流程下稳定拥有后台登录入口。

### 9.28 后台接口层已经形成“鉴权壳 + 管理薄层 + 现有业务内核”

第 52 步之后，后台核心接口并没有复制一套商品、订单、推荐业务，而是在现有业务内核外面加了一层受后台鉴权保护的管理接口：

* `backend/app/schemas/admin.py`：定义后台商品写接口和重建任务触发接口的请求结构。
  当前商品写模型明确只支持一个 `default_sku`，这是首轮后台范围的硬约束。
* `backend/app/api/v1/admin_products.py`：负责后台商品列表、创建、更新。
  它直接操作 `Product`、`ProductSku`、`Inventory`、`ProductMedia`、`ProductTag`，并复用当前“单默认 SKU”模型。
* `backend/app/api/v1/admin_orders.py`：负责后台订单列表与订单详情。
  它复用前台订单域的序列化结构，再补上一层下单用户信息，避免维护两套订单快照格式。
* `backend/app/api/v1/admin_dashboard.py`：提供后台首页需要的概览汇总，当前聚合的是前台用户数、商品数、订单数、待支付/已支付订单数。
* `backend/app/api/v1/admin_reindex.py`：负责后台手动触发商品 embedding 重建，底层直接调用 `backend/app/tasks/embedding_tasks.py` 的同步任务函数。
* `backend/tests/api/test_admin_products.py`、`backend/tests/api/test_admin_orders.py`、`backend/tests/api/test_admin_reindex.py`：分别锁定商品管理、订单/概览、推荐重建三条后台 API 主链路。

现在后台接口层有三个重要架构约束：

* 后台商品写接口不是一个通用商品 CMS，而是一个围绕比赛范围裁剪过的“默认 SKU 商品管理器”。
  这让后台页面可以更快落地，但也意味着后续如果扩展复杂规格，必须先扩展接口合同。
* 后台订单接口当前是只读管理视角，不直接改写订单状态。
  这样可以先把后台查询、核对和答辩演示跑通，再决定是否在后续步骤开放后台取消、发货等动作。
* 后台重建接口当前同步执行并立即返回结果。
  这对比赛演示很友好，因为点击后能立刻看到 `indexed/skipped` 数字；但如果未来迁移到异步任务队列，页面和测试都必须接受“提交任务成功”而不是“立即完成”的语义变化。

### 9.29 后台静态页面已经形成“一个前端壳 + 五个页面入口”的最小可用形态

第 53 步之后，`admin/` 目录不再是空壳，而是形成了一套最小后台静态站点：

* `admin/login.html`：后台登录入口，直接命中真实后台登录接口。
* `admin/index.html`：后台仪表盘首页，读取 `/api/v1/admin/dashboard/summary`。
* `admin/products.html`：后台商品列表页，读取 `/api/v1/admin/products`。
* `admin/orders.html`：后台订单列表页，读取 `/api/v1/admin/orders`。
* `admin/reindex.html`：后台推荐重建页，调用 `/api/v1/admin/reindex/products`。
* `admin/js/app.js`：当前后台前端壳的核心文件。
  它统一负责后台 access token 存取、登录提交、受保护页面守卫、导航渲染、页面数据加载和重建按钮动作。
* `admin/css/admin.css`：定义后台页面的统一视觉系统、布局、卡片、表格和登录页样式。
* `tests/e2e/conftest.py`：在测试时把 `/admin` 映射到 `admin/` 目录，从而让后台页面和 API 走同源真实联调。
* `tests/e2e/test_admin_basic.py`：锁定“默认后台管理员登录 -> 仪表盘可见 -> 商品页可见 -> 订单页可见 -> 重建页可触发”这条最小后台演示链路。

当前后台页面层有三个关键约束：

* 后台前端现在是“共享单文件脚本 + 多个静态页面”的架构，而不是组件化前端框架。
  这适合比赛工期和最小后台目标，但后续如果页面逻辑继续增长，应优先按功能拆脚本，而不是把更多逻辑继续堆进 `admin/js/app.js`。
* 后台页面当前只依赖 access token，使用 `sessionStorage` 保存后台令牌，并通过 `/api/v1/admin/auth/me` 验证登录态。
  这和前台“access token + refresh cookie”的链路是分开的，不能混用。
* `/admin` 的正式托管还没有进入主应用或生产编排。
  当前只有 e2e 测试夹具显式挂载了 `admin/` 静态目录，真正的生产托管责任会在 Step 56 交给 Nginx。

### 9.30 媒体上传现在已经形成“统一存储服务 + 双入口接口”结构

第 54 步之后，媒体上传不再是待办项，而是形成了一条清晰的服务边界：

* `backend/app/services/media.py`：定义媒体上传的核心协议。
  它统一负责允许的图片类型、商品图/评价图大小限制、对象名生成、桶名约定，以及默认 MinIO 存储实现。
* `backend/app/api/v1/admin_media.py`：提供后台商品图上传入口 `/api/v1/admin/media/products`。
  该入口受后台管理员鉴权保护，并会把上传动作记入 `operation_log`。
* `backend/app/api/v1/media.py`：提供前台评价图上传入口 `/api/v1/media/reviews`。
  该入口受普通用户登录态保护，用于评价图片上传。
* `backend/tests/api/test_media_upload.py` 与 `backend/tests/api/test_upload_limits.py`：通过覆盖 `get_media_storage` 依赖，验证上传成功、类型限制和大小限制，不直接耦合真实 MinIO 服务。

当前媒体上传层有三个重要约束：

* 商品图上传和评价图上传虽然共用同一个媒体服务，但鉴权域是分开的。
  商品图上传走后台管理员链路，评价图上传走前台用户链路，后续不要合并成一个“谁都能传”的通用匿名上传口。
* 上传接口当前只负责把文件放进对象存储并返回 URL，不负责自动改写商品表或评价表。
  这意味着“上传文件”和“保存业务关联”仍然是两个步骤，业务关系要由商品管理接口和评价接口自行确认。
* 存储实现当前默认是 MinIO，但接口层通过 `get_media_storage` 解耦。
  这让测试可以用假存储替身验证上传协议，也为后续切换到预签名上传或不同对象存储后端保留了替换空间。

### 9.31 缓存与安全加固已经形成可替换的基础设施层

第 55 步之后，缓存和安全守卫不再散落在接口内部，而是形成了两层基础设施：

* `backend/app/services/cache.py`：负责统一的 JSON 缓存读写。
  当前商品详情、首页推荐、搜索建议都通过它读写缓存键和值，并使用统一 TTL 约定。
* `backend/app/core/rate_limit.py`：负责按路径和客户端标识做固定窗口限流。
  目前已覆盖前台登录、后台登录、评价图上传和后台商品图上传等敏感入口。
* `backend/app/main.py`：现在除了请求 ID 中间件，还会注册限流中间件，因此安全加固已经进入全局请求链路，而不是页面或接口自己单独判断。
* `backend/app/api/v1/products.py` 与 `backend/app/api/v1/search.py`：当前已经成为缓存接入点。
  商品详情和首页推荐在命中缓存时直接返回缓存数据，搜索建议也会优先返回缓存建议项。
* `backend/tests/integration/test_cache_behavior.py`、`backend/tests/api/test_rate_limit.py`、`backend/tests/api/test_security_guards.py`：分别锁定缓存行为、限流行为和核心守卫边界。

这里有三个关键架构约束：

* 当前缓存层并不是“无副作用快速返回”。
  商品详情接口在缓存命中时仍会继续记录已登录用户的浏览行为，因为推荐系统依赖这条副作用链路。
* 当前限流器是应用内存态实现，不共享跨进程状态。
  这适合比赛阶段的单实例部署，但不应误解成生产级分布式限流方案。
* 安全守卫测试当前关注的是“最容易被绕过的关键边界”，例如后台/前台身份隔离和上传空文件拦截。
  这并不等于安全工作完成，而是把最小高价值防线先固定下来，为后续 Nginx、完整编排和全链路回归打基础。

### 9.32 完整编排现在已经形成“单入口 Nginx + 内部 API + 启动即迁移种子”的本地部署形态

第 56 步之后，仓库里的本地启动方式不再是“若干基础服务占位”，而是可直接演示的完整编排：

* `docker-compose.yml` 现在会拉起 PostgreSQL、Redis、MinIO、FastAPI 和 Nginx。
  `http://127.0.0.1/` 直接进入前台首页，`http://127.0.0.1/admin/` 直接进入后台静态页面，`/api` 则走反向代理命中 FastAPI。
* `nginx/default.conf` 现在承担正式静态托管职责，而不是让 FastAPI 主应用去挂静态目录。
  这让前台、后台和 API 文档都能通过同一个宿主机入口访问，更接近最终答辩部署形态。
* `backend/Dockerfile` 与 `backend/scripts/start_api.sh` 把 API 容器启动流程固定为“安装依赖 -> Alembic 迁移 -> 基础种子 -> Uvicorn”。
  这意味着 Compose 成功启动后，系统里至少会有默认后台管理员、会员等级、类目和商品数据，不需要再手动初始化。

这里有三个新的关键架构洞察：

* 从 SQLite 测试环境切到 PostgreSQL 真实运行环境后，迁移兼容性问题会被立刻放大。
  第 56 步已经证实：`Boolean` 字段如果写成 `server_default=sa.text("0")` 或 `sa.text("1")`，SQLite 可能放过，但 PostgreSQL 会直接拒绝并导致整套编排启动失败。后续所有迁移都必须统一使用 `sa.false()` / `sa.true()`。
* API 容器启动脚本现在内置了基础种子执行，因此“容器健康启动”和“系统具备最小演示数据”已经部分绑定。
  这适合比赛环境的一键启动，但也意味着后续如果引入更重的演示数据或回归数据集，应该单独区分“基础种子”和“演示场景种子”，不要把所有灌数都塞进 API 冷启动。
* 当前编排仍然把对象存储公开端口直接暴露为 `9000/9001`，媒体上传返回的 URL 仍由 MinIO endpoint 决定。
  这保证了对象存储在本地可调试，但如果后续需要更统一的公网访问路径，最好增加独立的“公开资源 URL”配置，而不是继续让业务接口直接暴露容器内服务名。

### 9.33 演示数据与完整回归现在已经形成“基础种子 + 演示种子 + 行为驱动推荐刷新”的闭环

第 57 步之后，系统里的演示能力不再依赖手工点点点准备数据，而是固定成了三层结构：

* `backend/scripts/seed_base_data.py` 负责最小业务底座。
  它保证类目、商品、会员等级和默认后台管理员始终存在。
* `backend/scripts/seed_demo_data.py` 负责答辩和展示所需的样例用户与样例交易。
  它在基础数据之上继续创建演示普通用户、默认地址、已支付/待支付订单、积分记录和推荐行为数据。
* `tests/e2e/test_full_demo_flow.py` 负责锁定用户侧主演示链路。
  该测试把注册登录、搜索、浏览、下单、支付、评价、积分变化和推荐变化串成一条可回归的真实页面流程。

这里有三个新的关键架构洞察：

* “基础种子”和“演示种子”必须分层。
  基础种子要保持小而稳定，适合所有开发和测试；演示种子则允许带样例订单、样例积分和样例行为。把两者分开后，测试和部署都更容易控制，不会因为演示数据过重而污染所有环境。
* 用户个性化推荐一旦被缓存，就必须在行为写入后显式失效。
  第 57 步已经证明：如果用户先拉取一次首页推荐，再去浏览、搜索、加购、下单和支付，若不主动清掉该用户的推荐缓存，首页“猜你喜欢”会一直停留在旧结果。现在浏览商品、关键词搜索、语义搜索、加购、创建订单和支付订单都会触发用户级推荐缓存失效。
* 完整演示链路的回归测试不应只看后端接口返回 200。
  `tests/e2e/test_full_demo_flow.py` 说明真正容易回归的地方是“页面状态是否真的更新”，例如订单成功模态、订单页状态文案、评价区分页、会员页积分等级和首页推荐文案是否同步变化；这些都需要页面级断言而不是纯 API 断言。

### 9.34 交付文档现在已经形成“设计说明 + 运行说明 + 验证说明 + AI 边界说明”的完整材料集合

第 58 步之后，`docs/` 目录不再只有实施过程中的事实文档，而是补齐了最终交付所需材料：

* `docs/database_design.md`：面向评审和后续开发者解释主数据结构。
* `docs/api_guide.md`：面向联调和答辩说明接口边界。
* `docs/deployment.md`：面向运行环境说明如何一键启动和重置。
* `docs/test_report.md`：面向验收说明当前真实跑过哪些命令、发现并修复了哪些问题。
* `docs/ai_usage_boundary.md`：面向合规与过程说明 AI 在当前仓库中的参与边界。

这里有两个最终交付层面的洞察：

* 事实文档和交付文档必须并存。
  `docs/current_state.md`、`docs/page_api_matrix.md` 解决“仓库现在是什么”，而新增五份文档解决“系统如何被理解、运行、验证和答辩”。两类文档服务对象不同，后续不要互相覆盖。
* AI 参与说明必须和测试结果一起交付。
  当前项目的实现大量依赖 AI 辅助，但真正可验收的依据仍然是 `docker compose` 启动结果、后端全量测试和完整 e2e 回归；因此 AI 边界文档与测试报告必须同时存在，才能把“如何做的”和“如何证明完成的”一起说清楚。

### 9.35 后台推荐调试台现在已经形成“真实画像 + 真实候选打分 + 可截图页面”的证据入口

为了让推荐系统在答辩里不只停留在首页“猜你喜欢”文案层面，第 59 次同日推进补了一条后台调试链路：

* `backend/app/api/v1/admin_recommendations.py`：后台推荐调试接口。
  当前提供 `GET /api/v1/admin/recommendations/debug`，按前台用户邮箱返回模型信息、用户画像、最近行为、候选商品打分、embedding 文本片段与向量预览，并写入后台操作日志。
* `backend/app/services/recommendations.py`：推荐服务现在除了最终推荐结果，还沉淀出共享的候选打分结构。
  `RecommendationCandidate`、`score_recommendation_candidate()`、`rank_recommendation_candidates()` 负责把“向量相似度 + 兴趣词加权 + 推荐理由”统一封装，前台推荐和后台调试页都复用它。
* `admin/recommendation-debug.html`：后台推荐调试页。
  页面允许管理员输入前台用户邮箱，直接查看该用户的画像文本、top terms、最近行为日志和候选推荐卡片，适合直接截图放进 PPT。
* `admin/js/app.js`：后台统一脚本现在新增“推荐调试”页面分支。
  它继续沿用同一个后台 token、导航和请求封装，只在受保护页面分发里增加调试页绑定和渲染逻辑。
* `admin/css/admin.css`：新增调试台所需的元信息卡片、标签、代码块和候选卡片样式。
* `backend/tests/api/test_admin_recommendation_debug.py`：验证管理员可查询推荐调试接口，并拿到行为数、画像向量维度、候选商品分数和操作日志。
* `tests/e2e/test_admin_basic.py`：后台最小页面回归已扩展到推荐调试页，证明管理员登录后确实能在浏览器里加载这份证据页。

这里有三个新的关键架构洞察：

* 推荐调试页不能有自己的一套“展示专用打分”。
  当前后台调试接口直接复用首页“猜你喜欢”背后的候选打分函数，因此页面里看到的 `vector_similarity`、`vector_score`、`term_bonus` 和 `reason` 与真实推荐结果保持同源。
* 管理员查询键选择“用户邮箱”是刻意为演示做的。
  相比用户 ID，邮箱更适合答辩场景里快速切换两个账号并现场对照截图，也更不容易因为环境重建导致 ID 漂移而影响演示稳定性。
* 证明推荐系统运行，不应只展示最终推荐商品名称。
  当前调试页同时给出“最近行为 -> top terms -> 候选商品 -> 分数拆解 -> embedding 片段/向量预览”这条因果链，这比单独展示首页卡片更能证明系统里确实存在画像构建和向量匹配过程。

### 9.36 推荐系统升级现在已经有了“可导出的 baseline 审计快照”

在正式引入 Qdrant 之前，第 60 次同日推进先把当前推荐系统的真实状态冻结成可重复导出的 baseline：

* `docs/recommendation_baseline_analysis.md`：当前推荐系统审计文档。
  这份文档明确指出：商品向量和用户画像向量还存放在 `backend/app/models/recommendation.py` 的 JSON 字段中，`backend/app/services/vector_search.py` 和 `backend/app/services/recommendations.py` 仍然采用“先拉全量商品，再在 Python 里做 cosine similarity 和规则加分”的模式。
* `docs/recommendation_upgrade_plan.md`：执行说明文档。
  它不替代 `memory-bank/shiyige_recommendation_upgrade_plan.md`，而是把当前开发阶段必须遵守的升级顺序、基线约束和验收命令压缩成一份更适合随代码一起查看的说明。
* `backend/scripts/export_baseline_recommendation_metrics.py`：baseline 导出脚本。
  该脚本会固定 4 个搜索 query 和 2 个基线用户，自动补齐基础商品数据与行为日志，然后导出当前搜索/推荐 TopK、top1 分数、理由和耗时到 `docs/recommendation_baseline_metrics.json`。
* `backend/tests/test_recommendation_baseline.py`：baseline 导出测试。
  它在临时 SQLite 数据库里运行导出脚本，并锁定报告结构与关键字段，避免后续重构时把 baseline 导出能力一并丢失。
* `docs/recommendation_baseline_metrics.json`：当前真实基线快照。
  这份 JSON 不是设计稿，而是基于当前代码真实跑出来的对照数据，后续升级必须能继续拿同一批 query 和用户样本进行前后比较。

这里有三个新的关键架构洞察：

* “升级推荐系统”之前，必须先把“当前系统到底怎么工作”写成审计文档。
  否则后续即使换成 Qdrant、多路召回和重排，也很难回答“比旧系统到底好在哪、快在哪、为什么更像独立向量数据库”。
* baseline 导出脚本应该和业务实现解耦，但必须复用真实业务服务。
  当前导出脚本没有复制一份平行推荐算法，而是直接调用 `semantic_search_products()` 和 `recommend_products_for_user()`；这样 baseline 文件天然就是“当前线上逻辑的快照”，而不是另一个测试替身。
* baseline 快照已经暴露出当前系统的真实短板。
  例如 `宋韵茶器雅致礼物` 这类 query 在当前 `local_hash + 全量遍历 + 规则加分` 基线上无法稳定命中真正的茶器商品，这正好说明后续 Phase 4 到 Phase 6 引入真实语义模型、sparse 检索和混合搜索是必要的，而不是为了“技术栈好看”。

### 9.37 向量基础设施现在已经分成“Qdrant 连接层 + 运行时标记层 + 旧逻辑 fallback”

第 61 次同日推进并没有直接改写推荐算法，而是先把向量基础设施接线完成：

* `docker-compose.yml`：新增 `qdrant` 服务。
  当前编排会同时拉起 PostgreSQL、Redis、MinIO、Qdrant、FastAPI 和 Nginx，`6333/6334` 暴露给宿主机，Qdrant 持久化数据落在 `qdrant-data` volume。
* `backend/app/core/config.py`：新增向量数据库配置。
  `AppSettings` 现在提供 `vector_db_provider`、`qdrant_url`、三个 collection 名称和 `recommendation_pipeline_version`，让 Qdrant 接入不需要把配置硬编码到业务层。
* `backend/app/services/qdrant_client.py`：Qdrant 连接层。
  它只负责创建 client、探测可用性、读取 collections 和判断 collection 是否存在，不承载任何搜索或推荐业务逻辑。
* `backend/app/services/vector_store.py`：向量运行时抽象层。
  这个模块把“配置了什么 provider”“Qdrant 当前是否可达”“是否已降级回 baseline”“当前搜索/推荐后端是谁”统一表达成一份 runtime marker，供健康检查和接口响应复用。
* `backend/app/main.py` 与 `backend/app/api/v1/health.py`：启动探测与健康输出。
  API 启动时会探测一次 Qdrant 连接；健康检查则实时返回 `qdrant_available`、`degraded_to_baseline` 和当前 active backend。
* `backend/app/api/v1/products.py` 与 `backend/app/api/v1/search.py`：运行时标记输出。
  当前“猜你喜欢”“相似商品”“语义搜索”接口会把 `pipeline` 标记一起返回，让前台和后台能明确知道当前虽已配置 Qdrant，但这一步仍在使用 baseline 逻辑。
* `.env.example` 与 `.gitignore`：环境模板现在正式入库。
  由于仓库原先会忽略 `.env.*`，本轮显式加入 `!.env.example`，避免配置模板再次被忽略。

这里有三个新的关键架构洞察：

* 在真正把搜索切到 Qdrant 之前，先把“运行时状态可观测”做好，比直接写检索代码更重要。
  现在任何人只看 `/api/v1/health` 或推荐接口里的 `pipeline` 字段，就能知道系统是“Qdrant 可用并准备好”还是“Qdrant 不可达，仍在 fallback”。
* “Qdrant 可用”和“当前请求实际由 Qdrant 驱动”是两回事。
  本轮健康检查出现 `qdrant_available=true` 同时 `active_search_backend=baseline`，正是为了明确区分“基础设施已接通”和“业务算法已切换”这两个阶段，避免后续误判已经完成搜索改造。
* fallback 机制不应藏在异常处理里，而应显式暴露。
  当前 `vector_store.py` 会明确给出 `degraded_to_baseline`，比单纯 try/except 后默默走旧逻辑更利于排障、答辩说明和后续灰度切换。

### 9.38 商品向量层现在已经形成“Qdrant collection schema + PostgreSQL 同步元数据”的双层结构

第 62 次同日推进把 Phase 3 落到了真正可运行的 schema 层：

* `backend/app/services/vector_schema.py`：Qdrant 商品 collection 规格定义。
  当前把 `shiyige_products_v1` 固定为一个带 named vectors 的 collection：`dense` 用于后续语义召回，`sparse` 用于关键词通道，`colbert` 用于后续 late interaction rerank 预留。
* `backend/app/tasks/qdrant_schema_tasks.py`：Qdrant schema 初始化任务。
  该任务会幂等地创建 collection、建立 payload index，并返回当前 schema 摘要，供测试和启动流程复用。
* `backend/app/main.py`：应用启动时自动确保商品 collection 存在。
  现在只要 Qdrant 可达，API 启动就会先探测运行时，再自动确保 `shiyige_products_v1` 和 11 个 payload index 存在，因此 `curl /collections/shiyige_products_v1` 已经能直接看到真实 schema。
* `backend/app/models/recommendation.py`：推荐元数据表职责被重新明确。
  `product_embedding` 继续保留现有 baseline 所需的 `embedding_vector`，同时新增 `qdrant_point_id`、`qdrant_collection`、`index_status`、`index_error`；`user_interest_profile` 新增 `qdrant_user_point_id`、`profile_version`、`last_synced_at`，把“画像/商品与 Qdrant 的同步状态”正式落到业务库。
* `backend/alembic/versions/20260424_10_qdrant_vector_metadata.py`：推荐元数据迁移。
  该迁移已经真实打到 PostgreSQL，不再只是 ORM 层字段补充。
* `docs/vector_database_design.md`：向量数据库设计文档。
  这份文档把 collection、payload 字段、payload index 和 PostgreSQL 侧元数据职责写成了可以直接引用的说明。

这里有三个新的关键架构洞察：

* Qdrant schema 不是“等索引任务写的时候顺手建一下”，而应提前成为一个可验证的系统契约。
  当前 `vector_schema.py` 和 `test_qdrant_schema.py` 让 named vectors、payload index 和 collection 名称都变成了可重复验证的事实，而不是藏在后续索引代码里的隐式约定。
* PostgreSQL 仍然是推荐系统的重要组成部分，但职责已经变化。
  现在它不再被设计成主向量检索库，而是负责保存 embedding 文本、content hash、Qdrant point id、索引状态和同步错误，这样后续 Phase 5 的增量索引、失败重试和状态查询才有落点。
* “API 启动就确保 collection 存在”是比赛型项目里比“完全手工初始化”更稳的选择。
  对答辩和演示环境而言，保证 API 启动后立刻能看到 `shiyige_products_v1` 的 schema，比要求评委或开发者额外手工跑一次初始化脚本更不容易出错。

### 9.39 Embedding 层现在已经分成“公共契约层 + provider 实现层 + 注册缓存层 + 多文本构建层”

第 63 次同日推进把 Phase 4 的 embedding 服务升级完整落到了代码和配置层：

* `backend/app/services/embedding.py`：公共契约与兼容 facade。
  当前集中保存 `EmbeddingModelDescriptor`、dense/sparse/colbert 三类 provider 的抽象接口、向量归一化工具和向后兼容的 `get_embedding_provider()` 入口；现有业务代码仍从这里取 dense provider，但底层实现已经改为注册中心分发。
* `backend/app/services/embedding_dense.py`：dense provider 实现层。
  当前同时承载 `LocalHashEmbeddingProvider`、`SentenceTransformerEmbeddingProvider` 和新的 `FastEmbedDenseEmbeddingProvider`，其中默认生产配置已切到 `fastembed_dense + BAAI/bge-small-zh-v1.5(512)`。
* `backend/app/services/embedding_sparse.py`：sparse provider 实现层。
  当前提供 `LocalHashSparseEmbeddingProvider` 和 `FastEmbedSparseEmbeddingProvider`，把关键词召回所需的 sparse vector 独立出来，不再试图用 dense 向量兼任精确关键词匹配。
* `backend/app/services/embedding_colbert.py`：late interaction provider 实现层。
  当前提供 `LocalHashColbertEmbeddingProvider` 和 `FastEmbedColbertEmbeddingProvider`，输出 token-level multivector，为后续 ColBERT 重排预留统一接口。
* `backend/app/services/embedding_registry.py`：provider 注册与缓存层。
  它负责根据 `AppSettings` 构造 dense/sparse/colbert descriptor，并用 `lru_cache` 复用真实模型实例，避免每次请求都重新加载 ONNX 模型。
* `backend/app/services/embedding_text.py`：多文本构建层。
  当前不再只产出一个 `embedding_text`，而是显式生成 `title_text`、`semantic_text`、`keyword_text` 和 `rerank_text` 四路文本；`embedding_text` 只是对 `semantic_text` 的兼容别名。
* `backend/app/core/config.py`：embedding 运行时配置入口。
  现在除了 dense 配置，还显式暴露 `SPARSE_EMBEDDING_*` 和 `COLBERT_EMBEDDING_*` 配置，并新增 `EMBEDDING_CACHE_DIR` 与 `EMBEDDING_THREADS`。
* `.env.example` 与 `docker-compose.yml`：本地演示环境配置模板。
  当前 Compose 会给 API 容器注入三类 embedding 的默认模型配置，并把 `/app/backend/.cache/fastembed` 挂到 `api-model-cache` volume，避免模型重复下载。
* `backend/tests/conftest.py`、`backend/tests/api/conftest.py`、`tests/e2e/conftest.py`：测试环境的 embedding 覆写入口。
  这三处会在导入 `create_app()` 之前先把 dense/sparse/colbert provider 固定到 `local_hash`，确保单元测试、API 测试和 e2e 不依赖真实模型下载。
* `backend/tests/test_embedding_providers.py`：Phase 4 provider 验收测试。
  当前覆盖 dense/sparse/colbert 的 fake model 转换、本地 hash fallback 和注册中心分发。
* `docs/embedding_model_design.md`：embedding 设计说明。
  当前记录默认模型、维度、用途、测试环境覆写方式和四路文本构建规则，是后续搜索/推荐升级的重要引用文档。

这里有三个新的关键架构洞察：

* embedding 层必须把“接口稳定性”和“模型实现替换”拆开。
  现在业务代码继续依赖 `get_embedding_provider()` 这一稳定入口，但真正的默认模型已经从 `local_hash` 切到 `fastembed_dense`，这说明只要 facade 稳定，就可以逐阶段替换底层 provider 而不必一次性重写整条搜索/推荐链路。
* 测试环境和演示环境必须显式分离，而不能共享同一组默认值。
  当前 `AppSettings` 的生产默认值已经是真实模型，但测试夹具会在模块导入前覆写成 `local_hash`；这种“导入前固定环境 + 缓存后稳定运行”的方式，是在保留真实默认值的同时避免回归测试变慢或失败的关键。
* 商品 embedding 文本不应再是单字符串黑盒。
  现在 `semantic_text`、`keyword_text` 和 `rerank_text` 已经对应 dense、sparse 和 ColBERT 三条后续链路，这意味着 Phase 5 的索引任务和 Phase 6 的混合搜索可以直接消费结构化文本，而不需要在检索逻辑里临时拼接字段。

### 9.40 商品索引层现在已经形成“文档构建层 + Qdrant 同步任务层 + 后台运维入口”的完整闭环

第 64 次同日推进把 Phase 5 落成了真正可运行的索引链路：

* `backend/app/services/product_index_document.py`：商品索引文档构建层。
  它负责把商品、SKU、库存、标签和四路 embedding 文本组合成统一的 payload 与 named vectors，并输出可直接写入 Qdrant 的 `PointStruct`。这让 payload 字段定义、向量命名和 point id 规则不再散落在任务层。
* `backend/app/tasks/qdrant_index_tasks.py`：Qdrant 商品同步任务层。
  当前集中承载全量索引、增量索引、失败重试、删除同步和状态查询逻辑，并把结果回写到 `product_embedding.index_status/index_error/last_indexed_at`。Phase 5 之后，“商品是否已经写入 Qdrant”不再需要靠猜测，而是有正式状态源。
* `backend/app/tasks/qdrant_schema_tasks.py`：商品 collection 契约守护层。
  现在除了幂等建 collection，还会检测 named vectors 是否和当前模型配置一致；在 full 模式重建时，schema drift 会触发 collection 重建，从而把旧版 `384/128` 向量 schema 切到新版 `512/96`。
* `backend/app/api/v1/admin_vector_index.py`：后台索引运维接口。
  当前提供状态查询和同步触发入口，允许管理员查看 collection 状态、失败商品和 point 数量，并发起 full/incremental/retry/delete 四类动作。
* `backend/scripts/reindex_products_to_qdrant.py`：命令行运维入口。
  这让 Qdrant 商品索引第一次具备了正式 CLI，而不是只能依赖后台页面或交互式脚本。
* `backend/app/services/vector_search.py` 与 `backend/app/services/recommendations.py`：baseline 过滤对齐层。
  尽管真正的 Qdrant 检索还在下一阶段，当前 baseline 搜索和猜你喜欢已经开始复用 `stock_available` 语义，把缺货商品排除掉，避免新旧链路在业务过滤规则上分叉。
* `backend/tests/test_product_qdrant_indexing.py`：索引任务验收测试。
  它直接验证“全量写入 20 个 point、增量更新标签 payload、下架商品删除 point、失败后重试成功、缺货商品不进入搜索/推荐结果”。
* `backend/tests/api/test_admin_vector_index.py`：后台索引接口验收测试。
  这组测试把状态接口和同步接口的路由接线、响应结构和操作日志固定住，避免后续只剩任务层测试而接口悄悄失效。
* `docs/indexing_operations.md`：索引运维说明。
  当前把 CLI 命令、后台接口、payload 字段和增量规则写成了可以直接交给后续开发者和答辩材料引用的说明。

这里有三个新的关键架构洞察：

* 商品索引必须是正式任务，而不能继续藏在检索请求里临时触发。
  现在 Qdrant point 的生成、更新、删除和失败重试都已经从搜索/推荐请求里剥离出来，变成后台接口和 CLI 任务；这正是“独立向量数据库链路”成立的前提。
* schema drift 在模型升级后是必然会发生的运维问题，不能假装它不存在。
  本轮真实验证中，Qdrant 里原先保留了 `dense=384 / colbert=128` 的旧 schema；如果没有在 full 模式里检测并重建 collection，新的 `512 / 96` 模型根本无法落索引。这说明“向量 schema 迁移”本身就是系统设计的一部分。
* `status` 和 `stock_available` 必须分开表达。
  当前索引层已经把“商品下架”定义为 point 删除，把“商品缺货”定义为 point 保留但过滤掉结果；这让后续 Phase 6 的 payload filter、Phase 7 的推荐召回和后台统计都可以基于同一套业务语义演进，而不会在一个字段上混杂多种状态。

### 9.41 搜索层现在已经形成“结构化过滤层 + 双路召回层 + 本地精排层 + 运行时切换层”的 Phase 6 形态

第 65 次同日推进把 Phase 6 的混合搜索链路接到了真实接口上：

* `backend/app/services/search_filters.py`：结构化过滤抽象层。
  当前把 `category_id`、价格区间、朝代风格、工艺、场景、节令和 `stock_only` 收敛成统一的 `SearchFilters`，并同时生成 Qdrant payload filter、baseline 商品过滤和日志序列化结果，避免新旧搜索路径各自维护一份筛选语义。
* `backend/app/services/search_reranker.py`：搜索精排信号层。
  当前集中保存 RRF 分数函数、ColBERT max-sim、本地 payload 语义 bonus、业务 bonus 和最终 reason 组装逻辑；这样 dense/sparse/ColBERT/文化特征的分数解释不再散落在主搜索函数里。
* `backend/app/services/hybrid_search.py`：Qdrant hybrid search 执行层。
  当前会对 query 同时生成 dense、sparse 和 ColBERT 向量；先在 Qdrant 里做 dense top 100 与 sparse top 100 召回，再在应用层做 RRF 融合，接着只对 Top 50 候选回取 ColBERT multivector 做本地重排，最后再按最终候选 ID 回表加载商品详情。
* `backend/app/services/vector_search.py`：公开搜索入口与 baseline 分界层。
  现在 `semantic_search_products()` 负责根据运行时状态选择 `qdrant_hybrid` 或 `baseline_semantic_search_products()`；旧的 PostgreSQL JSON 向量 + Python cosine 路径没有删除，而是被显式保留下来作为 fallback 与对照组。
* `backend/app/services/vector_store.py`：搜索 readiness 判定层。
  当前不再只检查“Qdrant 是否连得通”，而是进一步检查商品 collection 是否存在、schema 是否匹配当前 embedding 配置、以及 collection 是否已经写入 points；只有这些条件都满足时，`active_search_backend` 才会切成 `qdrant_hybrid`。
* `backend/app/api/v1/search.py` 与 `backend/app/schemas/search.py`：语义搜索接口层。
  当前 `POST /api/v1/search/semantic` 已支持 Phase 6 需要的全部结构化过滤字段，并会把过滤条件与当前搜索后端一起写进 `semantic_search` 行为日志。
* `backend/scripts/export_baseline_recommendation_metrics.py`：baseline 稳定性保护层。
  由于 Phase 6 之后默认搜索路径会切到 Qdrant，这个脚本现在显式传入 `force_baseline=True`，确保 Phase 1 导出的 baseline 指标仍然对应旧搜索逻辑，而不是被新的 hybrid runtime 污染。
* `backend/tests/test_search_filters.py` 与 `backend/tests/test_hybrid_search.py`：Phase 6 验收测试层。
  前者固定结构化过滤在 Qdrant 与 baseline 上的一致性；后者同时验证 RRF 融合、ColBERT 精排和“真实写入 Qdrant 后 `semantic_search_products()` 会走 hybrid 路径并尊重库存过滤”。
* `docs/search_pipeline.md`：搜索链路说明文档。
  当前把运行时切换条件、过滤字段、召回阶段、精排阶段和 fallback 契约写成了后续开发者与答辩材料都能直接引用的说明。

这里有三个新的关键架构洞察：

* “Qdrant 可用”不等于“Qdrant 搜索已经可以接流量”。
  当前只有在 collection 存在、schema 正确且 points 已写入后，系统才会把 `active_search_backend` 从 `baseline` 切到 `qdrant_hybrid`；这避免了“容器起来了，但搜索结果因为空 collection 直接变成空列表”的假切换。
* 结构化过滤必须同时约束 Qdrant 路径和 baseline 路径。
  现在 `search_filters.py` 同时服务于 payload filter 和 ORM fallback，意味着无论当前请求是否降级到 baseline，`category_id`、价格区间、朝代、工艺、节令、场景和库存语义都保持一致，不会出现“同一个接口在两条路径上筛选规则不同”的问题。
* 混合搜索真正替代“全量遍历”，关键不在于把向量搬进 Qdrant，而在于只回表最终候选。
  当前 `hybrid_search.py` 先在 Qdrant 内部做 dense/sparse 召回，再只把 Top 50 候选的 ColBERT 向量和最终少量商品 ID 拉回应用层；这已经从架构上切断了过去“先从 PostgreSQL 拉全量商品，再逐个算余弦”的旧模式。

### 9.42 推荐层现在已经形成“多路召回通道 + 候选融合层 + 多样性层 + 调试证据层”的 Phase 7 形态

第 66 次同日推进把首页推荐从单一路径升级成了真正的多路召回结构：

* `backend/app/services/recommendation_pipeline.py`：推荐编排层。
  当前负责构建用户画像、判断是否冷启动、调用各召回通道、做候选融合和多样性控制，并把最终候选包装成带 `recall_channels`、`channel_details`、`matched_terms`、`vector_score` 和 `term_bonus` 的统一对象。
* `backend/app/services/recall_content.py`：内容召回层。
  这里同时提供两条内容相关通道：一条是用 `UserInterestProfile.embedding_vector` 去 Qdrant 做 dense 召回的 `content_profile`；另一条是用用户最近浏览/加购商品的 dense vector 做相似商品延展的 `related_products`。这使推荐系统第一次具备了“用户整体兴趣”和“最近种子商品”两种内容视角。
* `backend/app/services/recall_sparse_interest.py`：关键词兴趣召回层。
  当前会把 `top_terms` 拼成 sparse query，命中 Qdrant 里的类目、标签、朝代、工艺、场景和节令 payload，从而让推荐不只依赖 dense 语义画像。
* `backend/app/services/recall_collaborative.py`：轻量协同过滤召回层。
  当前基于 `user_behavior_log` 中与当前用户有共同商品行为的其他用户，聚合这些相似用户进一步浏览/加购的商品，形成不依赖内容向量的协同候选。这还是 Phase 7 的轻量版本，真正的 sparse user vector 和 item-item 共现索引会在 Phase 8 深化。
* `backend/app/services/recall_trending.py`：热门趋势召回层。
  当前按最近 7 天行为日志的加权热度聚合商品，作为“站内流行趋势”补充通道。
* `backend/app/services/recall_new_arrival.py`：新品探索召回层。
  当前按商品创建时间倒序挑选上新商品，并只保留在售有库存的结果，用于给主推荐流补充探索性候选。
* `backend/app/services/candidate_fusion.py`：候选融合层。
  当前把所有召回通道统一成标准化 `RecallItem`，再用带通道权重的 RRF 做融合；同一个商品会保留全部召回来源与明细，而不是在融合时丢失证据链。
* `backend/app/services/diversity.py`：结果去同质化层。
  当前对重复类目、重复朝代和重复工艺做轻量惩罚，防止最终推荐列表被单一群组完全占满。
* `backend/app/services/recommendations.py`：公开推荐入口与 baseline 分界层。
  现在 `recommend_products_for_user()` 会在运行时检查 `active_recommendation_backend`，默认优先使用 Phase 7 的多路召回管线；旧的单画像向量 + 全量遍历逻辑被保留下来作为 `baseline_recommend_products_for_user()`。
* `backend/app/services/vector_store.py`：推荐 readiness 标记层。
  当前 `active_recommendation_backend` 已不再固定为 `baseline`，而是在商品 collection ready 时切换为 `multi_recall`，因此健康检查和接口 `pipeline` 字段终于能区分“旧推荐”和“新推荐”。
* `backend/app/api/v1/admin_recommendations.py`：推荐调试证据层。
  当前后台调试接口直接消费 `RecommendationPipelineRun`，除了画像文本和消费商品外，还会把每个候选的 `recall_channels` 与 `channel_details` 一起返回，使后台真正能展示“这个推荐是被哪几条召回链路带出来的”。
* `docs/recommendation_pipeline.md`：推荐管线说明文档。
  当前把运行时入口、召回通道、融合层、多样性层和调试输出写成了一份可以直接被后续开发和答辩材料引用的说明。

这里有三个新的关键架构洞察：

* 推荐系统的“多路召回”不是把几个排序规则堆到一起，而是让每条通道都能独立产出候选和证据。
  现在每个 `RecallItem` 都明确记录了 `recall_channel`、`recall_score`、`rank_in_channel`、`matched_terms` 和 `reason_parts`，这意味着后续无论接更强的排序模型还是做离线评估，都不会丢失候选的来源信息。
* 冷启动不应只是“没有画像时返回热门榜”，而应是正式的召回策略分支。
  当前 `recommendation_pipeline.py` 会在用户行为不足时显式生成 `cold_start` 通道，并把热门与新品混合进同一条证据链里；这样冷启动推荐不再是“其他通道失败后的副作用”，而是可解释的正式策略。
* 推荐接口“不全表扫描商品”的关键在于把全局信息拆回各自合适的数据源。
  现在内容与关键词召回走 Qdrant，协同过滤走用户行为日志，热门与新品走有界 SQL 查询，最后只把融合后的有限候选商品回表加载；这和旧版 `load_active_products_for_recommendations()` 再全量打分的思路已经是两套完全不同的系统边界。

### 9.43 协同过滤层现在已经形成“行为加权层 + 稀疏用户索引层 + 离线共现图层 + 双通道召回层”的 Phase 8 形态

第 67 次同日推进把 Phase 8 的协同过滤从“轻量日志聚合”升级成了可离线构建、可持久化、可解释的正式召回层：

* `backend/app/services/collaborative_filtering.py`：协同过滤核心服务层。
  当前集中保存行为权重表、时间衰减规则、`build_user_sparse_vector()`、相似用户 sparse 检索、item-item 共现图构建和两类召回结果的统一 `RecallItem` 输出。这里把 “product_id 作为 sparse 维度” 的设计固定下来，使协同过滤结果可以直接解释为“哪些商品行为导致了用户相似”。
* `backend/app/tasks/collaborative_index_tasks.py`：离线构建任务层。
  当前负责幂等创建 `QDRANT_COLLECTION_CF`、写入每个用户的 sparse `interactions` 向量、建立 `user_id` payload 索引，并把离线 item 共现图和构建元数据回写到数据库。Phase 8 之后，协同过滤不再只是请求时临时扫日志，而是有了正式的离线 build 步骤。
* `backend/app/models/recommendation_experiment.py`：推荐实验与工件元数据层。
  当前新增 `recommendation_experiment` 表，用于持久化 `experiment_key`、`strategy`、`pipeline_version`、`model_version`、`config_json` 和 `artifact_json`；本轮主要承载 `collaborative_item_cooccurrence_v1` 的离线工件，但表结构本身已经能继续支持后续排序特征缓存或实验快照。
* `backend/alembic/versions/20260424_11_recommendation_experiment.py`、`backend/alembic/env.py` 与 `backend/app/models/__init__.py`：迁移接线层。
  当前保证新实验表会进入 Alembic 元数据扫描，并随容器启动自动迁移，不需要后续开发者手工补建表。
* `backend/scripts/build_collaborative_index.py`：离线运维入口。
  当前提供正式 CLI，可直接从仓库根目录执行；脚本会在需要时补齐 ORM 元数据，并在 `http://qdrant:6333` 与 `http://127.0.0.1:6333` 间自动选择可用地址，兼容 Compose 容器内和本地直连两种运行方式。
* `backend/app/services/recall_collaborative.py`：协同召回分发层。
  当前不再自己做日志聚合，而是明确拆成 `collaborative_user` 与 `item_cooccurrence` 两条通道，并把两类结果作为独立 source 返回给推荐编排层。
* `backend/app/services/candidate_fusion.py` 与 `backend/app/services/recommendation_pipeline.py`：协同通道接入层。
  当前融合层已经识别新的协同过滤通道权重，推荐主流水线也会把两条通道的 `recall_channels`、`channel_details` 和原因说明原样带到最终调试响应里，不会在融合阶段丢失证据链。
* `backend/tests/test_collaborative_filtering.py` 与 `backend/tests/test_recommendation_pipeline.py`：Phase 8 验收测试层。
  前者验证 sparse 用户索引、相似用户召回和 item 共现召回的基本正确性；后者验证完整推荐流水线确实把 `collaborative_user` / `item_cooccurrence` 接到了最终候选集合里。
* `docs/collaborative_filtering_design.md`：协同过滤设计说明文档。
  当前把行为权重、时间衰减、Qdrant collection 契约、离线工件 key 和运行边界写成了后续开发者可直接复用的说明。

这里有三个新的关键架构洞察：

* 协同过滤的离线产物必须成为正式资产，而不是继续藏在请求时临时计算里。
  现在 sparse 用户索引写入 Qdrant，item 共现图写入 `recommendation_experiment`，这意味着“构建何时发生、工件存在哪里、运行时如何回退”都有了清晰边界；后续无论做 cron、手工运维还是实验回滚，都不需要重新把逻辑塞回接口请求里。
* `collaborative_user` 和 `item_cooccurrence` 必须保留为两条独立召回通道，而不是过早混成一个协同分。
  前者回答“和我相似的人还喜欢什么”，后者回答“和我最近看的商品经常一起出现什么”；它们的可解释性、冷启动表现和后续排序特征价值都不同，所以在 `channel_details` 里分开保留证据是必要的。
* 以 `product_id` 作为 sparse 向量维度，是比赛型推荐系统里比“复杂 latent factor 训练”更稳的第一步。
  这种表示法天然支持行为权重和时间衰减，也便于直接映射到“哪些商品行为导致了相似用户召回”；在答辩、调试和运维上都比黑盒 embedding 更容易解释和修正。

### 9.44 排序层现在已经形成“特征构建层 + Ranker 层 + 业务后处理层 + 双调试出口层”的 Phase 9 形态

第 68 次同日推进把推荐系统从“多路召回 + 融合分”推进到了真正的统一排序层：

* `backend/app/services/ranking_features.py`：排序特征构建层。
  当前会为每个候选同时构造 recall 特征、用户兴趣特征、商品质量特征和业务规则特征，并给出原始值与归一化视图。Phase 9 之后，推荐排序终于不再只是消费 `fusion_score` 和 `matched_terms`，而是有了一份正式的候选特征向量。
* `backend/app/services/ranker.py`：统一排序入口。
  当前实现默认 `weighted_ranker`，把最终分明确拆成 `recall_score`、`interest_score`、`quality_score`、`business_total` 和 `final_score`；同时它也负责接 `ltr_ranker` 的预测入口，并在模型不可用时自动回退到加权排序器。
* `backend/app/services/ltr_ranker.py`：LTR 兼容层。
  当前还没有接真实 LightGBM / XGBoost 模型，但已经完成“按配置加载 JSON 权重模型 + 失败时回退”的接口契约。这样后续进入 Phase 10 时，LTR 不需要重新改推荐主链路，只需要补训练样本和模型文件。
* `backend/app/services/business_rules.py`：业务后处理层。
  当前把“近期曝光降权、同类目连续上限、朝代/工艺集中度控制、探索位注入”从召回或融合逻辑中剥离出来，成为排序后的独立 post-processing 层。这让“业务约束”和“候选打分”终于分清了职责。
* `backend/app/services/recommendation_explainer.py`：排序解释层。
  当前负责把原始特征和分数拆解压缩成 `feature_summary`、`feature_highlights` 和最终解释文案，使公开 debug 接口和后台 debug 接口使用统一口径展示排序原因。
* `backend/app/services/recommendation_pipeline.py`：推荐编排层。
  当前已从“召回后直接做 diversity”升级为“召回 -> 特征构建 -> ranker -> 业务后处理 -> 最终候选”，并在 `RecommendationPipelineRun` 中正式暴露 `active_ranker`、`ranker_model_version` 和 `ltr_fallback_used`。
* `backend/app/core/config.py`：排序运行时配置入口。
  当前新增 `recommendation_ranker`、`recommendation_ltr_model_path`、`recommendation_exploration_ratio` 和 `recommendation_max_consecutive_category`，把排序器切换和后处理阈值纳入正式配置，而不是硬编码在函数内部。
* `backend/app/services/vector_store.py`：运行时标记层。
  当前 `build_runtime_marker()` 已能返回 `configured_recommendation_ranker`，使接口 `pipeline` 元数据不仅能说明“推荐后端是不是 multi_recall”，还能说明“当前配置想用哪种排序器”。
* `backend/app/api/v1/products.py`：公开推荐与调试出口。
  当前保留原有 `/api/v1/products/recommendations`，同时新增 `/api/v1/recommendations` 别名；当 `debug=true` 时，公开接口会直接返回 `ranking_features`、`feature_summary`、`feature_highlights`、`score_breakdown` 和 `ranker_name`。
* `backend/app/api/v1/admin_recommendations.py`：后台调试出口。
  当前不仅返回召回证据，还会把排序特征和打分拆解完整输出，使后台真正成为“召回 + 排序”双视角的调试界面，而不只是 recall trace view。
* `backend/tests/test_ranking_features.py` 与 `backend/tests/test_ranker.py`：Phase 9 验收测试层。
  前者固定特征工程的输出边界，后者固定“兴趣匹配优先于单一召回分”和“LTR 缺席时安全回退”的行为边界。
* `docs/ranking_design.md`：排序设计说明文档。
  当前把特征组、ranker 切换、post-processing 规则和 debug 输出写成了独立文档，是后续 Phase 10 评估和答辩材料的直接入口。

这里有三个新的关键架构洞察：

* 多路召回完成后，真正决定体验的已经不是“再多加一条召回通道”，而是“有没有统一的排序层把不同信号放到同一尺度上”。
  当前 `ranking_features.py + ranker.py` 的组合，第一次把 recall、兴趣、质量和业务约束同时放进了同一条打分链路；这比继续在 `candidate_fusion.py` 上堆启发式权重更可控，也更容易演进到 LTR。
* `weighted_ranker` 和 `ltr_ranker` 必须共享同一份特征契约，而不是各自维护一套输入。
  现在无论是加权排序还是未来 LTR，都消费 `RecommendationRankingFeatures`；这意味着后续训练、离线评估和线上推理都可以围绕同一份特征定义展开，而不会出现“训练特征”和“线上特征”两套体系逐渐漂移。
* 排序 debug 必须同时出现在公开接口和后台接口，而不能只留在管理员视角。
  当前 `/api/v1/recommendations?slot=home&debug=true` 和后台 debug 都能看到 `feature_summary` 与 `score_breakdown`，这让“推荐为什么这样排”不再只能靠后台解释；对演示、联调和后续日志验证都更有价值。

### 9.45 评估层现在已经形成“行为埋点层 + 评测脚本层 + 压测脚本层 + 报告产出层”的 Phase 10 形态

第 69 次同日推进把推荐系统从“能调试解释”推进到了“能量化评估和压测”：

* `backend/app/models/recommendation_analytics.py`：推荐与搜索分析日志模型层。
  当前集中定义 `recommendation_request_log`、`recommendation_impression_log`、`recommendation_click_log`、`recommendation_conversion_log`、`search_request_log` 和 `search_result_log` 六张表，使请求、曝光、点击、转化和搜索结果有了正式持久化落点。
* `backend/alembic/versions/20260424_12_recommendation_logging.py`：Phase 10 迁移层。
  当前把上述六张日志表正式纳入 Alembic 迁移链，后续开发者不需要手工补表就能接着用埋点数据做报表、训练集或答辩演示。
* `backend/app/services/recommendation_logging.py`：埋点编排层。
  当前统一处理请求计时、推荐请求/曝光写入、搜索请求/结果写入，以及“根据最近曝光反查 request_id 再记录点击/加购/下单/支付”的归因逻辑；接口层只需要调用服务，不再自己处理日志主键和去重。
* `backend/app/api/v1/products.py`：推荐请求与点击归因入口。
  当前首页推荐接口会在返回结果后写入 request/impression 日志；商品详情接口则会在用户点进推荐商品时把动作回填成 `click`，从而把曝光和点击串起来。
* `backend/app/api/v1/search.py`：搜索日志入口。
  当前关键词搜索和语义搜索都会记录 `query`、`mode`、`pipeline_version`、过滤条件、延迟和返回结果列表，使搜索效果评估不再只能依赖行为日志推断。
* `backend/app/api/v1/cart.py` 与 `backend/app/api/v1/orders.py`：转化归因入口。
  当前加购、下单和支付接口都会尝试沿着最近曝光记录回填 `add_to_cart`、`create_order` 和 `pay_order`，这意味着推荐链路终于具备了完整的曝光到支付归因闭环。
* `backend/scripts/generate_synthetic_catalog.py`：合成商品集生成层。
  当前支持把商品量扩到指定规模，并明确只从非 synthetic 模板复制，避免压测多次后 synthetic 商品再去复制 synthetic 商品导致数据质量失控。
* `backend/scripts/evaluate_recommendations.py`：离线评测执行层。
  当前会准备 Qdrant 商品索引和协同过滤索引，构造三组用户场景，并输出 `baseline`、`dense_only`、`dense_sparse`、`dense_sparse_colbert`、`multi_recall_weighted`、`multi_recall_ltr` 和 `multi_recall_ltr_diversity` 七组对比指标到 `docs/recommendation_evaluation.md`。
* `backend/scripts/benchmark_recommendations.py`：性能压测执行层。
  当前会扩容商品集、生成合成用户、重建 Qdrant 索引、预热接口，并测量 `search_keyword`、`search_semantic`、`recommend_home`、`related_products`、`reindex_products_qdrant` 和 `build_collaborative_index` 的 p50/p95/p99、QPS、错误率与候选数量，再输出到 `docs/performance_benchmark.md`。
* `docs/recommendation_evaluation.md` 与 `docs/performance_benchmark.md`：报告产出层。
  当前已经不只是“脚本打印 JSON”，而是有了可以直接提交和答辩展示的 Markdown 报告文件；Phase 10 之后，推荐系统第一次具备了正式的评测文档资产。
* `backend/tests/api/test_recommendation_logging.py`：Phase 10 验收测试层。
  当前固定了推荐请求/曝光、点击与转化、搜索日志的关键行为，确保后续继续改推荐接口时不会把归因链静默打断。

这里有四个新的关键架构洞察：

* 埋点必须跟请求链路同构，而不是等行为日志事后推断。
  当前推荐请求、曝光、点击、加购、下单和支付都显式落在分析表里，意味着后续做 CTR、CVR、Add-to-cart Rate 时不需要再从 `user_behavior_log` 里猜测“这个订单是不是来自推荐”。
* 评估脚本和线上接口必须共享同一份运行时能力，而不是另起一套“论文版”逻辑。
  现在 `evaluate_recommendations.py` 直接复用了推荐主流水线、排序器、Qdrant 索引和协同过滤构建步骤，所以离线指标对线上实现是有约束力的，不是脱离主代码的平行实验。
* 压测结果已经明确暴露出系统边界，而不是只证明“脚本跑通”。
  当前 10k 商品基准下，`recommend_home` 的 `p95` 达到 38 秒级，`related_products` 的 `p95` 达到 65 秒级，这说明真正的瓶颈已经从“模型能不能接上”转移到“画像、候选和相似商品是否有缓存/索引化”。
* `related_products` 现在是整个推荐链里最不适合继续放大的旧边界。
  它仍使用全库 embedding 相似度计算，而首页推荐和语义搜索已经进入 Qdrant / 多路召回时代；如果后续 Phase 11 要展示更大规模演示数据，优先级最高的技术债就是把相似商品接口从全量扫描迁到向量库或缓存层。

### 9.46 Phase 11 现在已经形成“前台证据化展示层 + 后台推荐看板层 + 并发安全 embedding 引导层”的完整答辩形态

第 70 次同日推进把 Phase 11 从“推荐系统能跑”推进到了“老师打开页面就能直接看到证据”的展示阶段：

* `front/js/main.js`：前台推荐展示共享层。
  当前新增 `window.shiyigeRecommendationUI`，统一负责来源徽章、搜索解释标签、推荐理由证据块和商品卡片渲染。Phase 11 之后，首页、搜索页、详情页、购物车页和结算成功态不再各自拼一套 HTML，而是共享同一份推荐/搜索可视化组件。
* `front/js/home-page.js`：首页推荐证据层。
  当前登录态首页会请求 `GET /api/v1/products/recommendations?limit=3&slot=home&debug=true`，直接渲染个性化来源、推荐理由和证据标签；未登录或接口失败时则回退到最新商品，并明确标成“新品探索”而不是假装个性化。
* `front/js/category-page.js`：搜索解释展示层。
  当前关键词搜索和语义搜索结果都会显示 `reason`、`search_mode` 和解释标签，例如“语义相关”“关键词命中”“文化标签匹配”；这让搜索页第一次具备了“为什么出现这条结果”的可视化说明。
* `front/js/product.js`：详情页相似商品展示层。
  当前相关推荐已经开始消费标准化的推荐来源字段，并复用共享卡片展示相似理由，使详情页能直接说明“为什么这几个商品和当前商品相近”。
* `front/cart.html` 与 `front/js/cart.js`：购物车推荐展示层。
  当前购物车页新增独立推荐面板，先尝试基于购物车商品拉取相似推荐，失败时退回个性化 `slot=cart`；这使购物车不再只是交易页，也成为推荐系统的答辩展示位。
* `front/checkout.html` 与 `front/js/checkout.js`：订单完成推荐展示层。
  当前支付成功弹窗内新增推荐区域，优先展示“基于刚下单商品的关联推荐”，必要时回退到个性化 `slot=order_complete`；推荐系统首次进入完整交易链路的尾部展示位。
* `front/css/style.css`：推荐解释样式层。
  当前补齐推荐徽章、解释标签、原因文本和证据区样式，使新增说明信息不会破坏现有静态前端风格。
* `backend/app/api/v1/products.py`：推荐公开接口展示协议层。
  当前推荐结果统一带 `source_type`、`source_label`、`reason`，debug 模式下还会带 `matched_terms`、`recall_channels`、`feature_highlights`、`feature_summary` 和 `score_breakdown`；这让前台展示和后台调试使用同一份结构化证据。
* `backend/app/api/v1/search.py`：搜索公开接口展示协议层。
  当前关键词搜索会输出 `score`、`reason`、`search_mode` 和 `explanations`，语义搜索也会输出 `search_mode` 和解释标签；前台搜索页因此可以直接做解释展示，而不是自己推断搜索模式。
* `backend/app/services/recommendation_admin.py`：后台聚合服务层。
  当前统一聚合推荐 KPI、搜索指标、向量运行状态、索引摘要和实验配置，让后台首页与配置页都能基于单一服务输出渲染，不必在前端拼多个来源。
* `backend/app/api/v1/admin_dashboard.py`：后台看板接口层。
  当前除了用户/商品/订单统计外，还返回 `runtime`、`vector_index`、`recommendation_metrics`、`search_metrics` 和 `experiments`，使后台首页真正成为推荐系统运行总览而不是普通电商仪表盘。
* `backend/app/api/v1/admin_recommendations.py`：后台调试与实验配置接口层。
  当前推荐调试接口已同时支持 `user_id` 与 `email` 两种用户定位方式，并新增实验配置读取接口，使后台能展示召回/排序证据和当前 pipeline 方案。
* `admin/index.html`：后台推荐效果看板页。
  当前首页已扩展为展示推荐 CTR、加购率、转化率、覆盖率、平均延迟，以及 Qdrant / 搜索 / 实验概况的总览页。
* `admin/reindex.html`：向量索引运维页。
  当前除旧的重建按钮外，还能展示 Qdrant 连接状态、collection 状态、已索引商品数、失败商品数和失败明细，并支持 full rebuild 与 retry failed 两种入口。
* `admin/recommendation-debug.html`：推荐调试页。
  当前支持输入 `user_id` 或邮箱，查看召回通道、排序特征、最终理由和候选细节，使后台调试正式具备“按用户追一条推荐证据链”的能力。
* `admin/recommendation-config.html`：实验方案展示页。
  当前以静态前端方式直接展示 `baseline`、`hybrid`、`hybrid_rerank` 和 `full_pipeline` 四档实验方案与当前运行配置，补上了答辩所需的“实验设计可视化”页面。
* `admin/js/app.js`：后台统一交互编排层。
  当前除了登录和基础页面加载外，还负责 dashboard KPI 渲染、vector status 渲染、调试查询、实验配置页渲染，以及 Qdrant 不可用时的 reindex 兼容回退。
* `admin/css/admin.css`：后台展示风格层。
  当前新增工具栏、调试表单栅格、配置页和指标卡片样式，使后台推荐看板、调试页和配置页共享统一视觉系统。
* `backend/app/services/qdrant_client.py` 与 `backend/app/services/vector_store.py`：运行时探测降噪层。
  当前 Qdrant 连接状态新增短 TTL 缓存，同时 runtime 判定避免同一轮请求里重复探测；这保证前后台展示页在频繁刷新指标时不会因为探活过多而明显卡顿。
* `backend/app/tasks/embedding_tasks.py`：并发安全的 embedding 引导层。
  当前商品 embedding 首次写入已从“依赖 ORM 关系状态”改成“显式按 `product_id` 回查 + 数据库原子 upsert”，并能处理 stale session relation；这修复了登录后首页自动拉推荐与测试代码同时请求推荐时触发的 `UNIQUE constraint failed: product_embedding.product_id`。
* `backend/tests/api/test_admin_dashboard.py`、`backend/tests/tasks/test_embedding_tasks.py`、`tests/e2e/test_admin_basic.py`、`tests/e2e/test_recommendation_ui.py`、`tests/e2e/test_cart_flow.py`、`tests/e2e/test_checkout_flow.py`、`tests/e2e/test_full_demo_flow.py`：Phase 11 验收测试层。
  当前既锁定后台看板和推荐调试响应结构，也锁定首页/搜索/购物车/下单成功态的推荐展示和并发首写场景，避免展示层升级后把真实推荐链路打穿。

这里有三个新的关键架构洞察：

* Phase 11 的前台推荐卡片已经不再只是“商品展示组件”，而是推荐系统的证据载体。
  现在每个展示位都能把来源类型、推荐理由和搜索解释直接渲染出来，意味着推荐系统的可解释性第一次进入用户可见层，而不是只存在于后台 debug JSON。
* 后台推荐页面的关键不是“多做几个按钮”，而是建立统一的聚合快照。
  当前 `recommendation_admin.py` 把 KPI、Qdrant 状态、索引摘要和实验方案收成一个稳定输出，这让后台静态页面可以更轻、更稳地展示系统全貌，也为后续加更多指标保留了清晰扩展点。
* 当首页登录成功后会自动发起推荐请求时，embedding 初始化就必须被视为并发入口而不是离线预热细节。
  本轮暴露出的 `product_embedding.product_id` 唯一键冲突证明：只要首页和测试/脚本同时拉推荐，商品 embedding 就会面临真实并发首写；因此 `embedding_tasks.py` 的幂等 upsert 现在已经是推荐展示层稳定性的基础设施，而不是单纯的数据任务实现。

### 9.47 Phase 12 现在已经形成“文档资产层 + 答辩讲稿层 + 最终验收约束层”的收尾形态

第 71 次同日推进把推荐系统从“实现完成”推进到了“可答辩、可验收、可复盘”的最终状态：

* `docs/vector_database_design.md`：向量数据库设计总说明。
  当前明确解释了为什么旧版“业务库 JSON 向量 + Python cosine”不够、为什么当前选择 Qdrant 而不是继续把 pgvector 当主方案，以及商品/协同过滤 collection、payload index、同步元数据和降级策略的职责边界。
* `docs/recommendation_pipeline.md`：推荐主链路文档。
  当前把多路召回、候选融合、排序、业务重排、冷启动和推荐理由串成了一张清晰流程图，使答辩时可以按模块解释，而不是临场从代码里找函数名。
* `docs/search_pipeline.md`：搜索主链路文档。
  当前把 dense+sparse hybrid retrieval、RRF、ColBERT rerank、过滤条件下推和解释生成都写成了正式说明，能直接回应“搜索是不是只是换个名字的 cosine”。
* `docs/recommendation_evaluation.md`：离线评估报告层。
  当前不再只是脚本打印的 Markdown 表，而是加入了场景定义、指标解释、模式对比和结论段，使 `baseline`、`dense_sparse_colbert`、`multi_recall_ltr` 之间的差异可直接作为答辩证据引用。
* `docs/performance_benchmark.md`：性能报告层。
  当前整理了 100 / 1000 / 10000 三档真实压测数据，并把 100000 商品规模明确写成容量推演而不是含糊带过；这让性能边界本身也成为可解释资产。
* `docs/defense_script.md`：答辩讲稿层。
  当前把开场讲稿、演示顺序和高频 FAQ 固定成一份统一口径文档，确保“不是只算余弦”“为什么不是 pgvector”“推荐系统完整性体现在哪”这些问题有工程一致的回答。
* `backend/app/services/qdrant_client.py`：Qdrant 状态缓存与失效层。
  当前除了短 TTL 状态缓存外，还新增 `invalidate_qdrant_connection_status(...)`，确保 collection 刚创建或 point 刚写入后，运行时探测不会继续读到几秒前的旧状态。
* `backend/app/tasks/qdrant_index_tasks.py`：索引写入后的状态同步层。
  当前在 full sync / delete 成功提交后会主动失效 Qdrant 状态缓存，从而保证 `probe_vector_store_runtime()`、后台索引看板和健康检查读到的是最新 collection 事实。
* `backend/tests/unit/test_settings.py`：环境隔离守护层。
  当前明确清掉 `QDRANT_URL` 环境变量，避免全量测试时被其他测试模块的 `os.environ.setdefault(...)` 污染；这保证“默认配置测试”测的真的是默认值，而不是全局副作用。
* `memory-bank/progress.md` 与 `memory-bank/architecture.md`：最终交接层。
  当前不仅记录了 Phase 12 的文档资产，还明确记下了最终验收时暴露出的 Qdrant 状态缓存失效约束和 Compose PostgreSQL 验收方式，为下一位开发者保留稳定入口。

这里有三个新的关键架构洞察：

* 对比赛型系统来说，文档和讲稿不是附属物，而是系统架构的一部分。
  当系统已经拥有多路召回、向量数据库和后台调试页后，如果没有统一的设计文档和答辩口径，老师看到的仍然只是“很多零散功能”；Phase 12 实际上是在给实现补上可解释、可证明的外层结构。
* 一旦引入运行时状态缓存，就必须同步设计缓存失效协议。
  本轮暴露出的 bug 说明：即使缓存 TTL 只有几秒，只要 collection 生命周期变化比 TTL 更快，runtime marker 就会出现“索引已经写入，但系统还以为没准备好”的错误判断。也就是说，Qdrant 状态缓存不是单纯的性能优化点，而是带有一致性语义的基础设施。
* 最终验收脚本依赖的数据库必须与当前迁移链保持同构。
  `backend/dev.db` 在本轮暴露出 schema 落后于 Alembic 的事实，所以最终验收改为显式指向 Compose PostgreSQL；这说明当前项目的“正式验收环境”已经不再是临时 SQLite，而是容器化 PostgreSQL + Qdrant 组合。

### 9.48 Phase 13 现在已经形成“协议对齐层 + 字段透传层 + 路由兼容层”的最终接口形态

第 72 次同日推进把推荐系统后半段文档里的接口规划真正落到了可调用 API 上：

* `backend/app/services/hybrid_search.py`：搜索分数透传层。
  当前 `HybridSearchHit` 已不再只保留一个最终分，而是显式携带 `matched_terms`、`dense_score`、`sparse_score`、`rerank_score` 和 `pipeline_version`。这让 Qdrant hybrid 路径的 dense/sparse/ColBERT 中间证据第一次能够完整穿透到公开接口，而不是在服务层被折叠成一句 `reason`。
* `backend/app/services/vector_search.py`：搜索与相似商品的兼容协议层。
  当前 `VectorSearchResult` 已扩成统一元数据容器，baseline 语义搜索会补齐 `matched_terms`、`dense_score` 和 `pipeline_version`，相似商品路径还会额外携带 `source_breakdown` 与 `diversity_result`。这意味着 baseline 与 Qdrant 路径终于开始共享同一套公开协议，而不是“功能上能降级、字段上却完全两套”。
* `backend/app/api/v1/search.py`：最终搜索接口层。
  当前新增 `GET /api/v1/products/search`，参数和字段形态对齐了计划文档第 13.1 节，同时保留原有 `/api/v1/search` 与 `/api/v1/search/semantic`。关键词搜索也已补齐 `final_score`、`matched_terms` 和 `pipeline_version`，所以旧页面和新协议现在都能共存。
* `backend/app/api/v1/products.py`：推荐与相似商品最终协议层。
  当前首页推荐默认返回 `recall_channels`、`final_score`、`reason` 和 `is_exploration`，debug 模式下还同时暴露 `rank_features` 与旧字段 `ranking_features`；相似商品接口则把 `dense_similarity`、`co_view_co_buy`、`cultural_match`、完整 `source_breakdown` 与 `diversity_result` 一并返回，满足第 13.2 和第 13.3 节的公开结构要求。
* `backend/app/api/v1/admin_vector_index.py`：索引运维兼容入口层。
  当前在原有 `/products/status`、`/products/sync` 基础上新增了 `/status`、`/rebuild` 和 `/products/{product_id}/reindex`，使后台索引接口既保留旧页面能用的入口，也拥有文档要求的最终命名。
* `backend/app/api/v1/admin_recommendations.py`：后台推荐兼容入口层。
  当前新增 `alias_router`，把 `/api/v1/admin/recommendations/...` 与 `/api/v1/admin/recommendation/...` 双轨并存，同时补齐 `GET /metrics`。这样后台页面、测试和最终答辩文档不需要在 singular/plural 命名之间二选一。
* `backend/app/api/v1/router.py`：路由优先级守护层。
  当前把 `search_router` 的注册顺序提前到 `products_router` 之前，明确避免 `/api/v1/products/search` 被 `/api/v1/products/{product_id}` 抢先匹配。Phase 13 之后，固定路径与参数路径的注册顺序已成为显式约束，而不再是“碰巧能用”的隐含行为。
* `backend/tests/api/test_search_semantic.py`、`backend/tests/api/test_recommendations.py`、`backend/tests/api/test_related_products.py`、`backend/tests/api/test_admin_vector_index.py`、`backend/tests/api/test_admin_recommendation_debug.py`：Phase 13 接口契约测试层。
  当前这些测试已经把新搜索别名、推荐新增字段、相似商品来源拆解和后台 singular/plural 别名路径都锁定下来，后续如果有人继续改接口命名或返回字段，会先在这里暴露出来。

这里有三个新的关键架构洞察：

* “最终接口规划”真正困难的部分不是再加几个字段，而是让中间证据沿链路不丢失。
  现在 `hybrid_search.py -> vector_search.py -> search.py` 已经形成了完整透传链，dense/sparse/ColBERT 的中间分数不再在服务边界被吞掉；这比单纯在接口层临时拼几个空字段更接近真实可解释系统。
* 在兼容旧前端和引入新协议时，最稳的策略不是替换，而是别名并存。
  当前搜索、推荐后台和索引后台都采用“保留旧入口 + 增加新入口 + 统一测试覆盖”的方式推进，因此可以继续往前实现第 14 和第 15 节，而不需要先做一轮高风险的 API 迁移。
* FastAPI 里固定路径和参数路径的注册顺序本身就是架构约束。
  本轮 `/api/v1/products/search` 被 `/api/v1/products/{product_id}` 抢匹配并返回 `422`，说明“路径设计正确”并不等于“运行时一定命中正确处理器”；当接口开始向最终命名收拢时，router 装载顺序必须被视为正式设计的一部分。

### 9.49 Phase 14 现在已经形成“分组加权层 + LTR 阈值守护层 + 强业务过滤层”的排序形态

第 73 次同日推进把第 14 节里的排序建议从“文档目标”推进成了线上 ranker 的正式结构：

* `backend/app/services/ranker.py`：分组加权排序层。
  当前 `score_weighted_candidate()` 已从旧的三段式启发式权重，重构成 8 组显式分数结构：`hybrid_retrieval_score`、`colbert_rerank_score`、`collaborative_group_score`、`user_interest_score`、`product_quality_score`、`trend_freshness_score`、`business_constraints_score` 和 `diversity_exploration_score`。这样后台 debug 的 `score_breakdown` 已经能直接映射到答辩里要讲的排序公式，而不是只能解释成“召回分 + 兴趣分 + 质量分”。
* `backend/app/services/ranker.py`：强业务过滤守护层。
  当前在进入加权打分前就会基于 `business_rules` 直接剔除未上架或无库存候选，不再让这些候选只靠 `-2.0` 罚分去“尽量排后”。这把“库存状态”从软特征提升成了真正的业务边界，也修复了专项回归里暴露出的无库存商品仍可能进入 TopN 的问题。
* `backend/app/core/config.py`：LTR 上线阈值配置入口。
  当前新增 `recommendation_ltr_min_training_samples`，让 LTR 是否允许接流量不再只由“有没有模型文件”决定，而是多了一个最小训练样本量约束。Phase 14 之后，LTR 的启用条件终于开始接近真实线上规则。
* `backend/app/services/ltr_ranker.py`：LTR 模型元数据守护层。
  当前 `JsonWeightLTRRanker` 已能读取 `training_sample_count`，并在样本量低于阈值时直接返回 `None`，从而触发 `weighted_ranker` 回退。同时这里还新增了 `LTR_EVENT_LABEL_WEIGHTS`，把 `impression_no_click / click / add_to_cart / pay_order` 的保留训练标签口径固定下来，为后续真正的离线训练脚本提供单一事实来源。
* `backend/tests/test_ranker.py`：排序行为回归层。
  当前不仅继续锁定“兴趣匹配优先于弱内容相似”和“模型缺失时回退 weighted”，还新增了“训练样本量不足时回退 LTR”的测试，并明确验证新的 `hybrid_retrieval_score` 与 `business_constraints_score` 已进入 `score_breakdown`。
* `backend/tests/unit/test_settings.py`：配置默认值守护层。
  当前新增了 `recommendation_ltr_min_training_samples` 的默认值校验，保证后续环境变量或配置重构不会悄悄把这个阈值删掉。
* `docs/ranking_design.md`：排序公式文档层。
  当前不再只写“weighted ranker 存在”，而是明确列出了 8 组权重和 LTR 最小样本阈值回退规则，使排序层的实现和文档再次对齐。

这里有三个新的关键架构洞察：

* 当推荐系统进入统一排序阶段后，最重要的不是“分数越多越好”，而是分数分组必须能被稳定解释。
  现在 `score_breakdown` 里已经把 hybrid、ColBERT、协同过滤、兴趣、质量、趋势、新鲜度、业务约束和探索分开展示；这使排序器终于从“一个复杂公式”变成了“若干可定位、可调权、可汇报的模块”。
* LTR 的上线门槛不能只看模型文件是否存在，还必须看训练样本量是否站得住。
  当前 `training_sample_count + recommendation_ltr_min_training_samples` 的组合，使“低样本伪模型误上线”这个风险第一次被正式约束住；这比简单的“文件加载成功就切换”更接近真实系统治理。
* 有些业务规则不适合留在加权公式里当软信号。
  无库存与未上架状态本轮被前移成 ranker 的硬过滤，说明排序层并不是所有约束都要被连续分值吸收；一旦某个规则本身代表“结果根本不该展示”，它就应该被提升为明确边界，而不是继续和其他分数混算。

### 9.50 Phase 15 现在已经形成“命名空间缓存层 + 画像快照层 + Qdrant 相关推荐快路径”的性能形态

第 74 次同日推进把第 15 节里最现实的性能项真正落到了运行链路上：

* `backend/app/services/cache.py`：统一缓存策略与命名空间层。
  当前不再只是几个 TTL 常量和简单 key 拼接，而是新增了 `SEMANTIC_SEARCH_CACHE_TTL`、`RELATED_PRODUCTS_CACHE_TTL`、`USER_PROFILE_CACHE_TTL`、slot-aware 推荐 key，以及基于 `DATABASE_URL` 的 cache namespace。Phase 15 之后，缓存终于开始具备环境隔离语义，而不是所有测试库和运行环境都挤在同一套 Redis key 上。
* `backend/app/services/recommendations.py`：用户画像快照层。
  当前 `build_user_interest_profile()` 在真正扫行为日志和商品文本前，会优先尝试读取缓存的 `UserInterestProfile` 快照；构建完成后再把画像序列化回缓存。这意味着“中间用户画像”已经从纯数据库表升级成了真正的可失效缓存对象。
* `backend/app/api/v1/products.py`：推荐与相关推荐缓存编排层。
  当前首页推荐缓存 key 已按 `user_id + slot + backend + limit` 拆开，修复了旧实现里不同展示位共用同一缓存的问题；相关推荐接口也新增了独立缓存，并在命中时直接返回稳定的公开协议，不需要再重复做相似度计算。
* `backend/app/api/v1/search.py`：语义搜索缓存编排层。
  当前最终搜索接口和语义搜索接口都具备了 query/filter/backend 维度的结果缓存；缓存命中时仍然保留行为日志和搜索日志写入，因此性能优化没有破坏后续评估和埋点链路。
* `backend/app/services/vector_search.py`：相关推荐双路径执行层。
  当前 `find_related_products()` 已升级成“Qdrant 优先、baseline 回退”的结构：当向量库 ready 时走 `find_related_products_with_qdrant()`，先从 Qdrant 取有限候选，再补 co-view/co-buy 和文化匹配分；只有在向量库不可用或异常时，才回退到旧的全量 embedding 相似度扫描。
* `backend/tests/integration/test_cache_behavior.py`：性能缓存回归层。
  当前不仅继续验证商品详情、搜索建议和推荐缓存，还新增了语义搜索缓存、推荐 slot 隔离、相关推荐缓存和用户画像缓存命中的回归测试，确保本轮加上的缓存不会因为 key 设计错误而变成功能 bug。
* `backend/tests/test_hybrid_search.py`：Qdrant 相关推荐路径验收层。
  当前新增的回归已经固定了 `find_related_products()` 在向量库 ready 时会返回 `pipeline_version=qdrant_related`，不再只是默认走 baseline；这让相关推荐的优化终于有了明确测试锚点。

这里有三个新的关键架构洞察：

* 在共享 Redis 的项目里，“cache key 命名空间”本身就是基础设施设计，而不是测试细节。
  本轮新增的用户画像缓存一上线就暴露出跨测试库串缓存的问题，说明只要缓存从商品级扩展到用户级，`user_id` 这种局部主键就不再足够；现在基于 `DATABASE_URL` 的命名空间已经成为所有缓存 key 的共同前缀约束。
* 最有效的性能优化往往不是把整条链路一起缓存，而是把“重建代价高、失效边界清晰”的中间状态单独缓存。
  `UserInterestProfile` 正是这种对象：它构建时要扫行为日志和商品文本，但失效又天然跟随用户行为发生。因此把画像做成可失效快照，比只扩大最终推荐 TTL 更稳，也更接近第 15 节“缓存中间用户画像”的目标。
* 相关推荐的性能优化不能牺牲解释结构。
  本轮 `find_related_products_with_qdrant()` 虽然把候选获取改成了向量库 fast path，但外层仍然保留 `source_breakdown`、`co_view_co_buy`、`cultural_match` 和 `diversity_result`。这说明“优化内部执行路径、保持外部协议不变”是这类系统里最稳的演进方式。

### 9.51 Phase 16 现在已经形成“答辩 FAQ 事实源 + 最终回归锚点”的收口形态

第 75 次同日推进把第 16 节从“文档尾声”推进成了可持续维护的最终材料层：

* `docs/defense_script.md`：答辩 FAQ 事实源层。
  当前除了原有的开场讲稿、演示顺序和核心问答外，又补齐了“怎么证明推荐更好”和“如何解决冷启动”两条关键 FAQ。这样这份文档已经能完整覆盖计划文档第 16 节的五个核心问题，不再需要答辩时临场在评估报告、推荐文档和讲稿之间来回拼答案。
* `memory-bank/progress.md`：最终验证记录层。
  当前不仅记录了 FAQ 文档的补齐，还明确写入了最终全量回归结果 `147 passed` 和 `test_full_demo_flow 1 passed`，把本轮连续三步的代码收口点固定成了明确可复查的状态。
* `memory-bank/architecture.md`：最终交接锚点层。
  当前把 `docs/defense_script.md` 升格成“统一口径事实源”，意味着后续不管是继续做增强版本、补更多实验，还是修改答辩措辞，都应该围绕这份文档集中收敛，而不是再让 FAQ 分散在多份 Markdown 里各写一套。

这里有两个新的关键架构洞察：

* 当系统进入答辩阶段后，FAQ 文档本身也成为架构资产。
  因为它承接的是“如何解释系统边界、如何解释算法收益、如何解释冷启动与完整性”这些跨模块问题，所以 `docs/defense_script.md` 实际上已经成为推荐系统对外语义层的一部分，而不是普通说明文档。
* 最终回归不是开发流程的附属动作，而是后续增强版本的起始锚点。
  本轮在补 FAQ 后重新跑了全量后端测试和完整 demo e2e，这使当前提交点具备了“可继续往第 17 节增强版本迭代”的稳定基线；后续任何新增实验、排序器或多模态能力，都应该建立在这个回归通过的锚点之上。

### 9.52 推荐系统现在开始具备“后台可观测层”，而不只是“有日志表”

第 76 次同日推进把推荐系统从“日志已经落库”进一步推进到“日志已经能被后台消费”：

* `backend/app/services/recommendation_admin.py`：指标聚合层。
  当前不再只返回 CTR、转化率和覆盖率，而是继续聚合 `unique_user_count`、`fallback_request_count`、`fallback_rate`、`average_impressions_per_request`、`channel_breakdown`，以及搜索侧 `pipeline_breakdown`。这让后台终于能回答“当前是不是还在回退 baseline”“哪些召回通道真的有曝光”“hybrid search 实际占比是多少”。
* `admin/recommendation-metrics.html`：指标展示层。
  当前后台新增独立“推荐指标”页面，专门承接推荐请求、曝光、点击、加购、支付转化、槽位分布、召回通道分布和搜索/推荐 pipeline 分布的展示，不再把所有推荐数据都挤在仪表盘里。
* `admin/js/app.js`：推荐后台编排层。
  当前统一后台脚本已经扩展出“推荐指标页”分支，说明后台推荐能力不再只停留在单页调试或实验说明，而是开始形成“仪表盘 -> 指标页 -> 调试页 -> 实验页”的分工结构。
* `backend/tests/services/test_recommendation_admin_metrics.py`：可观测层回归测试。
  当前新增测试已经把“fallback 比例”“召回通道分布”“搜索 pipeline 分布”固定成自动化回归项，避免未来继续改推荐日志或后台聚合时把这些关键指标悄悄改坏。

这里有两个新的关键架构洞察：

* 推荐系统是否“完整”，不仅取决于召回和排序链路，也取决于后台能不能把这些链路变成可读证据。
  现在 `recommendation_admin.py -> admin/js/app.js -> recommendation-metrics.html` 已经构成一条专门的可观测链路，这使项目从“实现了推荐”走向“能证明自己实现了推荐”。
* 当后台开始展示召回通道与 fallback 分布后，日志字段就不再只是埋点细节，而是后台协议的一部分。
  这意味着后续继续做实验对比、冷启动展示和评估页面时，应该优先复用现有指标聚合层，而不是各个页面各算一套统计口径。

### 9.53 实验配置页现在开始具备“能力矩阵层”，而不只是“方案卡片层”

第 77 次同日推进把推荐实验页从静态卡片说明，推进成了结构化对比页面：

* `backend/app/services/recommendation_admin.py`：实验对比聚合层。
  当前 `build_experiment_payload()` 不再只返回 `active_key + items`，而是同时返回 `runtime_summary`、`capability_catalog` 和 `comparison_notes`。这使实验页不需要自行猜测当前运行时，也不需要把能力字段硬编码在前端。
* `admin/recommendation-config.html`：实验对比展示层。
  当前页面新增了运行时摘要区、能力矩阵表和答辩提示卡片，已经从“展示有哪些方案”升级成“解释这些方案有什么差异、当前系统到底跑在哪个方案上”。
* `admin/js/app.js`：实验页编排层。
  当前实验页渲染逻辑已经开始把 `capability_catalog` 当成后端协议消费，这意味着前端不再直接写死“dense/sparse/ColBERT/协同过滤”的列集合，后续继续扩展能力时只需要在聚合层加目录定义即可。

这里有两个新的关键架构洞察：

* 当实验页开始承担答辩解释职责后，“能力目录”就应该成为后端输出，而不是前端常量。
  因为实验能力集合未来还会继续扩展，如果仍由前端自己维护列集合，就会再次出现“后端能力已经变化、实验页还停留在旧文案”的脱节问题。
* 实验配置页最重要的不是展示配置 JSON，而是把“当前运行时”和“理论方案”并排展示。
  只有这样，页面才能清楚回答“当前是不是已经退回 baseline”“当前 full_pipeline 是否真的生效”，而不是只停留在一份静态方案说明。

### 9.54 冷启动与探索位现在已经形成“排序追踪层 + 后台运营证据层”

第 78 次同日推进把推荐系统里原本藏在排序过程中的冷启动与探索位逻辑，推进成了可被后台直接消费的结构化证据：

* `backend/app/services/business_rules.py`：排序后处理追踪层。
  当前 `apply_post_ranking_rules()` 不再只负责类目去重和探索位注入，还会把 `selection_trace` 写回候选对象，明确标出该候选是首轮保留、因去重暂缓、结果补位，还是因探索位比例被强制保留。
* `backend/app/services/recommendation_pipeline.py`：推荐候选证据封装层。
  当前 `PipelineRecommendationCandidate` 已经不只携带分数、理由和特征，还会把 `business_rules` 与 `selection_trace` 一起带到调试出口，使后续接口和后台页面不需要再重新推断候选为何被保留。
* `backend/app/api/v1/admin_recommendations.py`：后台调试证据出口层。
  当前推荐调试接口已显式返回 `is_exploration`、`cold_start_candidate`、`new_arrival_candidate`、`business_rules`、`selection_trace`，并补充候选级冷启动/探索位统计，让页面可以直接展示而不是再写前端推理逻辑。
* `backend/app/services/recommendation_admin.py`：运营指标反推层。
  当前聚合逻辑不需要新增日志表，也能直接利用 `RecommendationImpressionLog.recall_channels` 反推出 `cold_start_request_count`、`exploration_hit_rate`、`new_arrival_share` 等运营指标。这使已有埋点第一次具备了冷启动与探索位的运营分析价值。
* `admin/js/app.js` 与 `admin/recommendation-debug.html` / `admin/recommendation-metrics.html`：后台展示证据层。
  当前后台不再只展示“召回通道”和“最终分数”，而是能继续展示探索位标签、业务规则、保留轨迹，以及冷启动和新品探索 KPI，使算法策略第一次具备稳定截图价值。

这里有两个新的关键架构洞察：

* 如果排序后处理不输出 `selection_trace`，探索位和类目去重就永远只能停留在“代码里确实写了”，无法变成答辩证据。
  现在 `business_rules.py -> recommendation_pipeline.py -> admin_recommendations.py -> admin/js/app.js` 已经形成一条完整追踪链路，说明排序后处理也应该被当成可解释协议的一部分，而不是内部黑盒。
* 冷启动与新品探索的运营指标，不一定要等到新增专门日志表才能开始做。
  只要曝光日志里已经保存了 `recall_channels`，就可以先通过请求级和曝光级聚合反推出冷启动请求数、Exploration 命中率和新品召回占比。这是当前仓库在比赛工期下最划算的证据化路径。

### 9.55 Phase E5 现在已经形成“人工结论文档层 + 脚本原始产物层 + 后台材料目录层”的收口形态

第 79 次同日推进把推荐系统增强计划的收口阶段从“文档补几页”推进成了真正可维护的材料体系：

* `docs/generated/`：脚本原始产物层。
  当前新增这个目录，专门承接 `backend/scripts/evaluate_recommendations.py` 与 `backend/scripts/benchmark_recommendations.py` 的最新输出。Phase E5 之后，评估和压测脚本不再覆盖 `docs/recommendation_evaluation.md` 与 `docs/performance_benchmark.md` 这些人工整理结论页，而是把原始报告稳定写到 `docs/generated/recommendation_evaluation_latest.md` 和 `docs/generated/performance_benchmark_latest.md`。
* `backend/scripts/evaluate_recommendations.py`：隔离评估运行时层。
  当前脚本会先创建临时 SQLite 数据库和独立 SQLAlchemy session，再灌入基础数据与实验数据，避免直接依赖仓库内 `backend/dev.db` 的 schema 状态。这样即使本地开发库尚未升级到最新字段，评估脚本也不会因为列缺失直接中断。
* `backend/scripts/benchmark_recommendations.py`：隔离压测运行时与规模验证层。
  当前脚本同样切换成临时 SQLite 数据库初始化，并把输出改到 `docs/generated/performance_benchmark_latest.md`。Phase E5 的真实压测结果已经证明脚本可以在 `10000` 商品 / `200` 用户规模下跑通，同时保留下次继续做更大规模压测的标准入口。
* `backend/app/services/recommendation_admin.py`：材料目录聚合层。
  当前实验配置聚合已不再只返回实验方案，还会集中返回 `artifact_summary` 与 `artifact_catalog`，把推荐流程说明、评估报告、压测报告、答辩讲稿、原始产物路径、生成命令和更新时间收束成统一协议。
* `admin/recommendation-config.html` 与 `admin/js/app.js`：后台材料台展示层。
  当前实验配置页已经扩成“评估与答辩材料”页面，能展示每份材料的入口文件、使用场景、脚本产物路径和最近更新时间。这样后台就不再只是解释算法方案，也开始承担“材料导航台”的职责。
* `docs/recommendation_pipeline.md`、`docs/recommendation_evaluation.md`、`docs/performance_benchmark.md`、`docs/defense_script.md`：人工结论收敛层。
  当前这些文档之间已经建立了交叉引用关系，分别承接结构说明、效果结论、性能边界和答辩讲稿；原始数据交给 `docs/generated/`，人工表述则继续保留在结论页中。

这里有三个新的关键架构洞察：

* 当系统开始依赖脚本生成评估材料时，“人工结论页”和“脚本原始产物页”必须分层。
  否则每次重新跑脚本都会把人写的答辩总结和解释性结论冲掉。当前 `docs/*.md` 与 `docs/generated/*.md` 的分层，实际上已经成为推荐系统材料管理的一部分。
* 后台实验页一旦开始承担答辩与交接职责，就不应只展示实验能力，还应该展示材料入口。
  现在 `recommendation_admin.py -> admin/js/app.js -> recommendation-config.html` 已经形成材料目录链路，后续新增评估报告或 A/B 看板时，应优先挂在这条链路上，而不是散落在文档目录里让使用者自己找。
* 压测脚本真正有价值的时刻，不是它成功输出 Markdown，而是它暴露出下一阶段最值得解决的瓶颈。
  Phase E5 的 `10000` 商品压测结果里，`recommend_home` p50 已到 `31.7s`，远高于搜索与相关推荐；这说明后续增强版本最优先的技术方向应转向 Redis 预计算推荐或更强缓存，而不是继续增加纯展示型材料。

### 9.56 Phase E6 现在已经形成“推荐响应组装层 + Redis 预计算快照层 + 后台预热运营层”的性能形态

第 80 次同日推进把 E5 暴露出的高延迟瓶颈，推进成了可被后台直接操作的预计算能力：

* `backend/app/services/recommendation_delivery.py`：推荐响应组装层。
  当前这个新模块统一承接推荐结果序列化、来源标签生成和运行时推荐 payload 组装。Phase E6 之后，实时推荐接口和预计算快照都复用同一套 `items + pipeline` 结构，不再分别在 API 层和预热层各自维护一套推荐响应拼装逻辑。
* `backend/app/services/precomputed_recommendations.py`：Redis 预计算快照层。
  当前这个新模块负责按 `user_id + slot + backend + limit` 生成快照、写入 Redis、维护预热摘要，并记录命中次数、未命中次数和按槽位拆分的命中率。它还负责解析“指定用户列表”和“自动扫描活跃用户”两种预热入口，使预热不再只是临时脚本行为，而是正式服务层能力。
* `backend/app/services/cache.py`：统一缓存与快照失效层。
  当前除了原有在线缓存 key 外，又新增了 `recommendation:precomputed` 快照 key 与状态 key；`invalidate_recommendation_cache_for_user()` 也已经扩展成同时清理在线缓存和预计算快照。这意味着用户行为发生后，个性化推荐的所有缓存层都会一起失效，不会再出现“实时缓存已清、预热快照还在”的状态漂移。
* `backend/app/api/v1/products.py`：三层推荐返回编排层。
  当前推荐接口的执行顺序已经变成“预计算快照优先 -> 在线缓存 -> 实时推荐流水线”。并且 `pipeline` 元数据里新增了 `cache_source` 和 `precomputed_generated_at`，让前端、联调和后台调试都能明确知道当前结果究竟来自预热、普通缓存还是实时计算。
* `backend/app/api/v1/admin_recommendations.py`：后台预热操作层。
  当前新增 `GET /admin/recommendation/precompute/status` 与 `POST /admin/recommendations/precompute/warm`，并保留 singular / plural 兼容入口。这样管理员已经可以直接通过后台 API 查看预热状态、手动触发首页/购物车推荐预热，而不需要再进容器或跑单独脚本。
* `backend/app/services/recommendation_admin.py`、`admin/recommendation-config.html`、`admin/js/app.js`：预热运营展示层。
  当前实验配置页已经不只展示实验能力和材料目录，还会继续展示 Redis 预热概况、预热槽位、最近预热时间、命中率和一键预热按钮。实验配置页因此开始兼具“实验解释”和“推荐运营控制台”的双重角色。
* `backend/tests/integration/test_cache_behavior.py` 与 `backend/tests/api/test_admin_recommendation_debug.py`：预计算链路回归层。
  当前新增测试已经把“预热写入 -> 接口命中 -> 用户行为后失效 -> 后台状态可见”这条链路固定下来，后续如果有人重构缓存层或后台预热接口，会首先在这里暴露问题。

这里有三个新的关键架构洞察：

* 预计算推荐不应该直接覆盖原有在线缓存，而应该成为一层独立快照。
  只有这样，系统才能区分“请求时临时算出来并缓存的结果”和“后台主动预热好的结果”，后续做命中率统计、A/B 对比或运营解释时才不会把两类缓存混成一团。
* 一旦引入预计算层，推荐系统的真正边界就不再只是“怎么算”，还包括“什么时候失效”。
  本轮把预计算快照失效直接挂到现有 `invalidate_recommendation_cache_for_user()` 上，说明用户行为驱动的失效边界已经成为推荐系统设计的一部分，而不是 Redis 层面的实现细节。
* 当性能优化已经能通过后台触发时，后台页面本身就成为系统调优的一环。
  现在 `recommendation-config.html` 已经可以展示预热状态并触发预热，这意味着后台不再只是演示页面，而开始承担运行期调优入口；后续的 A/B 看板和更大规模压测，也应该沿着这条“后台可操作”路线继续扩展。

### 9.57 Phase E7 现在已经形成“实验效果聚合层 + 实验看板展示层 + baseline 对比层”的运营形态

第 81 次同日推进把实验页从“解释有哪些方案”推进到“解释这些方案当前跑出了什么结果”：

* `backend/app/services/recommendation_admin.py`：实验效果聚合层。
  当前新增 `build_experiment_dashboard()`，会把 `RecommendationRequestLog / RecommendationImpressionLog / RecommendationClickLog / RecommendationConversionLog` 按 `pipeline_version + model_version + slot` 聚合成实验效果看板数据。这样后台终于能直接看到实验流量占比、CTR、加购率、支付转化率、fallback 比例和平均延迟，而不需要手动去日志表拼数据。
* `backend/app/services/recommendation_admin.py`：实验版本汇总层。
  当前除了 slot 级明细 `items` 外，还会继续聚合 `top_variants` 和 `comparison_cards`。前者负责按实验版本汇总流量最高的几个方案，后者则在存在 baseline 与主实验流量时自动生成差值摘要，把 CTR、CVR 和延迟差直接做成后台可以展示的对比卡片。
* `admin/recommendation-config.html` 与 `admin/js/app.js`：实验看板展示层。
  当前实验配置页已经不只是能力矩阵、预计算状态和材料目录页，还增加了 A/B 实验摘要、流量最高方案卡片、baseline 对比卡片，以及按“实验版本 x slot”展开的完整效果表格。实验配置页因此开始同时承担“能力解释页”和“实验效果看板页”两种职责。
* `backend/tests/services/test_recommendation_admin_metrics.py`：实验聚合口径守护层。
  当前新增测试已经锁定了实验版本流量聚合、fallback 比例和 baseline / v1 对比逻辑，避免后续继续改推荐日志或后台聚合时把 A/B 看板算歪。
* `backend/tests/api/test_admin_recommendation_debug.py`：实验接口契约守护层。
  当前实验配置接口测试已继续覆盖 `experiment_dashboard` 字段，保证前端实验看板渲染所需的数据结构不会被后续改动悄悄删掉。

这里有三个新的关键架构洞察：

* 只做“实验配置页”是不够的，实验系统必须同时回答“现在流量到底跑到了哪里”。
  当前 `build_experiment_dashboard()` 把推荐请求日志和效果日志真正接到实验页上，这意味着实验系统终于从“静态方案目录”变成了“带效果反馈的运行中系统”。
* 实验看板至少需要两层视角：版本视角和版本 x 槽位视角。
  本轮 `top_variants` 与 `items` 的分层，正是为了避免把“总体哪个实验流量最大”和“某个 slot 下哪个实验表现更好”混成同一种统计口径。
* baseline 对比不该停留在文档里，而应变成后台自动计算的结构化结果。
  现在 `comparison_cards` 已能在后台直接展示 baseline 与主实验的 CTR / CVR / 延迟差，这让答辩和交接时都不需要临时再翻评估文档手工做心算对比。

### 9.58 Phase E8 现在已经形成“多模式压测脚本层 + 按端点采样计划层 + 大规模执行手册层”的规模验证形态

第 82 次同日推进把压测脚本从“固定 1 万商品参数的一次性脚本”推进成了更像工程工具的形态：

* `backend/scripts/benchmark_recommendations.py`：多模式压测脚本层。
  当前脚本已经支持 `standard` 与 `light` 两种模式，以及按端点单独控制的 `--search-requests`、`--semantic-requests`、`--recommendation-requests`、`--related-requests` 参数。Phase E8 之后，压测不再只能以统一请求量给所有接口同样的压力，而是开始支持分接口放量和轻量验证。
* `backend/scripts/benchmark_recommendations.py`：采样计划与准备阶段记录层。
  当前脚本会把 `sample_plan`、`preparation`、`mode` 一并写进 JSON 和 Markdown 产物，显式记录基础种子耗时、数据集生成耗时、用户种子耗时、是否跳过重型索引准备，以及每个端点到底跑了多少请求。这样后续看压测报告时，不会再出现“只知道 p95，却不知道这次到底用什么模式跑出来”的解释缺口。
* `backend/tests/scripts/test_benchmark_recommendations.py`：脚本级契约守护层。
  当前新增测试已经把 CLI 参数解析、轻量模式采样计划和 Markdown 输出结构固定下来，说明压测脚本本身也已经从“无人校验的工具脚本”升级成了有自动化约束的工程入口。
* `docs/performance_benchmark.md`：大规模执行手册层。
  当前文档已经补充了 `light` 模式、本地先跑 2 万商品的建议，以及按端点单独覆盖请求量的参数说明。这使压测文档不再只是结果报告，也开始承担“如何安全执行更大规模压测”的操作手册角色。
* `docs/generated/performance_benchmark_latest.md`：当前规模事实层。
  当前最新原始产物已被新的 2 万商品轻量压测刷新。它不仅记录了端点延迟，还明确记录了 `sample_plan` 和 `preparation`，因此这份产物本身已经能证明“大规模脚本入口已经真的被跑过”，而不是只停留在代码参数层面。

这里有三个新的关键架构洞察：

* 大规模压测最先需要的，往往不是更大的绝对数据量，而是能安全扩量的“模式开关”。
  本轮 `light` 模式的意义就在这里：它让脚本可以先证明“2 万到 10 万量级是否能跑完、结果结构是否稳定”，而不用每次都把本地环境直接压到完整重型流程。
* 压测报告的可解释性，取决于是否把“请求采样计划”和“准备阶段耗时”一起记下来。
  现在 `sample_plan + preparation + rows` 已经成为同一个产物的一部分，这使后续任何人看到结果时，都能知道这次性能数字到底对应什么运行方式，而不是只看到一串延迟值。
* 当前真正的规模瓶颈已经非常明确地集中在首页推荐主链路。
  本轮 `20000` 商品轻量模式下，`recommend_home` p50 已超过 `100s`，远高于搜索和相关推荐。这说明如果继续做下一轮增强，技术优先级应继续集中在推荐主链路，而不是平均分散到所有模块。
