# 05: 真实摄取与隔离评测 harness

**What to build:** live 摄取 harness：专用 eval user（DB 行）+ 独立 Chroma collection
（名称后缀 `_eval`），直接调用真实 `KnowledgeService` 摄取链路
（parse→chunk→embed→index，不经 Redis/ARQ/FastAPI），维护 slug → document_id
映射，支持可重复运行与清理/重置。依赖：PostgreSQL + Chroma + DashScope embedding。

**Blocked by:** 01（语料与 manifest）

**Status:** open

- [ ] eval user 创建与复用（同 collection 跑多轮不互相污染）
- [ ] Chroma collection 隔离配置（`_eval` 后缀，跑前可重置）
- [ ] 摄取走真实 KnowledgeService/Indexer；返回 slug→document_id 映射
- [ ] 摄取结果与 manifest 对齐：每文档页数/chunk 数可校验
- [ ] 不启动 Redis / ARQ worker / FastAPI
- [ ] 重复运行幂等（已有向量清理或整 collection 重置策略）

## Comments
