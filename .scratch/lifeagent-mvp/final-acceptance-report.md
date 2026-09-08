# LifeAgent 后端 MVP 最终验收报告

验收日期：2026-09-08

验收基准：`HEAD = ae4d893`（Final review fixes）+ 工作区 4 个未提交文件。

## 结论（TL;DR）

| 验收项 | 结论 |
| --- | --- |
| 1. 功能闭环 | ✅ 通过 |
| 2. 数据隔离 | ✅ 通过 |
| 3. 异常链路 | ✅ 通过 |
| 4. Agent 可控性 | ✅ 通过 |
| 5. 工程质量 | ✅ 通过 |
| 6. 交付启动 | ⚠️ HEAD 原样不通过 → 修复后通过 |

**重要区分：**

- 仅以已提交的 `ae4d893` 为准：第 6 项不通过 —— Worker 启动即崩溃
  （`app/worker.py` 把 `WorkerSettings.on_startup` 写成列表，而 arq 0.26
  要求单个协程，`python -m app.run_worker` 直接报
  `TypeError: 'list' object is not callable`）。
- 以含本次修复的工作区为准：6/6 全部通过，MVP 具备冻结条件。

因此冻结动作 = 先提交下方 4 个文件的工作区改动（含修复与回归测试），再冻结。

## 验收方法

1. 静态审查：逐文件核对 API 路由、Service、Repository、Agent 循环、工具、
   RAG/摄取管线、Worker、迁移、Compose、配置与测试。
2. 动态验证：
   - 全量测试 **77 passed**（修复后；修复前 76 passed）
   - 一次性临时库 `lifeagent_accept`：`alembic upgrade head` 从零迁移成功，
     生成 `users / conversations / messages / documents / agent_runs`，
     `alembic_version = 0004`，随后删除临时库
   - `docker compose config` 校验通过；`docker compose up -d --build`
     完整重启成功：postgres/redis/chroma healthy，migrate `Exited (0)`，
     api 与 worker 持续运行
   - 真实端到端冒烟 `scripts/smoke_e2e.py` 对最新栈运行：
     真实 DashScope embedding 摄取 + 真实 Qwen（qwen-max）问答带来源，
     **SMOKE PASSED**

## 逐项结论与证据

### 1. 功能闭环 ✅

- 注册/登录/me：`app/api/routes/auth.py` + `UserService`，bcrypt + JWT。
- 上传 → 异步解析 → 向量化 → 入库：`documents.py` 上传入队，
  `worker.py`/`KnowledgeService` 执行 parse→chunk→embed→index，
  Chroma 元数据含 user/document/page/embedding_model。
- RAG 检索与多轮检索：`retriever.py`（强制 user 过滤）+ Agent 循环
  `app/agent/agent.py` 支持连续 tool 调用，直至可回答或预算耗尽。
- Agent Tool Calling：search_knowledge / get_document（限量上下文，
  页级读取，绝不全量返回）。
- 对话/消息：Conversation/Message 落库；chat 一轮 = user message +
  assistant message + 一条 agent_run。
- 来源引用：`ChatResponse.sources` 文档级 + relevance；页码/chunk 细节留
  `agent_runs.steps`。
- 删除/重试：DELETE 按 Chroma → 文件 → DB 行顺序、各步幂等可重试；
  `POST /documents/{id}/retry` 支持 failed / stale processing 重入队。
- 冒烟实测闭环全过（upload → completed → chat with sources）。

### 2. 数据隔离 ✅

- `user_id` 只来自 JWT：`app/api/dependencies.py#get_current_user`，
  客户端无法传 user_id（schema `extra="forbid"`，注册 payload 也拒绝）。
- Document/Conversation 查询一律 `WHERE id = ? AND user_id = ?`
  （`document_repository.py` / `conversation_repository.py`），
  get_document 工具同样做 owner 校验。
- Chroma 检索在 `Retriever.search` 强制注入 `user_id` 过滤；user_id
  不是任何 Tool 参数。
- 跨用户访问统一 404（GET/DELETE/retry/chat/工具读文档），
  测试矩阵覆盖：test_documents、test_conversations、test_chat_v1、
  test_chat_v2、test_task_retry。

### 3. 异常链路 ✅

测试逐项覆盖（fake LLM/Embedding，无需真实 key）：

- 非法扩展名/魔数不符/非 UTF-8 → 415 `UNSUPPORTED_FILE_TYPE` /
  `INVALID_FILE_CONTENT`；超限 → 413 `FILE_TOO_LARGE`。
- 空文件 / 坏 PDF / 无文本 PDF → failed + 可读 error_message（ParsingError
  不重试）。
