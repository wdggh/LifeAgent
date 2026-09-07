# Post-Review Fixes Report

> 范围：`code-review`（98743a4..HEAD）发现的 12 项 → 修复批次 `.scratch/post-review-fixes/issues/01-08`
> 日期：2026-09-07

## 修复清单与结论

| Ticket | 审查发现 | 修复方式 | 验证 |
| --- | --- | --- | --- |
| 01 | Spec 2：工具非法参数变 503 | search_knowledge 参数全量校验，返回 `ToolResult.error`；错误检索不计 retrieval_count | Chat 200 + steps.error；单测覆盖 |
| 02 | Spec 5：入队失败留 uploaded 僵尸 | 入队失败回滚（删记录+删文件）并返回 503 SERVICE_UNAVAILABLE | 上传 503 后列表/目录为空 |
| 03 | Spec 1：per-round ≤4 chunks 未实现 | `MAX_CHUNKS_PER_ROUND=4` 代码强制截断 | top_k=10 → 实际 4 |
| 04 | Spec 3：steps 缺 error | 成功 `error:null`，失败记录原因；未知工具同 | 单测 + Chat 步骤断言 |
| 05 | Spec 4：worker 启动无 stale sweep | `list_stale_processing` + worker `on_startup` 重入队 | 30min 陈旧入队 / 1min 新鲜不入队 |
| 06 | Standards 1：LLM 复用 embedding base URL | 新增 `LLM_BASE_URL`，DashScopeLLMClient 独立使用 | 真实 qwen-max 冒烟通过 |
| 07 | Standards 3：EMBEDDING_PROVIDER 未生效 | 最小 factory `get_embedding_client()`，deps/worker 接入 | 全套测试绿 |
| 08 | Standards 4/5/6：裸字符串/uuid 重复/函数内 import | 常量（DocumentStatus/ProcessingStage/MessageRole/AgentRunStatus）、共享 uuid helper、import 上移 | compileall + 全套测试绿 |

## 验证

- 新增 5 个修复回归测试（`tests/test_review_fixes.py`）
- 全套：**72 passed**（原 67 + 新增 5）
- 真实 compose + qwen-max 端到端冒烟：`SMOKE PASSED`（含 chat with sources）
- 修复了容器 Python 3.12 下暴露的注解延迟求值差异（补 `datetime` import）

## 残留说明（有意保留，非缺陷）

- Spec 内部矛盾：基线预算表写 top_k=5、同时写 per-round cap 4；实现按 per-round cap 4 优先并保留默认 top_k=5 配置字段。
- Standards #2（端口接口位于 infrastructure）与设计基线目录树一致，按"仓库文档优先"降级保留；后续若引入多 Context 再议。
- `DocumentService` 默认实例化 `ChromaVectorRepository` 属 P2 范围，本轮未重构（行为正确，路由注入可后续优化）。
- `steps.args_summary` 目前存完整参数而非摘要；MVP 调试期保留全量更利于回放，如后续涉及敏感字段再改为摘要。

## 第二轮修复（code-review of fix commit 5bc1c6f）

复查发现 4 项并全部修复（tickets 09-10）：

| 发现 | 修复 |
| --- | --- |
| get_document 失败路径未填 error | 全部失败路径补 `error=`（invalid document_id/page/max_chars、document_not_found、document_unreadable、page_not_found） |
| per-round cap 实为 per-call | ToolContext.chunk_budget 轮级预算，多 search 调用合计 ≤4（测试：两调用返回 3+1） |
| 工具 schema 上限 10 与截断 4 不一致 | schema maximum/描述与代码对齐为 CHUNKS_PER_ROUND=4 |
| document_type 清单三处重复 | 收敛为 domain/constants.DOCUMENT_TYPES |
| _fail 缩进回归 | 恢复 4 空格 |

验证：新增 2 个回归测试；全套 **74 passed**；compileall 通过。

## 第三轮（收尾 code-review of 7252aa2，tickets 09/10 跟进）

最终 code-review 双轴（Standards 子代理 4 项；Spec 内联 2 项）指向同一批小问题，已修复：

| 发现 | 修复 |
| --- | --- |
| `chunk_budget` 名不副实且 `max(1,0)` 使轮级上限可到 5 | 改名 `remaining_chunk_budget`；预算耗尽返回 `budget_exhausted`，严格 ≤4 |
| 预算默认值 4 双写 | 默认值改由 `CHUNKS_PER_ROUND` 提供单一来源 |
| 工具 schema enum 仍手写六值 | `enum=sorted(DOCUMENT_TYPES)` |
| API `DocumentType` Literal 与常量可能漂移 | 新增等价断言测试钉住 |
| 4+1 越界无测试覆盖 | 新增 `budget_exhausted` 边界测试（4+0） |

验证：新增 2 个测试；全套 **76 passed**；compileall 通过。
