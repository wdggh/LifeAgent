# 02: 上传入队失败不留 uploaded 僵尸（Spec 5）

**What to build:** 文档行创建后入队失败时回滚（删文件+删记录）并返回 503；绝不留下永远无人处理的 uploaded 文档。

**Blocked by:** None

**Status:** resolved

- [ ] dispatcher 抛异常时清理刚创建的文档记录与文件
- [ ] 上传返回 503 SERVICE_UNAVAILABLE（或等价统一错误）
- [ ] 清理后列表不含该文档、uploads 目录无残留文件
- [ ] 正常入队路径行为不变

## Answer

已修复：上传路由在入队失败时回滚（删记录+删文件）并返回 503 SERVICE_UNAVAILABLE，不再留下 uploaded 僵尸。详见 report.md。
