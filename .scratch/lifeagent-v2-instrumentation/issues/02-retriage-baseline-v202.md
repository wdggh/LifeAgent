# 02: 重跑 triage，发布 baseline-v2.0.2（ACTIVE）

**What to build:** 用冻结的 V2.0 dense retriever 在修订后的 v2 corpus 上重跑
live triage（--mark-hard），产出 `baseline-v2.0.2.json` 与
`triage-v2.0.2.raw.json`（gitignore）；确认 reg-003/004 由"结构 Recall=0.5"
变为可观察条款排序（MRR/NDCG），reg-001/002 gate 不回归；README 把 ACTIVE
切到 v2.0.2，v2.0.1 记历史。

**Blocked by:** 01

**Status:** claimed

- [ ] triage 重跑并回写 hard 标记（query 集合不变）
- [ ] baseline-v2.0.2.json 提交；status/gate 检查通过
- [ ] reg-003/004 指标语义说明写入报告/README（排序 vs 覆盖）
- [ ] README 双表更新（v2.0.2 ACTIVE / v2.0.1 historical）

## Comments
