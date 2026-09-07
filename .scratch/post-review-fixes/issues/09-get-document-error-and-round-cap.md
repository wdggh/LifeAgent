# 09: get_document error 契约 + 真 per-round cap + 契约对齐

**What to build:** get_document 所有失败路径填 error=；Agent 每轮检索注入总量 ≤4（跨多次调用）；工具 schema 上限与代码一致；document_type 清单收敛。

**Blocked by:** None

**Status:** resolved

- [ ] get_document 非法/不可读/找不到均返回 error 且 steps.error 非空
- [ ] 同一轮多次 search_knowledge 合计注入 ≤4 chunks
- [ ] search_knowledge schema maximum 与代码一致（≤4）
- [ ] document_type 允许清单收敛为共享常量

## Answer

已修复：get_document 全失败路径填 error；Agent 轮级 chunk 预算（ToolContext.chunk_budget）保证多 search 调用合计 ≤4；schema maximum 与代码一致（≤4）；DOCUMENT_TYPES 收敛到 domain/constants。新增 2 个回归测试。
