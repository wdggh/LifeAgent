# 08: Chat v1：Agent 检索问答

**What to build:** 用户能在已有知识的会话里提问；Agent 自主决定是否检索、可多次检索直到信息足够，按预算停止并如实承认信息不足；回答附文档级来源；消息与运行记录落库；检索严格限定在当前用户范围。

**Blocked by:** 03（会话管理）、05（摄取管线核心）

**Status:** resolved

- [ ] 提问后生成回答：user Message、assistant Message、AgentRun 均落库并关联
- [ ] 回答携带文档级 sources；metadata 含 retrieval_count 与 duration_ms
- [ ] Agent 只在需要时检索；无资料或与资料无关的问题不会编造个人资料
- [ ] 检索支持 document_type 与 document_id 过滤（如"只看健身合同""查这份合同"的定位）
- [ ] 信息不足时可再次检索（用 Fake LLM 脚本验证两轮场景），检索次数与迭代受预算上限约束
- [ ] 命中为空 / 连续检索无新增 / 预算耗尽时按停止规则收尾，不无限循环
- [ ] 所有检索强制注入当前用户过滤；任何跨用户数据不可见（隔离测试矩阵）
- [ ] 同一会话的追问能利用最近历史（最近 10 条、按 token 截断）
- [ ] 护栏生效：当前日期与时区由后端注入；文档内指令不会覆盖系统规则；LLM 失败时返回可读错误而非编造回答
- [ ] 他人会话提问返回 404；未认证返回 401

## Answer

已实现并验证（commit 见下方）：Chat v1（Agent 检索问答）全链路。

- 自研 Agent Loop（ADR-0006）：planning → search_knowledge Tool Call → observation → evaluating → completed；预算（max_iterations/max_retrievals）、停止规则（空命中/无新增/预算耗尽）与 grounding 指令在 [agent.py](app/agent/agent.py)
- search_knowledge 工具：query/top_k/document_type/document_id 过滤；user_id 永远由后端注入；检索结果标记为 data（防 Prompt 注入）
- LLM：`LLMClient` 接口 + DeepSeek OpenAI 兼容实现（测试用 Scripted Fake）
- Retriever：查询 Embedding + Chroma 检索（user_id 强制过滤，$and 组合过滤）
- 持久化：user/assistant Message + AgentRun（含 steps JSONB，消息 agent_run_id 关联）；agent_runs 表迁移 0004
- 护栏：当前日期/时区注入、资料指令不可执行、信息不足如实说明、LLM 失败 → 503 LLM_UNAVAILABLE 且记录 failed run
- API：POST /api/v1/chat → answer/sources（文档级+relevance）/metadata（retrieval_count/duration_ms）
- 测试：9 个 Chat v1 用例（多轮检索+持久化、免检索、空命中诚实回答、无新增停止、预算上限单元测试、跨用户隔离+404、doc_type 过滤、历史注入+护栏、LLM 失败 503）+ 全套 61 passed
