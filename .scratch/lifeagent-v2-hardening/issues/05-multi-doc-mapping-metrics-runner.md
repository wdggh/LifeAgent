# 05: Multi-doc gold 的 mapping/metrics/runner 泛化

**What to build:** 把 03 mapping 与 04 metrics 从单 gold 文档泛化为
`gold: [{document, pages}]` 数组（全 mandatory）：逐文档导出 G、union 为
G_chunks；document-level recall = 命中 gold docs / gold docs 总数，MRR = 首个
相关 result，page/chunk 沿用现有公式；runner 接受 dataset root 参数并输出
per-case（含 hard_candidate 标记与 triage 所需 MRR/NDCG）。现有 10 个 mapping
单测与 metrics 单测升级/补充多文档用例。

**Blocked by:** 01（目录）、03（schema v2）

**Status:** open

- [ ] mapping 输入泛化：逐文档 mapping + union + 单测
- [ ] metrics 泛化：gold docs 集合、doc recall 分母、多文档单测
- [ ] runner 支持 dataset root 参数与 per-case raw 输出
- [ ] fast 全绿；v1 schema 兼容性不需要保留（v1 冻结）

## Comments
