# 02: 重跑 triage，发布 baseline-v2.0.2（ACTIVE）

**What to build:** 用冻结的 V2.0 dense retriever 在修订后的 v2 corpus 上重跑
live triage（--mark-hard），产出 `baseline-v2.0.2.json` 与
`triage-v2.0.2.raw.json`（gitignore）；确认 reg-003/004 由"结构 Recall=0.5"
变为可观察条款排序（MRR/NDCG），reg-001/002 gate 不回归；README 把 ACTIVE
切到 v2.0.2，v2.0.1 记历史。

**Blocked by:** 01

**Status:** resolved

- [ ] triage 重跑并回写 hard 标记（query 集合不变）
- [ ] baseline-v2.0.2.json 提交；status/gate 检查通过
- [ ] reg-003/004 指标语义说明写入报告/README（排序 vs 覆盖）
- [ ] README 双表更新（v2.0.2 ACTIVE / v2.0.1 historical）

## Comments

## Answer

已跑通并提交（2026-09-10，真实栈）：

命令：`python -m tests.evaluation.runners.retrieval_eval live --dataset
synthetic-personal-kb-v2 --reset --mark-hard --report
reports/baseline-v2.0.2.json --raw reports/triage-v2.0.2.raw.json`

- `experiment=v2.0.2-instrumentation-baseline`，status PASS；
  dataset_revision=v2.0.2-instrumentation。
- overall：doc MRR@5 0.9207；page MRR@5 0.8373；chunk MRR@5 0.8373 /
  NDCG@5 0.8061 / Recall@5 0.85 / Recall@10 0.91。
- hard 分桶（10 条）：chunk MRR 0.5867 / NDCG 0.4974 / Recall@5 0.6167；
  easy 分桶（40 条）：0.9 / 0.8832 / 0.9083。本轮 triage 回写
  hard=10、easy-under-construction=6（query 集合未变）。
- 测量修复验证：reg-003 Recall@5 1.0（gap 0.0103，排序可测）；
  reg-004 暴露真实排序失败（Recall@5 0.0，gap −0.1039，干扰项排在目标条款前）。
  reg-001/002 gate PASS。
- `baseline-v2.0.2.json` 提交为 ACTIVE；v2.0.1 转历史；README 双表更新；
  `triage-v2.0.2.raw.json` 保持 gitignore。
- runner 报告新增 `dataset_revision` 字段；experiment 名由 revision 驱动。

验收清单满足。下一步 V2.0.2-03 answer-level 重跑与评分沿用。
