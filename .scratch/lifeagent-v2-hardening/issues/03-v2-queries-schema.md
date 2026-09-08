# 03: V2 queries：50 条 + schema v2

**What to build:** v2 `queries.jsonl` 共 50 条：保留 v1 易题作回归锚点；新增
hard candidates ≥15（跨文档 4–6、同族 near-tie ≥2、语义改写/多条件补齐）。
每条含 `schema_version: 2`、`gold: [{"document","pages"}, ...]`（全 mandatory）、
类别词表新增 `cross_document`；hard candidate 带 `hard_candidate: true`、
`decoy_documents`、`difficulty_note`（命中 N1–N5 哪些规则）。`answer_elements`
仅被 gold 页覆盖（N5）。

**Blocked by:** 01（目录）、02（v2 语料 slug）

**Status:** resolved

- [ ] 50 条，分布符合 spec（含保留锚点与 hard candidate ≥15）
- [ ] gold 数组化 + schema_version=2；跨文档全 mandatory
- [ ] 新类别 cross_document 入 README 词表
- [ ] decoy_documents/difficulty_note 齐全且引用真实 slug
- [ ] N5 抽检：answer_elements 不被 decoy 覆盖

## Comments

## Answer

已实现并验证：

- `datasets/synthetic-personal-kb-v2/dataset/queries.jsonl`：50 条，schema v2
  （`schema_version: 2`、`gold` 数组化、`decoy_documents`/`difficulty_note`
  诊断字段）。
- 类别分布：simple_fact 8、semantic_rewrite 10、exact_term 6、numeric_date 6、
  clause 6、cross_paragraph 4、clause_specific 4（reg-001..reg-004）、
  cross_document 6。
- hard_candidate = 16（≥15）：语义改写/同族干扰 4、跨段 2、条款定位 4、
  跨文档 6；final `hard: true` 由 triage run（V2.0.1-06）按
  MRR@5<1.0 或 chunk NDCG@5<0.95 回写。
- 规则校验：gold 页全部落在 manifest 页界内；cross_document 全部 ≥2 个
  mandatory gold；非 reg hard 的 decoy_documents ≥2 且与 gold 无交集；
  reg-001/002 允许同文档近义条款 decoy（note 声明同文档 chunk 干扰）；
  每条 hard_candidate 均有 difficulty_note。
- 结构校验输出：categories 分布正确、total 50、hard_candidates 16、
  regs = reg-001..004。

验收清单满足。下一步 V2.0.1-04 V2 校验器（schema v2 + N/D 规则自动化）。
