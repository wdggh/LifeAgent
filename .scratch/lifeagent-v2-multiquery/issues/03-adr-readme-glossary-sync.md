# 03: ADR/README/词表同步与 V2.2 收口

**What to build:** 校验 ADR-0010（Query Expansion、original 一等公民、
加权 RRF 与预注册消融）；README 记录 V2.2 结果与对照基线；
CONTEXT.md 判断是否新增术语（预期不加，需记录理由）；resolve 本 feature
全部 ticket，并说明 V2.3（Dense+BM25 汇入同一 RRF）与 V2.4（reranker）的衔接。

**Blocked by:** 02

**Status:** ready-for-agent

- [ ] ADR-0010 与实现一致（权重/候选/截断/fallback 语义）
- [ ] README V2.2 段：A/B/B1/B2 结果、成功标准判定、answer-013/010 状态
- [ ] CONTEXT.md 决策记录（加或明确不加 + 理由）
- [ ] 全部 ticket resolved，frontier 清空

## Comments
