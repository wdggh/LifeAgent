# 03: 实验运行、对比报告与 answer-level 重跑

**What to build:** 在 v2.0.2 基线上跑 A/B：A=`QUERY_REWRITE_ENABLED=false`
（应与 baseline-v2.0.2 一致）；B=true → `experiment-v2.1-query-rewrite.json`；
对比整体/hard/easy 的 chunk MRR/NDCG/Recall、reg gate；重跑 12 条 answer
transcripts 并对比 answer-007/010；按预先固定的成功标准给出结论
（通过/未通过/部分通过），不得事后更换指标。

**Blocked by:** 02

**Status:** open

- [ ] A/B 两次 live 运行，报告结构一致、可 diff
- [ ] 成功标准 (i)–(iv) 逐条判定并记录
- [ ] 12 条 answer 重跑；answer-010 是否至少 source=1 有结论
- [ ] 结论写入报告/README，失败也如实保留

## Comments
