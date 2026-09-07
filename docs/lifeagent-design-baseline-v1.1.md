# LifeAgent 设计基线 v1.1（MVP 定稿草稿）

> 状态：**DRAFT**，等待用户最终确认。确认后作为开发基线；后续改动核心架构需先讨论并记录 ADR。
> 关联文档：`CONTEXT.md`（术语）、`docs/adr/0001-0005`（决策）、`AGENTS.md`（工程技能配置）。

## 0. 相对 v1.0 的变更摘要

| 主题 | v1.0 | v1.1 决策 |
| --- | --- | --- |
| 数据库 | 未定 | PostgreSQL + SQLAlchemy + Alembic |
| 异步执行 | 未定 | ARQ + Redis 独立 worker；api/worker 分离 |
| Embedding | 未定 | 阿里 DashScope `text-embedding-v3`，OpenAI 兼容模式，维度 1024 |
| 会话 | 仅概念 | Conversation/Message 落库；role 仅 user/assistant；历史注入最近 10 条（按 token 截断） |
| 追踪 | 无 | `agent_runs` 单表 + `steps` JSONB |
| 工具 | search/get_document | 增加过滤参数；get_document 明确为"限量取上下文" |
| 文档生命周期 | 只有上传 | 增加 retry、删除一致性、15 分钟陈旧状态 |
| 权限语义 | 403 | 跨用户资源统一 404 |
| 引用 | 文档级 | UI 文档级；chunk/页码内部保留 |
| Parser | LangChain Loader | 自研按页解析 + langchain-text-splitters 切分 |
| LLM | deepseek.py | `LLMClient` 接口 + DeepSeek 实现 |
| Chroma | 未定 | 独立服务；collection 带模型标识；user_id metadata 过滤隔离 |
| 认证 | 只有注册/登录 | 增加 `GET /auth/me` |

## 1. 项目定位与 MVP 闭环

LifeAgent：个人生活信息与决策助手。用户上传个人资料，系统构建个人知识库；用户用自然语言提问，Agent 自主判断检索策略、必要时多次检索、综合资料回答并返回来源。

MVP 闭环：注册/登录 → 上传（PDF/TXT/MD）→ 异步解析/切分/Embedding/索引 → 提问 → Agent 规划 → Tool 调用 → RAG 检索 → 必要时再检索 → 综合分析 → 回答 + 来源。

MVP 明确不做：MCP、多 Agent、日历/提醒、自动执行类操作、邮件/微信/语音、OCR/扫描件、Word/Excel、混合检索/重排序/知识图谱、复杂权限与推荐系统。

## 2. 分层架构与依赖方向

```text
API Layer      → 参数校验、认证、响应格式、HTTP 异常映射（无业务逻辑）
Service Layer  → 业务流程编排（User/Document/Knowledge/Conversation/Agent）
Domain Layer   → 纯业务对象与规则（不依赖 FastAPI/SQLAlchemy/Chroma/LLM）
Repository Layer → 数据访问抽象接口
Infrastructure → PostgreSQL/SQLAlchemy、Chroma、LLM/Embedding Provider、本地文件存储

依赖方向：API → Service → Domain / Repository → Infrastructure
禁止反向依赖；Agent 不直接碰数据库/向量库，只通过 ToolRegistry。
```

核心模块：

```text
AgentService → Agent → ToolRegistry → Tool → Service/RAG → Repository → Infrastructure
DocumentService  → 只管理文档记录与文件（不执行解析）
KnowledgeService → 拥有摄取管线编排（ingest(document_id)），由 worker 调用
```

## 3. API 契约（base：`/api/v1`）

### Auth

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/auth/register` | username/password → user_id、username |
| POST | `/auth/login` | username/password → access_token、token_type |
| GET | `/auth/me` | 从 token 取当前用户信息 |

### Documents

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/documents` | multipart 上传（file + document_type）；快速返回，processing 异步执行 |
| GET | `/documents?page=&page_size=` | 当前用户文档列表（时间倒序） |
| GET | `/documents/{id}` | 详情：状态、processing_stage、error_message |
| DELETE | `/documents/{id}` | 删除：Chroma → 磁盘文件 → DB 行；任一步失败保留行可重试 |
| POST | `/documents/{id}/retry` | 失败/陈旧状态的文档重新入队（接受的 action 端点，不为纯 REST 纠结） |

