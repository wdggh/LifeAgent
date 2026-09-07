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
