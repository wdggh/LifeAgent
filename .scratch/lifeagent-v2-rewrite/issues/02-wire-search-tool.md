# 02: 接入 search_knowledge + 配置 + steps trace

**What to build:** `SearchKnowledgeTool` 内部先调用 QueryRewriter，用改写后的
单条 query 调 Retriever；失败回退原 query。保持 Tool 签名、Agent 循环、
`retrieval_count`、预算语义不变；steps 增加
`query_original/query_rewritten/rewrite_model/rewrite_fallback/
rewrite_fallback_reason/rewrite_duration_ms`；配置关闭时行为与 V2.0 完全一致。

**Blocked by:** 01

**Status:** open

- [ ] 工具内置改写；fake Retriever 断言实际检索用改写后 query
- [ ] 回退路径断言用原 query；retrieval_count 仍为 1
- [ ] steps 字段落库（JSONB，无迁移）
- [ ] `query_rewrite_enabled=false` 时行为与基线一致（回归测试）

## Comments