### Conversations & Chat

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/conversations` | 创建会话（title 可选） |
| GET | `/conversations` | 当前用户会话列表 |
| GET | `/conversations/{id}` | 会话及消息 |
| DELETE | `/conversations/{id}` | 删除会话 |
| POST | `/chat` | `{conversation_id, query}` → `{answer, sources, metadata}`；同步执行 |

`chat` 返回示例：

```json
{
  "answer": "...",
  "sources": [
    {"document_id": "doc_001", "document_name": "健身会员合同.pdf", "relevance": 0.91}
  ],
  "metadata": {"retrieval_count": 2, "duration_ms": 3240}
}
```

来源 UI 文档级；chunk/页码级引用保留在内部（agent_runs.steps），供回放与后续"来源下钻"。

### 统一错误

```json
{"error": {"code": "DOCUMENT_NOT_FOUND", "message": "...", "request_id": "req_001"}}
```

状态码：400 参数错误、401 未认证、404 资源不存在（**含跨用户资源，不泄露存在性**）、413/415 上传超限/类型不支持、422 校验失败、503 依赖服务不可用。资源查询一律 `WHERE id = ? AND user_id = current_user_id`。

## 4. 数据模型（PostgreSQL）

### users

`id, username, password_hash, created_at, updated_at`

### documents

`id, user_id, filename, file_type, file_path, file_size, document_type, status, processing_stage, error_message, embedding_model (nullable), created_at, updated_at`

### conversations

`id, user_id, title, created_at, updated_at`

### messages

`id, conversation_id, role (user|assistant), content, agent_run_id (nullable), created_at`

role 仅 user/assistant；system prompt 是配置，不落库。

### agent_runs

`id, user_id, conversation_id, query, status, iterations, retrieval_count, duration_ms, error_message, steps (JSONB), created_at`

steps 最小结构（不过度设计）：

```json
[
  {"iteration": 1, "tool": "search_knowledge", "args_summary": {"query": "...", "top_k": 5},
   "result_count": 3, "duration_ms": 420, "error": null}
]
```

关系：User 1:N Document / Conversation；Conversation 1:N Message；一次 chat = 一条 user Message + 一条 assistant Message + 一条 AgentRun。

### Chroma（独立服务）

每条记录：`id, embedding, content, metadata`

metadata 必含：`user_id, document_id, document_name, document_type, start_page, end_page, chunk_index, embedding_model`

- collection：`lifeagent_text-embedding-v3_1024`（命名带模型+维度）
- 隔离：所有检索在 Retriever 层强制注入 `user_id` 过滤；LLM 永远拿不到 user_id 参数
- 无 PostgreSQL Chunk 表：Chunk 存 Chroma

## 5. Agent 设计

### 工具签名

```python
search_knowledge(query: str, top_k: int = 5,
                 document_type: str | None = None,
                 document_id: str | None = None)
# 后端强制叠加 user_id 过滤；document_type/document_id 只是 LLM 的意图表达

get_document(document_id: str, page: int | None = None, max_chars: int = 8000)
# 返回该文档的有限上下文（按页/限量），不是整个 Document
```

两个工具都返回结构化结果：`{chunk_id/document_id/document_name/start_page/end_page/content/score}`。

### 预算与停止规则（常量，可调）

| 常量 | 值 |
| --- | --- |
| MAX_ITERATIONS | 5 |
| MAX_RETRIEVALS | 3 |
| top_k 默认 | 5 |
| 单 chunk 注入上限 | ~1000 tokens（超长截断并标记） |
| 单轮注入上限 | 4 条 chunk |
| LLM max_tokens | 1500 |
| 单次工具超时 | 10s |

停止规则：
1. 命中为空 → 停止，如实说明"资料中没有找到"；
2. 连续检索无新增 → 停止；
3. 预算耗尽 → 用已确认信息作答或声明不足；
4. 任何断言尽量对应 sources，宁可不答也不编造。

### 多轮上下文

每轮注入本会话最近 10 条消息，并按 token 预算截断。

### 回答护栏（已采纳）

- 后端注入当前日期 + 用户时区（不依赖模型猜"今天"）；
- 数值/聚合类回答展示关键数字出处、计算过程与假设；算不出就明说缺什么记录；
- 检索资料一律标记为 data（不可信内容），文档内指令不作为系统指令；
- 检索到的资料不执行指令性文字。

## 6. RAG 管线

```text
PDF/TXT/MD → Parser(自研, 按页) → PageDocument → Chunker(RecursiveCharacterTextSplitter)
           → Chunk(start_page/end_page) → Embedding(DashScope text-embedding-v3, dim 1024)
           → Indexer(自研) → Chroma
           → Retriever(自研, user_id 强制过滤) → SearchResult
```

- Parser：PDF 用 pypdf/pdfplumber 按页提取；TXT/MD 直接读（编码检测）；空文本检测 → failed（"疑似扫描件，暂不支持 OCR"）。
- Chunker：`langchain-text-splitters`；chunk 记录 `start_page/end_page`（允许跨页，但来源可定位到页区间）。
- Embedding：Provider 抽象，MVP 只实现 DashScope；三处版本记录（documents 列 / collection 名 / chunk metadata）。
- Retriever：只接受当前用户作用域；metadata 过滤参数可选叠加。

## 7. 状态机与任务语义

### Document 状态

```text
uploaded → processing（内部依次 parsing → chunking → embedding → indexing）→ completed
                              ↘ 任意阶段失败 → failed（记录 error_message）
