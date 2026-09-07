# 06: 任务执行与失败语义：worker、重试、陈旧状态

**What to build:** 摄取由独立 worker 异步执行；失败自动重试两次后变为 failed 且原因可读；用户可对失败文档发起 retry；worker 崩溃不会让文档永远卡在 processing。

**Blocked by:** 05（摄取管线核心）

**Status:** resolved

- [ ] 上传后处理在 worker 中异步完成，API 请求不阻塞且先返回
- [ ] 任务瞬态失败自动重试（最多 2 次、带退避），耗尽后 Document 变为 failed 并记录错误
- [ ] 对 failed 文档调用 retry 会重新入队，重跑前清理该文档此前残留的向量
- [ ] 成功 retry 后文档最终 completed
- [ ] processing 且超过 15 分钟未更新的文档被视为陈旧：可被 retry，worker 启动时也能扫描清理
- [ ] 模拟 worker 中途崩溃后，通过陈旧状态机制文档可恢复，不会无限停留在 processing

## Answer

已实现并验证（commit 见下方）：ARQ + Redis worker、自动重试、retry 端点、陈旧状态恢复。

- compose 新增 redis；上传端点创建文档后入队（`enqueue_document_ingestion`），立即返回 uploaded，worker 异步处理
- `app/worker.py`：ARQ 任务 + `run_ingestion_with_retries`（瞬态失败最多 3 次尝试、递增退避；ParsingError 永久失败不重试）
- retry 端点 `POST /documents/{id}/retry`：failed 或超过 15 分钟的陈旧 processing 可重试（202），completed 返回 409，跨用户 404
- 重跑前按 document_id 清理残留向量，避免新旧向量混合
- 陈旧状态：processing + updated_at 超 15 分钟视为可重试（通过直接回拨 updated_at 的窄缝测试验证）
- 测试：8 个任务/重试用例 + 全套 50 passed；真实端到端冒烟（uvicorn + ARQ worker + Redis + Chroma + Postgres）：上传立即返回 uploaded → worker 自动处理到 completed
