# 07: EMBEDDING_PROVIDER 真正生效（Standards 3）

**What to build:** 用最简单 factory 让 provider 配置生效；后续多 Provider 需要时再扩展。

**Blocked by:** None

**Status:** resolved

- [ ] get_embedding_client() 按 EMBEDDING_PROVIDER 选择实现
- [ ] dependencies/worker 不再写死 DashScopeEmbeddingClient

## Answer

已修复：get_embedding_client() factory 按 EMBEDDING_PROVIDER 选择；dependencies 与 worker 接入。详见 report.md。
