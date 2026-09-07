# 08: P2 housekeeping（Standards 4/5/6）

**What to build:** 顺手清理：状态/阶段/role 常量、uuid 去重、Agent 循环内函数级 import。

**Blocked by:** None

**Status:** resolved

- [ ] 关键状态/阶段/role 使用常量（不过度重构）
- [ ] _uuid_hex 重复定义收敛为共享工具
- [ ] Agent.run 内 import ToolContext 移到模块顶部

## Answer

已修复：DocumentStatus/ProcessingStage/MessageRole/AgentRunStatus 常量、共享 uuid helper、Agent.run 内 import 上移。详见 report.md。
