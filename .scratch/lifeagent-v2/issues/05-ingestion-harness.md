# 05: 真实摄取与隔离评测 harness

**What to build:** live 摄取 harness：专用 eval user（DB 行）+ 独立 Chroma collection
（名称后缀 `_eval`），直接调用真实 `KnowledgeService` 摄取链路
（parse→chunk→embed→index，不经 Redis/ARQ/FastAPI），维护 slug → document_id
映射，支持可重复运行与清理/重置。依赖：PostgreSQL + Chroma + DashScope embedding。

**Blocked by:** 01（语料与 manifest）

**Status:** resolved

- [ ] eval user 创建与复用（同 collection 跑多轮不互相污染）
- [ ] Chroma collection 隔离配置（`_eval` 后缀，跑前可重置）
- [ ] 摄取走真实 KnowledgeService/Indexer；返回 slug→document_id 映射
- [ ] 摄取结果与 manifest 对齐：每文档页数/chunk 数可校验
- [ ] 不启动 Redis / ARQ worker / FastAPI
- [ ] 重复运行幂等（已有向量清理或整 collection 重置策略）

## Comments

## Answer

已实现并验证（代码完成；真实栈 live 冒烟随 V2.0-09 baseline 执行）：

- `tests/evaluation/runners/ingest_corpus.py`：
  - `CorpusIngestionHarness`：eval_user 复用/注册、upload →
    KnowledgeService.ingest（真实 parse→chunk→embed→index 代码路径，不经
    Redis/ARQ/FastAPI）、slug→document_id 映射、摄取后 page coverage 校验
    （覆盖页集合 == manifest pages）、文档级幂等清理；
  - `live_harness`：只依赖 PostgreSQL + Chroma + 配置的 embedding provider；
    Chroma collection 隔离为 `<base>_eval`，`--reset` 重建 collection 并清理
    eval 用户文档（行+文件+向量）；
  - CLI：`python -m tests.evaluation.runners.ingest_corpus [--reset]`。
- `tests/evaluation/runners/test_ingest_corpus.py`：7 个 fast 用例全绿
  （collection 命名、eval user 注册后复用、slug 映射与 coverage 校验、coverage
  不一致明确失败、摄取未 completed 明确失败、重置删除全部文档、fixture 文件齐全）。
- 与 V2.0-03 seam 衔接：coverage 校验直接使用
  `VectorRepository.fetch_document_chunks`。

验收清单满足；"真实栈 live 摄取成功 + 幂等重跑"在 V2.0-09 用同一 harness 验证。
下一步 V2.0-06 Retrieval evaluation runner（fast/live）。
