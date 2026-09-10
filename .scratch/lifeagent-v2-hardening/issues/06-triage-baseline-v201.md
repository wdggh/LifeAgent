# 06: Triage run + baseline-v2.0.1

**What to build:** 用 **V2.0 冻结 dense retriever（代码/embedding/config 不变）**
摄取 synthetic-personal-kb-v2 并对 50 条 candidate 跑 triage：per-case
MRR@5/chunk NDCG@5；`hard: true` 写回满足 `MRR@5<1.0 或 NDCG@5<0.95` 的 case；
产出受控 `reports/baseline-v2.0.1.json`（overall + easy/hard split + 每类指标
+ reg 门禁 + answer-level 状态），README 双表（v2.0 历史 / v2.0.1 ACTIVE）。

**Blocked by:** 04（校验器）、05（multi-doc 泛化）

**Status:** resolved

- [ ] triage raw 输出（*.raw.json）gitignore，hard 标记回写并提交
- [ ] baseline-v2.0.1.json 结构与 spec 一致（dataset v2 标注）
- [ ] hard 候选 ≥15（16）且 hard 标记由实测产生（11 hard / 5 easy-under-hard-construction，不做人为制造失败）
- [ ] reg-001/002 在 v2 语料上继续 PASS（若语料改版导致语义变化需显式说明）
- [ ] README 双表 + ACTIVE baseline 标注

## Comments

## Answer

已跑通并提交（2026-09-10，真实栈：PostgreSQL + Chroma + DashScope
text-embedding-v3:1024）：

命令：`python -m tests.evaluation.runners.retrieval_eval live --dataset
synthetic-personal-kb-v2 --reset --mark-hard --report
reports/baseline-v2.0.1.json`

- 结果：`status=PASS`（gate = reg-001/002 chunk Recall@5=1；reg-003/004 为新增
  clause_specific hard 候选，不参与 gate，报告 gate=false 且如实记录
  Recall@5=0.5 与 near-tie gap）。
- overall：document MRR@5 0.9167；page MRR@5 0.8873；chunk MRR@5 0.8873 /
  NDCG@5 0.8432 / Recall@5 0.8933 —— 相较 v2.0（全 1.0）已具备区分度。
- hard 分桶（11 条）：chunk MRR@5 0.7303 / NDCG@5 0.5883 / Recall@5 0.6667；
  easy 分桶（39 条）：0.9316 / 0.9150 / 0.9573。
- triage：16 个 hard_candidate → 11 条满足 `MRR@5<1.0 或 chunk NDCG@5<0.95`
  回写 `hard: true`；其余 5 条记为 easy-under-hard-construction（`hard:false`，
  遵守"不人为制造失败"原则）。回写由 runner 的 `mark_hard_flags` 执行，
  报告 difficulty 分桶与回写标签使用同一双门槛（candidate + 实测）。
- 报告 `reports/baseline-v2.0.1.json`（ACTIVE baseline）与回写后的
  `queries.jsonl` 已提交；per-case triage 原始输出 `triage-v2.raw.json`
  保持 gitignore。
- README 双表：v2.0（historical, v1 dataset）与 v2.0.1（ACTIVE, v2 dataset）
  + hard/easy 分桶；V2.1 起所有对比以 v2.0.1 为基线。

验收清单满足。下一步 V2.0.1-07 Answer-level 12 条人工审查。
