# 03: ADR/README/词表同步与 V2.2 收口

**What to build:** 校验 ADR-0010（Query Expansion、original 一等公民、
加权 RRF 与预注册消融）；README 记录 V2.2 结果与对照基线；
CONTEXT.md 判断是否新增术语（预期不加，需记录理由）；resolve 本 feature
全部 ticket，并说明 V2.3（Dense+BM25 汇入同一 RRF）与 V2.4（reranker）的衔接。

**Blocked by:** 02

**Status:** resolved

- [ ] ADR-0010 与实现一致（权重/候选/截断/fallback 语义）
- [ ] README V2.2 段：A/B/B1/B2 结果、成功标准判定、answer-013/010 状态
- [ ] CONTEXT.md 决策记录（加或明确不加 + 理由）
- [ ] 全部 ticket resolved，frontier 清空

## Comments

## Answer

V2.2 正式收口：

- answer review 定稿：`reviews/answer_review_v2.2.json`（READY，13 条，
  11/13 source、10/13 completeness、11/13 no_hallucination；answer-013 0/0/0；
  answer-010 继续作为歧义/多轮用例单独跟踪）。
- ADR-0010 增加 2026-09-11 更新段：A==baseline；B hard-10 MRR +0.0300
  （边界通过）但归因显示 7/10 `no_new_recall`、2 `original_sufficient`、
  1 `rank_only_gain`，收益来自单个 case 重排，expansion 未提供新召回；
  Query Expansion 代码保留、默认关闭；V2.2b 暂不做。
- README V2.2 段补上"指标结果 → failure attribution → 瓶颈 → 选型"叙事：
  明确说明为什么下一步是 BM25/Sparse（词面型召回瓶颈），而不是继续调
  rewrite prompt；ACTIVE baseline 仍为 `baseline-v2.0.2.json`。
- CONTEXT.md 无需新增术语：query expansion / hybrid retrieval 属实现概念，
  不是产品领域词；该结论记录在 ADR/README。
- 受控产物：`experiment-v2.2-A-baseline.json`、
  `experiment-v2.2-query-expansion.json`、`experiment-v2.2-analysis.md`；
  raw 输出 gitignore。

V2.2 feature 全部 ticket resolved。下一步 V2.3（Dense + Sparse/BM25 + RRF,
ADR-0011）。
