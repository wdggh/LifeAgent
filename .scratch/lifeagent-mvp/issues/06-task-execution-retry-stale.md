# 06: 任务执行与失败语义：worker、重试、陈旧状态

**What to build:** 摄取由独立 worker 异步执行；失败自动重试两次后变为 failed 且原因可读；用户可对失败文档发起 retry；worker 崩溃不会让文档永远卡在 processing。

**Blocked by:** 05（摄取管线核心）

**Status:** ready-for-agent

- [ ] 上传后处理在 worker 中异步完成，API 请求不阻塞且先返回
- [ ] 任务瞬态失败自动重试（最多 2 次、带退避），耗尽后 Document 变为 failed 并记录错误
- [ ] 对 failed 文档调用 retry 会重新入队，重跑前清理该文档此前残留的向量
- [ ] 成功 retry 后文档最终 completed
- [ ] processing 且超过 15 分钟未更新的文档被视为陈旧：可被 retry，worker 启动时也能扫描清理
- [ ] 模拟 worker 中途崩溃后，通过陈旧状态机制文档可恢复，不会无限停留在 processing