```

### 任务语义（ARQ + Redis）

- `max_retries=2`，指数退避；耗尽后 Document = failed，用户可 retry；
- 陈旧状态：processing 且 `updated_at` 超过 15 分钟视为可重试（retry 端点接受），worker 启动时可扫描清理；
- worker 崩溃不丢已入队任务；中断任务靠陈旧状态机制兜底。

### 删除顺序（幂等、可重试）

Chroma（按 document_id）→ 磁盘文件 → DB 行；任一步失败返回 5xx 且保留 DB 行，重复调用 DELETE 即可。

## 8. 部署拓扑（Docker Compose）

```text
postgres
  ↓ healthy
migrate（一次性：alembic upgrade head）
  ↓ service_completed_successfully
api + worker
redis（api/worker 共用）
chroma（独立服务，api/worker 通过 HTTP 访问）
uploads volume → 同时挂载 api 与 worker
```

`docker compose up` 一次完成开发环境初始化。

## 9. 工程规范

- 认证：bcrypt 哈希；JWT access token（过期默认 24h）；无 refresh/logout/邮箱验证（MVP 外）；user_id 只来自认证信息。
- 上传：扩展名 + magic bytes 双重校验；单文件 ≤50MB；存储名用 UUID，原始文件名仅存 DB；目录不可被静态服务访问。
- 日志：request_id 贯穿中间件；结构化字段（user_id/conversation_id/document_id/agent iteration/tool/retrieval count/stage/duration）；不记 chunk 原文、凭据、完整资料。
- 可观测：agent_runs 落库用于"为什么答错"回放；依赖健康检查后置。
- 测试：unit/integration/api；越权矩阵（跨用户 document/conversation → 404）；LLM/Embedding 用 fake 以便无 key 可跑；状态机与检索隔离用例。
- Git：`.gitignore` 已建（.env、data/uploads、Python 缓存）；feature branch 流程。

## 10. 目录结构（含本次调整）

```text
life-agent/
├── app/
│   ├── api/routes/{auth,documents,conversations,chat,health}.py + dependencies.py
│   ├── services/{user,document,knowledge,conversation,agent}_service.py
│   ├── domain/entities/{user,document,conversation,message}.py
│   ├── domain/models/{chunk,search_result,agent_state,agent_response}.py
│   ├── repositories/{user,document,conversation,vector}_repository.py
│   ├── agent/{agent,state,tool_registry}.py + tools/{search_knowledge,get_document}.py
│   ├── rag/ingestion/{parser,chunker,embedder,indexer}.py
│   ├── rag/retrieval/retriever.py
│   ├── infrastructure/
│   │   ├── database/（SQLAlchemy models + session）
│   │   ├── vector_store/chroma.py
│   │   ├── llm/{base.py → LLMClient, deepseek.py → DeepSeekClient}
│   │   ├── embedding/{base.py → EmbeddingClient, dashscope.py}
│   │   └── storage/local_storage.py
│   ├── schemas/{auth,document,conversation,chat}.py
│   ├── core/{config,security,exceptions,logging}.py
│   ├── worker.py（ARQ 任务注册/入口）
│   └── main.py
├── tests/{unit,integration,api}/
├── data/uploads/（volume）
├── migrations/
├── .env / .env.example / .gitignore
├── Dockerfile / docker-compose.yml / requirements.txt
└── README.md
```

## 11. 开发顺序（基线不变）

① 项目骨架与配置 → ② 认证/用户 → ③ 文档上传与文件存储 → ④ Document 状态机 + 任务骨架 → ⑤ Parser/Chunker → ⑥ Embedding/Index → ⑦ Retriever + 隔离测试 → ⑧ Agent Loop + 工具 → ⑨ Chat API + 会话 → ⑩ 异常/日志/测试加固 → ⑪ Docker Compose 联调 → ⑫ RAG/Agent 效果调优。

## 12. 待确认默认值 / 占位

- `DEEPSEEK_MODEL`：.env 留空，按你账号实际可用模型 id 填入；
- agent_runs 字段清单与 steps 最小结构按上文，若你想加/减字段（如 token_usage）在确认时提出；
- 会话/消息列表分页与标题自动生成：暂定后置（先按时间倒序全量返回，量大再加分页）；
- 文件下载/原文预览端点：后置；
- LLM/Embedding 失败时的服务降级文案与 503 语义：实现时按统一错误体补全。

## 13. 变更原则

核心架构改动（DB、任务模型、Agent 工具签名、部署拓扑）先讨论并补 ADR，不边写边改。术语以 `CONTEXT.md` 为准；与 ADR 冲突时显式提出。
