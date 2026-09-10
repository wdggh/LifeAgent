# 02: Live A/B 实验与 answer-level 重跑

**What to build:** 在 v2.0.2 基线上跑 A/B：A=改写关闭（应与基线一致）；
B=改写开启，产出受控实验报告。按预先固定标准判定：hard 子集 chunk
MRR/NDCG 提升 ≥0.03；easy 子集回退 ≤0.01；reg-001/002 gate 不回归；
`answer-010` 至少 source_correctness=1。随后重跑 12 条 answer 对话并对比
v2.0.2 的 11/9/11。结论如实记录（通过/未通过/部分通过）。

**Blocked by:** 01

**Status:** resolved

- [ ] A 运行结果与 baseline-v2.0.2 一致（同 dataset/revision）
- [ ] B 运行产出 `reports/experiment-v2.1-query-rewrite.json`（raw 输出 gitignore）
- [ ] 成功标准 (i)–(iv) 逐条判定并记录，不改事后指标
- [ ] 12 条 answer transcripts 重跑；`answer-005/007/010` 状态对比
- [ ] 结论写入 README/报告（含未达标项）

## Comments

## Answer

实验已完成，结论 **未通过预先固定的成功标准**（如实记录）：

- A 组（工具路径 + 改写关闭，`--via-tool`）与 baseline-v2.0.2 指标逐项完全一致
  → 工具路径是有效测量口径。
- B 组（改写开启，43/50 改写、7 条编号跳过、平均 948ms）：
  - hard-10：chunk MRR 0.5867→0.5667，NDCG 0.4974→0.4591（退化）；
  - easy-40：MRR -0.0075 / NDCG -0.0056（在 ≤0.01 阈值内）；
  - overall：MRR 0.8373→0.8273，NDCG 0.8061→0.7940，Recall@5 0.85→0.85；
  - reg-001/002 gate PASS；reg-004 仍 Recall=0（gap -0.1039→-0.0795）。
- 成功标准判定：(i) FAIL（hard 排序退化）；(ii) PASS；(iii) PASS；
  (iv) FAIL（answer-010 仍 0/0/0）。
- 归因（raw per-case）：改写丢弃判别性词（cd-006、v2-040），并对不含相对日期的
  问题注入当前日期（v2-014）；改写结果在两次运行间不稳定。
- 正向副作用：answer-005 completeness 0→1（新草案 11/10/11，待用户确认）。
- 产物：`reports/experiment-v2.1-A-tool-baseline.json`、
  `reports/experiment-v2.1-query-rewrite.json`（controlled），raw 输出
  gitignore；README 增加实验段。

后续二选一（待用户决策）：V2.1b 定向修 prompt（仅显式相对日期解析、
要求保留原判别词、降低随机性）重跑；或直接进入 V2.2 original+rewritten
multi-query。
