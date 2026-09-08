# 06: Triage run + baseline-v2.0.1

**What to build:** 用 **V2.0 冻结 dense retriever（代码/embedding/config 不变）**
摄取 synthetic-personal-kb-v2 并对 50 条 candidate 跑 triage：per-case
MRR@5/chunk NDCG@5；`hard: true` 写回满足 `MRR@5<1.0 或 NDCG@5<0.95` 的 case；
产出受控 `reports/baseline-v2.0.1.json`（overall + easy/hard split + 每类指标
+ reg 门禁 + answer-level 状态），README 双表（v2.0 历史 / v2.0.1 ACTIVE）。

**Blocked by:** 04（校验器）、05（multi-doc 泛化）

**Status:** open

- [ ] triage raw 输出（*.raw.json）gitignore，hard 标记回写并提交
- [ ] baseline-v2.0.1.json 结构与 spec 一致（dataset v2 标注）
- [ ] hard subset ≥15 且均有实测依据；easy-under-hard-construction 保留不标 hard
- [ ] reg-001/002 在 v2 语料上继续 PASS（若语料改版导致语义变化需显式说明）
- [ ] README 双表 + ACTIVE baseline 标注

## Comments
