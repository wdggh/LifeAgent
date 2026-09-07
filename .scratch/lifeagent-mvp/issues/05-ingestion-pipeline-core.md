# 05: 摄取管线核心：解析 → 切分 → Embedding → 索引

**What to build:** 上传后的 Document 能自动经过 parsing → chunking → embedding → indexing 变为 completed；PDF 按页解析并保留页区间；Chunk 带完整来源 metadata 写入向量库；扫描件/空文本等无法解析的文件进入 failed 并给出可读原因。

**Blocked by:** 04（文档上传与管理）

**Status:** resolved

- [ ] Document 状态从 processing 依次推进并在成功时变为 completed（通过文档详情可见）
- [ ] PDF 按页解析；切分后的 Chunk 携带 start_page/end_page/chunk_index
- [ ] 每条向量 metadata 含 user_id、document_id、document_name、document_type、页区间、chunk_index、embedding_model
- [ ] Embedding 只通过 Provider 抽象调用；测试用 Fake，真实配置走环境变量
- [ ] 向量库 collection 命名与 embedding_model 记录一致（含模型与维度）
- [ ] 无文本/疑似扫描件 PDF 进入 failed，错误信息说明暂不支持 OCR；损坏或无法解析的文件同样 failed 且错误可读
- [ ] 解析/切分/嵌入逻辑在测试里可独立验证，且不触碰真实外部 API

## Answer

已实现并验证（commit 见下方）：摄取管线核心 + Chroma 独立服务接入。

- Parser：自研按页解析（PDF 用 pypdf 逐页提取；TXT/MD 单页读取）；空文本/损坏 PDF → ParsingError（"疑似扫描件/无文本"或"解析失败"可读信息）
- Chunker：langchain-text-splitters `RecursiveCharacterTextSplitter`（1000/200），chunk 带 start_page/end_page/chunk_index，页内切分不跨页
- Embedding：Provider 抽象（EmbeddingClient）+ DashScope OpenAI 兼容实现（真实调用需 DASHSCOPE_API_KEY，测试用 Fake）
- Indexer/VectorRepository：Chroma 独立服务（docker compose 新服务，HTTP 8000）；metadata 含 user_id/document_id/document_name/document_type/start_page/end_page/chunk_index/embedding_model（text-embedding-v3:1024）
- KnowledgeService.ingest：parsing→chunking→embedding→indexing→completed 状态推进，失败置 failed+error_message；uploaded 状态的自动触发/入队由 ticket 06（ARQ worker）接入
- 测试：4 个摄取用例（完成+向量 metadata 校验、空文档失败、损坏 PDF 失败、chunker 页区间）+ 全套 42 passed；真实 Chroma 写入验证通过
