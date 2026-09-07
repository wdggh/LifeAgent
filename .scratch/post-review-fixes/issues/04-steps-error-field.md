# 04: AgentRun.steps 增加 error 字段（Spec 3）

**What to build:** 每次工具调用 steps 记录 error（成功 null，失败给原因），便于回放排查。

**Blocked by:** None

**Status:** resolved

- [ ] 成功步骤 error=null
- [ ] 参数失败步骤 error 含原因（如 invalid top_k）
- [ ] 未知工具错误同样记录

## Answer

已修复：AgentRun.steps 每步增加 error（成功 null / 失败原因）。详见 report.md。
