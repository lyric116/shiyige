# 测试与开发工具说明

## 依赖入口

* `backend/requirements.txt`：运行时依赖
* `backend/requirements-dev.txt`：开发与测试依赖

## 当前测试结构

* `backend/tests/`：后端单元测试、接口测试、集成测试
* `tests/e2e/`：端到端烟雾测试

## 当前基础命令

* 收集测试：`pytest --collect-only`
* 运行后端测试：`pytest backend/tests -q`
* 运行端到端测试：`pytest tests/e2e -q`
* 运行格式检查：`ruff check .`

## 当前阶段说明

当前仍处于 Phase 0 工程初始化阶段，所以只提供最小占位测试，用于验证测试框架已接通。后续每完成一个接口或模块，都必须补充真实自动化测试，而不是继续依赖占位测试。
