# 03: Gold mapping 规范 + StoredChunk + Repository 接口

**What to build:** `tests/evaluation/mapping/gold_mapping.py`：由 manifest slug →
摄取期 document map → `VectorRepository.fetch_document_chunks()` → overlap
（`start_page <= p <= end_page`）→ 去重导出 runtime gold chunk 集 G；并把
`SearchResult` 投影为 document/page/chunk-derived 三级相关性与去重列表。同时新增
domain `StoredChunk`（chunk_id/content/start_page/end_page/chunk_index，无 embedding
与 vector metadata）与 `VectorRepository.fetch_document_chunks()` 抽象接口，Chroma
实现与现有 fakes 同步实现（该接口同时是 V2.3 sparse 重建的输入边界）。

**Blocked by:** 02（dataset schema 定稿）

**Status:** open

- [ ] StoredChunk dataclass 落 domain 层；不含 embedding/user_id/vector metadata
- [ ] VectorRepository ABC 新增 `fetch_document_chunks(document_id)`；Chroma 实现基于
      collection.get（documents+metadatas，不取 embeddings）；fakes 同步实现
- [ ] overlap 规则实现与单测：含未来跨页 chunk 语义（7–9 覆盖 gold 7/8/9）
- [ ] gold_mapping：slug→document→G 的导出与去重单测
- [ ] SearchResult → document/page/chunk 三级投影与去重单测
- [ ] 生产 Retriever/Agent/AgentService 行为零改动（只做增量只读接口）

## Comments