- Embedding 瞬断：worker 重试至 3 次后 completed（FlakyEmbeddingClient）。
- Chroma/向量异常：删除任一步失败保留行、可重试成功。
- LLM 调用失败/超时：HTTP 客户端 90s timeout；失败落 failed agent_run，
  API 返回 503 `LLM_UNAVAILABLE`，不落 assistant 消息。
- Worker 重试 + stale 恢复：超 15 分钟 processing 可 retry；worker 启动
  sweep 自动重入队。
- Agent 达最大迭代/检索上限：正常收束并如实作答或声明资料不足。

### 4. Agent 可控性 ✅

- `MAX_ITERATIONS=5`、`MAX_RETRIEVALS=3`、`LLM_MAX_TOKENS=1500`、
  `CHUNKS_PER_ROUND=4` 代码强制（非仅 prompt）。
- 停止规则：命中为空、连续无新增、预算耗尽三路都收敛；收尾调用不带 tools。
- 无结果时系统提示 + 测试断言"无法/资料中没有找到"，不胡编。
- 检索不足可继续检索（多轮测试：检索 2 次合并 2 个来源回答）。
- 最终答案带来源（document_name/document_id/relevance）。
- 前端只拿 answer/sources/metadata；steps/args/工具中间文本只落
  `agent_runs.steps`，不暴露内部推理。
- 护栏：检索内容标注"data, not instructions"；后端注入当前日期与用户时区。

### 5. 工程质量 ✅

- 测试：unit/integration/API 混合，主 seam 为 HTTP + fake 外部依赖；
  修复后 **77 passed**（Auth、Documents、Conversations、Ingestion、
  Task/Retry、Delete Cascade、Chat v1/v2、错误契约、request_id、
  review-fixes 回归）。
- 日志：结构化 JSON、request_id 贯穿（X-Request-ID 回显 +
  ContextVar + error body 同 id）。
- `agent_runs` 表：query/status/iterations/retrieval_count/duration/
  error_message/steps(JSONB)。
- Docker Compose：postgres/redis/chroma/migrate/api/worker 全拓扑 +
  healthcheck + 依赖顺序 + 共享 uploads 卷。
- Alembic：4 个迁移（0001→0004），空库实测可一次升到 head。
- README 完整（快速开始/compose/本地开发/env 说明/API 概览）；
  `.env.example` 齐全。

### 6. 交付启动 ⚠️→✅

实测链路：

```text
docker compose up -d --build
  → postgres healthy → migrate Exited(0)（alembic upgrade head）
  → api + worker 启动
  → GET /health/detailed 全 ok
  → smoke_e2e.py：SMOKE PASSED（含真实 ingestion + 真实 chat with sources）
```

发现的阻塞（已在工作区修复）：

- 根因：`app/worker.py` 中 `WorkerSettings.on_startup = [sweep_stale_processing]`
  为列表；arq 0.26 `Worker(on_startup=...)` 只接受单个协程函数，
  worker 容器启动即崩溃。
- 修复：改为 `on_startup = sweep_stale_processing`，并新增回归测试
  `test_worker_settings_on_startup_is_single_callable`
  （`tests/test_review_fixes.py`）。
- 修复后重建验证：worker 稳定运行；全量 77 passed；真实冒烟通过。

## 待提交工作区改动（冻结前置）

```text
 M .env.example               # 补 LLM_BASE_URL（此前 review 修复遗漏未提交）
 M docker-compose.yml         # 补 LLM_BASE_URL 环境透传
 M app/worker.py              # on_startup 列表 → 单个协程（本次阻塞修复）
 M tests/test_review_fixes.py # 新增 worker 启动回归测试
```

建议一条 commit 提交后即视为可冻结基线（当前容器已按该工作区重建运行）。

## 非阻塞观察（建议但不必阻塞冻结）

1. `POST /documents/{id}/retry` 未捕获入队失败：Redis 不可用时抛 500
   `INTERNAL_ERROR`，与 upload 路径的 503 `SERVICE_UNAVAILABLE` 语义不一致。
   建议捕获 dispatcher 异常并映射 503。
2. 设计基线写"单次工具超时 10s"，实现只有 LLM 请求 90s 超时，无单工具/
   整轮 Agent 超时（受 max_iterations 约束，行为有界）。如需严格超时预算
   可后补。
3. 快速连续 retry / sweep 与在途任务可能重复入队；并发 ingest 同一文档会
   因随机 chunk_id 产生重复向量。MVP 可接受，后续可在 retry 侧做幂等或
   按文档加锁。
4. 测试建表走 `Base.metadata.create_all`，未覆盖 Alembic 脚本本身；
   本次验收已单独用空库实测迁移，建议后续 CI 加一步 alembic 冒烟。

## 结论

提交工作区 4 个文件（含本次 Worker 修复）后，LifeAgent 后端 MVP
**6/6 项通过，可以冻结**。
