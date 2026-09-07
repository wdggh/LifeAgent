# 01: 工具非法参数优雅失败（Spec 2）

**What to build:** search_knowledge/get_document 对非法参数返回结构化失败，Agent 正常继续/停止，绝不因参数错误把整个请求打成 503。

**Blocked by:** None

**Status:** resolved

- [ ] search_knowledge 的 top_k/document_type/document_id 非法输入不抛异常
- [ ] 非法参数时 ToolResult 带 error 字段与可读 text
- [ ] AgentRun.steps 中该步记录 error
- [ ] Chat 返回 200 且步骤含 error（不再 LLM_UNAVAILABLE/503）

## Answer

已修复：search_knowledge 对 query/top_k/document_type/document_id 全量校验，非法输入返回 ToolResult.error；未知工具同样记录 error；参数错误的检索不再计入 retrieval_count。详见 report.md。
