# 拾遗阁

拾遗阁是一个面向古风文化商品场景的 Web 应用仓库，当前包含：

* `front/` 前台静态商城页面
* `admin/` 后台静态管理页面
* `backend/` FastAPI 后端、数据库迁移、种子脚本与测试
* `docker-compose.yml` 本地完整编排，拉起 PostgreSQL、Redis、MinIO、Qdrant、API、Nginx

推荐优先使用 Docker Compose 运行整套项目；如果只做后端开发，也支持在本机直接启动 FastAPI。

## 项目环境

当前仓库与配置约定如下：

* Python：`3.11`
* 后端框架：`FastAPI` + `SQLAlchemy 2.x` + `Alembic`
* 关系数据库：`PostgreSQL 16` + `pgvector` 镜像
* 缓存：`Redis 7`
* 对象存储：`MinIO`
* 向量数据库：`Qdrant`
* Web 入口：`Nginx 1.27`
* 前端形态：原生 `HTML/CSS/JavaScript`
* 测试：`pytest`、`pytest-asyncio`、`httpx`、`playwright`
* 代码检查：`ruff`
* 本地 Python 依赖缓存目录：`.uv-cache`
* 本地 Python 虚拟环境目录：`.venv`

## 仓库结构

### 根目录文件

* `README.md`：仓库入口说明，描述目录结构、环境、启动方式和常用命令。
* `AGENTS.md`：仓库协作约束，规定目录职责、开发命令、测试要求和交接习惯。
* `docker-compose.yml`：本地完整运行编排；负责拉起 `postgres`、`redis`、`minio`、`qdrant`、`api`、`nginx`。
* `.env.example`：本地直接启动后端时可参考的环境变量模板。
* `pytest.ini`：pytest 收集入口；当前覆盖 `backend/tests` 与 `tests/e2e`。
* `ruff.toml`：Ruff 规则入口；当前目标 Python 版本是 `py311`，行宽为 `100`。

### 前台与后台

* `front/`：前台站点根目录。
* `front/index.html`：首页。
* `front/category.html`：分类/搜索结果页。
* `front/product.html`：商品详情页。
* `front/cart.html`：购物车页。
* `front/checkout.html`：结算页。
* `front/orders.html`：订单页。
* `front/profile.html`：个人中心。
* `front/membership.html`：会员中心。
* `front/login.html` 与 `front/register.html`：前台认证页面。
* `front/js/`：前台页面脚本；负责真实 API 接线、推荐展示、购物车、结算、用户中心等交互。
* `front/css/`：前台样式文件。
* `front/images/`：前台图片素材。
* `admin/`：后台站点根目录，由 Nginx 挂载在 `/admin/`。
* `admin/index.html`：后台仪表盘。
* `admin/products.html`：商品管理页。
* `admin/orders.html`：订单管理页。
* `admin/reindex.html`：向量索引任务页。
* `admin/recommendation-debug.html`：推荐调试页。
* `admin/recommendation-config.html`：推荐实验配置页。
* `admin/recommendation-metrics.html`：推荐指标页。
* `admin/js/` 与 `admin/css/`：后台脚本与样式文件。

### 后端与测试

* `backend/`：后端主目录。
* `backend/app/`：FastAPI 应用代码。
* `backend/app/main.py`：应用入口，负责注册中间件、路由和启动时检查。
* `backend/app/api/`：API 路由层。
* `backend/app/models/`：SQLAlchemy 模型。
* `backend/app/schemas/`：Pydantic 请求模型。
* `backend/app/services/`：推荐、搜索、媒体、会员、缓存等服务实现。
* `backend/app/tasks/`：索引与离线任务封装。
* `backend/app/core/`：配置、数据库、安全、Redis、MinIO、异常响应等基础设施代码。
* `backend/alembic/`：数据库迁移目录。
* `backend/scripts/`：迁移后启动、基础数据初始化、索引重建、评估等命令脚本。
* `backend/scripts/start_api.sh`：容器内 API 启动脚本；会先执行 Alembic、基础种子与演示种子，再启动 Uvicorn。
* `backend/tests/`：后端 API、模型、服务、任务、集成测试。
* `backend/requirements.txt`：运行时依赖。
* `backend/requirements-dev.txt`：开发与测试依赖。
* `backend/Dockerfile`：API 镜像定义。
* `tests/e2e/`：浏览器级端到端测试。

### 文档与项目记忆

* `docs/`：部署、接口、测试、数据库、推荐设计等说明文档。
* `docs/deployment.md`：部署与运行补充说明。
* `docs/api_guide.md`：接口分组和演示账号说明。
* `docs/testing.md`：测试命令和验证入口说明。
* `nginx/default.conf`：Nginx 站点配置，负责托管 `front/`、`admin/` 并反向代理 `/api`、`/docs` 等路径。

