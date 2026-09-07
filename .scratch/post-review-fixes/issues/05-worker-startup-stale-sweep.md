# 05: worker 启动扫描陈旧 processing（Spec 4）

**What to build:** worker 启动时扫描超过 15 分钟的 processing 文档并重新入队，崩溃恢复不再依赖人工。

**Blocked by:** None

**Status:** resolved

- [ ] DocumentRepository 提供按 updated_at 查陈旧 processing 的方法
- [ ] worker on_startup 执行扫描并重新入队
- [ ] 陈旧(>15min)文档被入队、新鲜(<15min)的不被入队

## Answer

已修复：DocumentRepository.list_stale_processing + worker on_startup 扫描重新入队；run_worker 同步接入。详见 report.md。
