# 01: QueryRewriter 模块（prompt + guards + fake 测试）

**What to build:** `app/rag/query/rewriter.py`（或等价位置）：`QueryRewriter`
接口 + LLM 实现，输入 query/now，输出单行改写或回退；规则：口语转书面、同义词/
业务词扩展、相对日期解析、保留专有名词与编号、多意图合并、≤120 字符；
守卫：编号正则跳过、超时(8s)/异常/空/多行/超长 → 回退；配置
`query_rewrite_enabled`、`query_rewrite_timeout_seconds`、
`query_rewrite_max_tokens=200`。测试只用 ScriptedFakeLLM 覆盖成功与全部回退
路径，不调真实 API。

**Blocked by:** V2.0.2 完成

**Status:** open

- [ ] 接口与 LLM 实现；失败 fail-open 且带 reason
- [ ] exact-term 跳过；当前日期注入；长度/单行约束
- [ ] 配置项入 config.py + .env.example
- [ ] ScriptedFakeLLM 单测：成功、超时、异常、空、多行、超长、编号跳过、日期解析

## Comments
