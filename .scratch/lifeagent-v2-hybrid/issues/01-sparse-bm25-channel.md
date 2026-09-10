# 01: Sparse/BM25 通道 + 索引生命周期 + 双通道 RRF 端到端

**What to build:** 开启配置后，`search_knowledge` 在 dense 通道旁并联一个
BM25 稀疏通道（rank_bm25 + jieba，按用户建索引、懒加载缓存、语料版本变化即
重建），两路各取候选后用等权 RRF（k=60，dense 优先 tie-break）融合去重并
按预算截断；稀疏通道不可用时 fail-open 回退 dense-only 并记录原因。完成即可
验证：用假 dense/稀疏源可以看到两路查询、融合顺序、按文档过滤与用户隔离，
关闭配置时与 v2.0.2 基线完全一致。Query Expansion 保持关闭。

**Blocked by:** None（V2.2 已收口）

**Status:** resolved

- [ ] jieba 分词 + 数字/编号原样保留；rank_bm25 排序；k1=1.5、b=0.75
- [ ] 按用户建索引（来源于该用户已存 chunk：document_id/document_type/pages/content），支持 document_type/document_id 过滤与用户隔离
- [ ] 懒加载缓存 + 语料版本失效（Redis `kb:{user_id}:corpus_version`；worker 摄取完成、API 删除时递增；Redis 不可用退化为 TTL）
- [ ] 并行 dense/sparse 检索（各 8 候选）→ 去重 → 等权 RRF（k=60，dense 优先 tie-break）→ 截断（评测 10 / Agent ≤4）
- [ ] 稀疏索引失败/超时 → dense-only，trace 记录 sparse_fallback(_reason)
- [ ] trace：dense_hit_ids / sparse_hit_ids / per_channel_hits / sparse_index_version / sparse_index_rebuild_ms / fusion_candidates / fusion_top / rrf_k
- [ ] 配置项（enabled/candidate_k/k1/b/rrf_k/version_ttl）+ .env.example；rank_bm25、jieba 进入 requirements.txt；默认 disabled
- [ ] 单测：中文分词与词面匹配、编号/数字保留、用户隔离、文档过滤、缓存版本失效、fail-open、RRF dense 优先 tie-break、禁用等价基线

## Comments

## Answer

已实现并验证：

- `app/rag/retrieval/sparse.py`：
  - `tokenize`：jieba 分词 + 编号（`PO-2025-0099` 等）原样保留 + 数字保留；
  - `BM25Index`：BM25Okapi（k1=1.5、b=0.75），支持 document_type/document_id
    过滤；小语料 IDF 退化为 0 时使用确定性词面重叠回退，保证仍按词面排序；
  - `BM25SparseSearcher`：按用户懒加载索引（来源 = 该用户已存 chunk），
    缓存命中/重建耗时上报；版本变化（Redis `kb:{user_id}:corpus_version`）
    即重建，版本不可用时按 TTL 重建；索引异常抛 SparseIndexError 由 Tool
    fail-open；
  - `RedisCorpusVersionStore`：best-effort current/bump（Redis 不可用返回 None/不影响主流程）。
- `search_knowledge`：sparse 开启时并行 dense/sparse（各 8 候选）→ 去重 →
    等权 RRF（k=60，dense 优先 tie-break）→ 截断到工具预算；sparse 失败
    回退 dense-only；trace 记录 dense_hit_ids / sparse_hit_ids /
    per_channel_hits / sparse_index_version / sparse_index_rebuild_ms /
    sparse_fallback(_reason) / fusion_candidates / fusion_top / rrf_k。
- 生命周期：worker 摄取成功后递增语料版本；`DocumentService.delete_document`
    成功后递增；均为 best-effort，不影响主流程。
- 配置：`QUERY_SPARSE_ENABLED=false`（实验通过前默认关闭）、candidate_k=8、
    k1=1.5、b=0.75、rrf_k=60、version_ttl=60；`.env.example` 同步；
    `rank_bm25`、`jieba` 进入 requirements.txt（生产依赖）。
- runner（`--via-tool`）在 sparse 开启时注入 BM25SparseSearcher，供
    V2.3-02 的 A/B 使用。
- 测试：`tests/test_hybrid_retrieval.py` 8 个用例全绿（分词/编号保留、
    BM25 词面排序与过滤、用户隔离与缓存命中、版本变化重建、TTL 回退、
    双通道融合、sparse 失败 fail-open、禁用等价基线）；evaluation 49 与
    全量 pytest 均通过。

验收清单满足。下一步 V2.3-02 Live A/B（dense-only vs dense+sparse）与
13 条 answer 重跑。
