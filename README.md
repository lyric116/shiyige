# 十一个

一个包含前台商城、后台管理和 FastAPI 接口的演示项目。推荐直接用 Docker Compose 本地启动，最快。

## 运行环境

- Docker
- Docker Compose

## 快速启动

在项目根目录执行：

```bash
docker compose up -d
```

首次启动会自动拉起数据库、缓存、对象存储、API 和 Nginx。

## 启动后访问地址

- 前台：`http://127.0.0.1/`
- 后台：`http://127.0.0.1/admin/`
- API 健康检查：`http://127.0.0.1/api/v1/health`
- API 文档：`http://127.0.0.1/docs`
- MinIO 控制台：`http://127.0.0.1:9001`

## 演示账号

- 前台用户：`user@shiyige-demo.com` / `user123456`
- 后台管理员：`admin@shiyige-demo.com` / `admin123456`

## 常用命令

停止服务：

```bash
docker compose down
```

彻底重置环境：

```bash
docker compose down -v --remove-orphans
docker compose up -d
```

运行后端测试：

```bash
./.venv/bin/python -m pytest backend/tests -q
```

运行端到端测试：

```bash
./.venv/bin/python -m pytest tests/e2e/test_full_demo_flow.py -q
```

## 目录说明

- `front/`：前台静态页面
- `admin/`：后台静态页面
- `backend/`：FastAPI 服务与测试
- `docs/`：部署、接口和测试文档
- `memory-bank/`：设计、实施计划和项目记录

更多说明见：

- `docs/deployment.md`
- `docs/api_guide.md`
