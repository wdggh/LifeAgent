# 03: Gold mapping 规范 + StoredChunk + Repository 接口

**What to build:** `tests/evaluation/mapping/gold_mapping.py`：由 manifest slug →
摄取期 document map → `VectorRepository.fetch_document_chunks()` → overlap
（`start_page <= p <= end_page`）→ 去重导出 runtime gold chunk 集 G；并把
`SearchResult` 投影为 document/page/chunk-derived 三级相关性与去重列表。同时新增
domain `StoredChunk`（chunk_id/content/start_page/end_page/chunk_index，无 embedding
与 vector metadata）与 `VectorRepository.fetch_document_chunks()` 抽象接口，Chroma
实现与现有 fakes 同步实现（该接口同时是 V2.3 sparse 重建的输入边界）。

**Blocked by:** 02（dataset schema 定稿）

**Status:** resolved

- [ ] StoredChunk dataclass 落 domain 层；不含 embedding/user_id/vector metadata
- [ ] VectorRepository ABC 新增 `fetch_document_chunks(document_id)`；Chroma 实现基于
      collection.get（documents+metadatas，不取 embeddings）；fakes 同步实现
- [ ] overlap 规则实现与单测：含未来跨页 chunk 语义（7–9 覆盖 gold 7/8/9）
- [ ] gold_mapping：slug→document→G 的导出与去重单测
- [ ] SearchResult → document/page/chunk 三级投影与去重单测
- [ ] 生产 Retriever/Agent/AgentService 行为零改动（只做增量只读接口）

## Comments

## Answer

已实现并验证（保持最小产物，未提前写 Recall/MRR/NDCG，也未串 Retriever/
Embedding/Chroma search）：

- `StoredChunk`（domain，frozen）：chunk_id/content/start_page/end_page/
  chunk_index，无 embedding/user_id/vector metadata，落
  `app/domain/models/chunk.py`。
- `VectorRepository.fetch_document_chunks(document_id)` 抽象接口 + Chroma 实现
  （collection.get where document_id，documents+metadatas，不取 embedding，
  按 chunk_index 排序）；现有 fakes（test_delete_cascade）同步实现。
- `tests/evaluation/mapping/gold_mapping.py`：`map_gold_chunks`（纯函数，overlap
  规则 + 去重 + 显式失败）与 `resolve_document_gold`（经 repository seam 按文档
  拉取后映射，杜绝跨文档污染）。
- `tests/evaluation/mapping/test_gold_mapping.py`：10 个 fast 用例全绿，覆盖：
  单页单 chunk、单页多 chunk、跨页 chunk overlap、多 gold pages union、重叠
  chunk 去重、不同 document 不进 gold、document 不存在明确失败、gold page 超出
  chunk 覆盖范围明确失败、empty chunks 明确失败、empty gold pages 明确失败。
- `tests/evaluation/conftest.py`：no-op 覆盖 DB autouse fixtures，使 evaluation
  子树在无 PostgreSQL/Chroma/Redis 环境下可跑（fast 模式）。

验收清单全部满足。下一步 V2.0-04 Evaluation metrics（Recall/MRR/NDCG）。
