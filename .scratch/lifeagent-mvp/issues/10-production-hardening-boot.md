# 10: 生产化收口：一键启动与端到端验收

**What to build:** 一条命令启动完整环境（数据库、Redis、向量库、API、worker、迁移）；错误契约与依赖健康检查收口；README 与新用户快速开始流程齐全；端到端冒烟覆盖 MVP 主闭环；全量测试绿。

**Blocked by:** 06（任务执行与失败语义）、07（删除级联：向量、文件、记录）、09（Chat v2：get_document 深挖与页级来源）

**Status:** resolved

- [ ] `docker compose up` 一次完成：postgres healthy → migrate 完成 → api/worker 启动，redis 与独立向量库可用，上传目录为 api/worker 共享卷
- [ ] 端到端冒烟：注册 → 上传 → 文档 completed → 提问 → 得到带来源的回答
- [ ] 依赖不可用时健康检查或相关接口返回 503 类明确错误，而不是笼统崩溃
- [ ] 统一错误体在所有端点生效（code/message/request_id）
- [ ] README 含快速开始、环境变量说明与本地开发指引
- [ ] 全量自动化测试通过，含跨用户隔离矩阵

## Answer

已实现并验证（commit 见下方）：MVP 生产化收口。

- Dockerfile（python:3.12-slim、非 root appuser、/data/uploads 共享卷权限）+ .dockerignore + app/run_worker.py（ARQ 入口）
- docker-compose 全拓扑：postgres(healthy) → migrate(completed) → api/worker；redis、chroma（独立服务）healthcheck；api 宿主 8080、chroma 8000、postgres 5433；上传目录 uploads_data 同时挂载 api/worker
- `GET /health/detailed`：逐项检查 postgres/redis/chroma，任一不可用返回 503 SERVICE_UNAVAILABLE + 统一错误体
- 冒烟脚本 scripts/smoke_e2e.py：health → 依赖 → 注册/登录 → 会话 → 上传 → 轮询 completed →（有 key 时）chat + sources；自动清理冒烟数据
- README：快速开始、compose 启动、本地开发、环境变量与 API 概览
- 验证：全套 67 passed；真实 compose 一键启动成功；真实 DashScope Embedding 摄取 completed（chat 因本机未设 DEEPSEEK_MODEL 跳过）
