# 03: V2 queries：50 条 + schema v2

**What to build:** v2 `queries.jsonl` 共 50 条：保留 v1 易题作回归锚点；新增
hard candidates ≥15（跨文档 4–6、同族 near-tie ≥2、语义改写/多条件补齐）。
每条含 `schema_version: 2`、`gold: [{"document","pages"}, ...]`（全 mandatory）、
类别词表新增 `cross_document`；hard candidate 带 `hard_candidate: true`、
`decoy_documents`、`difficulty_note`（命中 N1–N5 哪些规则）。`answer_elements`
仅被 gold 页覆盖（N5）。

**Blocked by:** 01（目录）、02（v2 语料 slug）

**Status:** open

- [ ] 50 条，分布符合 spec（含保留锚点与 hard candidate ≥15）
- [ ] gold 数组化 + schema_version=2；跨文档全 mandatory
- [ ] 新类别 cross_document 入 README 词表
- [ ] decoy_documents/difficulty_note 齐全且引用真实 slug
- [ ] N5 抽检：answer_elements 不被 decoy 覆盖

## Comments
