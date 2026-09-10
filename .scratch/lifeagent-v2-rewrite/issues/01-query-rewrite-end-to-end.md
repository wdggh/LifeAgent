# 01: Query Rewrite 端到端接入 search_knowledge

**What to build:** 开启配置后，每次 `search_knowledge` 调用先用单条改写后的
查询做检索；改写失败（超时/异常/空/多行/超长）回退原查询。改写过程写入
AgentRun trace。关闭配置时行为与 v2.0.2 基线完全一致。完成即可验证：
用脚本化假 LLM 与记录型假检索器，可以看到"检索实际使用了改写后的查询"或
"回退使用了原查询"，且 `retrieval_count`、预算与 Tool 签名不变。

**Blocked by:** None（v2.0.2 baseline 已完成）

**Status:** resolved

- [ ] 单条改写：口语转书面、同义词/业务词扩展、相对日期解析、保留专有名词与编号、多意图合并为一条、≤120 字符单行
- [ ] 守卫：含唯一编号正则时跳过；超时(默认 8s)/异常/空/多行/超长 → 回退原查询并记录原因
- [ ] 配置项 `query_rewrite_enabled` / `query_rewrite_timeout_seconds` / `query_rewrite_max_tokens`（含 .env.example）
- [ ] `search_knowledge` 使用改写查询调用检索；steps 记录 query_original / query_rewritten / rewrite_model / rewrite_fallback / rewrite_fallback_reason / rewrite_duration_ms
- [ ] `retrieval_count` 与每轮 chunk 预算语义不变
- [ ] fake LLM + fake Retriever 单测覆盖成功与全部回退路径；关闭配置时与基线行为一致

## Comments

## Answer

已实现并验证：

- `app/rag/query/rewriter.py`：单条查询改写（口语转书面、同义词/业务词扩展、
  用后端时区当前时间解析相对日期、保留专有名词与编号、多意图合并、
  ≤120 字符单行）；守卫：唯一编号正则跳过（如 PO-/WTY-/ABC-…），
  超时/异常/空/多行/超长 → fail-open 返回原 query 并记录原因；
  复用现有 LLMClient，`query_rewrite_max_tokens` 经 LLMClient 透传
  （接口新增可选 max_tokens 参数，OpenAI 兼容客户端使用）。
- 配置：`query_rewrite_enabled`（生产默认 true）、
  `query_rewrite_timeout_seconds=8`、`query_rewrite_max_tokens=200`
  （config.py + .env.example）。
- `search_knowledge`：启用时用改写后的单条 query 调 Retriever；`ToolResult`
  新增 `metadata`，Agent 将 metadata 合并进 `agent_runs.steps`
  （query_original / query_rewritten / rewrite_model / rewrite_fallback /
  rewrite_fallback_reason / rewrite_duration_ms，JSONB 无迁移）；
  `retrieval_count`、Tool 签名与预算语义不变。
- `AgentService` 用现有 LLMClient 构造 QueryRewriter 注入工具；测试环境通过
  conftest 默认 `QUERY_REWRITE_ENABLED=false`，既有测试保持基线行为。
- 测试：`tests/test_query_rewrite.py` 9 个用例全绿（成功、去引号、编号跳过、
  超时、异常、空、多行、超长、Tool 成功/回退/关闭、Agent step trace）。
- 回归：全量 pytest 仅 health 因 redis 容器未启动失败（与本改动无关）；
  启动 redis 后 health 2/2 通过；tests/evaluation 48 个 fast 用例全绿。

验收清单满足。下一步 V2.1-02 Live A/B 实验与 answer-level 重跑。
