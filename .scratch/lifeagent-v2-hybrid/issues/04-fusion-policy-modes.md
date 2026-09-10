# 04: 三种融合模式（等权 RRF / dense-priority supplement / 加权 RRF 2:1）

**What to build:** 在同一 dense/BM25/候选数下，把融合策略做成配置可选：
`equal_rrf`（现控制组）、`dense_priority`（dense 先占位，sparse 只补 dense
未覆盖的 chunk，永不重排 dense）、`weighted_rrf`（dense weight 2.0、sparse
1.0，k=60，dense 优先 tie-break）。trace 记录 fusion_mode；默认仍为
`equal_rrf` 且 `QUERY_SPARSE_ENABLED=false`（实验前不改变生产行为）。

**Blocked by:** None（V2.3-01/02 已完成）

**Status:** resolved

- [ ] `dense_priority_supplement` 纯函数：保持 dense 顺序、按 chunk 去重、sparse 只填空槽、limit 截断
- [ ] 加权 RRF 复用现有 RRF（weights=[2.0, 1.0]，dense 优先 tie-break）
- [ ] 配置 `query_sparse_fusion_mode`（equal_rrf|dense_priority|weighted_rrf）+ `query_sparse_rrf_weight_dense=2.0`；.env.example
- [ ] Tool 按模式选择融合；trace 增加 `fusion_mode`
- [ ] 单测：dense-priority 不重排 dense、只补空隙、去重、截断；加权 RRF 反例（dense rank1 正确 vs sparse rank1 错误 → dense 胜出）；三种模式 metadata

## Comments

## Answer

已实现并验证：

- `app/rag/retrieval/fusion.py` 新增 `dense_priority_supplement`：dense 顺序
  原样保留，sparse 只补 dense 未覆盖的 chunk，按 chunk_id 去重后截断；
- 加权 RRF 复用现有 `reciprocal_rank_fusion`（weights=[2.0, 1.0]，k=60，
  dense 优先 tie-break）；
- 配置：`query_sparse_fusion_mode`（equal_rrf|dense_priority|weighted_rrf，
  默认 equal_rrf）与 `query_sparse_rrf_weight_dense=2.0`（.env.example 同步）；
- `search_knowledge` 按模式选择融合，trace 增加 `fusion_mode`；默认
  `QUERY_SPARSE_ENABLED=false` 不变，实验前不影响生产行为；
- 测试：`tests/test_hybrid_retrieval.py` 11 个用例全绿，新增
  dense-priority 不重排 dense / 只补空隙 / 去重 / 截断，加权 RRF 反例
  （dense rank1 正确 vs sparse rank1 错误 → dense 胜出），以及两种模式的
  Tool metadata 断言；tests/evaluation 49/49 保持通过。

验收清单满足。下一步 05：三臂 live 消融（equal_rrf / dense_priority /
weighted_rrf 2:1）与 13 条 answer 重跑。
