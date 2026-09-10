# 02: Live A/B 实验与 answer-level 重跑

**What to build:** 在 v2.0.2 基线上跑 A/B：A=改写关闭（应与基线一致）；
B=改写开启，产出受控实验报告。按预先固定标准判定：hard 子集 chunk
MRR/NDCG 提升 ≥0.03；easy 子集回退 ≤0.01；reg-001/002 gate 不回归；
`answer-010` 至少 source_correctness=1。随后重跑 12 条 answer 对话并对比
v2.0.2 的 11/9/11。结论如实记录（通过/未通过/部分通过）。

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] A 运行结果与 baseline-v2.0.2 一致（同 dataset/revision）
- [ ] B 运行产出 `reports/experiment-v2.1-query-rewrite.json`（raw 输出 gitignore）
- [ ] 成功标准 (i)–(iv) 逐条判定并记录，不改事后指标
- [ ] 12 条 answer transcripts 重跑；`answer-005/007/010` 状态对比
- [ ] 结论写入 README/报告（含未达标项）

## Comments
