# 09: Chat v2：get_document 深挖与页级来源

**What to build:** Agent 找到目标文档后能读取其有限上下文（按页/限量）再作答，例如回答"这份合同里的退款条款"；工具调用与页区间信息保留在运行记录中供追踪。

**Blocked by:** 08（Chat v1：Agent 检索问答）

**Status:** resolved

- [ ] Agent 可对检索命中的文档调用 get_document，读取受 page/max_chars 约束的内容（绝不含整篇文档）
- [ ] 读取后能给出比单次检索更准确的回答（用"合同退款条款"类场景验证）
- [ ] 工具结果与内部 steps 保留页区间，可追溯到"第几页"
- [ ] 尝试读取他人文档时不会泄露任何内容（视为不可用/无结果）
- [ ] 工具参数非法时优雅失败并继续/停止，不崩溃

## Answer

已实现并验证（commit 见下方）：get_document 深挖 + 页级来源追踪。

- [get_document 工具](app/agent/tools/get_document.py)：按 document_id + 当前用户校验归属（他人文档与不存在同响应，零泄露）；只返回受限内容（可选 page、max_chars 默认 8000、上限 20000），绝不全量返回
- Agent 循环支持混合工具轮：get_document 轮不再误判"无检索结果即停止"，可继续让 LLM 决定下一步
- 深挖结果带文件名 + 页码/页区间 + 截断标记；steps 记录工具名与参数（含 page），AgentRun 可回放
- 非法参数（缺 document_id、page<=0、max_chars 非法）返回工具级错误，不崩溃
- 测试：5 个 Chat v2 用例（深挖作答、跨用户不可读、参数容错、max_chars 截断、页码不存在）+ 全套 66 passed