## 启动方式

### 方案一：Docker Compose 启动整套项目

这是当前仓库最完整、最接近演示环境的启动方式。

前置要求：

* 已安装 `Docker`
* 已安装 `Docker Compose`

启动命令：

```bash
docker compose up -d --build
```

查看运行状态：

```bash
docker compose ps
docker compose logs -f api nginx
```

启动后访问入口：

* 前台：`http://127.0.0.1/`
* 后台：`http://127.0.0.1/admin/`
* API 健康检查：`http://127.0.0.1/api/v1/health`
* API 文档：`http://127.0.0.1/docs`
* OpenAPI JSON：`http://127.0.0.1/openapi.json`
* MinIO API：`http://127.0.0.1:9000`
* MinIO 控制台：`http://127.0.0.1:9001`
* Qdrant：`http://127.0.0.1:6333/collections`
* PostgreSQL：`127.0.0.1:5432`
* Redis：`127.0.0.1:6379`

说明：

* `api` 容器不会直接暴露 `8000` 到宿主机；对外统一通过 `nginx` 的 `80` 端口访问。
* `backend/scripts/start_api.sh` 会在容器启动时自动执行迁移、基础种子和演示种子。
* Compose 方案已经内置运行所需的核心环境变量，不需要额外准备 `.env`。

### 方案二：本地直接启动后端

这个方案适合只调试 FastAPI、数据库迁移或测试，不适合单独验证完整前后台站点。

#### 1. 准备项目虚拟环境

如果本地还没有 `.venv`，先创建它：

```bash
python3.11 -m venv .venv
```

安装开发依赖：

```bash
UV_CACHE_DIR=.uv-cache uv pip install --python .venv/bin/python -r backend/requirements-dev.txt
```

如果要跑 e2e，额外安装 Playwright 浏览器：

```bash
./.venv/bin/playwright install chromium
```

#### 2. 启动基础设施

本地直接跑 API 时，仍然需要 PostgreSQL、Redis、MinIO、Qdrant：

```bash
docker compose up -d postgres redis minio qdrant
```

#### 3. 准备环境变量

复制模板：

```bash
cp .env.example .env
```

如果 API 运行在宿主机而不是容器内，需要把 `.env` 中的容器主机名改成本机地址。最少需要检查这些字段：

```env
DATABASE_URL=postgresql+psycopg://shiyige:shiyige@127.0.0.1:5432/shiyige
REDIS_URL=redis://127.0.0.1:6379/0
MINIO_ENDPOINT=127.0.0.1:9000
QDRANT_URL=http://127.0.0.1:6333
```

#### 4. 执行迁移与种子

```bash
./.venv/bin/python -m alembic -c backend/alembic.ini upgrade head
./.venv/bin/python -m backend.scripts.seed_base_data
./.venv/bin/python -m backend.scripts.seed_demo_data
```

#### 5. 启动 API

```bash
./.venv/bin/python -m uvicorn backend.app.main:app --reload
```

本地直接启动后，接口入口默认是：

* API：`http://127.0.0.1:8000/api/v1/health`
* 文档：`http://127.0.0.1:8000/docs`

说明：

* 这个模式只启动 FastAPI，不会自动托管 `front/` 和 `admin/`。
* 如果你要同时访问前后台页面，仍然建议使用 Compose 方案，让 Nginx 统一托管静态资源与 API 反代。

## 演示账号

默认种子会创建以下账号：

* 前台演示用户：`user@shiyige-demo.com` / `user123456`
* 后台演示管理员：`admin@shiyige-demo.com` / `admin123456`

## 常用命令

检查 Compose 配置：

```bash
docker compose config --quiet
```

停止服务：

```bash
docker compose down
```

彻底重置环境：

```bash
docker compose down -v --remove-orphans
docker compose up -d --build
```

收集测试：

```bash
PYTHONPATH=. UV_CACHE_DIR=.uv-cache uv run --with pytest pytest --collect-only -q
```

运行后端测试：

```bash
./.venv/bin/python -m pytest backend/tests -q
```

运行端到端测试：

```bash
./.venv/bin/python -m pytest tests/e2e -q
```

运行代码检查：

```bash
./.venv/bin/ruff check .
```

## 补充说明

* 当前仓库的首选交付入口是 `docker-compose.yml`，不是单独的后端进程。
* `.env.example` 更适合作为“宿主机直跑 API”时的参考模板；Compose 模式主要读取 `docker-compose.yml` 中定义的环境变量。

