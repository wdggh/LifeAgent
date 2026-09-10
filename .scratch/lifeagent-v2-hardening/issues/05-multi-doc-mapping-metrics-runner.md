# 05: Multi-doc gold 的 mapping/metrics/runner 泛化

**What to build:** 把 03 mapping 与 04 metrics 从单 gold 文档泛化为
`gold: [{document, pages}]` 数组（全 mandatory）：逐文档导出 G、union 为
G_chunks；document-level recall = 命中 gold docs / gold docs 总数，MRR = 首个
相关 result，page/chunk 沿用现有公式；runner 接受 dataset root 参数并输出
per-case（含 hard_candidate 标记与 triage 所需 MRR/NDCG）。现有 10 个 mapping
单测与 metrics 单测升级/补充多文档用例。

**Blocked by:** 01（目录）、03（schema v2）

**Status:** resolved

- [ ] mapping 输入泛化：逐文档 mapping + union + 单测
- [ ] metrics 泛化：gold docs 集合、doc recall 分母、多文档单测
- [ ] runner 支持 dataset root 参数与 per-case raw 输出
- [ ] fast 全绿；v1 schema 兼容性不需要保留（v1 冻结）

## Comments

## Answer

已实现并验证：

- mapping 泛化：新增 `resolve_gold_chunks(chunk_source, slug_id_map,
  gold_entries)`（逐文档映射，任一 leg 无 chunk 即显式失败）与
  `union_gold_chunks`（G_chunks = 各文档 union）；单文档 API 保留。
- metrics 泛化：`compute_query_metrics(results, gold_documents: {doc_id: pages},
  gold_chunk_ids)`；document-level Recall 分母 = gold 文档数、MRR = 第一个
  命中任一 gold doc 的结果；page-level 按 (doc,page) 逐文档覆盖；chunk-level
  沿用 union 语义；公式与 K 不变。
- runner：`evaluate_query` 改为 schema v2 数组 gold；`run_live_evaluation`
  返回 (report, outcomes)；新增 `write_raw_outcomes`，live CLI 输出
  `reports/triage-v2.raw.json`（gitignored）；fast 子命令按 dataset 选择
  v1/v2 校验器。
- 测试：mapping 新增多文档 union 与"某 leg 缺失显式失败"2 例；metrics 新增
  多文档部分召回（doc recall 0.5 / chunk 0.5 / MRR 0.5）与双文档满分 2 例，
  既有单文档用例全部迁到新签名；runner 回归用例升级 schema v2。
- 验证：tests/evaluation **47 passed**；`retrieval_eval fast`（默认 v2）输出
  "v2 ok ... / corpus ok ... / fast checks ok"。

验收清单满足。下一步 V2.0.1-06 Triage run + baseline-v2.0.1。
