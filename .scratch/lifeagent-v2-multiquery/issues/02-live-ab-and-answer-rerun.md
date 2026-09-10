# 02: Live A/B（双路最小版）与 13 条 answer 重跑

**What to build:** 在 v2.0.2 基线上跑两次实验：A=扩展关闭（应与基线一致）；
B=原查询 + 1 条改写、等权 RRF + original 同分优先。按预先固定标准判定：hard-10
chunk MRR/NDCG 提升 ≥0.03；easy-40 回退 ≤0.01；reg-001/002 gate 不回归；
answer-013（自行车单轮用例）source_correctness=1。`answer-010` 作为歧义/多轮
用例单独跟踪，不作为通过标准。13 条 answer 对话重跑并对比既有 review。
多变体与权重消融（1.0 vs 1.5）明确留到 V2.2b/V2.3，不在本实验内。

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] A 与 baseline-v2.0.2 逐项一致（工具路径、扩展关闭）
- [ ] B 产出 `experiment-v2.2-query-expansion.json`（raw gitignore）
- [ ] 成功标准 (i)–(iv) 逐条判定；融合规则为预注册的等权 RRF + original 同分优先，不事后调参
- [ ] 13 条 answer transcripts 重跑；answer-013 与 answer-010 分别记录
- [ ] 结论（通过/未通过/部分通过 + 未达标项）写入 README/报告

## Comments
