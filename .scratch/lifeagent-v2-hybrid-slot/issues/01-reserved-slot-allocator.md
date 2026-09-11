# 01: 预留 sparse 槽位分配器 + Tool 接入 + 测试

**What to build:** 新增融合模式 `reserved_slot`：最终输出 L 个槽位时，前
L−1 个按 dense 顺序保留，最后 1 个槽位留给"dense 未覆盖的最高排名 sparse
chunk"；若没有这样的 chunk（或 sparse 不可用），退化为 dense-priority 填充。
dense/BM25/分词/候选宽度均不变；trace 记录 slot_policy / reserved_slot_chunk_id /
reserved_slot_sparse_rank / dense_slot_count / sparse_slot_count；关闭配置时
与 v2.0.2 基线一致。

**Blocked by:** None

**Status:** resolved

- [ ] 纯函数分配器：dense 顺序保留、预留槽取最高排名 sparse-only chunk、去重、L=4/10 均正确
- [ ] 无 sparse-only chunk 时退化为 dense-priority 填充并记录原因
- [ ] 配置 `query_sparse_reserved_slots=1`（默认 1）与 `fusion_mode=reserved_slot`
- [ ] Tool 使用分配器并写入 trace 字段；`retrieval_count`/预算/签名不变
- [ ] 单测：dense 顺序保持、预留槽命中 sparse-only、重复跳过、退化路径、禁用等价基线

## Comments

## Answer

已实现并通过 01→02 gate review：

- 口径按 review 锁定：`sparse-only = chunk_id ∉ 全部 dense 候选`（不是
  ∉ dense_selected）；spec/ADR 同时写明 reserved slot 只改变最终消费集合、
  不改变候选排序与融合分数；(i) 判定为 MRR +0.03 或 NDCG +0.03。
- `app/rag/retrieval/fusion.py` 新增纯函数 `reserved_slot_allocation`：
  dense 顺序保留、预留槽取最高 sparse rank 的真 sparse-only chunk、去重、
  无真 sparse-only 时退化为 dense-priority 填充并记录原因。
- Tool 新增 `reserved_slot` 模式与 trace 字段：slot_policy /
  reserved_slot_chunk_id / reserved_slot_sparse_rank / dense_slot_count /
  sparse_slot_count / reserved_slot_fallback_reason；配置
  `query_sparse_reserved_slots=1`（默认 sparse 关闭，生产行为不变）。
- 测试：tests/test_hybrid_retrieval.py **15/15**（新增：忽略未入选的 dense
  候选、无真 sparse-only 退化、L=10 去重截断、Tool metadata）；evaluation
  49/49。
- 真实 trace 样例（answer-013 问题）：L=4 时 dense top3 + reserved
  purchase p3（sparse rank 3），L=10 时 dense top8 + p3 保留槽；
  dense 第 4 名被正确排除在 sparse-only 之外。

验收清单满足。下一步 02：live A/B（dense-only vs reserved_slot）与 13 条
answer 重跑。
