# 03: ADR/README/词表同步与收口

**What to build:** 校验并落地 ADR-0009（实现与原决策不一致时更新）；README
记录 V2.1 实验结论与对照基线；明确 CONTEXT.md 是否新增术语（预期不加，
需记录理由）；resolve 本 feature 全部 ticket。

**Blocked by:** 02

**Status:** resolved

- [ ] ADR-0009 与实现一致（必要时补充 consequences）
- [ ] README V2.1 段：基线、A/B 结果、成功标准判定、失败样本状态
- [ ] CONTEXT.md 决策记录（加术语或明确不加 + 理由）
- [ ] 全部 ticket resolved，frontier 清空

## Comments

## Answer

V2.1 文档/实验/失败结论已全部沉淀：

- ADR-0009 增加 2026-09-11 更新段：A/B 未通过（hard MRR −0.020、NDCG
  −0.0383、answer-010 不变），缺陷为丢判别词与日期误注入、改写不稳定；
  单查询改写默认关闭，默认检索路径保持 v2.0.2 baseline。
- `query_rewrite_enabled` 默认改为 **false**（config + .env.example），
  V2.1 保留为实验开关。
- README V2.1 段增加 Closure：CLOSED/FAIL、不做 V2.1b、默认关闭、
  answer-005 为单次运行观察不作因果证据、answer-010 改判为歧义/多轮用例。
- 正式 review：`reviews/answer_review_v2.1.json`（READY，11/10/11，
  reviewer=user 2026-09-11，含 causality_note）。
- CONTEXT.md 无需新增术语：query rewrite/expansion 属实现概念而非产品领域词，
  本结论记录在此处与 ADR/README。
- 受控实验报告：`reports/experiment-v2.1-A-tool-baseline.json` 与
  `reports/experiment-v2.1-query-rewrite.json`；raw 输出 gitignore。

V2.1 feature 全部 ticket resolved。下一步进入 V2.2 Query Expansion /
Multi-Query Retrieval（ADR-0010）。
