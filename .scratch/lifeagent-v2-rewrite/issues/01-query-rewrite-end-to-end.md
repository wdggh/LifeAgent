# 01: Query Rewrite 端到端接入 search_knowledge

**What to build:** 开启配置后，每次 `search_knowledge` 调用先用单条改写后的
查询做检索；改写失败（超时/异常/空/多行/超长）回退原查询。改写过程写入
AgentRun trace。关闭配置时行为与 v2.0.2 基线完全一致。完成即可验证：
用脚本化假 LLM 与记录型假检索器，可以看到"检索实际使用了改写后的查询"或
"回退使用了原查询"，且 `retrieval_count`、预算与 Tool 签名不变。

**Blocked by:** None（v2.0.2 baseline 已完成）

**Status:** claimed

- [ ] 单条改写：口语转书面、同义词/业务词扩展、相对日期解析、保留专有名词与编号、多意图合并为一条、≤120 字符单行
- [ ] 守卫：含唯一编号正则时跳过；超时(默认 8s)/异常/空/多行/超长 → 回退原查询并记录原因
- [ ] 配置项 `query_rewrite_enabled` / `query_rewrite_timeout_seconds` / `query_rewrite_max_tokens`（含 .env.example）
- [ ] `search_knowledge` 使用改写查询调用检索；steps 记录 query_original / query_rewritten / rewrite_model / rewrite_fallback / rewrite_fallback_reason / rewrite_duration_ms
- [ ] `retrieval_count` 与每轮 chunk 预算语义不变
- [ ] fake LLM + fake Retriever 单测覆盖成功与全部回退路径；关闭配置时与基线行为一致

## Comments
