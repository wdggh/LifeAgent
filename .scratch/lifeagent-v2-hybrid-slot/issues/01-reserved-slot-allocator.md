# 01: 预留 sparse 槽位分配器 + Tool 接入 + 测试

**What to build:** 新增融合模式 `reserved_slot`：最终输出 L 个槽位时，前
L−1 个按 dense 顺序保留，最后 1 个槽位留给"dense 未覆盖的最高排名 sparse
chunk"；若没有这样的 chunk（或 sparse 不可用），退化为 dense-priority 填充。
dense/BM25/分词/候选宽度均不变；trace 记录 slot_policy / reserved_slot_chunk_id /
reserved_slot_sparse_rank / dense_slot_count / sparse_slot_count；关闭配置时
与 v2.0.2 基线一致。

**Blocked by:** None

**Status:** claimed

- [ ] 纯函数分配器：dense 顺序保留、预留槽取最高排名 sparse-only chunk、去重、L=4/10 均正确
- [ ] 无 sparse-only chunk 时退化为 dense-priority 填充并记录原因
- [ ] 配置 `query_sparse_reserved_slots=1`（默认 1）与 `fusion_mode=reserved_slot`
- [ ] Tool 使用分配器并写入 trace 字段；`retrieval_count`/预算/签名不变
- [ ] 单测：dense 顺序保持、预留槽命中 sparse-only、重复跳过、退化路径、禁用等价基线

## Comments
