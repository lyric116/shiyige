# 部署说明

## 1. 本地一键启动

前置要求：

* 已安装 Docker 与 Docker Compose

启动命令：

```bash
docker compose up -d
```

启动后入口：

* 前台：`http://127.0.0.1/`
* 后台：`http://127.0.0.1/admin/`
* API 健康检查：`http://127.0.0.1/api/v1/health`
* API 文档：`http://127.0.0.1/docs`
* MinIO：`http://127.0.0.1:9001`
* Qdrant：`http://127.0.0.1:6333/collections`

默认演示账号：

* 前台：`user@shiyige-demo.com` / `user123456`
* 后台：`admin@shiyige-demo.com` / `admin123456`

## 2. 编排说明

当前 `docker-compose.yml` 会拉起：

* `postgres`
* `redis`
* `minio`
* `qdrant`
* `api`
* `nginx`

其中：

* `nginx` 正式托管 `front/` 和 `admin/`
* `/api`、`/docs`、`/redoc`、`/openapi.json` 由 `nginx` 反代到 `api`
* `api` 容器启动时会自动执行迁移、基础种子和演示数据种子
* `qdrant` 提供独立向量数据库入口，当前阶段主要用于连通性检查、后续 collection 初始化和推荐检索升级

## 3. 本地测试命令

```bash
curl -s http://127.0.0.1:6333/collections
./.venv/bin/python -m pytest backend/tests -q
./.venv/bin/python -m pytest tests/e2e/test_full_demo_flow.py -q
```

## 4. 重置环境

```bash
docker compose down -v --remove-orphans
docker compose up -d
```

## 5. 当前已知注意事项

* 推荐缓存依赖行为写入后的显式失效，新增行为类型时要同步接入失效逻辑。
* MinIO 上传返回 URL 仍由对象存储 endpoint 决定；如果未来需要统一公网资源域名，建议增加单独的公开资源配置。
* 当前阶段 Qdrant 已接入编排和健康检查，但搜索与个性化推荐仍保留 baseline 逻辑；健康检查和推荐接口会显式标记 `degraded_to_baseline` 状态。
